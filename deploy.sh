#!/usr/bin/env bash
# Build, push and deploy the Lambda container image.
set -euo pipefail

# ── Config ────────────────────────────────────────────────
REGION="eu-west-1"
REPO_NAME="invoice-lambda"
LAMBDA_NAME="SendMonthlyInvoice"
ROLE_NAME="lambda-basic-execution"   # IAM role ARN tail
IMAGE_TAG="latest"
DOCKERFILE="Dockerfile.lambda"
ENV_FILE=".env"                      # local env file to sync
# ───────────────────────────────────────────────────────────

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
IMAGE_URI="${ECR_URI}/${REPO_NAME}:${IMAGE_TAG}"

# 1) Making sure the ECR repo exists ------------------------------------------------
aws ecr describe-repositories \
    --repository-names "$REPO_NAME" --region "$REGION" >/dev/null 2>&1 ||
aws ecr create-repository \
    --repository-name "$REPO_NAME" --region "$REGION"

# 2) Docker login -> build -> push --------------------------------------------------
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "$ECR_URI"

docker build -t "${REPO_NAME}:${IMAGE_TAG}" -f "$DOCKERFILE" .
docker tag  "${REPO_NAME}:${IMAGE_TAG}" "$IMAGE_URI"
docker push "$IMAGE_URI"

# 3) Create function first time, otherwise just update the image ------------------
if aws lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Updating Lambda image…"
  aws lambda update-function-code \
      --region "$REGION" \
      --function-name "$LAMBDA_NAME" \
      --image-uri "$IMAGE_URI"
else
  echo "Creating Lambda…"
  aws lambda create-function \
      --region "$REGION" \
      --function-name "$LAMBDA_NAME" \
      --package-type Image \
      --code ImageUri="$IMAGE_URI" \
      --role "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
fi

# 4) Sync .env -> Lambda environment variables -------------------------------------
if [[ -f "$ENV_FILE" ]]; then
  echo "Syncing $ENV_FILE into function configuration…"

  # Build a compact JSON object from KEY=VAL lines, stripping surrounding quotes.
  JSON_VARS=$(awk -F= '
    /^[A-Za-z0-9_]+=/{                      # only real KEY=VAL lines
        key=$1
        val=$2
        sub(/^"/, "", val); sub(/"$/, "", val)   # drop outer quotes if present
        gsub(/"/, "\\\\\"", val)                 # escape interior quotes
        vars[key]=val
    }
    END{
        printf "{"
        first=1
        for(k in vars){
            if(!first) printf ","
            printf "\"%s\":\"%s\"", k, vars[k]
            first=0
        }
        printf "}"
    }' "$ENV_FILE")

  aws lambda update-function-configuration \
      --region "$REGION" \
      --function-name "$LAMBDA_NAME" \
      --environment "Variables=${JSON_VARS}"
fi

echo "OK!  Deploy complete - Lambda now uses image: $IMAGE_URI"
