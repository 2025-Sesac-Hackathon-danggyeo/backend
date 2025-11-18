"""
발표 대본 관리 API
- 발표 대본 업로드 및 메타데이터 관리
- 슬라이드 대본 업로드 및 처리
- 문장 데이터 조회 및 클론 준비
"""

import uuid
from datetime import datetime
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from core.database import db, scripts_table, slides_table, sentences_table, practice_scores_table
from core.security import get_current_user_id
from core.script_processor import ScriptProcessor
from models.script import (
    UploadScriptRequest, UploadSlideRequest, UploadSlideResponse,
    ScriptMetadata, SlideData, SentenceData, SentencesListResponse,
    ScriptSummaryResponse, SlideStatus
)

router = APIRouter(
    prefix="/scripts",
    tags=["Scripts"],
    dependencies=[Depends(get_current_user_id)]
)


def _serialize_datetime(obj):
    """datetime을 ISO 형식 문자열로 변환"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def get_script_by_id(script_id: str, user_id: str) -> dict:
    """스크립트 조회 (권한 확인)"""
    from tinydb import Query as TinyQuery
    Q = TinyQuery()
    script = scripts_table.get(Q.script_id == script_id)
    
    if not script:
        raise HTTPException(status_code=404, detail="스크립트를 찾을 수 없습니다.")
    
    if script['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
    
    return script


def get_slide_by_id(slide_id: str, user_id: str) -> dict:
    """슬라이드 조회 (권한 확인)"""
    from tinydb import Query as TinyQuery
    Q = TinyQuery()
    slide = slides_table.get(Q.slide_id == slide_id)
    
    if not slide:
        raise HTTPException(status_code=404, detail="슬라이드를 찾을 수 없습니다.")
    
    # 슬라이드가 속한 스크립트의 권한 확인
    script = get_script_by_id(slide['script_id'], user_id)
    return slide


@router.post(
    "",
    response_model=ScriptMetadata,
    summary="새 발표 대본 생성",
    responses={
        200: {
            "description": "발표 대본 생성 성공",
            "model": ScriptMetadata
        }
    }
)
def create_script(
    request: UploadScriptRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    새로운 발표 대본을 생성합니다.
    
    **요청 바디:**
    - `script_name`: 발표 제목 (필수)
    - `description`: 발표 설명 (선택)
    - `total_slides`: 예상 슬라이드 개수 (선택)
    
    **응답:**
    생성된 스크립트 메타데이터 및 고유 `script_id` 포함
    """
    script_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    script_data = {
        "script_id": script_id,
        "user_id": user_id,
        "script_name": request.script_name,
        "description": request.description or "",
        "total_slides": request.total_slides or 0,
        "created_at": _serialize_datetime(now),
        "updated_at": _serialize_datetime(now)
    }
    
    scripts_table.insert(script_data)
    
    return {
        "script_id": script_id,
        "user_id": user_id,
        "script_name": request.script_name,
        "total_slides": request.total_slides or 0,
        "description": request.description,
        "created_at": now,
        "updated_at": now
    }


@router.patch(
    "/{script_id}/slide/{slide_number}",
    response_model=UploadSlideResponse,
    summary="슬라이드 대본 업로드 및 처리",
    responses={
        200: {
            "description": "슬라이드 업로드 및 처리 성공",
            "model": UploadSlideResponse
        },
        404: {
            "description": "스크립트를 찾을 수 없음"
        }
    }
)
def upload_slide(
    script_id: str,
    slide_number: int,
    request: UploadSlideRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    슬라이드 대본을 업로드하고 자동으로 처리합니다.
    
    **처리 과정:**
    1. 마침표 기준으로 문장 분할
    2. 읽기에 적당한 길이로 청크화
    3. 각 청크를 개별 문장 데이터로 데이터베이스 저장
    
    **경로 매개변수:**
    - `script_id`: 상위 스크립트 ID
    - `slide_number`: 슬라이드 순서 (1부터 시작)
    
    **요청 바디:**
    - `script_text`: 해당 슬라이드의 전체 대본 텍스트
    
    **응답:**
    처리된 슬라이드 정보 및 생성된 문장 데이터 포함
    """
    # 권한 확인
    script = get_script_by_id(script_id, user_id)
    
    # 슬라이드 생성
    slide_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    slide_data = {
        "slide_id": slide_id,
        "script_id": script_id,
        "slide_number": slide_number,
        "status": SlideStatus.PROCESSING,
        "created_at": _serialize_datetime(now),
        "updated_at": _serialize_datetime(now)
    }
    slides_table.insert(slide_data)
    
    # 대본 처리
    processor = ScriptProcessor()
    processed_chunks = processor.process_slide_script(request.script_text)
    
    # 문장 데이터 생성
    sentence_list = []
    for idx, (chunk_text, duration, original_indices) in enumerate(processed_chunks, 1):
        sentence_id = str(uuid.uuid4())
        
        sentence_data = {
            "sentence_id": sentence_id,
            "slide_id": slide_id,
            "script_id": script_id,
            "sentence_number": idx,
            "text": chunk_text,
            "original_sentence_indices": original_indices,
            "duration_estimate": duration,
            "created_at": _serialize_datetime(now)
        }
        sentences_table.insert(sentence_data)
        
        sentence_list.append({
            "sentence_id": sentence_id,
            "slide_id": slide_id,
            "sentence_number": idx,
            "text": chunk_text,
            "original_sentence_indices": original_indices,
            "duration_estimate": duration,
            "created_at": now
        })
    
    # 슬라이드 상태 업데이트
    from tinydb import Query as TinyQuery
    Q = TinyQuery()
    slides_table.update(
        {"status": SlideStatus.COMPLETED, "updated_at": _serialize_datetime(datetime.utcnow())},
        Q.slide_id == slide_id
    )
    
    # 스크립트의 total_slides 업데이트 (필요시)
    if slide_number > script.get('total_slides', 0):
        scripts_table.update(
            {"total_slides": slide_number, "updated_at": _serialize_datetime(datetime.utcnow())},
            Q.script_id == script_id
        )
    
    return {
        "slide_id": slide_id,
        "script_id": script_id,
        "slide_number": slide_number,
        "status": SlideStatus.COMPLETED,
        "sentence_count": len(sentence_list),
        "sentences": sentence_list
    }


@router.get(
    "/{script_id}",
    response_model=ScriptSummaryResponse,
    summary="스크립트 요약 정보 조회",
    responses={
        200: {
            "description": "스크립트 정보 조회 성공",
            "model": ScriptSummaryResponse
        },
        404: {
            "description": "스크립트를 찾을 수 없음"
        }
    }
)
def get_script_info(
    script_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """스크립트의 기본 정보와 생성된 문장 개수를 조회합니다."""
    script = get_script_by_id(script_id, user_id)
    
    from tinydb import Query as TinyQuery
    Q = TinyQuery()
    sentence_count = sentences_table.search(Q.script_id == script_id).__len__()
    
    created_at = script['created_at']
    updated_at = script['updated_at']
    
    # ISO 문자열을 datetime으로 변환
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at)
    
    return {
        "script_id": script_id,
        "script_name": script['script_name'],
        "user_id": script['user_id'],
        "total_slides": script.get('total_slides', 0),
        "sentence_count": sentence_count,
        "created_at": created_at,
        "updated_at": updated_at
    }


@router.get(
    "/{script_id}/sentences",
    response_model=SentencesListResponse,
    summary="스크립트 문장 데이터 조회 (클론 준비)",
    responses={
        200: {
            "description": "문장 데이터 조회 성공",
            "model": SentencesListResponse
        },
        404: {
            "description": "스크립트를 찾을 수 없음"
        }
    }
)
def get_sentences(
    script_id: str,
    slide_id: Optional[str] = Query(None, description="특정 슬라이드만 조회 (선택)"),
    user_id: str = Depends(get_current_user_id)
):
    """
    스크립트의 모든 문장 데이터를 조회합니다.
    
    클론 API를 통해 음성 파일로 변환할 준비가 된 데이터를 반환합니다.
    
    **쿼리 파라미터:**
    - `slide_id`: 특정 슬라이드의 문장만 필터 (선택사항)
    
    **응답:**
    모든 문장 데이터 및 메타데이터 포함
    """
    script = get_script_by_id(script_id, user_id)
    
    from tinydb import Query as TinyQuery
    Q = TinyQuery()
    
    if slide_id:
        # 특정 슬라이드 필터
        get_slide_by_id(slide_id, user_id)
        sentences = sentences_table.search(
            (Q.script_id == script_id) & (Q.slide_id == slide_id)
        )
    else:
        # 전체 스크립트 문장
        sentences = sentences_table.search(Q.script_id == script_id)
    
    # datetime 변환
    sentence_list = []
    for sent in sentences:
        created_at = sent['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        sentence_list.append({
            "sentence_id": sent['sentence_id'],
            "slide_id": sent['slide_id'],
            "sentence_number": sent['sentence_number'],
            "text": sent['text'],
            "original_sentence_indices": sent.get('original_sentence_indices', []),
            "duration_estimate": sent.get('duration_estimate'),
            "created_at": created_at
        })
    
    # 정렬 (슬라이드 > 문장 순서)
    sentence_list.sort(
        key=lambda x: (
            slides_table.get(lambda s: s['slide_id'] == x['slide_id']).get('slide_number', 999) if slides_table.get(lambda s: s['slide_id'] == x['slide_id']) else 999,
            x['sentence_number']
        )
    )
    
    created_at = script['created_at']
    updated_at = script['updated_at']
    
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at)
    
    return {
        "script_id": script_id,
        "script_name": script['script_name'],
        "total_slides": script.get('total_slides', 0),
        "slide_id": slide_id,
        "sentences": sentence_list,
        "total_count": len(sentence_list)
    }


@router.patch(
    "/{script_id}",
    response_model=ScriptMetadata,
    summary="스크립트 메타데이터 수정",
    responses={
        200: {"description": "스크립트 수정 성공", "model": ScriptMetadata},
        404: {"description": "스크립트를 찾을 수 없음"}
    }
)
def update_script(
    script_id: str,
    request: UploadScriptRequest,
    user_id: str = Depends(get_current_user_id)
):
    """스크립트 제목/설명/total_slides 수정"""
    # 권한 및 존재 확인
    script = get_script_by_id(script_id, user_id)

    from tinydb import Query as TinyQuery
    Q = TinyQuery()

    now = datetime.utcnow()
    update_fields = {
        "script_name": request.script_name,
        "description": request.description or script.get('description', ''),
        "total_slides": request.total_slides or script.get('total_slides', 0),
        "updated_at": _serialize_datetime(now)
    }

    scripts_table.update(update_fields, Q.script_id == script_id)

    # 반환용 데이터 구성
    return {
        "script_id": script_id,
        "user_id": script['user_id'],
        "script_name": update_fields['script_name'],
        "total_slides": update_fields['total_slides'],
        "description": update_fields['description'],
        "created_at": datetime.fromisoformat(script['created_at']) if isinstance(script.get('created_at'), str) else script.get('created_at'),
        "updated_at": now
    }


@router.delete(
    "/{script_id}",
    summary="스크립트 삭제",
    responses={
        200: {"description": "삭제 성공", "content": {"application/json": {"example": {"deleted": True}}}},
        404: {"description": "스크립트를 찾을 수 없음"}
    }
)
def delete_script(
    script_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """스크립트 및 관련 슬라이드/문장/점수 모두 삭제(영구삭제)"""
    # 존재 및 권한 확인
    get_script_by_id(script_id, user_id)

    from tinydb import Query as TinyQuery
    Q = TinyQuery()

    # 삭제 수행
    scripts_table.remove(Q.script_id == script_id)
    slides_table.remove(Q.script_id == script_id)
    sentences_table.remove(Q.script_id == script_id)
    # practice_scores_table may contain related entries
    try:
        practice_scores_table.remove(Q.script_id == script_id)
    except Exception:
        pass

    return {"deleted": True, "script_id": script_id}
