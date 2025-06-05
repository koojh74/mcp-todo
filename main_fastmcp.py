# server.py

from fastmcp import FastMCP
from datetime import datetime, timedelta
# import datetime
import os

mcp = FastMCP(
    name="foottraffic-remote",
    instructions="get foot traffic data of department store"
)


# @mcp.tool()
# def current_datetime(timezone: str = "America/New_York") -> str:
#     """
#     Returns the current date and time as a string. 
#     If you are asked for the current date or time, call this function.
#     Args:
#         timezone: Timezone name (e.g., 'UTC', 'US/Pacific', 'Europe/London').
#                  Defaults to 'America/New_York'.
    
#     Returns:
#         A formatted date and time string.
#     """
    
#     try:
#         tz = pytz.timezone(timezone)
#         now = datetime.datetime.now(tz)
#         return now.strftime("%Y-%m-%d %H:%M:%S %Z")
#     except pytz.exceptions.UnknownTimeZoneError:
#         return f"Error: Unknown timezone '{timezone}'. Please use a valid timezone name."


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


if __name__ == "__main__":
    import asyncio
    # port = int(os.environ.get("PORT", 8080))
    asyncio.run(
        mcp.run_sse_async(
            host="0.0.0.0",  # Changed from 127.0.0.1 to allow external connections
            port=8080,
            log_level="debug"
        )
    )