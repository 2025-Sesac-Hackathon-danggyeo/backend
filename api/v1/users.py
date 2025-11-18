from fastapi import APIRouter, HTTPException, Depends
from core.database import users_table, blacklist_table, UserQuery
from core.security import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token,
    get_token_payload, get_current_user_id, cleanup_expired_blacklist_tokens
)
from models.user import UserSignup, UserLogin, TokenRefreshRequest
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from datetime import timedelta
from api.v1.schemas import LoginResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/users", tags=["Auth"])


@router.post(
    "/register",
    summary="회원가입",
    description=(
        "새 사용자 계정을 생성합니다. 요청 바디에 `id`(사용자명)과 `password`를 포함해야 합니다. "
        "이미 존재하는 아이디로 등록 시 400을 반환합니다. 성공 시 간단한 성공 메시지를 반환합니다."
    ),
    responses={
        200: {
            "description": "회원가입 성공",
            "content": {
                "application/json": {
                    "example": {"message": "Register successful"}
                }
            }
        },
        400: {
            "description": "이미 존재하는 아이디",
            "content": {
                "application/json": {
                    "example": {"detail": "이미 존재하는 아이디입니다."}
                }
            }
        }
    }
)
def register(user: UserSignup):
    """
    새 사용자 등록 엔드포인트

    - 요청: `UserSignup` 모델(JSON) — `id`, `password`
    - 동작: 비밀번호를 해시하여 사용자 테이블에 저장
    - 응답: 성공 메시지 또는 에러(이미 존재하는 경우 400)
    """
    if users_table.search(UserQuery.id == user.id):
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    hashed_password = get_password_hash(user.password)
    users_table.insert({"id": user.id, "password": hashed_password})
    return {"message": "Register successful"}

@router.post(
    "/login",
    summary="로그인",
    description=(
        "사용자 아이디와 비밀번호를 검증하고, 인증에 성공하면 Access/Refresh 토큰을 반환합니다. "
        "Access 토큰은 API 호출에 사용되며 만료 시간이 적용됩니다."
    ),
    responses={
        200: {
            "description": "로그인 성공 (토큰 발급)",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Login success",
                        "token": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                        }
                    }
                }
            }
        },
        401: {
            "description": "인증 실패 (사용자 미존재 또는 비밀번호 불일치)",
            "content": {
                "application/json": {
                    "example": {"detail": "아이디가 존재하지 않습니다."}
                }
            }
        }
    }
)
def login(user: UserLogin):
    """
    사용자 인증 및 토큰 발급

    - 요청: `UserLogin` 모델(JSON) — `id`, `password`
    - 응답(성공): `token.access`(JWT), `token.refresh`(JWT)
    - 오류: 사용자 미존재 또는 비밀번호 불일치 → 401
    """
    search_result = users_table.search(UserQuery.id == user.id)
    if not search_result:
        raise HTTPException(status_code=401, detail="아이디가 존재하지 않습니다.")
    user_data = search_result[0]
    if not verify_password(user.password, user_data['password']):
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")
    access_token = create_access_token(
        data={"sub": user_data['id']},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": user_data['id']},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    return {
        "message": "Login success",
        "token": {"access": access_token, "refresh": refresh_token}
    }

@router.post(
    "/token/refresh",
    summary="토큰 재발급",
    description=(
        "Refresh 토큰을 이용해 새로운 Access 토큰을 발급합니다. 서버는 Refresh 토큰의 유효성 및 블랙리스트 여부를 검증합니다."
    ),
    responses={
        200: {
            "description": "토큰 재발급 성공",
            "content": {
                "application/json": {
                    "example": {
                        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                    }
                }
            }
        },
        401: {
            "description": "유효하지 않은 Refresh 토큰",
            "content": {
                "application/json": {
                    "example": {"detail": "유효하지 않은 리프레시 토큰입니다."}
                }
            }
        }
    }
)
def refresh_token(request_body: TokenRefreshRequest):
    from jose import JWTError
    from core.config import SECRET_KEY, ALGORITHM
    from jose import jwt
    try:
        payload = jwt.decode(request_body.refresh, SECRET_KEY, algorithms=[ALGORITHM])
        if blacklist_table.search(UserQuery.jti == payload.get("jti")):
            raise HTTPException(status_code=401, detail="토큰이 무효화되었습니다.")
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다.")
        access_token = create_access_token(
            data={"sub": user_id},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        # 만료된 토큰 정리 (DB 크기 관리)
        cleanup_expired_blacklist_tokens()
        return {"access": access_token}
    except (JWTError, AttributeError):
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다.")

@router.delete(
    "/logout",
    summary="로그아웃",
    description=(
        "현재 사용 중인 토큰을 서버측 블랙리스트에 추가하여 무효화합니다. "
        "요청은 인증된 상태에서만 가능하며, 성공 시 간단한 성공 메시지를 반환합니다."
    ),
    responses={
        200: {
            "description": "로그아웃 성공",
            "content": {
                "application/json": {
                    "example": {"message": "Logout success"}
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
        },
        500: {
            "description": "서버 오류",
            "content": {
                "application/json": {
                    "example": {"detail": "로그아웃 처리 중 오류 발생: ..."}
                }
            }
        }
    }
)
def logout(payload: dict = Depends(get_token_payload)):
    """
    현재 토큰을 블랙리스트에 추가하여 즉시 무효화합니다.

    - 요청: 인증된 상태에서 호출
    - 동작: 토큰의 `jti`와 `exp`를 블랙리스트 테이블에 저장
    - 응답: 성공 메시지 또는 서버 에러(500)
    """
    try:
        jti = payload.get("jti")
        exp = payload.get("exp")
        blacklist_table.insert({"jti": jti, "exp": exp})
        # 만료된 토큰 정리 (DB 크기 관리)
        cleanup_expired_blacklist_tokens()
        return {"message": "Logout success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 처리 중 오류 발생: {e}")

@router.delete(
    "/deregister",
    summary="회원 탈퇴(본인)",
    description=(
        "현재 인증된 사용자의 계정을 삭제합니다. 호출 시 해당 사용자의 정보가 DB에서 완전 삭제됩니다. "
        "중요: 이 작업은 되돌릴 수 없습니다."
    ),
    responses={
        200: {
            "description": "회원 탈퇴 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "사용자 'user123'가 정상적으로 탈퇴(삭제)되었습니다."
                    }
                }
            }
        },
        404: {
            "description": "사용자 미발견",
            "content": {
                "application/json": {
                    "example": {"detail": "삭제할 사용자를 찾을 수 없습니다."}
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
def delete_user_me(current_user_id: str = Depends(get_current_user_id)):
    """
    현재 인증된 사용자의 계정을 영구 삭제합니다.

    - 권한: 본인만 호출 가능
    - 응답: 삭제 성공 메시지 또는 404(사용자 미존재)
    """
    if not users_table.search(UserQuery.id == current_user_id):
        raise HTTPException(status_code=404, detail="삭제할 사용자를 찾을 수 없습니다.")
    users_table.remove(UserQuery.id == current_user_id)
    return {
        "status": "success",
        "message": f"사용자 '{current_user_id}'가 정상적으로 탈퇴(삭제)되었습니다."
    }
