"""
Cloud Run용 MCP (Model Context Protocol) Server

간단한 날씨 정보를 제공하는 테스트용 MCP 서버입니다.
"""

import os
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from mcp.server.fastmcp import FastMCP
import uvicorn

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp-server")

# OAuth2 설정 및 샘플 사용자 데이터
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 예제 사용자
SAMPLE_USER = {
    "username": "sample1",
    "password": "1111",
    "data": {"greeting": "Hello, sample1!"},
}

# 발급된 토큰 저장소 (간단한 메모리 저장)
issued_tokens: dict[str, str] = {}

def authenticate_user(username: str, password: str) -> bool:
    return username == SAMPLE_USER["username"] and password == SAMPLE_USER["password"]

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    user = issued_tokens.get(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user

# FastAPI 애플리케이션 생성
app = FastAPI()

# FastMCP 서버 초기화
mcp = FastMCP("standard_mcp_foottraffic")

# 로그인 엔드포인트: 유효한 사용자라면 토큰을 발급한다.
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = secrets.token_urlsafe(32)
    issued_tokens[token] = SAMPLE_USER["username"]
    return {"access_token": token, "token_type": "bearer"}


# 인증된 사용자에게만 반환되는 테스트용 데이터 엔드포인트
@app.get("/userdata")
async def read_user_data(user: str = Depends(get_current_user)):
    return {"username": user, "data": SAMPLE_USER["data"]}

# Add an foot traffic data tool
@mcp.tool()
def foottraffic(store_name: str) -> list:
    """foot traffic, 유동인구, 방문자 수, 최근 10일 방문자 수 및 날짜"""
    traffic = None
    if store_name == '이마트':
        traffic = [10, 20, 10, 15, 13, 18, 19, 20, 23, 24]
    elif store_name == '롯데마트':
        traffic = [20, 10, 15, 13, 18, 19, 20, 23, 24, 28]
    elif store_name == '홈플러스':
        traffic = [5, 8, 10, 20, 10, 15, 13, 18, 19, 20]

    if traffic is None:
        return []

    today = datetime.today()
    date_traffic = []

    for i in range(10):
        day = (today - timedelta(days=9 - i)).strftime('%Y-%m-%d')
        date_traffic.append({'date': day, 'visitors': traffic[i]})

    return date_traffic


# MCP SSE 엔드포인트 인증을 위한 미들웨어
@app.middleware("http")
async def sse_auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/chat"):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer", "").strip()
        if token not in issued_tokens:
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Invalid token"})
        request.state.user = issued_tokens[token]
    return await call_next(request)



# 메인 실행 지점
if __name__ == "__main__":
    # 환경 변수에서 포트 가져오기 (Cloud Run용)
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"MCP 서버 시작 중... 포트: {port}")
    
    # FastMCP 인스턴스에서 SSE 앱 가져오기 후 /chat 경로에 마운트
    app.mount("/chat", mcp.sse_app())

    # Uvicorn으로 앱 실행
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    # mcp.run(transport='sse')
