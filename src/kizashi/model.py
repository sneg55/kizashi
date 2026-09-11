import os

from strands.models.model import Model

DEFAULT_PROVIDER = "mantle"
DEFAULT_MANTLE_MODEL_ID = "google.gemma-4-31b"
DEFAULT_ANTHROPIC_MODEL_ID = "claude-sonnet-5"
DEFAULT_REGION = "us-east-1"
MAX_TOKENS = 8000
RESPONSES_MODEL_PREFIXES = ("openai.gpt-oss",)


def _provider() -> str:
    return os.environ.get("KIZASHI_MODEL_PROVIDER", DEFAULT_PROVIDER).strip().lower()


def _region() -> str:
    return os.environ.get("AWS_REGION", DEFAULT_REGION)


def _model_id(provider: str) -> str:
    default = DEFAULT_ANTHROPIC_MODEL_ID if provider == "anthropic" else DEFAULT_MANTLE_MODEL_ID
    return os.environ.get("KIZASHI_MODEL_ID", default)


def model_descriptor() -> dict:
    provider = _provider()
    model_id = _model_id(provider)
    if provider == "anthropic":
        return {"provider": "anthropic", "model_id": model_id, "region": None}
    return {"provider": "bedrock-mantle", "model_id": model_id, "region": _region()}


def make_model() -> Model:
    provider = _provider()
    model_id = _model_id(provider)
    if provider == "anthropic":
        from strands.models.anthropic import AnthropicModel

        return AnthropicModel(
            client_args={"api_key": os.environ["ANTHROPIC_API_KEY"]},
            model_id=model_id,
            max_tokens=MAX_TOKENS,
        )
    mantle_config = {"region": _region()}
    if model_id.startswith(RESPONSES_MODEL_PREFIXES):
        from strands.models.openai_responses import OpenAIResponsesModel

        return OpenAIResponsesModel(
            bedrock_mantle_config=mantle_config,
            model_id=model_id,
            params={"max_output_tokens": MAX_TOKENS, "temperature": 0},
        )
    from strands.models.openai import OpenAIModel

    return OpenAIModel(
        bedrock_mantle_config=mantle_config,
        model_id=model_id,
        params={"max_tokens": MAX_TOKENS, "temperature": 0},
    )


def aws_session_live() -> bool:
    if _provider() == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    try:
        import boto3

        boto3.client("sts", region_name=_region()).get_caller_identity()
        return True
    except Exception:
        return False
