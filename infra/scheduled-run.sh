#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="kizashi-runs-${ACCOUNT}"
REPO="kizashi"
CLUSTER="kizashi"
FAMILY="kizashi-sweep"
LOG_GROUP="/kizashi/scheduled-run"
SCHEDULE="kizashi-monthly"
CRON="cron(0 12 7 * ? *)"
EXEC_ROLE="kizashi-task-execution"
TASK_ROLE="kizashi-task"
SCHED_ROLE="kizashi-scheduler"
SG_NAME="kizashi-task"
IMAGE_TAG="${KIZASHI_IMAGE_TAG:-latest}"
OUT_DIR="${KIZASHI_INFRA_OUT:-${TMPDIR:-/tmp}/kizashi-infra}"
SCHEDULE_ARN=""

aws() { command aws --region "$REGION" "$@"; }

mkdir -p "$OUT_DIR"

if ! aws s3api head-bucket --bucket "$BUCKET" >/dev/null 2>&1; then
  aws s3api create-bucket --bucket "$BUCKET" >/dev/null
fi
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

if ! aws ecr describe-repositories --repository-names "$REPO" >/dev/null 2>&1; then
  aws ecr create-repository --repository-name "$REPO" --image-tag-mutability MUTABLE >/dev/null
fi
REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

if ! aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'] | [0].logGroupName" --output text | grep -q "$LOG_GROUP"; then
  aws logs create-log-group --log-group-name "$LOG_GROUP"
  aws logs put-retention-policy --log-group-name "$LOG_GROUP" --retention-in-days 30
fi

ensure_role() {
  local name="$1" service="$2"
  if aws iam get-role --role-name "$name" >/dev/null 2>&1; then
    return
  fi
  aws iam create-role --role-name "$name" --assume-role-policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Principal\": {\"Service\": \"${service}\"},
      \"Action\": \"sts:AssumeRole\"
    }]
  }" >/dev/null
}

ensure_role "$EXEC_ROLE" "ecs-tasks.amazonaws.com"
aws iam attach-role-policy --role-name "$EXEC_ROLE" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

ensure_role "$TASK_ROLE" "ecs-tasks.amazonaws.com"
aws iam put-role-policy --role-name "$TASK_ROLE" --policy-name kizashi-task-access --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Action\": [\"s3:GetObject\", \"s3:PutObject\", \"s3:DeleteObject\"],
      \"Resource\": \"arn:aws:s3:::${BUCKET}/*\"
    },
    {
      \"Effect\": \"Allow\",
      \"Action\": [\"s3:ListBucket\", \"s3:GetBucketLocation\"],
      \"Resource\": \"arn:aws:s3:::${BUCKET}\"
    },
    {
      \"Effect\": \"Allow\",
      \"Action\": [
        \"bedrock:CallWithBearerToken\",
        \"bedrock:InvokeModel\",
        \"bedrock:InvokeModelWithResponseStream\",
        \"bedrock-mantle:*\"
      ],
      \"Resource\": \"*\"
    }
  ]
}"

ensure_role "$SCHED_ROLE" "scheduler.amazonaws.com"
aws iam put-role-policy --role-name "$SCHED_ROLE" --policy-name kizashi-scheduler-runtask --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Action\": \"ecs:RunTask\",
      \"Resource\": \"arn:aws:ecs:${REGION}:${ACCOUNT}:task-definition/${FAMILY}:*\",
      \"Condition\": {\"ArnLike\": {\"ecs:cluster\": \"arn:aws:ecs:${REGION}:${ACCOUNT}:cluster/${CLUSTER}\"}}
    },
    {
      \"Effect\": \"Allow\",
      \"Action\": \"iam:PassRole\",
      \"Resource\": [
        \"arn:aws:iam::${ACCOUNT}:role/${EXEC_ROLE}\",
        \"arn:aws:iam::${ACCOUNT}:role/${TASK_ROLE}\"
      ],
      \"Condition\": {\"StringLike\": {\"iam:PassedToService\": \"ecs-tasks.amazonaws.com\"}}
    }
  ]
}"

CLUSTER_ARN="$(aws ecs describe-clusters --clusters "$CLUSTER" \
  --query "clusters[?status=='ACTIVE'] | [0].clusterArn" --output text)"
if [ "$CLUSTER_ARN" = "None" ] || [ -z "$CLUSTER_ARN" ]; then
  CLUSTER_ARN="$(aws ecs create-cluster --cluster-name "$CLUSTER" --query cluster.clusterArn --output text)"
fi

VPC_ID="$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)"
SUBNETS="$(aws ec2 describe-subnets \
  --filters Name=vpc-id,Values="$VPC_ID" Name=default-for-az,Values=true \
  --query "Subnets[?AvailabilityZone!='${REGION}e'].SubnetId" --output text | tr '\t' ',')"

SG_ID="$(aws ec2 describe-security-groups \
  --filters Name=vpc-id,Values="$VPC_ID" Name=group-name,Values="$SG_NAME" \
  --query 'SecurityGroups[0].GroupId' --output text)"
if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
  SG_ID="$(aws ec2 create-security-group --group-name "$SG_NAME" --vpc-id "$VPC_ID" \
    --description "kizashi scheduled sweep, egress only" --query GroupId --output text)"
fi

IMAGE_DIGEST="$(aws ecr describe-images --repository-name "$REPO" --image-ids imageTag="$IMAGE_TAG" \
  --query 'imageDetails[0].imageDigest' --output text 2>/dev/null || true)"
if [ -n "$IMAGE_DIGEST" ] && [ "$IMAGE_DIGEST" != "None" ]; then
  IMAGE="${REGISTRY}/${REPO}@${IMAGE_DIGEST}"
else
  IMAGE="${REGISTRY}/${REPO}:${IMAGE_TAG}"
fi

cat >"${OUT_DIR}/taskdef.json" <<JSON
{
  "family": "${FAMILY}",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "4096",
  "runtimePlatform": {"cpuArchitecture": "X86_64", "operatingSystemFamily": "LINUX"},
  "executionRoleArn": "arn:aws:iam::${ACCOUNT}:role/${EXEC_ROLE}",
  "taskRoleArn": "arn:aws:iam::${ACCOUNT}:role/${TASK_ROLE}",
  "containerDefinitions": [
    {
      "name": "kizashi",
      "image": "${IMAGE}",
      "essential": true,
      "environment": [
        {"name": "KIZASHI_BUCKET", "value": "${BUCKET}"},
        {"name": "AWS_REGION", "value": "${REGION}"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "${LOG_GROUP}",
          "awslogs-region": "${REGION}",
          "awslogs-stream-prefix": "sweep"
        }
      }
    }
  ]
}
JSON

TASKDEF_ARN="$(aws ecs register-task-definition --cli-input-json "file://${OUT_DIR}/taskdef.json" \
  --query taskDefinition.taskDefinitionArn --output text)"

cat >"${OUT_DIR}/network.json" <<JSON
{"awsvpcConfiguration": {"Subnets": ["$(echo "$SUBNETS" | sed 's/,/", "/g')"], "SecurityGroups": ["${SG_ID}"], "AssignPublicIp": "ENABLED"}}
JSON

cat >"${OUT_DIR}/schedule-target.json" <<JSON
{
  "Arn": "${CLUSTER_ARN}",
  "RoleArn": "arn:aws:iam::${ACCOUNT}:role/${SCHED_ROLE}",
  "EcsParameters": {
    "TaskDefinitionArn": "${TASKDEF_ARN}",
    "LaunchType": "FARGATE",
    "PlatformVersion": "LATEST",
    "TaskCount": 1,
    "NetworkConfiguration": $(cat "${OUT_DIR}/network.json")
  },
  "RetryPolicy": {"MaximumRetryAttempts": 0}
}
JSON

schedule_args=(
  --name "$SCHEDULE"
  --schedule-expression "$CRON"
  --schedule-expression-timezone UTC
  --flexible-time-window '{"Mode": "OFF"}'
  --state ENABLED
  --description "Monthly Kizashi sweep after the IRS file refresh"
  --target "file://${OUT_DIR}/schedule-target.json"
)
if aws scheduler get-schedule --name "$SCHEDULE" >/dev/null 2>&1; then
  SCHEDULE_ARN="$(aws scheduler update-schedule "${schedule_args[@]}" --query ScheduleArn --output text)"
else
  for attempt in 1 2 3; do
    if SCHEDULE_ARN="$(aws scheduler create-schedule "${schedule_args[@]}" --query ScheduleArn --output text)"; then
      break
    fi
    sleep 10
  done
fi

cat >"${OUT_DIR}/summary.env" <<ENVFILE
ACCOUNT=${ACCOUNT}
BUCKET=${BUCKET}
REGISTRY=${REGISTRY}
CLUSTER_ARN=${CLUSTER_ARN}
TASKDEF_ARN=${TASKDEF_ARN}
IMAGE=${IMAGE}
SUBNETS=${SUBNETS}
SG_ID=${SG_ID}
SCHEDULE_ARN=${SCHEDULE_ARN}
LOG_GROUP=${LOG_GROUP}
ENVFILE

cat "${OUT_DIR}/summary.env"
