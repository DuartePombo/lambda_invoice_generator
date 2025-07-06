#!/usr/bin/env bash
# Build, push and deploy the Lambda container image.
set -euo pipefail
export AWS_PAGER=""

# ── Config ────────────────────────────────────────────────
REGION="eu-west-1"
REPO_NAME="invoice-lambda"
LAMBDA_NAME="SendMonthlyInvoice"
ROLE_NAME="lambda-basic-execution"   # IAM role ARN tail
IMAGE_TAG="latest"
DOCKERFILE="Dockerfile.lambda"
ENV_FILE=".env"                      # local env file to sync

# Lambda Runtime limits
TIMEOUT_SECONDS=15                     # 1–900 s
MEMORY_MB=256                          # 128–10240 MB
# ──────────────────────────────────────────────────────────

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_URI="${ECR_URI}/${REPO_NAME}:${IMAGE_TAG}"

# 1) Ensure ECR repo exists
aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$REGION" >/dev/null 2>&1 ||
aws ecr create-repository --repository-name "$REPO_NAME" --region "$REGION"

# 2) Docker login → build → push
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URI"

export DOCKER_BUILDKIT=0
docker build -t "${REPO_NAME}:${IMAGE_TAG}" -f "$DOCKERFILE" .
docker tag  "${REPO_NAME}:${IMAGE_TAG}" "$IMAGE_URI"
docker push "$IMAGE_URI"

# 3) Create or update Lambda image
if aws lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Updating Lambda image…"
  aws lambda update-function-code \
      --region "$REGION" \
      --function-name "$LAMBDA_NAME" \
      --image-uri "$IMAGE_URI"

  # Wait until the code update finishes
  aws lambda wait function-updated \
      --region "$REGION" \
      --function-name "$LAMBDA_NAME"

  # apply new timeout / memory as part of the same deploy
  aws lambda update-function-configuration \
      --region "$REGION" \
      --function-name "$LAMBDA_NAME" \
      --timeout "$TIMEOUT_SECONDS" \
      --memory-size "$MEMORY_MB"

  # Wait until the code update finishes
  aws lambda wait function-updated --function-name "$LAMBDA_NAME" --region "$REGION"

else
  echo "Creating Lambda…"

  aws lambda create-function \
      --region "$REGION" \
      --function-name "$LAMBDA_NAME" \
      --package-type Image \
      --code ImageUri="$IMAGE_URI" \
      --role "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}" \
      --timeout "$TIMEOUT_SECONDS" \
      --memory-size "$MEMORY_MB"

  aws lambda wait function-active --function-name "$LAMBDA_NAME" --region "$REGION"
fi

# 4) Sync .env -> Lambda environment variables
if [[ -f "$ENV_FILE" ]]; then
  echo "Syncing $ENV_FILE into function configuration…"

  JSON_VARS=$(awk -F= '
      /^[A-Za-z0-9_]+=/{ key=$1; val=$2;
          gsub(/\r/,"",key); gsub(/\r/,"",val);
          sub(/^"/,"",val); sub(/"$/,"",val);
          gsub(/"/,"\\\"",val); vars[key]=val }
      END{
          printf "{"; first=1;
          for(k in vars){
              if(!first) printf ",";
              printf "\""k"\":\""vars[k]"\""; first=0 }
          printf "}" }' "$ENV_FILE")

  ENV_JSON=$(printf '{"Variables":%s}' "$JSON_VARS")
  # echo "DEBUG ENV_JSON=$ENV_JSON"   # uncomment to inspect if environ var are being correclty parsed

  aws lambda update-function-configuration \
      --region "$REGION" \
      --function-name "$LAMBDA_NAME" \
      --environment "$ENV_JSON"
fi

unset DOCKER_BUILDKIT
echo "OK!  Deploy complete - Lambda now uses image: $IMAGE_URI"
