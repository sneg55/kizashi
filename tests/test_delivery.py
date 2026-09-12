from botocore.stub import Stubber
import boto3

from kizashi.delivery import DryRunDelivery, SesDelivery, alert_subject, delivery_from_env


def test_dry_run_is_the_default_and_never_touches_ses():
    deliverer = delivery_from_env({})
    assert isinstance(deliverer, DryRunDelivery)
    first = deliverer.deliver("223456789", "2027-05-15", "subject", "note")
    again = deliverer.deliver("223456789", "2027-05-15", "subject", "note")
    assert first.channel == "dry-run"
    assert first.delivery_id.startswith("dry-run-")
    assert first == again


def test_ses_needs_sender_recipient_and_the_explicit_send_flag():
    partial = {"KIZASHI_SES_FROM": "alerts@example.org", "KIZASHI_SES_TO": "grants@example.org"}
    assert isinstance(delivery_from_env(partial), DryRunDelivery)
    full = dict(partial, KIZASHI_SES_SEND="1", AWS_REGION="us-west-2")
    deliverer = delivery_from_env(full)
    assert isinstance(deliverer, SesDelivery)
    assert deliverer.region == "us-west-2"


def test_ses_delivery_sends_the_note_verbatim_through_sesv2():
    client = boto3.client("sesv2", region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test")
    subject = alert_subject("TERRAPIN CLUB", "2027-05-15")
    note = "Note for the grants lead: TERRAPIN CLUB, EIN 03-0564207. Please contact the organization."
    with Stubber(client) as stub:
        stub.add_response(
            "send_email",
            {"MessageId": "0100018f-test-message-id"},
            {
                "FromEmailAddress": "alerts@example.org",
                "Destination": {"ToAddresses": ["grants@example.org"]},
                "Content": {
                    "Simple": {
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": {"Text": {"Data": note, "Charset": "UTF-8"}},
                    }
                },
            },
        )
        delivery = SesDelivery("alerts@example.org", "grants@example.org", client=client).deliver(
            "030564207", "2027-05-15", subject, note
        )
        stub.assert_no_pending_responses()
    assert delivery.channel == "ses"
    assert delivery.delivery_id == "0100018f-test-message-id"
