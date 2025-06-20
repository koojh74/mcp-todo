"""Simple MCP Server with Google OAuth Authentication."""


# connection process
# claude.ai 
# --> mcp/register 
# --> mcp/authorize --> google auth 
# --> claude.ai/callback (auth code)
# --> mcp/toekn (auth code) --> get token_data from google, then generate access_token

# using mcp tool: claude.ai access mcp.tool with access_token


import os
import logging
from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import jwt

from todo_mcp import mcp
from database import user_db


# logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서만 허용. 프로덕션에선 반드시 도메인 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mcp.run(transport="sse")
app.mount("/mcp", mcp.sse_app())


@app.post("/register")
def register(request: Request):
    data = request.json()
    logging.info(f"Received client registration: {data}")
    # 실제 프로덕션에서는, client_id, client_secret 생성 및 반환
    return {
        "client_id": GOOGLE_CLIENT_ID,
        # "client_secret": GOOGLE_CLIENT_SECRET,
        # "redirect_uris": data.get("/auth/login"),
        # "grant_types": data.get("grant_types"),
        # 기타 필요한 정보 반환
    }

@app.get("/authorize")
def login_with_google(request: Request):

    params = dict(request.query_params)
    # 로그 찍기
    for k, v in params.items():
        print(f"{k}: {v}")

    params['client_id'] = GOOGLE_CLIENT_ID
    params['response_type'] = "code"
    params['scope'] = "openid email profile"
    params['prompt'] = "consent"
    params['access_type'] = "offline"
    # params['redirect_uri'] = "https://mcp-server-auth-google-822395763299.asia-northeast3.run.app/auth_callback"
    # for k, v in params.items():
    #     print(f"--{k}: {v}")

    import urllib.parse
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@app.post("/token")
async def token(request: Request):
    # data = request.json() # coroutine object Request.json
    payload = await request.form()
    print(f"token: {dict(payload)}")
    payload = dict(payload)

    # Access Token 요청
    token_url = "https://oauth2.googleapis.com/token"
    payload['client_id'] = GOOGLE_CLIENT_ID
    payload['client_secret'] = GOOGLE_CLIENT_SECRET

    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=payload)

    if token_response.status_code != 200:
        return JSONResponse({
            "error": "Token request failed",
            "status": token_response.status_code,
            "details": token_response.text
        }, status_code=token_response.status_code)

    token_data = token_response.json()
    print(token_data)
    id_token = token_data['id_token']
    decoded = jwt.decode(id_token, options={"verify_signature": False})
    print(decoded)

    google_user_id = decoded['sub']
    email = decoded.get('email', '')
    name = decoded.get('name', '')
    
    # Save or update user information in database
    user_data = user_db.get_or_create_user(google_user_id, email, name)
    # print(f"User {email} logged in, access_count: {user_data['access_count']}")

    response = {
        "access_token": jwt.encode({"user_id": google_user_id}, GOOGLE_CLIENT_SECRET, algorithm="HS256"),
        "token_type": "Bearer"
    }
    
    return JSONResponse(response, headers={"Connection": "close"})
    # return response
    