# 발표 대본 관리 및 연습 점수 API 가이드

## 개요

새로 추가된 API는 다음의 기능을 제공합니다:

1. **발표 대본 관리**: 사용자가 발표 대본을 업로드하고 자동으로 처리
2. **문장 분할 및 청크화**: 마침표 기준 분할 후 읽기에 적당한 길이로 재배치
3. **연습 점수 관리**: 사용자의 연습 결과를 기록 및 추적

---

## 데이터 구조 설계

### 계층 구조

```
Script (발표 대본 전체)
  ├─ script_id (UUID)
  ├─ user_id
  ├─ script_name (발표 제목)
  ├─ total_slides (총 슬라이드 수)
  └─ created_at, updated_at
  
  └─ Slide (슬라이드 단위)
       ├─ slide_id (UUID)
       ├─ slide_number (순서)
       ├─ status (uploading/processing/completed/failed)
       └─ created_at, updated_at
       
       └─ Sentence (마침표 기준 분할 후 청크화)
            ├─ sentence_id (UUID)
            ├─ sentence_number (슬라이드 내 순서)
            ├─ text (한번에 읽기에 적당한 길이)
            ├─ original_sentence_indices (원본 문장 추적용)
            ├─ duration_estimate (예상 읽기 시간)
            └─ created_at
            
            └─ PracticeScore (연습 점수)
                 ├─ score_id (UUID)
                 ├─ user_id (연습한 사용자)
                 ├─ accuracy (발음 정확도 0-100)
                 ├─ fluency (유창성 0-100)
                 ├─ time_taken (소요 시간)
                 ├─ attempts (시도 횟수)
                 ├─ best_score (최고 점수)
                 └─ created_at, updated_at
```

### 업로드 방식: 슬라이드 단위

**권장 이유:**
- 메모리 효율적 (대용량 파일도 안전하게 처리)
- 부분 실패 처리 용이 (슬라이드별로 독립적)
- 사용자에게 진행 상황 표시 가능
- 나중에 슬라이드별 점수 분석 가능

---

## API 엔드포인트

### 1. 발표 대본 생성

**요청:**
```http
POST /api/v1/scripts
Authorization: Bearer <token>

{
  "script_name": "리더십 워크숍",
  "description": "팀 관리 효율화",
  "total_slides": 5
}
```

**응답:**
```json
{
  "script_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "user123",
  "script_name": "리더십 워크숍",
  "total_slides": 5,
  "description": "팀 관리 효율화",
  "created_at": "2025-11-18T10:00:00",
  "updated_at": "2025-11-18T10:00:00"
}
```

---

### 2. 슬라이드 대본 업로드 및 처리

**요청:**
```http
PATCH /api/v1/scripts/{script_id}/slide/{slide_number}
Authorization: Bearer <token>

{
  "script_text": "안녕하십니까. 지금부터 발표를 시작하겠습니다. 오늘은 효율적인 팀 관리에 대해 얘기하려고 합니다."
}
```

**응답:**
```json
{
  "slide_id": "s1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "script_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "slide_number": 1,
  "status": "completed",
  "sentence_count": 3,
  "sentences": [
    {
      "sentence_id": "sen-001",
      "slide_id": "s1a2b3c4-d5e6-7890-abcd-ef1234567890",
      "sentence_number": 1,
      "text": "안녕하십니까. 지금부터 발표를 시작하겠습니다.",
      "original_sentence_indices": [0, 1],
      "duration_estimate": 3.2,
      "created_at": "2025-11-18T10:05:00"
    },
    {
      "sentence_id": "sen-002",
      "slide_id": "s1a2b3c4-d5e6-7890-abcd-ef1234567890",
      "sentence_number": 2,
      "text": "오늘은 효율적인 팀 관리에 대해 얘기하려고 합니다.",
      "original_sentence_indices": [2],
      "duration_estimate": 3.6,
      "created_at": "2025-11-18T10:05:00"
    }
  ]
}
```

**자동 처리 프로세스:**
1. 마침표(`.`, `!`, `?`) 기준으로 문장 분할
2. 읽기에 적당한 길이(약 200자, 3문장 이하)로 청크화
3. 예상 읽기 시간 계산 (한국어 150단어/분 기준)
4. 각 청크를 개별 문장 데이터로 저장

---

### 3. 스크립트 정보 조회

**요청:**
```http
GET /api/v1/scripts/{script_id}
Authorization: Bearer <token>
```

**응답:**
```json
{
  "script_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "script_name": "리더십 워크숍",
  "user_id": "user123",
  "total_slides": 5,
  "sentence_count": 12,
  "created_at": "2025-11-18T10:00:00",
  "updated_at": "2025-11-18T10:10:00"
}
```

---

### 4. 문장 데이터 조회 (클론 준비)

**요청:**
```http
GET /api/v1/scripts/{script_id}/sentences
Authorization: Bearer <token>

# 선택: 특정 슬라이드만 조회
GET /api/v1/scripts/{script_id}/sentences?slide_id={slide_id}
```

**응답:**
```json
{
  "script_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "script_name": "리더십 워크숍",
  "total_slides": 5,
  "slide_id": null,
  "sentences": [
    {
      "sentence_id": "sen-001",
      "slide_id": "s1a2b3c4-d5e6-7890-abcd-ef1234567890",
      "sentence_number": 1,
      "text": "안녕하십니까. 지금부터 발표를 시작하겠습니다.",
      "original_sentence_indices": [0, 1],
      "duration_estimate": 3.2,
      "created_at": "2025-11-18T10:05:00"
    },
    // ... 모든 문장
  ],
  "total_count": 12
}
```

**용도:** 이 데이터를 클론 API에 전달하여 음성 파일로 변환

---

### 5. 연습 점수 제출

**요청:**
```http
POST /api/v1/practice/scores/{sentence_id}
Authorization: Bearer <token>

{
  "accuracy": 85.5,
  "fluency": 90.0,
  "time_taken": 3.5
}
```

**응답:**
```json
{
  "score_id": "score-001",
  "sentence_id": "sen-001",
  "best_score": 87.75,
  "attempts": 1,
  "created_at": "2025-11-18T10:15:00"
}
```

**기능:**
- 새로운 점수 기록 생성
- 기존 기록이 있으면 `attempts` 증가 및 `best_score` 갱신
- `accuracy`와 `fluency` 평균을 최고 점수로 저장

---

### 6. 연습 점수 조회 (단일 문장)

**요청:**
```http
GET /api/v1/practice/scores/{sentence_id}
Authorization: Bearer <token>
```

**응답:**
```json
{
  "score_id": "score-001",
  "sentence_id": "sen-001",
  "slide_id": "s1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "script_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "user123",
  "accuracy": 85.5,
  "fluency": 90.0,
  "time_taken": 3.5,
  "attempts": 2,
  "best_score": 87.75,
  "created_at": "2025-11-18T10:15:00",
  "updated_at": "2025-11-18T10:20:00"
}
```

---

### 7. 스크립트 전체 연습 통계

**요청:**
```http
GET /api/v1/practice/scripts/{script_id}/stats
Authorization: Bearer <token>
```

**응답:**
```json
{
  "script_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "total_sentences": 12,
  "attempted_sentences": 10,
  "completion_rate": 83.33,
  "average_best_score": 85.5,
  "total_attempts": 15,
  "estimated_practice_time": 120.5
}
```

**포함 정보:**
- 총 문장 수 / 시도한 문장 수
- 완료율 (%)
- 평균 최고 점수
- 총 시도 횟수
- 누적 연습 시간 (초)

---

### 8. 스크립트 전체 점수 목록

**요청:**
```http
GET /api/v1/practice/scripts/{script_id}/scores
Authorization: Bearer <token>
```

**응답:**
```json
{
  "script_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "scores": [
    {
      "score_id": "score-001",
      "sentence_id": "sen-001",
      "best_score": 87.75,
      "attempts": 2
    },
    {
      "score_id": "score-002",
      "sentence_id": "sen-002",
      "best_score": 90.0,
      "attempts": 1
    }
  ],
  "total_count": 2
}
```

---

## 사용 흐름 예제

### 1. 발표 준비 및 업로드

```bash
# 1. 새 발표 생성
POST /api/v1/scripts
{
  "script_name": "Q4 마케팅 전략",
  "total_slides": 3
}
# → script_id: "abc-123"

# 2. 첫 번째 슬라이드 업로드
PATCH /api/v1/scripts/abc-123/slide/1
{
  "script_text": "안녕하세요. 오늘은 4분기 마케팅 전략을 발표하겠습니다. 시장 현황을 먼저 살펴보겠습니다."
}
# → 자동으로 3개의 문장 생성 (sentence_id들)

# 3. 두 번째 슬라이드 업로드
PATCH /api/v1/scripts/abc-123/slide/2
{ ... }

# 4. 세 번째 슬라이드 업로드
PATCH /api/v1/scripts/abc-123/slide/3
{ ... }
```

### 2. 클론 준비

```bash
# 모든 문장 데이터 조회
GET /api/v1/scripts/abc-123/sentences

# 응답의 sentences 배열을 순회하며
# 각 sentence를 클론 API에 전달하여 음성 파일 생성
for sentence in sentences:
    POST /api/v1/voice/clone
    {
      "text": sentence.text,
      "script_id": "abc-123",
      "sentence_id": sentence.sentence_id,
      "voice_id": "user_voice_id"
    }
```

### 3. 연습 및 점수 기록

```bash
# 사용자가 각 문장을 읽고 평가 받음
POST /api/v1/practice/scores/sen-001
{
  "accuracy": 85.5,
  "fluency": 90.0,
  "time_taken": 3.2
}

# 같은 문장을 다시 연습
POST /api/v1/practice/scores/sen-001
{
  "accuracy": 92.0,
  "fluency": 93.5,
  "time_taken": 3.1
}
# → best_score가 92.75로 자동 갱신, attempts = 2

# 전체 진행 상황 확인
GET /api/v1/practice/scripts/abc-123/stats
# → completion_rate: 100%, average_best_score: 90.5 등
```

---

## 설계 특징

### 1. 확장성

- **미래의 기능 추가**: 문장별 점수 데이터 구조가 설계되어 있어 추가 메트릭 확대 용이
- **다중 버전 지원**: 같은 스크립트의 여러 버전 관리 가능
- **사용자별 추적**: 각 사용자의 진행 상황을 개별적으로 추적

### 2. 효율성

- **자동 청크화**: 불규칙한 문장 길이를 자동으로 최적화
- **읽기 시간 추정**: 예상 지속 시간으로 사용자 체감 개선
- **슬라이드 단위 처리**: 메모리 안전, 병렬 처리 가능

### 3. 유연성

- **마침표 기준 분할**: 한국어/영어 혼합 텍스트 지원
- **청크 크기 조정**: 설정으로 청크 크기 커스터마이징 가능
- **다양한 점수 메트릭**: accuracy, fluency, time_taken 등 확장 가능

---

## 문장 분할 및 청크화 알고리즘

### 분할 기준

1. **마침표 `.`, 물음표 `?`, 느낌표 `!`**를 기준으로 문장 분할
2. 각 문장의 공백을 정규화

### 청크화 규칙

```
최대 200자 또는 최대 3개 문장 중 먼저 도달하는 조건으로 청크 생성

예시:
원본: "안녕하십니까(8자). 지금부터(7자) 발표를(5자) 시작하겠습니다(9자). 
      오늘은(6자) 효율적인(7자) 팀(2자) 관리에(6자) 대해(3자) 
      얘기하려고(7자) 합니다(4자)."

분할: ["안녕하십니까.", "지금부터", "발표를", "시작하겠습니다.", 
       "오늘은", "효율적인", "팀", "관리에", "대해", "얘기하려고", "합니다."]

청크화:
[1] "안녕하십니까. 지금부터 발표를 시작하겠습니다." (29자, 2문장)
[2] "오늘은 효율적인 팀 관리에 대해 얘기하려고 합니다." (28자, 1문장)
```

### 읽기 시간 계산

```
한국어 기준: 약 150단어/분 = 0.4초/단어

텍스트: "안녕하십니까. 지금부터 발표를 시작하겠습니다."
한글 문자: 20자 / 3 (평균) ≈ 7단어
예상 시간: 7 × 0.4 = 2.8초
```

---

## 데이터베이스 스키마 (TinyDB)

### scripts 테이블
```python
{
  "script_id": "uuid",
  "user_id": "user123",
  "script_name": "리더십 워크숍",
  "total_slides": 5,
  "description": "팀 관리 효율화",
  "created_at": "2025-11-18T10:00:00",
  "updated_at": "2025-11-18T10:10:00"
}
```

### slides 테이블
```python
{
  "slide_id": "uuid",
  "script_id": "parent_script_uuid",
  "slide_number": 1,
  "status": "completed",  # uploading, processing, completed, failed
  "created_at": "2025-11-18T10:05:00",
  "updated_at": "2025-11-18T10:05:00"
}
```

### sentences 테이블
```python
{
  "sentence_id": "uuid",
  "slide_id": "parent_slide_uuid",
  "script_id": "parent_script_uuid",
  "sentence_number": 1,
  "text": "청크화된 문장 텍스트",
  "original_sentence_indices": [0, 1],  # 분할 전 문장 인덱스
  "duration_estimate": 3.2,
  "created_at": "2025-11-18T10:05:00"
}
```

### practice_scores 테이블
```python
{
  "score_id": "uuid",
  "sentence_id": "parent_sentence_uuid",
  "slide_id": "parent_slide_uuid",
  "script_id": "parent_script_uuid",
  "user_id": "user123",
  "accuracy": 85.5,
  "fluency": 90.0,
  "time_taken": 3.2,
  "attempts": 2,
  "best_score": 87.75,
  "created_at": "2025-11-18T10:15:00",
  "updated_at": "2025-11-18T10:20:00"
}
```

---

## 향후 확장 계획

### Phase 2: 고급 분석
- 슬라이드별 평균 점수 분석
- 시간대별 연습 패턴 분석
- 연습 효율성 지표 (점수 상승 추세)

### Phase 3: AI 기반 피드백
- 발음 문제 구간 자동 감지
- 개선 제안 API
- 유사 발표 문장 추천

### Phase 4: 협업 기능
- 팀 발표 공동 작성
- 그룹 연습 세션
- 강사 피드백 기능

---

## 주의사항

1. **대용량 대본**: 슬라이드 단위로 나누어 업로드 권장 (한번에 10MB 이상 권장X)
2. **토큰 만료**: 각 API 호출 시 유효한 JWT 토큰 필요
3. **점수 중복 기록**: 같은 문장에 다시 점수 제출 시 자동 업데이트 (덮어쓰기 아님)
4. **데이터 삭제**: 현재 삭제 API는 미지원 (soft delete 필요시 요청)
