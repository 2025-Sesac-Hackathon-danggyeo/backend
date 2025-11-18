from pydantic import BaseModel, Field

class UserSignup(BaseModel):
    id: str = Field(..., title="사용자 아이디", example="user123")
    password: str = Field(..., title="비밀번호", example="password123")

class UserLogin(BaseModel):
    id: str = Field(..., example="user123")
    password: str = Field(..., example="password123")

class TokenRefreshRequest(BaseModel):
    refresh: str
