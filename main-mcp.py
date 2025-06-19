"""
Cloud Run용 MCP (Model Context Protocol) Server

간단한 날씨 정보를 제공하는 테스트용 MCP 서버입니다.
"""

# import os
# import logging
# from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import FastMCP
# import uvicorn

# 로깅 설정
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
# )
# logger = logging.getLogger("mcp-server")

# FastMCP 서버 초기화
# mcp = FastMCP("standard_mcp_foottraffic")
mcp = FastMCP(
    name="Simple MCP Server",
    host="0.0.0.0", 
    port=8080,
    debug=True
)

# Add an foot traffic data tool
@mcp.tool()
async def todo_list() -> list:
    """Get todo list for authenticated user"""
    
    # 인증된 사용자 정보 접근
    # logger.info("Fetching todo list for authenticated user")
    
    todo_list = [
        {"id": 1, "title": "MCP 서버 배포", "completed": False},
        {"id": 2, "title": "MCP 서버 테스트", "completed": False},
        {"id": 3, "title": "MCP 서버 문서 작성", "completed": False},
    ]
    
    return todo_list


# 메인 실행 지점
if __name__ == "__main__":
    # 환경 변수에서 포트 가져오기 (Cloud Run용)
    # port = int(os.environ.get("PORT", 8080))    
    # logger.info(f"MCP 서버 시작 중... 포트: {port}")
    
    # FastMCP 인스턴스에서 SSE 앱 가져오기
    # app = mcp.sse_app()
    
    # Uvicorn으로 앱 실행
    # uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    mcp.run(transport='sse')

