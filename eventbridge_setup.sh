#!/usr/bin/env bash
set -euo pipefail
export AWS_PAGER=""

# ─── Configuration ───────────────────────────────────────────────────────
REGION="eu-west-1"

LAMBDA_NAME="SendMonthlyInvoice"

SCHEDULE_NAME="LastDay-0800-Ireland"
TIME_ZONE="Europe/Dublin"                 # auto-handles DST
CRON_EXPR="cron(0 8 L * ? *)"             # 8:00 on **L**ast day of month

ROLE_NAME="SchedulerInvokeLambda"
# ─────────────────────────────────────────────────────────────────────────

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
FN_ARN=$(aws lambda get-function --function-name "$LAMBDA_NAME" --region "$REGION" \
           --query 'Configuration.FunctionArn' --output text)

########################################
# 1) Ensure the role exists & is ready #
########################################
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  echo "Creating IAM role $ROLE_NAME …"
  aws iam create-role --role-name "$ROLE_NAME" \
      --assume-role-policy-document '{
        "Version":"2012-10-17",
        "Statement":[{
          "Effect":"Allow",
          "Principal":{"Service":"scheduler.amazonaws.com"},
          "Action":"sts:AssumeRole"
        }]
      }'
fi

aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaRole || true

########################################
# 2) Create or update the schedule     #
########################################
if aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$REGION" >/dev/null 2>&1; then
  echo "Updating existing schedule $SCHEDULE_NAME …"
  aws scheduler update-schedule \
      --name "$SCHEDULE_NAME" \
      --region "$REGION" \
      --schedule-expression "$CRON_EXPR" \
      --schedule-expression-timezone "$TIME_ZONE" \
      --target "{\"Arn\":\"$FN_ARN\",\"RoleArn\":\"$ROLE_ARN\"}" \
      --flexible-time-window '{"Mode":"OFF"}' \
      --description "Run $LAMBDA_NAME at 8:00 on the last day of each month (Ireland time)"
else
  echo "Creating new schedule $SCHEDULE_NAME …"
  aws scheduler create-schedule \
      --name "$SCHEDULE_NAME" \
      --region "$REGION" \
      --schedule-expression "$CRON_EXPR" \
      --schedule-expression-timezone "$TIME_ZONE" \
      --target "{\"Arn\":\"$FN_ARN\",\"RoleArn\":\"$ROLE_ARN\"}" \
      --flexible-time-window '{"Mode":"OFF"}' \
      --description "Run $LAMBDA_NAME at 8:00 on the last day of each month (Ireland time)"
fi

echo "OK! Scheduler '$SCHEDULE_NAME' is now configured."
