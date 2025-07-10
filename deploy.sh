#!/bin/bash
set -e

# 변수 설정
APP_NAME=mcp-todo-app
PROJECT_ID=loplat-ai
REPO_NAME=my-repo-todo
REGION=asia-northeast3
IMAGE_URI=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${APP_NAME}:latest

echo "---------------------------"
echo "1. 도커 이미지 빌드 (amd64)..."
docker build --platform linux/amd64 -t ${APP_NAME} .

echo "---------------------------"
echo "2. GCP Artifact Registry 태그 붙이기..."
docker tag ${APP_NAME}:latest ${IMAGE_URI}

echo "---------------------------"
echo "3. 도커 이미지 푸시..."
docker push ${IMAGE_URI}

echo "---------------------------"
echo "4. Cloud Run 재배포..."
gcloud run deploy ${APP_NAME} \
  --image ${IMAGE_URI} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated

echo "---------------------------"
echo "배포 완료! Cloud Run에서 ${APP_NAME} 서비스를 확인하세요."

# repo 생성
# gcloud artifacts repositories create my-repo-todo \
#   --repository-format=docker \
#   --location=asia-northeast3 \
#   --description="Foot traffic project container repo"

# gcloud artifacts repositories delete my-repo-2 \
#   --location=asia-northeast3 \
#   --quiet