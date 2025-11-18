# AWS S3 Presigned URL(일시적 파일 접근 링크) 연동 및 사용법

이 문서는 본 백엔드 프로젝트에서 외부 오디오 파일(etc) 접근을 위해 AWS S3 presigned url 기능을 사용하는 방법을 안내합니다.

---

## 1. AWS S3 및 IAM 사전 준비

1) AWS 콘솔에서 S3 버킷을 생성
2) IAM(사용자)에서 '액세스 키' 발급
3) 해당 사용자에게 "AmazonS3ReadOnlyAccess" 최소 권한 이상 할당

---

## 2. 환경설정/자격증명 세팅

**.env 파일 또는 시스템 환경변수에 아래 값 필수 세팅**

```
AWS_ACCESS_KEY_ID=발급받은아이디
AWS_SECRET_ACCESS_KEY=발급받은시크릿
S3_BUCKET_NAME=내버킷이름
S3_REGION=ap-northeast-2
```

### *터미널에서 aws configure 사용 예시:*
```bash
aws configure
# 순서대로 위 값들을 입력
```

---

## 3. Presigned URL 발급 API 사용법

### (1) 백엔드 API 예시
```
GET /api/v1/files/presigned-url?object_key=경로/파일명.mp3&expires_in=300
```
응답 예시:
```json
{ "presigned_url": "https://....s3.amazonaws.com/경로/파일명.mp3?..." }
```

### (2) 프론트엔드 활용 예시
```html
<audio controls src="(백엔드에서 받은 presigned_url)"></audio>
```

---

## 4. 주요 참고 사항
- presigned url은 유효시간(expires_in 파라미터) 만료 시 즉시 접근불가
- 파일이 실제로 S3 버킷에 존재해야 정상적으로 stream/play 가능
- 보안을 위해 access key는 반드시 환경변수나 .env로 관리하고 코드에 하드코딩 금지
- presigned url은 외부에 노출해도 안전하나, 장기 노출 시 만료값을 짧게 관리하는 것이 권장

---

## 5. 오류 및 문의
- presigned url이 발급되지 않으면 AWS 설정, access 권한, S3 버킷/리전/오브젝트 경로 확인 필요
- 자세한 문의는 백엔드 담당자에 연락
