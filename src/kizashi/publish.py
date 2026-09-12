import argparse
import json
from pathlib import Path
from typing import Any

STATE_KEY = "state/alerts.json"
LATEST_KEY = "runs/latest.json"
CONTENT_TYPE = "application/json"
DEFAULT_REGION = "us-east-1"


def _client(region: str) -> Any:
    import boto3

    return boto3.client("s3", region_name=region)


def _join(prefix: str, key: str) -> str:
    prefix = prefix.strip("/")
    return f"{prefix}/{key}" if prefix else key


def _missing_key(error: Exception) -> bool:
    code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
    return code in {"NoSuchKey", "404", "NotFound"}


def pull_state(bucket: str, prefix: str, state_dir: Path, client: Any) -> str | None:
    from botocore.exceptions import ClientError

    key = _join(prefix, STATE_KEY)
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except ClientError as error:
        if _missing_key(error):
            return None
        raise
    body = response["Body"].read()
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "alerts.json").write_bytes(body)
    return key


def publish_run(bucket: str, prefix: str, runs_dir: Path, state_dir: Path, client: Any) -> list[str]:
    latest = runs_dir / "latest.json"
    if not latest.exists():
        raise SystemExit(f"no report at {latest}")
    payload = latest.read_bytes()
    run_id = json.loads(payload)["run_id"]
    written = []
    for key in (f"runs/{run_id}.json", LATEST_KEY):
        full = _join(prefix, key)
        client.put_object(Bucket=bucket, Key=full, Body=payload, ContentType=CONTENT_TYPE)
        written.append(full)
    alerts = state_dir / "alerts.json"
    if alerts.exists():
        full = _join(prefix, STATE_KEY)
        client.put_object(Bucket=bucket, Key=full, Body=alerts.read_bytes(), ContentType=CONTENT_TYPE)
        written.append(full)
    return written


def cmd_publish(args: argparse.Namespace) -> None:
    client = _client(args.region)
    for key in publish_run(args.bucket, args.prefix, Path(args.runs), Path(args.state), client):
        print(f"put s3://{args.bucket}/{key}")


def cmd_pull_state(args: argparse.Namespace) -> None:
    client = _client(args.region)
    key = pull_state(args.bucket, args.prefix, Path(args.state), client)
    if key is None:
        print(f"no state at s3://{args.bucket}/{_join(args.prefix, STATE_KEY)}")
    else:
        print(f"got s3://{args.bucket}/{key}")


def add_parsers(sub: Any) -> None:
    publish_p = sub.add_parser("publish")
    publish_p.add_argument("--bucket", required=True)
    publish_p.add_argument("--prefix", default="")
    publish_p.add_argument("--region", default=DEFAULT_REGION)
    publish_p.add_argument("--runs", default="data/runs")
    publish_p.add_argument("--state", default="data/state")
    publish_p.set_defaults(func=cmd_publish)

    pull_p = sub.add_parser("pull-state")
    pull_p.add_argument("--bucket", required=True)
    pull_p.add_argument("--prefix", default="")
    pull_p.add_argument("--region", default=DEFAULT_REGION)
    pull_p.add_argument("--state", default="data/state")
    pull_p.set_defaults(func=cmd_pull_state)
