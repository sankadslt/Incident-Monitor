import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def send_email_api(payload, timeout=30):
    target_url = payload.get("ConfiguredEmailApiUrl")
    if not target_url:
        return {"status": "error", "reason": "ConfiguredEmailApiUrl is missing"}

    request_payload = dict(payload)
    request_payload.pop("ConfiguredEmailApiUrl", None)

    body = json.dumps(request_payload).encode("utf-8")
    
    # Do not print full payload to terminal; log metadata only
    logger = logging.getLogger('appLogger')
    logger.debug("Sending payload to %s — keys=%d, size=%d bytes", target_url, len(request_payload), len(body))
    request = Request(
        target_url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw_response = response.read().decode("utf-8")
            try:
                response_body = json.loads(raw_response) if raw_response else {}
            except json.JSONDecodeError:
                response_body = raw_response

            return {
                "status": "sent",
                "http_status": getattr(response, "status", 200),
                "response": response_body,
                "details": response_body.get("details") if isinstance(response_body, dict) else None,
            }
    except HTTPError as err:
        error_text = err.read().decode("utf-8") if err.fp else str(err)
        return {
            "status": "error",
            "reason": f"HTTP {err.code}: {error_text}",
        }
    except URLError as err:
        return {
            "status": "error",
            "reason": f"Unable to reach email API: {err.reason}",
        }