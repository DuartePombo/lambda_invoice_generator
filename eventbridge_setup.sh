#!/usr/bin/env bash
# Run once to schedule the Lambda on the *last* day of each month.
set -euo pipefail

REGION="eu-west-1"
RULE_NAME="LastDayOfMonthRule"
LAMBDA_NAME="SendMonthlyInvoice"
STATEMENT_ID="EventBridgeInvoke-${RULE_NAME}"

# 1) Create or update the EventBridge rule (00:05 UTC on last day of month)
aws events put-rule \
    --region "$REGION" \
    --name   "$RULE_NAME" \
    --schedule-expression "cron(5 0 L * ? *)"

# 2) Attach the Lambda as the target
TARGET_ARN=$(aws lambda get-function \
               --region "$REGION" \
               --function-name "$LAMBDA_NAME" \
               --query 'Configuration.FunctionArn' --output text)

aws events put-targets --region "$REGION" \
    --rule "$RULE_NAME" \
    --targets "Id"="1","Arn"="$TARGET_ARN"

# 3) Allow EventBridge to invoke the function (idempotent)
aws lambda add-permission \
    --region "$REGION" \
    --function-name "$LAMBDA_NAME" \
    --statement-id "$STATEMENT_ID" \
    --action 'lambda:InvokeFunction' \
    --principal events.amazonaws.com \
    --source-arn "$(aws events describe-rule --name $RULE_NAME --region $REGION --query Arn --output text)" \
    2>/dev/null || echo "Permission already exists, skipping."

echo "⏰  EventBridge rule '${RULE_NAME}' is in place."
