"""
연습 점수 관리 API
- 사용자 연습 결과 저장
- 점수 조회 및 통계
- 연습 진행 상태 추적
"""

import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from core.database import (
    db, scripts_table, slides_table, sentences_table, practice_scores_table
)
from core.security import get_current_user_id
from models.script import (
    PracticeScoreRequest, PracticeScoreResponse, PracticeScoreData
)
from tinydb import Query as TinyQuery

router = APIRouter(
    prefix="/practice",
    tags=["Practice - 연습 점수 관리"],
    dependencies=[Depends(get_current_user_id)]
)


def _serialize_datetime(obj):
    """datetime을 ISO 형식 문자열로 변환"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def get_script_by_id(script_id: str, user_id: str, require_owner=False):
    """스크립트 조회"""
    Q = TinyQuery()
    script = scripts_table.get(Q.script_id == script_id)
    
    if not script:
        raise HTTPException(status_code=404, detail="스크립트를 찾을 수 없습니다.")
    
    if require_owner and script['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
    
    return script


def get_sentence_by_id(sentence_id: str) -> dict:
    """문장 조회"""
    Q = TinyQuery()
    sentence = sentences_table.get(Q.sentence_id == sentence_id)
    
    if not sentence:
        raise HTTPException(status_code=404, detail="문장을 찾을 수 없습니다.")
    
    return sentence


@router.post(
    "/scores/{sentence_id}",
    response_model=PracticeScoreResponse,
    summary="연습 점수 저장",
    responses={
        200: {
            "description": "연습 점수 저장 성공",
            "model": PracticeScoreResponse
        },
        404: {
            "description": "문장을 찾을 수 없음"
        }
    }
)
def submit_practice_score(
    sentence_id: str,
    request: PracticeScoreRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    사용자의 연습 점수를 저장합니다.
    
    **경로 매개변수:**
    - `sentence_id`: 평가 대상 문장 ID
    
    **요청 바디:**
    - `accuracy`: 발음 정확도 (0-100, 선택)
    - `fluency`: 유창성 점수 (0-100, 선택)
    - `time_taken`: 소요 시간(초) (선택)
    
    **기능:**
    - 새로운 점수 기록 생성
    - 기존 기록이 있으면 attempts 증가 및 best_score 업데이트
    - 연습 진행 상태 추적
    """
    sentence = get_sentence_by_id(sentence_id)
    
    # 점수 계산 (accuracy, fluency 평균)
    scores = []
    if request.accuracy is not None:
        scores.append(request.accuracy)
    if request.fluency is not None:
        scores.append(request.fluency)
    
    overall_score = sum(scores) / len(scores) if scores else None
    
    now = datetime.utcnow()
    
    Q = TinyQuery()
    
    # 기존 점수 기록 조회
    existing_score = practice_scores_table.get(
        (Q.sentence_id == sentence_id) & (Q.user_id == user_id)
    )
    
    if existing_score:
        # 기존 기록 업데이트 (attempts 증가, best_score 갱신)
        best_score = existing_score.get('best_score')
        
        if overall_score is not None:
            if best_score is None:
                best_score = overall_score
            else:
                best_score = max(best_score, overall_score)
        
        attempts = existing_score.get('attempts', 1) + 1
        
        practice_scores_table.update(
            {
                "attempts": attempts,
                "best_score": best_score,
                "accuracy": request.accuracy or existing_score.get('accuracy'),
                "fluency": request.fluency or existing_score.get('fluency'),
                "time_taken": request.time_taken or existing_score.get('time_taken'),
                "updated_at": _serialize_datetime(now)
            },
            Q.score_id == existing_score['score_id']
        )
        
        score_id = existing_score['score_id']
    else:
        # 새로운 기록 생성
        score_id = str(uuid.uuid4())
        
        score_data = {
            "score_id": score_id,
            "sentence_id": sentence_id,
            "slide_id": sentence['slide_id'],
            "script_id": sentence['script_id'],
            "user_id": user_id,
            "accuracy": request.accuracy,
            "fluency": request.fluency,
            "time_taken": request.time_taken,
            "attempts": 1,
            "best_score": overall_score,
            "created_at": _serialize_datetime(now),
            "updated_at": _serialize_datetime(now)
        }
        
        practice_scores_table.insert(score_data)
    
    # 업데이트된 데이터 조회
    updated_score = practice_scores_table.get(Q.score_id == score_id)
    
    return {
        "score_id": score_id,
        "sentence_id": sentence_id,
        "best_score": updated_score.get('best_score'),
        "attempts": updated_score.get('attempts', 1),
        "created_at": now
    }


@router.get(
    "/scores/{sentence_id}",
    response_model=PracticeScoreData,
    summary="문장 연습 점수 조회",
    responses={
        200: {
            "description": "점수 조회 성공",
            "model": PracticeScoreData
        },
        404: {
            "description": "점수 기록을 찾을 수 없음"
        }
    }
)
def get_practice_score(
    sentence_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    사용자의 특정 문장에 대한 연습 점수를 조회합니다.
    
    **경로 매개변수:**
    - `sentence_id`: 문장 ID
    
    **응답:**
    점수 기록, 시도 횟수, 최고 점수 등 포함
    """
    sentence = get_sentence_by_id(sentence_id)
    
    Q = TinyQuery()
    score = practice_scores_table.get(
        (Q.sentence_id == sentence_id) & (Q.user_id == user_id)
    )
    
    if not score:
        raise HTTPException(status_code=404, detail="점수 기록을 찾을 수 없습니다.")
    
    created_at = score['created_at']
    updated_at = score['updated_at']
    
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at)
    
    return {
        "score_id": score['score_id'],
        "sentence_id": score['sentence_id'],
        "slide_id": score['slide_id'],
        "script_id": score['script_id'],
        "user_id": score['user_id'],
        "accuracy": score.get('accuracy'),
        "fluency": score.get('fluency'),
        "time_taken": score.get('time_taken'),
        "attempts": score.get('attempts', 1),
        "best_score": score.get('best_score'),
        "created_at": created_at,
        "updated_at": updated_at
    }


@router.get(
    "/scripts/{script_id}/stats",
    summary="스크립트 전체 연습 통계",
    responses={
        200: {
            "description": "통계 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "script_id": "uuid",
                        "total_sentences": 10,
                        "attempted_sentences": 8,
                        "completion_rate": 80.0,
                        "average_best_score": 85.5,
                        "total_attempts": 12,
                        "estimated_practice_time": 120.5
                    }
                }
            }
        }
    }
)
def get_script_statistics(
    script_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    스크립트 전체에 대한 사용자의 연습 통계를 조회합니다.
    
    **쿼리 매개변수:**
    - `script_id`: 스크립트 ID
    
    **응답 포함:**
    - 시도한 문장 개수 / 전체 문장 개수
    - 완료율 (%)
    - 평균 최고 점수
    - 총 시도 횟수
    - 예상 연습 시간
    """
    # 스크립트 존재 확인
    get_script_by_id(script_id, user_id)
    
    Q = TinyQuery()

    # 스크립트의 모든 문장
    all_sentences = sentences_table.search(Q.script_id == script_id)
    total_sentences = len(all_sentences)
    
    # 사용자의 점수 기록
    user_scores = practice_scores_table.search(
        (Q.script_id == script_id) & (Q.user_id == user_id)
    )
    
    attempted_sentences = len(set(s['sentence_id'] for s in user_scores))
    completion_rate = (attempted_sentences / total_sentences * 100) if total_sentences > 0 else 0
    
    # 평균 최고 점수
    best_scores = [s.get('best_score') for s in user_scores if s.get('best_score') is not None]
    average_best_score = sum(best_scores) / len(best_scores) if best_scores else None
    
    # 총 시도 횟수
    total_attempts = sum(s.get('attempts', 1) for s in user_scores)
    
    # 예상 연습 시간
    times = [s.get('time_taken') for s in user_scores if s.get('time_taken') is not None]
    estimated_practice_time = sum(times) if times else 0
    
    return {
        "script_id": script_id,
        "total_sentences": total_sentences,
        "attempted_sentences": attempted_sentences,
        "completion_rate": round(completion_rate, 2),
        "average_best_score": average_best_score,
        "total_attempts": total_attempts,
        "estimated_practice_time": estimated_practice_time
    }


@router.get(
    "/scripts/{script_id}/scores",
    summary="스크립트 전체 점수 목록",
    responses={
        200: {
            "description": "점수 목록 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "script_id": "uuid",
                        "scores": [
                            {
                                "score_id": "uuid",
                                "sentence_id": "uuid",
                                "best_score": 85.5,
                                "attempts": 2
                            }
                        ],
                        "total_count": 1
                    }
                }
            }
        }
    }
)
def list_script_scores(
    script_id: str,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(500, ge=1, le=2000, description="최대 반환 개수")
):
    """
    스크립트 내 모든 문장의 사용자 점수를 조회합니다.
    
    **응답:**
    문장별 점수, 시도 횟수, 최고 점수 등 포함
    """
    # 스크립트 존재 확인
    get_script_by_id(script_id, user_id)
    
    Q = TinyQuery()
    scores = practice_scores_table.search(
        (Q.script_id == script_id) & (Q.user_id == user_id)
    )[:limit]
    
    return {
        "script_id": script_id,
        "scores": [
            {
                "score_id": s['score_id'],
                "sentence_id": s['sentence_id'],
                "best_score": s.get('best_score'),
                "attempts": s.get('attempts', 1)
            }
            for s in scores
        ],
        "total_count": len(scores)
    }
