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

# from starlette.responses import Response
from starlette.datastructures import URL

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
# app.mount("/mcp", mcp.sse_app())

sse_app = mcp.sse_app()

# 해당 mcp 가 authentication 이 필요하다고 알려주는 부분
# 이게 없으면 자동연결을 하는데, 그러면 auth 없이 연결이 되어서 추후 동작에 문제가 생김
@sse_app.middleware("http")
async def mcp_auth_middleware(request: Request, call_next):
    print('mcp_auth_middleware ---')
    # print(f'request path: {request.url.path}')

    # rewrite path manually to prevent redirect
    if request.url.path == "/mcp/sse":
        scope = request.scope
        scope["path"] = "/mcp/sse/"
        request._url = URL(scope=scope)  # Update cached URL
        print("Manually rewrote path to /mcp/sse/ to avoid redirect")

    # Authorization check
    if request.url.path.endswith("/sse/"):
        auth_header = request.headers.get("authorization")
        print(f'auth: {auth_header}--')
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    response = await call_next(request)
    return response

app.mount("/mcp", sse_app)

# mcp.run(transport="sse")
# app.mount("/mcp", mcp.sse_app())


@app.get("/.well-known/oauth-authorization-server")
def oauth_server(request: Request):
    # base_url = str(request.base_url).rstrip('/')
    base_url = 'https://mcp-todo-app-822395763299.asia-northeast3.run.app'
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "registration_endpoint": f"{base_url}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"]
    }


@app.post("/register")
async def register(request: Request):
    data = await request.json()
    logging.info(f"Received client registration: {data}")
    
    # Return the registered client information
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": data.get("redirect_uris", []),
        # "grant_types": data.get("grant_types", ["authorization_code"]),
        # "response_types": data.get("response_types", ["code"]),
        # "token_endpoint_auth_method": "client_secret_post"
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
    