from datetime import datetime, timedelta, timezone
import bcrypt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import uuid
from core.database import blacklist_table, users_table, UserQuery
from core.config import SECRET_KEY, ALGORITHM
from tinydb import Query as TinyQuery

token_scheme = HTTPBearer()


def cleanup_expired_blacklist_tokens():
    """
    만료된 토큰들을 블랙리스트에서 제거합니다.
    로그아웃/토큰 재발급 시 호출하여 DB 크기 증가를 방지합니다.
    """
    current_time = datetime.now(timezone.utc).timestamp()
    Q = TinyQuery()
    # exp < current_time인 항목 모두 제거 (만료된 토큰)
    blacklist_table.remove(Q.exp < current_time)


# JWT 토큰 payload 검증 함수
def get_token_payload(auth: HTTPAuthorizationCredentials = Depends(token_scheme)):
    token = auth.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if blacklist_table.search(UserQuery.jti == payload.get("jti")):
            raise HTTPException(status_code=401, detail="토큰이 무효화되었습니다. (로그아웃됨)")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었습니다.")
    except (JWTError, AttributeError):
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

# 인증된 유저 id 추출 함수
def get_current_user_id(payload: dict = Depends(get_token_payload)):
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    if not users_table.search(UserQuery.id == user_id):
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user_id

# bcrypt 해시 생성 함수
# bcrypt는 72바이트 초과 비밀번호는 잘라서 처리하므로, 보안 위해 명시적 슬라이스 필요
# (참고: 한글 등 다국어는 인코딩 후 72바이트 슬라이스, 잘린 문자는 무시)
def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', 'ignore')
        password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

# bcrypt로 해시된 비밀번호 검증
# bcrypt는 72바이트까지 비교. 입력 비밀번호도 동일하게 슬라이스 처리 필요
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        plain_password_bytes = plain_password.encode('utf-8')
        if len(plain_password_bytes) > 72:
            plain_password = plain_password_bytes[:72].decode('utf-8', 'ignore')
            plain_password_bytes = plain_password.encode('utf-8')
        hashed_password_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except Exception:
        return False

# access 토큰 생성 함수
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# refresh 토큰 생성 함수
def create_refresh_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
