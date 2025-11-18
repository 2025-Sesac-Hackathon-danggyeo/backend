"""
발표 대본 관련 데이터 모델
- Script: 발표 대본 전체 메타데이터
- Slide: 슬라이드 단위 메타데이터
- Sentence: 마침표 기준 분할 및 청크화된 문장 단위
- PracticeScore: 사용자 연습 점수 데이터
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SlideStatus(str, Enum):
    """슬라이드 처리 상태"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScriptMetadata(BaseModel):
    """발표 대본 메타데이터"""
    script_id: str = Field(..., description="고유 스크립트 ID (UUID)")
    user_id: str = Field(..., description="발표 소유자 ID")
    script_name: str = Field(..., description="발표 이름")
    total_slides: int = Field(default=0, description="총 슬라이드 개수")
    description: Optional[str] = Field(default=None, description="발표 설명")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SlideData(BaseModel):
    """슬라이드 정보"""
    slide_id: str = Field(..., description="고유 슬라이드 ID")
    script_id: str = Field(..., description="상위 스크립트 ID")
    slide_number: int = Field(..., description="슬라이드 순서 (1부터 시작)")
    status: SlideStatus = Field(default=SlideStatus.UPLOADING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SentenceData(BaseModel):
    """문장 데이터 (마침표 기준 분할 후 청크화)"""
    sentence_id: str = Field(..., description="고유 문장 ID (UUID)")
    slide_id: str = Field(..., description="상위 슬라이드 ID")
    sentence_number: int = Field(..., description="슬라이드 내 문장 순서")
    text: str = Field(..., description="한번에 읽기에 적당한 길이의 텍스트")
    original_sentence_indices: List[int] = Field(
        default_factory=list,
        description="원본 문장들의 인덱스 (분할 전 문장 추적용)"
    )
    duration_estimate: Optional[float] = Field(
        default=None,
        description="예상 읽기 시간(초)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PracticeScoreData(BaseModel):
    """연습 점수 데이터"""
    score_id: str = Field(..., description="고유 점수 레코드 ID")
    sentence_id: str = Field(..., description="평가 대상 문장 ID")
    slide_id: str = Field(..., description="슬라이드 ID")
    script_id: str = Field(..., description="스크립트 ID")
    user_id: str = Field(..., description="연습한 사용자 ID")
    accuracy: Optional[float] = Field(default=None, description="발음 정확도 (0-100)")
    fluency: Optional[float] = Field(default=None, description="유창성 점수 (0-100)")
    time_taken: Optional[float] = Field(default=None, description="소요 시간(초)")
    attempts: int = Field(default=1, description="총 시도 횟수")
    best_score: Optional[float] = Field(
        default=None,
        description="최고 점수 (여러 시도 중)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ===== API Request/Response Schemas =====

class UploadScriptRequest(BaseModel):
    """발표 대본 생성 요청"""
    script_name: str = Field(..., description="발표 제목", example="리더십 워크숍")
    description: Optional[str] = Field(None, description="발표 설명")
    total_slides: Optional[int] = Field(
        default=0,
        description="예상 슬라이드 개수 (선택사항)"
    )


class UploadSlideRequest(BaseModel):
    """슬라이드 대본 업로드 요청"""
    script_text: str = Field(..., description="해당 슬라이드의 발표 대본 전체")


class UploadSlideResponse(BaseModel):
    """슬라이드 업로드 응답"""
    slide_id: str
    script_id: str
    slide_number: int
    status: SlideStatus
    sentence_count: int
    sentences: List[SentenceData]


class ScriptSummaryResponse(BaseModel):
    """스크립트 요약 정보"""
    script_id: str
    script_name: str
    user_id: str
    total_slides: int
    sentence_count: int
    created_at: datetime
    updated_at: datetime


class SentencesListResponse(BaseModel):
    """문장 목록 조회 응답 (클론 준비용)"""
    script_id: str
    script_name: str
    total_slides: int
    slide_id: Optional[str] = Field(None, description="특정 슬라이드만 조회시 ID")
    sentences: List[SentenceData]
    total_count: int


class PracticeScoreRequest(BaseModel):
    """연습 점수 제출 요청"""
    accuracy: Optional[float] = Field(None, ge=0, le=100)
    fluency: Optional[float] = Field(None, ge=0, le=100)
    time_taken: Optional[float] = Field(None, gt=0)


class PracticeScoreResponse(BaseModel):
    """연습 점수 저장 응답"""
    score_id: str
    sentence_id: str
    best_score: Optional[float]
    attempts: int
    created_at: datetime
