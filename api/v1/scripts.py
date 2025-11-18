from fastapi import APIRouter, Query, Depends, HTTPException
from core.database import s3_table, db
from core.s3 import create_presigned_url
from core.security import get_current_user_id
from api.v1.schemas import ScriptsResponse, ScriptEntry

router = APIRouter(
    prefix="/scripts",
    tags=["Scripts"]
)


def load_s3_files_list():
    try:
        lst = s3_table.all()
        if isinstance(lst, list):
            return lst
    except Exception:
        pass
    return db.storage.read().get("s3_files", [])


def make_object_key(file_info):
    key = file_info["user_id"]
    if file_info.get("script_name"):
        key += f'/{file_info["script_name"]}'
    key += f'/{file_info["file_name"]}'
    return key


@router.get("/contents", 
    summary="스크립트 목록 조회 및 선택적 presigned URL 포함",
    response_model=ScriptsResponse,
    responses={
        200: {
            "description": "스크립트 목록 조회 성공",
            "model": ScriptsResponse
        },
        403: {
            "description": "접근 권한 없음 (다른 사용자의 스크립트)",
            "content": {
                "application/json": {
                    "example": {"detail": "다른 유저의 스크립트는 조회할 수 없습니다."}
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
def get_script_contents(
    user_id_query: str = Query(None, description="파일 소유자(예: base_audio 또는 특정 유저)"),
    script_name: str = Query(None, description="script_name으로 필터(선택)"),
    include_presigned: bool = Query(False, description="각 항목에 presigned URL 포함 여부"),
    limit: int = Query(500, ge=1, le=2000, description="최대 반환 개수(DoS 방지)") ,
    user_id: str = Depends(get_current_user_id)
) -> ScriptsResponse:
    """
    `s3_files`에서 스크립트 텍스트들을 조회합니다.
    - `user_id_query`가 주어지면 해당 소유자의 항목만 조회합니다.
      (단, `base_audio`는 누구나 조회 가능하며, 다른 유저의 항목은 본인만 조회 가능)
    - `script_name`이 주어지면 정확 매칭으로 필터합니다.
    - `include_presigned=True`이면 각 항목에 presigned URL을 추가합니다.
    """
    # Load s3 file list and perform in-Python filtering (robust for current db.json shape)
    if user_id_query is not None and user_id_query != "base_audio" and user_id_query != user_id:
        raise HTTPException(status_code=403, detail="다른 유저의 스크립트는 조회할 수 없습니다.")

    s3_files = load_s3_files_list()
    if user_id_query:
        filtered = [f for f in s3_files if f.get("user_id") == user_id_query]
    else:
        filtered = [f for f in s3_files if f.get("user_id") == "base_audio" or f.get("user_id") == user_id]
    if script_name is not None:
        filtered = [f for f in filtered if f.get("script_name", "") == script_name]
    if not filtered:
        return ScriptsResponse(results=[], count=0)
    filtered = filtered[:limit]

    results = []
    for info in filtered:
        obj_key = make_object_key(info)
        # permission: base_audio or owner
        if not obj_key.startswith("base_audio/") and not obj_key.startswith(f"{user_id}/"):
            continue
        entry = ScriptEntry(
            user_id=info.get('user_id'),
            script_name=info.get('script_name', ''),
            file_name=info.get('file_name'),
            object_key=obj_key,
            script=info.get('script')
        )
        if include_presigned:
            # protect against huge presigned generation: cap per-request
            if len(results) >= 500:
                break
            entry.presigned_url = create_presigned_url(obj_key, 300)
        results.append(entry)

    return ScriptsResponse(results=results, count=len(results))
