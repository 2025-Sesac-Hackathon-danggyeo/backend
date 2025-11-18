# SFITZ API 완벽 가이드

이 문서는 현재 백엔드 프로젝트의 모든 API 엔드포인트를 상세히 설명합니다. 이 문서만으로 모든 API의 동작을 완벽하게 이해하고 사용할 수 있습니다.

---

## 📋 목차

1. [개요 및 환경 설정](#개요-및-환경-설정)
2. [인증 API (Auth)](#인증-api-auth)
3. [S3 파일 API (Files)](#s3-파일-api-files)
4. [스크립트 API (Scripts)](#스크립트-api-scripts)
5. [데이터 구조](#데이터-구조)
6. [권한 정책](#권한-정책)
7. [HTTP 상태 코드](#http-상태-코드)
8. [사용 예시](#사용-예시)

---

## 개요 및 환경 설정

### 프로젝트 정보
- **프로젝트명**: SFITZ API
- **인증**: JWT (JSON Web Token)

### 필수 환경 변수 (.env 파일)

```env
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=your-bucket-name
S3_REGION=ap-northeast-2
SECRET_KEY=your-secret-key-for-jwt
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 인증 헤더

대부분의 엔드포인트는 JWT 토큰을 요구합니다. 요청 시 다음과 같이 헤더를 포함하세요:

```http
Authorization: Bearer <access_token>
```

---

## 인증 API (Auth)

모든 인증 엔드포인트는 `/api/v1/users` 경로에 있습니다.

### 1️⃣ 회원가입 (POST /api/v1/users/register)

새 사용자 계정을 생성합니다.

**요청:**
```http
POST /api/v1/users/register
Content-Type: application/json

{
  "id": "user123",
  "password": "password123"
}
```

**요청 필드:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| id | string | ✓ | 사용자 아이디 (고유값) |
| password | string | ✓ | 사용자 비밀번호 (평문, 서버에서 해시 처리) |

**응답 (성공, 200):**
```json
{
  "message": "Register successful"
}
```

**에러 응답:**
- **400 Bad Request**: 이미 존재하는 아이디
  ```json
  {
    "detail": "이미 존재하는 아이디입니다."
  }
  ```

**주의:**
- `id`는 전체 시스템에서 유일해야 합니다.
- 비밀번호는 최소 8자 이상 권장.

---

### 2️⃣ 로그인 (POST /api/v1/users/login)

사용자 아이디와 비밀번호를 검증하고 JWT 토큰을 발급합니다.

**요청:**
```http
POST /api/v1/users/login
Content-Type: application/json

{
  "id": "user123",
  "password": "password123"
}
```

**응답 (성공, 200):**
```json
{
  "message": "Login success",
  "token": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**응답 필드:**
| 필드 | 타입 | 설명 |
|------|------|------|
| token.access | string | API 호출 시 사용할 Access Token (기본 유효 시간: 30분) |
| token.refresh | string | 새로운 Access Token을 발급받을 때 사용 (기본 유효 시간: 7일) |

**에러 응답:**
- **401 Unauthorized**: 사용자 미존재 또는 비밀번호 불일치
  ```json
  {
    "detail": "아이디가 존재하지 않습니다."
  }
  ```

**사용 팁:**
1. Access Token을 별도의 HTTP 헤더로 저장
2. Refresh Token은 안전한 저장소(예: httpOnly 쿠키, 안전한 로컬 스토리지)에 보관
3. Access Token 만료 시 Refresh Token으로 새 Access Token 발급

---

### 3️⃣ 토큰 재발급 (POST /api/v1/users/token/refresh)

Refresh Token을 이용해 새로운 Access Token을 발급받습니다.

**요청:**
```http
POST /api/v1/users/token/refresh
Content-Type: application/json

{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**요청 필드:**
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| refresh | string | ✓ | 로그인 시 발급받은 Refresh Token |

**응답 (성공, 200):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**에러 응답:**
- **401 Unauthorized**: Refresh Token이 무효하거나 블랙리스트에 있음
  ```json
  {
    "detail": "유효하지 않은 리프레시 토큰입니다."
  }
  ```

**동작:**
- Refresh Token은 만료되지 않았지만 블랙리스트에 있는 경우도 거부됩니다.
- 새로 발급된 Access Token의 유효 시간은 30분입니다.

---

### 4️⃣ 로그아웃 (DELETE /api/v1/users/logout)

현재 사용 중인 Access Token을 서버의 블랙리스트에 추가하여 즉시 무효화합니다.

**요청:**
```http
DELETE /api/v1/users/logout
Authorization: Bearer <access_token>
```

**응답 (성공, 200):**
```json
{
  "message": "Logout success"
}
```

**에러 응답:**
- **401 Unauthorized**: 인증되지 않은 요청
- **500 Internal Server Error**: 서버 오류

**주의:**
- 로그아웃 후 기존 Access Token으로는 API 호출 불가
- Refresh Token도 함께 삭제 권장 (프론트엔드에서)

---

### 5️⃣ 회원 탈퇴 (DELETE /api/v1/users/deregister)

현재 인증된 사용자의 계정을 영구 삭제합니다. **⚠️ 이 작업은 되돌릴 수 없습니다.**

**요청:**
```http
DELETE /api/v1/users/deregister
Authorization: Bearer <access_token>
```

**응답 (성공, 200):**
```json
{
  "status": "success",
  "message": "사용자 'user123'가 정상적으로 탈퇴(삭제)되었습니다."
}
```

**에러 응답:**
- **401 Unauthorized**: 인증되지 않은 요청
- **404 Not Found**: 사용자를 찾을 수 없음

**경고:**
- 탈퇴 후 사용자의 모든 정보 및 관련 데이터가 삭제됩니다.
- 복구 불가능하므로 사용자 확인 후 진행하세요.

---

## S3 파일 API (Files)

모든 파일 관련 엔드포인트는 `/api/v1/files` 경로에 있습니다.

### 1️⃣ Presigned URL 발급 (GET /api/v1/files/presigned-url)

지정한 파일에 대한 S3 Presigned URL과 메타데이터를 반환합니다.

**요청:**
```http
GET /api/v1/files/presigned-url?file_name=basic_audio_1.wav&user_id_query=base_audio&expires_in=300
Authorization: Bearer <access_token>
```

**쿼리 파라미터:**
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| file_name | string | ✓ | - | S3 파일명 (예: `basic_audio_1.wav`) |
| user_id_query | string | ✗ | - | 파일 소유자 지정 (예: `base_audio` 또는 특정 유저 ID) |
| script_name | string | ✗ | - | 스크립트 이름으로 추가 필터링 |
| expires_in | integer | ✗ | 300 | Presigned URL 유효 시간 (초 단위, 최소 1초) |

**응답 (성공, 200):**
```json
{
  "presigned_url": "https://your-bucket.s3.amazonaws.com/base_audio/basic_audio_1.wav?X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
  "object_key": "base_audio/basic_audio_1.wav",
  "file_name": "basic_audio_1.wav",
  "script": "안녕하십니까. 지금부터 발표를 시작하겠습니다."
}
```

**응답 필드:**
| 필드 | 타입 | 설명 |
|------|------|------|
| presigned_url | string | S3에 임시 접근할 수 있는 URL (만료 시간 포함) |
| object_key | string | S3 객체의 경로 (예: `base_audio/basic_audio_1.wav`) |
| file_name | string | 요청한 파일명 |
| script | string \| null | 저장된 스크립트 텍스트 (없으면 미포함) |

**에러 응답:**
- **400 Bad Request**: Presigned URL 생성 실패 (AWS 설정 확인 필요)
  ```json
  {
    "detail": "Presigned URL 발급에 실패했습니다. AWS 설정 확인 필요"
  }
  ```
- **403 Forbidden**: 접근 권한 없음 (다른 사용자의 파일)
  ```json
  {
    "detail": "본인 소유 파일만 접근 가능합니다."
  }
  ```
- **404 Not Found**: 해당 파일이 DB에 없음
  ```json
  {
    "detail": "해당 파일이 DB에 없습니다."
  }
  ```
- **401 Unauthorized**: 인증되지 않은 요청

**동작 흐름:**
1. 요청 전 JWT 토큰 검증 (인증)
2. 파라미터로 파일 검색 (`file_name` 필수, 그 외는 선택)
3. 권한 확인:
   - `base_audio` 소유 파일: 모두 접근 가능 (공용)
   - 그 외: 현재 사용자만 접근 가능
4. AWS S3에서 Presigned URL 생성
5. 메타데이터와 함께 응답

**주의사항:**
- Presigned URL은 발급 시점부터 `expires_in` 초 동안만 유효합니다.
- URL은 외부에 노출해도 상대적으로 안전하지만, 만료 시간은 짧게 설정 권장.
- 파일은 반드시 S3 버킷에 존재해야 합니다.

---

## 스크립트 API (Scripts)

모든 스크립트 관련 엔드포인트는 `/api/v1/scripts` 경로에 있습니다.

### 1️⃣ 스크립트 목록 조회 (GET /api/v1/scripts/contents)

조건에 맞는 스크립트 항목들을 조회합니다. 선택적으로 각 항목의 Presigned URL도 함께 반환할 수 있습니다.

**요청:**
```http
GET /api/v1/scripts/contents?user_id_query=base_audio&script_name=intro&include_presigned=true&limit=50
Authorization: Bearer <access_token>
```

**쿼리 파라미터:**
| 파라미터 | 타입 | 필수 | 기본값 | 범위 | 설명 |
|---------|------|------|--------|------|------|
| user_id_query | string | ✗ | - | - | 파일 소유자로 필터 (예: `base_audio`, `user123`) |
| script_name | string | ✗ | - | - | 스크립트 이름으로 필터 (정확 매칭) |
| include_presigned | boolean | ✗ | false | - | 각 항목에 Presigned URL 포함 여부 |
| limit | integer | ✗ | 500 | 1-2000 | 반환할 최대 항목 수 |

**응답 (성공, 200):**
```json
{
  "results": [
    {
      "user_id": "base_audio",
      "script_name": "intro",
      "file_name": "basic_audio_1.wav",
      "object_key": "base_audio/intro/basic_audio_1.wav",
      "script": "안녕하십니까. 지금부터 발표를 시작하겠습니다.",
      "presigned_url": "https://your-bucket.s3.amazonaws.com/base_audio/intro/basic_audio_1.wav?X-Amz-Algorithm=..."
    }
  ],
  "count": 1
}
```

**응답 필드:**
| 필드 | 타입 | 설명 |
|------|------|------|
| results | array | 조건에 맞는 스크립트 항목 배열 |
| results[].user_id | string | 파일 소유자 ID |
| results[].script_name | string | 스크립트 그룹 이름 |
| results[].file_name | string | 파일명 |
| results[].object_key | string | S3 객체 경로 |
| results[].script | string | 스크립트 텍스트 |
| results[].presigned_url | string \| null | Presigned URL (`include_presigned=true`일 때만) |
| count | integer | 반환된 항목 개수 |

**에러 응답:**
- **403 Forbidden**: 다른 사용자의 스크립트를 조회하려고 할 때
  ```json
  {
    "detail": "다른 유저의 스크립트는 조회할 수 없습니다."
  }
  ```
- **401 Unauthorized**: 인증되지 않은 요청

**동작 흐름:**
1. JWT 토큰 검증
2. 권한 확인: `user_id_query`가 다른 사용자이면 403 반환
3. 필터 조건 적용:
   - `user_id_query` 지정: 해당 소유자의 항목만
   - 미지정: 현재 사용자 + `base_audio` 항목
   - `script_name` 지정: 일치하는 항목만
4. 최대 `limit`개까지 결과 반환
5. `include_presigned=true`인 경우 각 항목에 Presigned URL 추가 (최대 500개까지 생성)

**사용 시나리오:**

**시나리오 1: 본인과 공용 스크립트 모두 조회**
```http
GET /api/v1/scripts/contents?limit=100
```
→ 요청자(`user_id`)와 `base_audio` 스크립트를 모두 반환

**시나리오 2: 특정 소유자의 공용 스크립트만 조회**
```http
GET /api/v1/scripts/contents?user_id_query=base_audio
```
→ `base_audio` 소유 항목만 반환 (누구나 조회 가능)

**시나리오 3: 스크립트명으로 필터링**
```http
GET /api/v1/scripts/contents?script_name=intro&include_presigned=true
```
→ 현재 사용자가 접근 가능한 항목 중 `script_name=intro`인 항목에 Presigned URL 포함

**주의사항:**
- `include_presigned=true`일 때: 반환 개수가 500개를 초과하면 처음 500개만 Presigned URL 생성 (AWS 호출 횟수 제한)
- 권한이 없는 항목은 결과에서 제외됨 (필터링)
- 매우 많은 항목을 조회할 때는 `limit`을 적절히 설정 권장

---

## 데이터 구조

### S3 파일 항목 (s3_files 테이블)

데이터베이스에 저장되는 각 S3 파일 항목의 구조:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "base_audio",
  "script_name": "intro",
  "file_name": "basic_audio_1.wav",
  "object_key": "base_audio/intro/basic_audio_1.wav",
  "script": "안녕하십니까. 지금부터 발표를 시작하겠습니다.",
  "visibility": "public",
  "size": 123456,
  "content_hash": "sha256:abc123...",
  "created_at": "2025-11-15T12:00:00Z",
  "updated_at": "2025-11-15T12:00:00Z",
  "deleted": false
}
```

**필드 설명:**
| 필드 | 타입 | 설명 |
|------|------|------|
| id | string (UUID) | 항목의 고유 식별자 |
| user_id | string | 파일 소유자 ID (예: `base_audio`, `user123`) |
| script_name | string | 스크립트 그룹 이름 (예: `intro`, `main`, `outro`) |
| file_name | string | 파일명 (예: `basic_audio_1.wav`) |
| object_key | string | S3 내 전체 경로 (user_id/script_name/file_name 조합) |
| script | string | 실제 스크립트 텍스트 (음성 대사 등) |
| visibility | string | 공개 범위 (`public` 또는 `private`) |
| size | integer | 파일 크기 (바이트) |
| content_hash | string | 파일 체크섬 (예: SHA256) |
| created_at | string (ISO 8601) | 생성 시간 |
| updated_at | string (ISO 8601) | 마지막 수정 시간 |
| deleted | boolean | soft-delete 플래그 |

---

## 권한 정책

### 1. 파일/스크립트 접근 권한

**공용 파일 (base_audio)**
- 소유자: `base_audio`
- 접근: 모든 인증된 사용자 가능
- 사용 용도: 기본 음성 자료, 공용 샘플

**사용자 개인 파일**
- 소유자: `user_id` (로그인한 사용자 ID)
- 접근: 파일 소유자만 가능
- 사용 용도: 개인 녹음, 사용자 정의 자료

### 2. 토큰 권한

**Access Token**
- 용도: API 요청 시 사용 (모든 엔드포인트)
- 유효 시간: 30분
- 만료 후: 새로운 Access Token 발급 필요

**Refresh Token**
- 용도: 새로운 Access Token 발급
- 유효 시간: 7일
- 로그아웃 시: 블랙리스트 추가로 무효화

### 3. 작업별 필요 권한

| 작업 | 필요 권한 |
|------|----------|
| 회원가입 | 없음 (누구나) |
| 로그인 | 없음 (누구나) |
| API 호출 | Access Token (JWT) |
| 공용 파일 조회 | 인증만 필요 |
| 개인 파일 조회 | 인증 + 소유권 |
| 토큰 재발급 | Refresh Token |
| 로그아웃 | Access Token |
| 회원 탈퇴 | Access Token |

---

## HTTP 상태 코드

| 코드 | 의미 | 일반적인 원인 |
|------|------|------------|
| **200** | OK | 요청 성공 |
| **201** | Created | 새 리소스 생성 (해당 API 없음) |
| **400** | Bad Request | 잘못된 파라미터, AWS 설정 오류 |
| **401** | Unauthorized | 인증 없음, 토큰 만료, 토큰 무효 |
| **403** | Forbidden | 권한 부족 (다른 사용자의 파일 등) |
| **404** | Not Found | 리소스 미발견 (파일/사용자 없음) |
| **500** | Internal Server Error | 서버 오류 |

---

## 사용 예시

### 🔐 전체 인증 플로우

**1단계: 회원가입**
```bash
curl -X POST "http://localhost:8000/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "user123",
    "password": "password123"
  }'
```

**2단계: 로그인**
```bash
curl -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "user123",
    "password": "password123"
  }'

# 응답 예시:
# {
#   "message": "Login success",
#   "token": {
#     "access": "eyJ...",
#     "refresh": "eyJ..."
#   }
# }
```

**3단계: Access Token 저장**
```javascript
const accessToken = response.token.access;
const refreshToken = response.token.refresh;
// accessToken을 이후 모든 API 요청의 Authorization 헤더에 사용
```

### 📁 파일 조회 및 Presigned URL 발급

**공용 파일 조회 (base_audio)**
```bash
curl -X GET "http://localhost:8000/api/v1/files/presigned-url?file_name=basic_audio_1.wav&user_id_query=base_audio" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 응답:
# {
#   "presigned_url": "https://...",
#   "object_key": "base_audio/basic_audio_1.wav",
#   "file_name": "basic_audio_1.wav",
#   "script": "안녕하십니까..."
# }
```

**프론트엔드에서 사용**
```html
<audio controls>
  <source src="<presigned_url>" type="audio/wav">
</audio>
```

### 📝 스크립트 목록 조회

**모든 접근 가능한 스크립트 조회**
```bash
curl -X GET "http://localhost:8000/api/v1/scripts/contents?limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**공용 스크립트만 조회**
```bash
curl -X GET "http://localhost:8000/api/v1/scripts/contents?user_id_query=base_audio" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Presigned URL 포함하여 조회**
```bash
curl -X GET "http://localhost:8000/api/v1/scripts/contents?include_presigned=true&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 🔄 토큰 재발급

**Access Token 만료 시**
```bash
curl -X POST "http://localhost:8000/api/v1/users/token/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH_TOKEN\"}"

# 응답:
# {
#   "access": "eyJ..." (새로운 Access Token)
# }
```

### 🚪 로그아웃 및 탈퇴

**로그아웃**
```bash
curl -X DELETE "http://localhost:8000/api/v1/users/logout" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**회원 탈퇴 (⚠️ 되돌릴 수 없음)**
```bash
curl -X DELETE "http://localhost:8000/api/v1/users/deregister" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## 🔗 API Swagger 문서

프로젝트 실행 중에 브라우저에서 다음 주소로 접속하면 인터랙티브 API 문서를 볼 수 있습니다:

```
http://localhost:8000/docs
```

또는 ReDoc 형식:
```
http://localhost:8000/redoc
```

---

## 📚 추가 정보

### 마이그레이션 및 백업

기존 `db.json`을 새 스키마로 업그레이드하려면:

```bash
python3 scripts/migrate_s3.py
```

이 스크립트는:
- 자동으로 `db.json`을 백업 (`db.bak.<timestamp>`)
- 각 항목에 `id`, `object_key`, `visibility` 등 필드 추가
- 새 스키마로 `db.json` 갱신

### 개발 팁

**로컬 환경에서 테스트**
```bash
# 가상 환경 활성화
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload

# 브라우저에서 접속
# http://localhost:8000/docs
```

**환경 변수 확인**
```bash
# .env 파일이 올바르게 설정되었는지 확인
cat .env
```

---

**최종 수정**: 2025-11-15  
**버전**: 1.1.0  
**담당**: 백엔드팀

---

## ❓ 자주 묻는 질문 (FAQ)

**Q: Presigned URL이 만료되면?**
A: URL로 접근 불가능합니다. 새 URL을 발급받아야 합니다.

**Q: Access Token이 만료됐다고 나오면?**
A: Refresh Token으로 새 Access Token을 발급받으세요 (`/api/v1/users/token/refresh`).

**Q: 다른 사용자의 파일을 조회할 수 없나요?**
A: 기본 정책상 `base_audio` 공용 파일만 조회 가능합니다. 그 외 파일은 소유자만 접근 가능합니다.

**Q: 스크립트와 음성 파일의 관계는?**
A: 각 스크립트 항목은 S3 음성 파일과 메타 정보(텍스트)를 함께 저장하는 구조입니다.

**Q: limit 최대값이 2000인 이유는?**
A: DoS(Denial of Service) 공격 방지 및 서버 성능 관리를 위해 설정됨.

