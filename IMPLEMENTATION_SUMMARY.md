# 발표 대본 및 연습 점수 관리 시스템 - 구현 완료 요약

## 📋 구현 내용

### 1. 새로 추가된 파일

#### 모델 파일
- **`models/script.py`** - 발표 대본 관련 Pydantic 모델
  - `ScriptMetadata`: 발표 대본 메타데이터
  - `SlideData`: 슬라이드 정보
  - `SentenceData`: 마침표 기준 분할 후 청크화된 문장
  - `PracticeScoreData`: 연습 점수 데이터
  - API Request/Response 스키마 포함

#### 유틸리티 파일
- **`core/script_processor.py`** - 발표 대본 처리 유틸리티
  - `ScriptProcessor` 클래스
  - 마침표 기준 문장 분할
  - 읽기에 적당한 길이로 청크화 (약 200자, 3문장 이하)
  - 예상 읽기 시간 계산 (한국어 150단어/분 기준)
  - 예제 및 테스트 코드 포함

#### API 라우터 파일
- **`api/v1/speech_scripts.py`** - 발표 대본 관리 API
  - `POST /api/v1/scripts` - 새 발표 대본 생성
  - `PATCH /api/v1/scripts/{script_id}/slide/{slide_number}` - 슬라이드 업로드 및 자동 처리
  - `GET /api/v1/scripts/{script_id}` - 스크립트 정보 조회
  - `GET /api/v1/scripts/{script_id}/sentences` - 문장 데이터 조회 (클론 준비)

- **`api/v1/practice_scores.py`** - 연습 점수 관리 API
  - `POST /api/v1/practice/scores/{sentence_id}` - 연습 점수 제출 (자동 업데이트)
  - `GET /api/v1/practice/scores/{sentence_id}` - 단일 문장 점수 조회
  - `GET /api/v1/practice/scripts/{script_id}/stats` - 스크립트 전체 연습 통계
  - `GET /api/v1/practice/scripts/{script_id}/scores` - 스크립트 전체 점수 목록

#### 문서 및 테스트
- **`SPEECH_SCRIPTS_API_GUIDE.md`** - 완전한 API 사용 가이드
  - 데이터 구조 설계 설명
  - 모든 엔드포인트 문서화
  - 사용 흐름 예제
  - 알고리즘 설명
  - 향후 확장 계획

- **`test_speech_scripts_api.py`** - API 테스트 스크립트
  - 로컬 유틸리티 테스트 포함
  - 모든 엔드포인트 통합 테스트 함수 포함

#### 수정된 파일
- **`core/database.py`** - TinyDB 테이블 추가
  - `scripts_table` - 발표 대본 메타데이터
  - `slides_table` - 슬라이드 정보
  - `sentences_table` - 청크화된 문장
  - `practice_scores_table` - 연습 점수

- **`main.py`** - 새 라우터 등록
  - `speech_scripts_router` 등록
  - `practice_scores_router` 등록

---

## 🎯 핵심 기능

### 1. 자동 대본 처리 파이프라인

```
사용자 입력 (발표 대본)
    ↓
마침표/물음표/느낌표 기준 분할
    ↓
읽기에 적당한 길이로 청크화 (200자, 3문장 이하)
    ↓
예상 읽기 시간 계산
    ↓
데이터베이스 저장 (슬라이드 단위)
    ↓
클론 API 준비 완료
```

### 2. 발표 대본 업로드 (슬라이드 단위)

**선택 이유:**
- 메모리 효율적 (대용량 파일 안전 처리)
- 부분 실패 처리 용이
- 사용자에게 진행 상황 표시 가능
- 슬라이드별 독립적 점수 분석 가능

### 3. 연습 점수 추적 (확장 가능 설계)

```
한 문장에 여러 번 연습 가능
    ↓
각 시도마다 점수 기록 (accuracy, fluency, time_taken)
    ↓
best_score 자동 갱신
    ↓
attempts 카운트 증가
    ↓
전체 통계 집계 가능
```

### 4. 읽기 시간 자동 계산

```
한국어 평균 읽기 속도: 150단어/분 = 0.4초/단어

예: "안녕하십니까. 지금부터 발표를 시작하겠습니다."
    → 약 20자 ≈ 7단어 → 2.8초
```

---

## 📊 데이터베이스 스키마

### 계층 구조

```
scripts (발표 대본 전체)
├─ script_id (UUID)
├─ user_id
├─ script_name
├─ total_slides
└─ created_at, updated_at

slides (슬라이드 - 발표 대본의 한 단계)
├─ slide_id (UUID)
├─ script_id (참조)
├─ slide_number
├─ status (uploading/processing/completed/failed)
└─ created_at, updated_at

sentences (마침표 기준 분할 후 청크화된 문장)
├─ sentence_id (UUID)
├─ slide_id, script_id (참조)
├─ sentence_number (슬라이드 내 순서)
├─ text (청크화된 텍스트)
├─ original_sentence_indices (분할 전 문장 추적용)
├─ duration_estimate (예상 읽기 시간)
└─ created_at

practice_scores (연습 점수 - 확장 가능)
├─ score_id (UUID)
├─ sentence_id, slide_id, script_id (참조)
├─ user_id (연습한 사용자)
├─ accuracy (0-100)
├─ fluency (0-100)
├─ time_taken (초)
├─ attempts (시도 횟수)
├─ best_score (최고 점수)
└─ created_at, updated_at
```

---

## 🔄 사용 흐름 예제

### 발표 준비

```bash
1. 발표 생성
   POST /api/v1/scripts
   → script_id 생성

2. 슬라이드 1 업로드
   PATCH /api/v1/scripts/{script_id}/slide/1
   → 자동 처리: 문장 분할 → 청크화 → 저장
   → sentence_id 들 반환

3. 슬라이드 2, 3, ... 업로드
   PATCH /api/v1/scripts/{script_id}/slide/2
   ...
```

### 클론 준비

```bash
1. 모든 문장 조회
   GET /api/v1/scripts/{script_id}/sentences
   
2. 각 문장을 클론 API로 변환
   POST /api/v1/voice/clone
   {
     "text": sentence.text,
     "sentence_id": sentence.sentence_id,
     ...
   }
```

### 연습 및 평가

```bash
1. 사용자가 문장 읽음 → 음성 인식/평가

2. 점수 기록
   POST /api/v1/practice/scores/{sentence_id}
   {
     "accuracy": 85.5,
     "fluency": 90.0,
     "time_taken": 3.2
   }

3. 같은 문장 재연습 시
   POST /api/v1/practice/scores/{sentence_id}
   (자동으로 기존 기록 업데이트)

4. 전체 진행 상황 확인
   GET /api/v1/practice/scripts/{script_id}/stats
   → completion_rate, average_best_score, total_attempts 등
```

---

## ✨ 설계 특징

### 1. 확장성
- 새로운 점수 메트릭 추가 용이 (현재: accuracy, fluency, time_taken)
- 슬라이드별 독립적 관리로 미래의 협업 기능 확대 가능
- 사용자별 개별 추적으로 팀 기능 확대 가능

### 2. 효율성
- **자동 청크화**: 불규칙한 문장 길이를 최적화
- **슬라이드 단위**: 메모리 안전, 병렬 처리 가능
- **읽기 시간 자동 계산**: UX 개선

### 3. 유연성
- **마침표 기준 분할**: 한국어/영어 혼합 텍스트 지원
- **청크 크기 조정 가능**: 설정으로 커스터마이징
- **다양한 점수 메트릭**: 향후 AI 피드백 통합 용이

---

## 🚀 테스트 및 검증

### 로컬 테스트 실행

```bash
# 1. 유틸리티 테스트 (토큰 불필요)
python3 test_speech_scripts_api.py

# 2. 서버 시작
python3 -m uvicorn main:app --reload

# 3. API 통합 테스트 (TEST_TOKEN 설정 후)
python3 test_speech_scripts_api.py
```

### 테스트 결과

```
총 청크 개수: 2

청크 [1]
  텍스트: 안녕하십니까. 지금부터 발표를 시작하겠습니다. 오늘은 효율적인 팀 관리에 대해 얘기하려고 합니다.
  읽기시간: 5.2초
  원본문장인덱스: [0, 1, 2]

청크 [2]
  텍스트: 먼저 팀 문화의 중요성을 살펴보겠습니다. 좋은 팀 문화는 조직의 생산성을 높입니다. 이번에는 구체적인 사례를 보여드리겠습니다.
  읽기시간: 6.8초
  원본문장인덱스: [3, 4, 5]
```

✅ 문장 분할 및 청크화 기능 정상 작동 확인

---

## 📖 문서

### 상세 가이드
- **`SPEECH_SCRIPTS_API_GUIDE.md`**
  - 전체 API 문서
  - 데이터 구조 설명
  - 사용 흐름 예제
  - 알고리즘 상세 설명
  - 데이터베이스 스키마
  - 향후 확장 계획

### 테스트 코드
- **`test_speech_scripts_api.py`**
  - 로컬 유틸리티 테스트
  - 모든 엔드포인트 테스트 함수
  - 통합 테스트 시나리오

---

## 🔮 향후 확장 계획

### Phase 2: 고급 분석
- [ ] 슬라이드별 평균 점수 분석
- [ ] 시간대별 연습 패턴 분석
- [ ] 연습 효율성 지표 (점수 상승 추세)

### Phase 3: AI 기반 피드백
- [ ] 발음 문제 구간 자동 감지
- [ ] 개선 제안 API
- [ ] 유사 발표 문장 추천

### Phase 4: 협업 기능
- [ ] 팀 발표 공동 작성
- [ ] 그룹 연습 세션
- [ ] 강사 피드백 기능

### Phase 5: 고급 기능
- [ ] 발표 녹음 및 비교 분석
- [ ] 감정 표현 분석
- [ ] 개인화된 연습 계획 생성

---

## 📝 API 엔드포인트 빠른 참조

### 발표 대본 관리
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/v1/scripts` | 새 발표 대본 생성 |
| PATCH | `/api/v1/scripts/{script_id}/slide/{slide_number}` | 슬라이드 업로드 및 처리 |
| GET | `/api/v1/scripts/{script_id}` | 스크립트 정보 조회 |
| GET | `/api/v1/scripts/{script_id}/sentences` | 문장 데이터 조회 |

### 연습 점수 관리
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/v1/practice/scores/{sentence_id}` | 연습 점수 제출 |
| GET | `/api/v1/practice/scores/{sentence_id}` | 문장 점수 조회 |
| GET | `/api/v1/practice/scripts/{script_id}/stats` | 전체 연습 통계 |
| GET | `/api/v1/practice/scripts/{script_id}/scores` | 전체 점수 목록 |

---

## ✅ 구현 완료 체크리스트

- [x] 데이터 모델 설계 및 구현
- [x] 발표 대본 처리 유틸리티
- [x] 발표 대본 관리 API
- [x] 연습 점수 관리 API
- [x] 데이터베이스 통합
- [x] 권한 확인 및 보안
- [x] 완전한 API 문서화
- [x] 테스트 코드 작성
- [x] 로컬 테스트 검증

---

## 🎓 핵심 설계 결정사항

### 1. 슬라이드 단위 업로드 방식
- **이유**: 메모리 효율, 부분 실패 처리, UX 개선
- **대안 검토**: 전체 한번에 vs 슬라이드 단위 vs 문장 단위
- **선택**: 슬라이드 단위 (최적 균형)

### 2. 자동 청크화 알고리즘
- **기준**: 200자 또는 3문장 (먼저 도달하는 것)
- **이유**: 한번에 읽기에 적당한 길이 (TTS, 음성 인식 최적화)
- **조정 가능**: 설정으로 변경 가능

### 3. 점수 데이터 구조
- **다중 시도 지원**: `attempts` 카운트
- **최고 점수 추적**: `best_score` 자동 갱신
- **확장성**: 추가 메트릭 용이 (fluency, tone, pacing 등)

### 4. 데이터베이스 조직
- **계층 구조**: Script → Slide → Sentence → PracticeScore
- **참조 저장**: 원본 문장 인덱스로 분할 전후 추적 가능
- **독립성**: 각 테이블이 독립적으로 조회 및 필터 가능

---

## 📞 주의사항

1. **대용량 대본**: 슬라이드 단위로 나누어 업로드 (한번에 10MB 이상 권장 X)
2. **토큰 만료**: 각 API 호출 시 유효한 JWT 토큰 필수
3. **점수 중복 기록**: 같은 문장 재제출 시 자동 업데이트 (덮어쓰기 X)
4. **데이터 삭제**: 현재 삭제 API 미지원 (필요시 soft delete 구현)

---

## 🔗 관련 파일 경로

```
/home/ubuntu/backend/
├─ models/
│  └─ script.py                          # 새 모델
├─ core/
│  ├─ script_processor.py                # 새 유틸리티
│  └─ database.py                        # 수정됨 (테이블 추가)
├─ api/v1/
│  ├─ speech_scripts.py                  # 새 라우터
│  └─ practice_scores.py                 # 새 라우터
├─ main.py                               # 수정됨 (라우터 등록)
├─ SPEECH_SCRIPTS_API_GUIDE.md            # 새 문서
├─ test_speech_scripts_api.py             # 새 테스트
└─ IMPLEMENTATION_SUMMARY.md              # 이 파일
```

---

**마지막 수정**: 2025-11-18
**상태**: ✅ 구현 완료 및 테스트 검증 완료
