from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
from io import BytesIO
import os
import requests
from pydub import AudioSegment
import boto3
from botocore.exceptions import ClientError

from core.security import get_current_user_id
from core.database import users_table, UserQuery
from core.config import SUPERTONE_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_REGION
from core.s3 import create_presigned_url
from api.v1.schemas import VoiceCloneResponse

router = APIRouter(
    prefix="/voice",
    tags=["Voice - 보이스 클로닝"]
)


def detect_leading_silence(audio: AudioSegment, silence_threshold: int = -40, chunk_duration: int = 100) -> int:
    """
    오디오의 시작 부분에서 침묵 구간을 감지하고 지속 시간(ms)을 반환합니다.
    
    Args:
        audio: 분석할 AudioSegment
        silence_threshold: 침묵 판정 기준 (dB, 기본값 -40dB)
        chunk_duration: 분석 단위 (ms, 기본값 100ms)
    
    Returns:
        제거할 시작 침묵의 지속 시간 (ms)
    """
    silence_duration = 0
    chunk_size = int(audio.frame_rate * chunk_duration / 1000)  # chunk_duration을 샘플 수로 변환
    
    for chunk in audio[::chunk_duration]:
        if chunk.dBFS < silence_threshold:
            silence_duration += chunk_duration
        else:
            break
    
    return silence_duration


def adjust_gain_to_target(audio: AudioSegment, target_dBFS: float = -12.0, max_change_db: float = 20.0) -> AudioSegment:
    """
    오디오의 dBFS를 목표값(target_dBFS)으로 맞춥니다. 필요시 증폭(또는 감쇠)을 적용합니다.

    - target_dBFS: 목표 RMS/레벨(예: -12.0 dBFS)
    - max_change_db: 한 번에 적용 가능한 최대 증폭/감쇠(dB)
    """
    try:
        current_dbfs = audio.dBFS
    except Exception:
        return audio

    if current_dbfs is None:
        return audio

    change_db = target_dBFS - current_dbfs
    # 변경량을 제한
    if change_db > 0:
        change_db = min(change_db, max_change_db)
    else:
        change_db = max(change_db, -max_change_db)

    # 만약 변화가 거의 없다면 원본 반환
    if abs(change_db) < 0.1:
        return audio

    return audio.apply_gain(change_db)



@router.post("/clone", summary="음성 3개 합쳐서 보이스 클로닝 요청", response_model=VoiceCloneResponse,
             responses={
                 200: {"description": "voice_id 및 예제 오디오 정보 반환"},
                 400: {"description": "잘못된 요청(파일 형식/크기 등)"},
                 413: {"description": "생성된 오디오가 너무 큼"},
                 502: {"description": "외부 API 호출 또는 S3 업로드 실패"}
             })
async def clone_voice(
    files: List[UploadFile] = File(..., description="3개의 음성 파일을 업로드하세요 (wav/mp3 등)."),
    user_id: str = Depends(get_current_user_id)
):
    """
    웹에서 업로드된 3개의 음성 파일을 받아 각 합친 후
    Supertone API에 동기 요청을 보내 목소리 클로닝을 수행합니다.

    반환된 `voice_id`는 `users` 테이블의 해당 사용자 레코드에 저장됩니다.
    "안녕하세요. 이제 저와 함께, 열심히 발표 연습을 해보실까요?"라는 예제 문장을 TTS로 생성하여
    S3에 업로드하고, 해당 오디오의 presigned URL을 함께 반환합니다.
    """
    # 설정 확인
    api_key = SUPERTONE_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="Supertone API key가 설정되어 있지 않습니다.")

    if not files or len(files) != 3:
        raise HTTPException(status_code=400, detail="정확히 3개의 음성 파일을 업로드해야 합니다.")

    segments = []
    max_individual = 3 * 1024 * 1024  # 각 업로드 파일 최대 3MB
    for f in files:
        contents = await f.read()

        # 파일 크기 검사
        if len(contents) > max_individual:
            raise HTTPException(status_code=400, detail="각 파일은 3MB 이하의 WAV 또는 MP3이어야 합니다.")

        bio = BytesIO(contents)
        # 포맷 추정 (확장자 기반), 허용 형식은 wav/mp3
        ext = (f.filename or '').rsplit('.', 1)[-1].lower() if f.filename else 'wav'
        if ext not in ('wav', 'wave', 'mp3'):
            raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다. WAV 또는 MP3만 허용됩니다.")

        fmt = 'wav' if ext in ('wav', 'wave') else 'mp3'
        try:
            seg = AudioSegment.from_file(bio, format=fmt)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"파일 형식 처리 실패: {e}")

        # 시작 무음(침묵) 제거
        leading_silence_duration = detect_leading_silence(seg, silence_threshold=-40, chunk_duration=100)
        seg = seg[leading_silence_duration:]

        # 볼륨이 작은 경우 목표 dBFS로 증폭(또는 너무 큰 경우 감쇠)
        seg = adjust_gain_to_target(seg, target_dBFS=-12.0, max_change_db=20.0)

        segments.append(seg)

    silence = AudioSegment.silent(duration=100)  # 0.1 seconds
    merged = segments[0] + silence + segments[1] + silence + segments[2]

    out_bio = BytesIO()
    # 기본은 WAV로 내보내되, 너무 크면 MP3로 압축/샘플레이트를 낮추는 시도 수행
    merged.export(out_bio, format='wav')
    out_bio.seek(0)

    payload_bytes = out_bio.getvalue()
    max_size = 3 * 1024 * 1024  # Supertone 제한에 맞춰 3MB 상한

    files_payload = None
    # 페이로드가 크게 나오면 압축 시도
    if len(payload_bytes) > max_size:
        compressed_bio = None
        # 시도 순서: 샘플레이트 낮추기 -> 여러 비트레이트로 mp3 내보내기
        for rate in (22050, 16000, 12000):
            candidate = merged.set_frame_rate(rate).set_channels(1)
            for bitrate in ("64k", "48k", "32k"):
                bio = BytesIO()
                try:
                    candidate.export(bio, format='mp3', bitrate=bitrate)
                except Exception:
                    # 일부 포맷/옵션에서 실패할 수 있으므로 무시하고 다음 시도
                    continue
                bio.seek(0)
                if len(bio.getvalue()) <= max_size:
                    compressed_bio = bio
                    break
            if compressed_bio:
                break

        if compressed_bio:
            files_payload = {'files': ('merged.mp3', compressed_bio, 'audio/mpeg')}
        else:
            # 마지막 수단: 길이 제한(예: 첫 30초)로 잘라서 시도
            trimmed = merged[:30 * 1000]
            trimmed_bio = BytesIO()
            trimmed.export(trimmed_bio, format='wav')
            trimmed_bio.seek(0)
            if len(trimmed_bio.getvalue()) > max_size:
                raise HTTPException(status_code=413, detail="생성된 오디오가 너무 큽니다. 업로드할 파일 크기를 줄여주세요.")
            files_payload = {'files': ('merged.wav', trimmed_bio, 'audio/wav')}
    else:
        files_payload = {'files': ('merged.wav', out_bio, 'audio/wav')}

    # Supertone API 호출
    url = "https://supertoneapi.com/v1/custom-voices/cloned-voice"
    headers = {"x-sup-api-key": api_key}
    data = {'name': user_id}

    try:
        resp = requests.post(url, headers=headers, data=data, files=files_payload, timeout=60)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Supertone API 호출 실패: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Supertone API 오류 ({resp.status_code}): {resp.text}")

    try:
        j = resp.json()
        voice_id = j.get('voice_id')
    except Exception:
        raise HTTPException(status_code=502, detail="Supertone API 응답 처리 실패")

    if not voice_id:
        raise HTTPException(status_code=502, detail="Supertone가 voice_id를 반환하지 않았습니다.")

    # users 테이블에 voice_id 저장
    if not users_table.search(UserQuery.id == user_id):
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    users_table.update({'voice_id': voice_id}, UserQuery.id == user_id)

    # TTS 음성 생성
    tts_text = "안녕하세요. 이제 저와 함께, 열심히 발표 연습을 해보실까요?"
    
    # Supertone TTS API 호출
    tts_url = f"https://supertoneapi.com/v1/text-to-speech/{voice_id}?output_format=wav"
    headers = {
        "x-sup-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": tts_text,
        "language": "ko",
        "style": "neutral",
        "model": "sona_speech_1",
        "voice_settings": {
            "pitch_shift": 0,
            "pitch_variance": 1,
            "speed": 1
        }
    }
    
    try:
        tts_resp = requests.post(tts_url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Supertone TTS API 호출 실패: {e}")
    
    if tts_resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Supertone TTS API 오류 ({tts_resp.status_code}): {tts_resp.text}")
    
    # S3에 업로드
    object_key = f"{user_id}/example.wav"
    audio_data = tts_resp.content
    
    try:
        s3_client = boto3.client(
            's3',
            region_name=S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=audio_data,
            ContentType='audio/wav'
        )
    except ClientError as e:
        raise HTTPException(status_code=502, detail=f"S3 업로드 실패: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"S3 업로드 중 예기치 못한 오류: {e}")
    
    # Presigned URL 생성
    presigned_url = create_presigned_url(object_key, expiration=3600)  # 1시간 유효
    if not presigned_url:
        raise HTTPException(status_code=502, detail="Presigned URL 생성 실패")
    
    return {
        "voice_id": voice_id,
        "example_audio": {
            "object_key": object_key,
            "presigned_url": presigned_url,
            "audio_length": tts_resp.headers.get("X-Audio-Length", "unknown")
        }
    }
