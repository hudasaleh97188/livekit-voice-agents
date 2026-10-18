"""Bounded HTTP calls. No automatic replay of billable POST requests."""
import requests


def json_response(response: requests.Response):
    if not response.ok:
        hints = {401: "check the API key and API version", 402: "check account credits",
                 403: "check permissions", 429: "quota or rate limit; wait before retrying"}
        hint = hints.get(response.status_code, "check provider status and request settings")
        # Do not include request headers or raw provider bodies in error logs.
        raise RuntimeError(f"HTTP {response.status_code}: {hint}.")
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError("Provider returned a non-JSON response.") from None
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError("Provider reported an error; check its dashboard.")
    return payload


def run_cli(main) -> None:
    try:
        main()
    except (ValueError, RuntimeError, OSError, requests.RequestException) as exc:
        if isinstance(exc, requests.RequestException):
            message = "Network request failed or timed out; check connectivity and provider status."
        else:
            message = str(exc)
        raise SystemExit(message) from None

