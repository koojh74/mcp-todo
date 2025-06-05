# FROM python:3.11-slim

# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY main.py .
# EXPOSE 8080

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]


FROM python:3.11-slim

WORKDIR /app

# 종속성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 파일 복사
COPY main.py .

# 포트 노출
EXPOSE 8080

# 실행 명령어
CMD ["python", "main.py"]
# CMD ["uvicorn", "main:mcp", "--host", "0.0.0.0", "--port", "8080"]
