from pydantic import BaseModel, Field
from typing import Optional, List


class ScriptEntry(BaseModel):
    """스크립트 항목 (단일 파일 메타데이터)"""
    user_id: str = Field(
        ...,
        title="파일 소유자 ID",
        description="파일을 소유한 사용자 ID (예: 'base_audio', 'user123')",
        example="base_audio"
    )
    script_name: Optional[str] = Field(
        default="",
        title="스크립트",
        description="스크립트 이름",
        example="intro"
    )
    file_name: str = Field(
        ...,
        title="파일명",
        description="S3 에 저장된 실제 파일명",
        example="basic_audio_1.wav"
    )
    object_key: str = Field(
        ...,
        title="S3 객체 경로",
        description="S3 내 전체 경로 (user_id/script_name/file_name 형식)",
        example="base_audio/intro/basic_audio_1.wav"
    )
    script: Optional[str] = Field(
        default=None,
        title="스크립트 텍스트",
        description="실제 발표/음성 대본 텍스트",
        example="안녕하십니까. 지금부터 발표를 시작하겠습니다."
    )
    presigned_url: Optional[str] = Field(
        default=None,
        title="Presigned URL",
        description="S3 임시 접근 URL (include_presigned=true일 때만 포함)",
        example="https://your-bucket.s3.amazonaws.com/base_audio/intro/basic_audio_1.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&..."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "base_audio",
                "script_name": "intro",
                "file_name": "basic_audio_1.wav",
                "object_key": "base_audio/intro/basic_audio_1.wav",
                "script": "안녕하십니까. 지금부터 발표를 시작하겠습니다.",
                "presigned_url": "https://your-bucket.s3.amazonaws.com/..."
            }
        }


class ScriptsResponse(BaseModel):
    """스크립트 목록 조회 응답"""
    results: List[ScriptEntry] = Field(
        ...,
        title="스크립트 항목 배열",
        description="조건에 일치하는 모든 스크립트 항목"
    )
    count: int = Field(
        ...,
        title="반환된 항목 개수",
        description="results 배열의 길이",
        example=1
    )

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "user_id": "base_audio",
                        "script_name": "intro",
                        "file_name": "basic_audio_1.wav",
                        "object_key": "base_audio/intro/basic_audio_1.wav",
                        "script": "안녕하십니까. 지금부터 발표를 시작하겠습니다.",
                        "presigned_url": "https://your-bucket.s3.amazonaws.com/..."
                    }
                ],
                "count": 1
            }
        }


class PresignedResponse(BaseModel):
    """Presigned URL 발급 응답"""
    presigned_url: str = Field(
        ...,
        title="S3 Presigned URL",
        description="S3 객체에 임시 접근할 수 있는 URL (expires_in 만료 시간까지만 유효)",
        example="https://your-bucket.s3.amazonaws.com/base_audio/intro/basic_audio_1.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&..."
    )
    object_key: str = Field(
        ...,
        title="S3 객체 경로",
        description="S3 내 전체 경로",
        example="base_audio/intro/basic_audio_1.wav"
    )
    file_name: str = Field(
        ...,
        title="파일명",
        description="요청한 파일명",
        example="basic_audio_1.wav"
    )
    script: Optional[str] = Field(
        default=None,
        title="스크립트 텍스트",
        description="DB에 저장된 스크립트 텍스트 (있으면 포함, 없으면 생략)",
        example="안녕하십니까. 지금부터 발표를 시작하겠습니다."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "presigned_url": "https://your-bucket.s3.amazonaws.com/base_audio/intro/basic_audio_1.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIOSFODNN7EXAMPLE%2F20251115%2Fap-northeast-2%2Fs3%2Faws4_request&X-Amz-Date=20251115T120000Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=...",
                "object_key": "base_audio/intro/basic_audio_1.wav",
                "file_name": "basic_audio_1.wav",
                "script": "안녕하십니까. 지금부터 발표를 시작하겠습니다."
            }
        }


class TokenResponse(BaseModel):
    """JWT 토큰 응답"""
    access: str = Field(
        ...,
        title="Access Token",
        description="API 요청에 사용할 JWT Access Token (기본 유효 시간: 30분)"
    )


class LoginResponse(BaseModel):
    """로그인 응답"""
    message: str = Field(
        ...,
        example="Login success"
    )
    token: dict = Field(
        ...,
        title="토큰 정보",
        description="Access Token과 Refresh Token 포함",
        example={
            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    )


class VoiceExampleAudio(BaseModel):
    """클로닝 후 생성된 예시 오디오 정보"""
    object_key: str = Field(..., title="S3 객체 경로", example="user123/example.wav")
    presigned_url: str = Field(..., title="Presigned URL", example="https://...")
    audio_length: str = Field(..., title="오디오 길이(초)", example="3.42")


class VoiceCloneResponse(BaseModel):
    """보이스 클로닝 응답"""
    voice_id: str = Field(..., title="생성된 voice_id", example="91992bbd4758bdcf9c9b01")
    example_audio: VoiceExampleAudio = Field(..., title="예제 TTS 오디오 정보")

    class Config:
        json_schema_extra = {
            "example": {
                "voice_id": "91992bbd4758bdcf9c9b01",
                "example_audio": {
                    "object_key": "user123/example.wav",
                    "presigned_url": "https://s3.amazonaws.com/sfitz-storage/user123/example.wav?X-Amz-...",
                    "audio_length": "3.42"
                }
            }
        }
