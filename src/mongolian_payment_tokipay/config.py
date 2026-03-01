"""Environment-based configuration loader for TokiPay SDK."""

import os

from .types import TokiPayConfig


def load_config_from_env() -> TokiPayConfig:
    """Load TokiPay configuration from environment variables.

    Required environment variables:
        TOKIPAY_ENDPOINT - TokiPay API base URL.
        TOKIPAY_API_KEY - API key provided by TokiPay.
        TOKIPAY_IM_API_KEY - IM API key for POS endpoints.
        TOKIPAY_AUTHORIZATION - Authorization token string.
        TOKIPAY_MERCHANT_ID - Merchant ID assigned by TokiPay.
        TOKIPAY_SUCCESS_URL - Default success redirect URL.
        TOKIPAY_FAILURE_URL - Default failure redirect URL.

    Optional environment variables:
        TOKIPAY_APP_SCHEMA_IOS - iOS app schema for deeplinks.

    Returns:
        A populated TokiPayConfig instance.

    Raises:
        ValueError: If any required variable is missing.
    """
    required = [
        ("endpoint", "TOKIPAY_ENDPOINT"),
        ("api_key", "TOKIPAY_API_KEY"),
        ("im_api_key", "TOKIPAY_IM_API_KEY"),
        ("authorization", "TOKIPAY_AUTHORIZATION"),
        ("merchant_id", "TOKIPAY_MERCHANT_ID"),
        ("success_url", "TOKIPAY_SUCCESS_URL"),
        ("failure_url", "TOKIPAY_FAILURE_URL"),
    ]

    values = {}
    missing = []

    for key, env_var in required:
        value = os.environ.get(env_var)
        if not value:
            missing.append(env_var)
        else:
            values[key] = value

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    app_schema_ios = os.environ.get("TOKIPAY_APP_SCHEMA_IOS")
    if app_schema_ios:
        values["app_schema_ios"] = app_schema_ios

    return TokiPayConfig(**values)
