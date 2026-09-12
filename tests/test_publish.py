import json

import boto3
from botocore.stub import ANY, Stubber

from kizashi.publish import pull_state, publish_run

BUCKET = "kizashi-runs-test"
REPORT = {"run_id": "2026-09-12T12-00-00Z-portfolio-nj-086", "summary": {"alerts_sent": 1, "alerts_held": 2}}
ALERTS = {"123456789:2026-11-15": {"status": "sent"}}


def _client():
    return boto3.client("s3", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="y")


def _report_dirs(tmp_path):
    runs = tmp_path / "runs"
    state = tmp_path / "state"
    runs.mkdir()
    state.mkdir()
    (runs / "latest.json").write_text(json.dumps(REPORT))
    (state / "alerts.json").write_text(json.dumps(ALERTS))
    return runs, state


def test_publish_writes_run_latest_and_state_keys(tmp_path):
    runs, state = _report_dirs(tmp_path)
    client = _client()
    stubber = Stubber(client)
    for key in (
        f"runs/{REPORT['run_id']}.json",
        "runs/latest.json",
        "state/alerts.json",
    ):
        stubber.add_response(
            "put_object",
            {},
            {"Bucket": BUCKET, "Key": key, "Body": ANY, "ContentType": "application/json"},
        )
    with stubber:
        written = publish_run(BUCKET, "", runs, state, client)
    stubber.assert_no_pending_responses()
    assert written == [f"runs/{REPORT['run_id']}.json", "runs/latest.json", "state/alerts.json"]


def test_publish_honours_prefix(tmp_path):
    runs, state = _report_dirs(tmp_path)
    client = _client()
    stubber = Stubber(client)
    for key in (
        f"kizashi/runs/{REPORT['run_id']}.json",
        "kizashi/runs/latest.json",
        "kizashi/state/alerts.json",
    ):
        stubber.add_response(
            "put_object",
            {},
            {"Bucket": BUCKET, "Key": key, "Body": ANY, "ContentType": "application/json"},
        )
    with stubber:
        written = publish_run(BUCKET, "kizashi", runs, state, client)
    stubber.assert_no_pending_responses()
    assert written[1] == "kizashi/runs/latest.json"


def test_publish_skips_state_when_absent(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "latest.json").write_text(json.dumps(REPORT))
    client = _client()
    stubber = Stubber(client)
    for key in (f"runs/{REPORT['run_id']}.json", "runs/latest.json"):
        stubber.add_response(
            "put_object",
            {},
            {"Bucket": BUCKET, "Key": key, "Body": ANY, "ContentType": "application/json"},
        )
    with stubber:
        written = publish_run(BUCKET, "", runs, tmp_path / "state", client)
    stubber.assert_no_pending_responses()
    assert written == [f"runs/{REPORT['run_id']}.json", "runs/latest.json"]


def test_pull_state_writes_file(tmp_path):
    client = _client()
    stubber = Stubber(client)
    body = json.dumps(ALERTS).encode()
    stubber.add_response(
        "get_object",
        {"Body": _stream(body)},
        {"Bucket": BUCKET, "Key": "state/alerts.json"},
    )
    state = tmp_path / "state"
    with stubber:
        key = pull_state(BUCKET, "", state, client)
    assert key == "state/alerts.json"
    assert json.loads((state / "alerts.json").read_text()) == ALERTS


def test_pull_state_returns_none_when_missing(tmp_path):
    client = _client()
    stubber = Stubber(client)
    stubber.add_client_error("get_object", service_error_code="NoSuchKey", http_status_code=404)
    state = tmp_path / "state"
    with stubber:
        assert pull_state(BUCKET, "", state, client) is None
    assert not (state / "alerts.json").exists()


def _stream(payload: bytes):
    from botocore.response import StreamingBody
    from io import BytesIO

    return StreamingBody(BytesIO(payload), len(payload))
