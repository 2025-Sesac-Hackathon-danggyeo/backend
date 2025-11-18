from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1.users import router as users_router
from api.v1.files import router as files_router
from api.v1.scripts import router as scripts_router
from api.v1.voice import router as voice_router

# FastAPI 앱 객체, Swagger 등 글로벌 설정만 담당
app = FastAPI(
    title="SFITZ API",
    description="React 프론트엔드와 통신하기 위한 백엔드 API입니다.\n\n[담당자] 백엔드팀",
    version="1.1.0"
)

# CORS 등 글로벌 미들웨어 설정
origins = [
    "http://localhost:3000",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 버전별 API 라우터 등록
app.include_router(users_router)
# 파일 관련 S3 presigned url 등 API 라우터 등록 (API v1 하위로 포함)
app.include_router(files_router, prefix="/api/v1")
# 스크립트 전용 라우터 등록 (파일 presigned 처리와 분리) - API v1 하위로 포함
app.include_router(scripts_router, prefix="/api/v1")
# 보이스 클로닝 라우터 등록
app.include_router(voice_router, prefix="/api/v1")
 
# 서버 상태 확인 API
@app.get("/", tags=["General"], summary="서버 상태 확인")
def read_root():
    """서버가 정상적으로 동작 중인지 확인하는 간단한 헬스체크 API입니다."""
    return {"message": "Server is running securely!"}