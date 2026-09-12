import hashlib
import os
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

SES_FROM_ENV = "KIZASHI_SES_FROM"
SES_TO_ENV = "KIZASHI_SES_TO"
SES_SEND_ENV = "KIZASHI_SES_SEND"
DEFAULT_REGION = "us-east-1"


@dataclass(frozen=True)
class Delivery:
    channel: str
    delivery_id: str


class Deliverer(Protocol):
    channel: str

    def deliver(self, ein: str, predicted: str, subject: str, message: str) -> Delivery: ...


class DryRunDelivery:
    channel = "dry-run"

    def deliver(self, ein: str, predicted: str, subject: str, message: str) -> Delivery:
        digest = hashlib.sha256(f"{ein}:{predicted}".encode()).hexdigest()[:12]
        return Delivery(channel=self.channel, delivery_id=f"dry-run-{digest}")


class SesDelivery:
    channel = "ses"

    def __init__(self, sender: str, recipient: str, region: str = DEFAULT_REGION, client: Any = None) -> None:
        self.sender = sender
        self.recipient = recipient
        self.region = region
        self._client = client

    def client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("sesv2", region_name=self.region)
        return self._client

    def deliver(self, ein: str, predicted: str, subject: str, message: str) -> Delivery:
        response = self.client().send_email(
            FromEmailAddress=self.sender,
            Destination={"ToAddresses": [self.recipient]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": message, "Charset": "UTF-8"}},
                }
            },
        )
        return Delivery(channel=self.channel, delivery_id=response["MessageId"])


def alert_subject(name: str, predicted: str) -> str:
    return f"Kizashi: {name} loses exempt status on {predicted} unless it files"


def delivery_from_env(env: Mapping[str, str] | None = None) -> Deliverer:
    e = os.environ if env is None else env
    sender = e.get(SES_FROM_ENV, "").strip()
    recipient = e.get(SES_TO_ENV, "").strip()
    if sender and recipient and e.get(SES_SEND_ENV, "").strip() == "1":
        return SesDelivery(sender, recipient, e.get("AWS_REGION", DEFAULT_REGION))
    return DryRunDelivery()
