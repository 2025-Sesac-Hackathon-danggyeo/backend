from fastapi import APIRouter, Query, HTTPException, Depends
from core.s3 import create_presigned_url
from core.security import get_current_user_id
from core.database import s3_table, db
from api.v1.schemas import PresignedResponse

router = APIRouter(
    prefix="/files",
    tags=["Files - S3 파일"]
)

# S3 파일 메타데이터 전체 리스트(TinyDB에서 s3_files 테이블 전체 가져옴)
def load_s3_files_list():
    # Support both TinyDB table structure and legacy raw list in db.json
    try:
        # s3_table.all() works when TinyDB stored table format is used
        lst = s3_table.all()
        # If underlying storage was migrated to a plain list, ensure it's a list
        if isinstance(lst, list):
            return lst
    except Exception:
        pass
    # Fallback: read raw JSON key (works with current db.json shape)
    return db.storage.read().get("s3_files", [])

# Object key 생성 유틸 함수 (script_name 있으면 경로에 포함)
def make_object_key(file_info):
    key = file_info["user_id"]
    if file_info.get("script_name"):
        key += f'/{file_info["script_name"]}'
    key += f'/{file_info["file_name"]}'
    return key

@router.get("/presigned-url", 
    summary="S3 Presigned URL 발급 및 메타데이터 반환", 
    response_model=PresignedResponse,
    responses={
        200: {
            "description": "Presigned URL 발급 성공",
            "model": PresignedResponse
        },
        400: {
            "description": "Presigned URL 생성 실패",
            "content": {
                "application/json": {
                    "example": {"detail": "Presigned URL 발급에 실패했습니다. AWS 설정 확인 필요"}
                }
            }
        },
        403: {
            "description": "접근 권한 없음",
            "content": {
                "application/json": {
                    "example": {"detail": "본인 소유 파일만 접근 가능합니다."}
                }
            }
        },
        404: {
            "description": "파일 미발견",
            "content": {
                "application/json": {
                    "example": {"detail": "해당 파일이 DB에 없습니다."}
                }
            }
        },
        401: {
            "description": "인증되지 않은 요청",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    }
)
def get_presigned_url(
    file_name: str = Query(..., description="S3 파일명(ex: basic_audio_1.wav)"),
    user_id_query: str = Query(None, description="파일 소유자(공용 파일은 base_audio)"),
    script_name: str = Query(None, description="script_name이 있으면 지정(선택)"),
    expires_in: int = Query(300, description="presigned url 유효 시간(초). 기본 300초"),
    user_id: str = Depends(get_current_user_id)  # JWT 인증
):
    """
    주어진 파일명에 대응하는 S3 객체의 presigned URL과 메타데이터를 반환합니다.

    동작 요약:
    - `file_name`으로 DB에서 항목을 검색합니다. 필요시 `user_id_query`와 `script_name`을 추가로 지정할 수 있습니다.
    - 권한 검사: `base_audio`(공용)는 누구나 접근 가능. 그 외 항목은 현재 인증된 사용자 본인만 접근 가능합니다.
    - presigned URL 발급에 실패하면 400, 항목 미발견시 404, 권한 없으면 403을 반환합니다.

    파라미터 예시:
    - `file_name=basic_audio_1.wav`
    - `user_id_query=base_audio` (공용 파일 조회)
    - `script_name=` (스크립트 그룹이 있을 경우 지정)

    반환 필드:
    - `presigned_url`: S3 presigned GET URL
    - `object_key`: S3 객체 키(예: base_audio/basic_audio_1.wav)
    - `file_name`: 요청한 파일명
    - `script`(선택): DB에 저장된 스크립트 텍스트(존재하는 경우)
    """
    # Load list and perform in-Python filtering to be robust against DB shape
    s3_files = load_s3_files_list()
    match = None
    for info in s3_files:
        if info.get("file_name") != file_name:
            continue
        if user_id_query and info.get("user_id") != user_id_query:
            continue
        if script_name is not None and info.get("script_name", "") != script_name:
            continue
        match = info
        break
    if match is None:
        raise HTTPException(status_code=404, detail="해당 파일이 DB에 없습니다.")
    # object key/composite key 생성
    object_key = make_object_key(match)
    # 권한 정책: base_audio/는 모두 허용, 그 외에는 본인만
    if object_key.startswith("base_audio/"):
        pass
    elif not object_key.startswith(f"{user_id}/"):
        raise HTTPException(status_code=403, detail="본인 소유 파일만 접근 가능합니다.")
    url = create_presigned_url(object_key, expires_in)
    if url is None:
        raise HTTPException(status_code=400, detail="Presigned URL 발급에 실패했습니다. AWS 설정 확인 필요")
    resp = {"presigned_url": url}
    if match.get("script"):
        resp["script"] = match["script"]
    resp["object_key"] = object_key
    resp["file_name"] = match["file_name"]
    return resp
