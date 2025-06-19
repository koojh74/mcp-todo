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
import time
from dotenv import load_dotenv
import httpx
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# from mcp.server.fastmcp.server import FastMCP, Context
from fastmcp import FastMCP, Context

import threading
import jwt

# 글로벌 쓰레드-로컬 변수
# request_local = threading.local()

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

mcp = FastMCP(
    name="Auth MCP Server",
    # instructions="A simple MCP server with GitHub OAuth authentication",
    host="0.0.0.0",
    port=8080,
    debug=True,
)

# mcp.run(transport="sse")
app.mount("/mcp", mcp.sse_app())


# @app.middleware("http")
# async def log_request_headers(request: Request, call_next):
#     # 모든 요청에서 헤더를 로그로 남김
#     # logging.info(f"-------------------S")
#     # request_local.authorization = request.headers.get("authorization")
#     # logging.info(f"PATH: {request.url.path}")
#     # for k, v in request.headers.items():
#     #     logging.info(f"Header: {k}: {v}")
#     response = await call_next(request)
#     # request_local.authorization = None
#     # logging.info(f"-------------------E")
#     return response


# @app.get("/.well-known/oauth-authorization-server")
# def oauth_server(request: Request):
#     data = request.json()
#     logging.info(f".well-known: {data}")


@app.post("/register")
def register(request: Request):
    data = request.json()
    logging.info(f"Received client registration: {data}")
    # 실제 프로덕션에서는, client_id, client_secret 생성 및 반환
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
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


# in actual flow, google auth callback to claude.ai
# for debugging purpose
# @app.get("/auth_callback")
# async def auth_callback(request: Request):
#     try:
#         code = request.query_params.get("code")
#         if not code:
#             return JSONResponse({"error": "Missing code"}, status_code=400)

#         # Access Token 요청
#         token_url = "https://oauth2.googleapis.com/token"
#         payload = {
#             "code": code,
#             "client_id": GOOGLE_CLIENT_ID,
#             "client_secret": GOOGLE_CLIENT_SECRET,
#             "redirect_uri": 'https://mcp-server-auth-google-822395763299.asia-northeast3.run.app/auth_callback',
#             "grant_type": "authorization_code",
#         }
#         async with httpx.AsyncClient() as client:
#             token_response = await client.post(token_url, data=payload)

#         if token_response.status_code != 200:
#             return JSONResponse({
#                 "error": "Token request failed",
#                 "status": token_response.status_code,
#                 "details": token_response.text
#             }, status_code=token_response.status_code)

#         token_data = token_response.json()
#         id_token = token_data['id_token']
#         decoded = jwt.decode(id_token, options={"verify_signature": False})
#         print(decoded)
#         return JSONResponse(decoded)
#         # return JSONResponse(token_data)

#     except Exception as e:
#         return JSONResponse({"error": "Server error", "details": str(e)}, status_code=500)


@app.post("/token")
async def token(request: Request):
    # data = request.json() # coroutine object Request.json
    payload = await request.form()
    print(f"token: {dict(payload)}")
    payload = dict(payload)

    # Access Token 요청
    token_url = "https://oauth2.googleapis.com/token"
    # payload = {
    #     "code": code,
    #     "client_id": GOOGLE_CLIENT_ID,
    #     "client_secret": GOOGLE_CLIENT_SECRET,
    #     "redirect_uri": 'https://mcp-server-auth-google-822395763299.asia-northeast3.run.app/auth_callback',
    #     "grant_type": "authorization_code",
    # }
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

    response = {
        "access_token": jwt.encode({"user_id": google_user_id}, GOOGLE_CLIENT_SECRET, algorithm="HS256"),
        "token_type": "Bearer"
    }
    
    return JSONResponse(response, headers={"Connection": "close"})
    # return response
    
    # return {
    #     "access_token": "abcdefg",
    #     "token_type": "Bearer",
    #     "expires_in": 3600,
    #     "refresh_token": "xxxxxxxxxxxxxx",
    #     "scope": data.get("scope", "openid email")  # 클라이언트 scope 값 그대로 응답해도 무방
    # }


def get_user_id(ctx):
    request = ctx.get_http_request()
    headers = request.headers
    authorization_header = headers.get('Authorization')
    access_token = authorization_header.replace('Bearer ', '')
    payload = jwt.decode(access_token, GOOGLE_CLIENT_SECRET, algorithms=["HS256"])
    user_id = payload['user_id']
    print(f'user_id: {user_id}')

    return user_id


@mcp.tool()
def get_todo(ctx:Context) -> list:
    """return to do list
    """
    print(f"todo list ---")

    user_id = get_user_id(ctx)

    todo_list = ["사업 계획 수립하기", "AI 공부하기"]
    
    return todo_list


# def main():
#     """Run the simple Google MCP server."""

#     # logger.info(f"Starting server with {transport} transport")
#     mcp.run(transport="sse")
#     # return 0


# if __name__ == "__main__":
#     main()


# from claude.ai (redirected from google) to /token
# token: {
# 'grant_type':'authorization_code', 
# 'code': '4/0AUJR-x4Y_eCycpK73MHwjWnWw9jdyjzi8OTYHbTF9Nt9vToL82OGKt7k2F9zD_KwpEJYOw',
# 'client_id': '822395763299-bh32da4s2g4367di7poleoim0laklnnv.apps.googleusercontent.com',
# 'code_verifier': 'u9S2943AVEcX-K1cbTrSTqR4rvVF6QBMFbA_-1aLQlw', 
# 'redirect_uri':'https://claude.ai/api/mcp/auth_callback
# '}


# mcp get token_data from google auth with code value
# token_data: 
# {
#   "access_token": "ya29.REDACTED",
#   "expires_in": 3599,
#   "refresh_token": "1//REDACTED",
#   "scope": "https://www.googleapis.com/auth/userinfo.profile openid https://www.googleapis.com/auth/userinfo.email",
#   "token_type": "Bearer",
#   "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjFiYjc3NGJkODcyOWVhMzhlOWMyZmUwYzY0ZDJjYTk0OGJmNjZmMGYiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiI4MjIzOTU3NjMyOTktYnZwYjJ2N3JxaWllOGNjbG11cmtqcDFjYmltbmpjaW0uYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiI4MjIzOTU3NjMyOTktYnZwYjJ2N3JxaWllOGNjbG11cmtqcDFjYmltbmpjaW0uYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMTIxNDA3NzYyMjgzOTc4NDA5MzMiLCJlbWFpbCI6Imtvb2poNzRAZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImF0X2hhc2giOiJmbzk3eVMwTG81SkdqcFFQMW1VV09BIiwibmFtZSI6IkphaHlvdW5nIEtvbyIsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NMUzdScGxLN1hlTC12eHA2cFFmdGNUel9GM2dSaG9mbkhNSVZMbDN3aFlNREN4RmczMz1zOTYtYyIsImdpdmVuX25hbWUiOiJKYWh5b3VuZyIsImZhbWlseV9uYW1lIjoiS29vIiwiaWF0IjoxNzUwMjM0NzIwLCJleHAiOjE3NTAyMzgzMjB9.ugoM77_Unq-0C4b-rzrMhjyAHWehz0gbqSrjEx4J0VhMT5E-g6Ndon18HqcKK2nCqSBrgAwJy06yUyE8L82TOkS0dX9KdcqoqPzpw5MBI-L3dzO4gHuOZZsxKAKrTomxdp2pSd6ryVutYuxvY9uyRzEijRl_WGryk4xByTpltfJgea6IZ3fPoqkEgCD9krWm_dHemqwXpTXUO2vzmx0TOFQ3mq6Yz7b_Lnl0R4o8OhuF4EKn4CaL163HJYDml-xMJTlzs-aKQf61CpZt7dGLzHqMNaq_Oq2Ahg4tC2xbMGykqn7NnLLWE-KkI5yiTzm6gMkiIWUKJ_KuJOa_L2YAaw"
# }

# id_token: (JWT)
# {
#   "iss": "https://accounts.google.com",
#   "azp": "822395763299-bvpb2v7rqiie8cclmurkjp1cbimnjcim.apps.googleusercontent.com",
#   "aud": "822395763299-bvpb2v7rqiie8cclmurkjp1cbimnjcim.apps.googleusercontent.com",
#   "sub": "112140776228397840933", --> Google User ID
#   "email": "koojh74@gmail.com",
#   "email_verified": true,
#   "at_hash": "ZengSdWhIwvrSl-HVmneSg",
#   "name": "Jahyoung Koo",
#   "picture": "https://lh3.googleusercontent.com/a/ACg8ocLS7RplK7XeL-vxp6pQftcTz_F3gRhofnHMIVLl3whYMDCxFg33=s96-c",
#   "given_name": "Jahyoung",
#   "family_name": "Koo",
#   "iat": 1750235332,
#   "exp": 1750238932
# }
