"""
Cloud Run용 MCP (Model Context Protocol) Server

간단한 날씨 정보를 제공하는 테스트용 MCP 서버입니다.
"""

import os
import logging
from mcp.server.fastmcp import FastMCP
import uvicorn
from datetime import datetime, timedelta

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp-server")

# FastMCP 서버 초기화
mcp = FastMCP("standard_mcp_foottraffic")

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



# 메인 실행 지점
if __name__ == "__main__":
    # 환경 변수에서 포트 가져오기 (Cloud Run용)
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"MCP 서버 시작 중... 포트: {port}")
    
    # FastMCP 인스턴스에서 SSE 앱 가져오기
    app = mcp.sse_app()
    
    # # Uvicorn으로 앱 실행
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    # mcp.run(transport='sse')
