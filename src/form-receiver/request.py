import base64
import logging
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)


def parse_form_request(event: dict) -> dict:
    body = event.get("body", "")
    is_base64 = event.get("isBase64Encoded", False)

    if is_base64 and body:
        body = base64.b64decode(body).decode("utf-8")

    try:
        parsed = parse_qs(body)
        return {key: values[0] for key, values in parsed.items()}
    except Exception as exc:
        logger.error(f"Failed to parse request body: {exc}")
        return {}
