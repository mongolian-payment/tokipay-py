"""Tests for the TokiPay payment SDK."""

import os
from unittest.mock import patch

import httpx
import pytest

from mongolian_payment_tokipay import (
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_EXPIRED,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    AsyncTokiPayClient,
    TokiPayClient,
    TokiPayConfig,
    TokiPayError,
    TokiPayPaymentInput,
    TokiPayRefundInput,
    load_config_from_env,
)

# ── Fixtures ──


@pytest.fixture
def config() -> TokiPayConfig:
    return TokiPayConfig(
        endpoint="https://api.tokipay.test/",
        api_key="test_api_key",
        im_api_key="test_im_api_key",
        authorization="test_auth_token",
        merchant_id="test_merchant",
        success_url="https://example.com/success",
        failure_url="https://example.com/failure",
        app_schema_ios="myapp://",
    )


@pytest.fixture
def payment_input() -> TokiPayPaymentInput:
    return TokiPayPaymentInput(
        order_id="ORD-001",
        amount=10000,
        notes="Test payment",
    )


@pytest.fixture
def refund_input() -> TokiPayRefundInput:
    return TokiPayRefundInput(
        request_id="req-123",
        refund_amount=5000,
    )


def _make_json_response(
    status_code: int,
    json_data: dict,
    method: str = "POST",
    url: str = "https://api.tokipay.test/test",
) -> httpx.Response:
    """Helper to build a mock httpx.Response with JSON content."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request(method, url),
    )


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for order status constants."""

    def test_order_status_paid(self) -> None:
        assert ORDER_STATUS_PAID == "APPROVED"

    def test_order_status_completed(self) -> None:
        assert ORDER_STATUS_COMPLETED == "COMPLETED"

    def test_order_status_pending(self) -> None:
        assert ORDER_STATUS_PENDING == "PENDING"

    def test_order_status_canceled(self) -> None:
        assert ORDER_STATUS_CANCELED == "EXPIRED"

    def test_order_status_expired(self) -> None:
        assert ORDER_STATUS_EXPIRED == "EXPIRED"


# ============================================================================
# Sync Client Tests
# ============================================================================


class TestTokiPayClient:
    """Tests for the synchronous TokiPayClient."""

    def test_constructor_strips_trailing_slash(self, config: TokiPayConfig) -> None:
        client = TokiPayClient(config)
        assert client._endpoint == "https://api.tokipay.test"

    def test_constructor_strips_multiple_trailing_slashes(self) -> None:
        cfg = TokiPayConfig(
            endpoint="https://api.tokipay.test///",
            api_key="k",
            im_api_key="ik",
            authorization="auth",
            merchant_id="m",
            success_url="https://ok.test",
            failure_url="https://fail.test",
        )
        client = TokiPayClient(cfg)
        assert client._endpoint == "https://api.tokipay.test"

    def test_constructor_requires_endpoint(self) -> None:
        with pytest.raises(ValueError, match="endpoint is required"):
            TokiPayClient(
                TokiPayConfig(
                    endpoint="",
                    api_key="k",
                    im_api_key="ik",
                    authorization="auth",
                    merchant_id="m",
                    success_url="https://ok.test",
                    failure_url="https://fail.test",
                )
            )

    def test_constructor_requires_authorization(self) -> None:
        with pytest.raises(ValueError, match="authorization is required"):
            TokiPayClient(
                TokiPayConfig(
                    endpoint="https://api.tokipay.test",
                    api_key="k",
                    im_api_key="ik",
                    authorization="",
                    merchant_id="m",
                    success_url="https://ok.test",
                    failure_url="https://fail.test",
                )
            )

    def test_payment_qr(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"requestId": "req-abc"},
                "type": "QR",
            },
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.payment_qr(payment_input)

            mock.assert_called_once()
            call_args = mock.call_args
            assert call_args.args[0] == "POST"
            body = call_args.kwargs["json"]

            assert body["orderId"] == "ORD-001"
            assert body["amount"] == 10000
            assert body["notes"] == "Test payment"
            assert body["merchantId"] == "test_merchant"
            assert body["successUrl"] == "https://example.com/success"
            assert body["failureUrl"] == "https://example.com/failure"
            assert body["authorization"] == "test_auth_token"

            # Check headers
            headers = call_args.kwargs["headers"]
            assert headers["api_key"] == "spos_pay_v4"
            assert headers["im_api_key"] == "test_im_api_key"
            assert headers["Authorization"] == "test_auth_token"

        assert result.status_code == 200
        assert result.data.request_id == "req-abc"
        assert result.type == "QR"

    def test_payment_send_to_user(
        self, config: TokiPayConfig
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"requestId": "req-user"},
                "type": "USER",
            },
        )

        client = TokiPayClient(config)
        inp = TokiPayPaymentInput(
            order_id="ORD-002",
            amount=5000,
            notes="Send to user",
            phone_no="99887766",
            country_code="+976",
        )

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.payment_send_to_user(inp)

            body = mock.call_args.kwargs["json"]
            assert body["phoneNo"] == "99887766"
            assert body["countryCode"] == "+976"

        assert result.data.request_id == "req-user"

    def test_payment_scan_user(
        self, config: TokiPayConfig
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"requestId": "req-scan"},
                "type": "SCAN",
            },
        )

        client = TokiPayClient(config)
        inp = TokiPayPaymentInput(
            order_id="ORD-003",
            amount=3000,
            notes="Scan user",
            request_id="user-qr-123",
        )

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.payment_scan_user(inp)

            body = mock.call_args.kwargs["json"]
            assert body["requestId"] == "user-qr-123"

        assert result.data.request_id == "req-scan"

    def test_payment_status(self, config: TokiPayConfig) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"status": "APPROVED"},
                "type": "STATUS",
            },
            method="GET",
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.payment_status("req-abc")

            call_args = mock.call_args
            assert call_args.args[0] == "GET"
            url = call_args.args[1]
            assert "requestId=req-abc" in url

        assert result.data.status == "APPROVED"

    def test_payment_cancel(self, config: TokiPayConfig) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Cancelled",
                "responseType": "CANCEL",
            },
            method="DELETE",
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.payment_cancel("req-cancel")

            call_args = mock.call_args
            assert call_args.args[0] == "DELETE"
            assert "requestId=req-cancel" in call_args.args[1]

        assert result.response_type == "CANCEL"

    def test_payment_refund(
        self, config: TokiPayConfig, refund_input: TokiPayRefundInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Refunded",
                "responseType": "REFUND",
            },
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.payment_refund(refund_input)

            call_args = mock.call_args
            assert call_args.args[0] == "PUT"
            body = call_args.kwargs["json"]
            assert body["requestId"] == "req-123"
            assert body["refundAmount"] == 5000
            assert body["merchantId"] == "test_merchant"

        assert result.response_type == "REFUND"

    def test_third_party_deeplink(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"deeplink": "tokipay://pay?id=123"},
                "type": "DEEPLINK",
            },
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.third_party_deeplink(payment_input)

            call_args = mock.call_args
            headers = call_args.kwargs["headers"]
            assert headers["api_key"] == "third_party_pay"
            assert "im_api_key" not in headers

            body = call_args.kwargs["json"]
            assert body["appSchemaIos"] == "myapp://"
            assert body["tokiWebSuccessUrl"] == "https://example.com/success"
            assert body["tokiWebFailureUrl"] == "https://example.com/failure"

        assert result.data.deeplink == "tokipay://pay?id=123"

    def test_third_party_deeplink_success_url_override(
        self, config: TokiPayConfig
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"deeplink": "tokipay://pay?id=456"},
                "type": "DEEPLINK",
            },
        )

        client = TokiPayClient(config)
        inp = TokiPayPaymentInput(
            order_id="ORD-DL",
            amount=7000,
            notes="Deeplink override",
            success_url="https://custom.test/ok",
        )

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            client.third_party_deeplink(inp)

            body = mock.call_args.kwargs["json"]
            assert body["successUrl"] == "https://custom.test/ok"
            assert body["tokiWebSuccessUrl"] == "https://custom.test/ok"

    def test_third_party_phone_request(
        self, config: TokiPayConfig
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": None,
                "type": "PHONE",
            },
        )

        client = TokiPayClient(config)
        inp = TokiPayPaymentInput(
            order_id="ORD-PH",
            amount=2000,
            notes="Phone request",
            phone_no="99001122",
        )

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.third_party_phone_request(inp)

            body = mock.call_args.kwargs["json"]
            assert body["phoneNo"] == "99001122"
            assert body["countryCode"] == "+976"
            assert body["tokiWebSuccessUrl"] == "https://example.com/success"

        assert result.status_code == 200

    def test_third_party_status(self, config: TokiPayConfig) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"status": "COMPLETED"},
                "type": "STATUS",
            },
            method="GET",
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = client.third_party_status("req-tp")

            call_args = mock.call_args
            headers = call_args.kwargs["headers"]
            assert headers["api_key"] == "third_party_pay"

        assert result.data.status == "COMPLETED"

    def test_http_error_raises_tokipay_error(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            500,
            {"error": "Internal Server Error"},
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(TokiPayError, match="500") as exc_info:
                client.payment_qr(payment_input)

            assert exc_info.value.status_code == 500

    def test_status_code_error_in_body(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 401,
                "error": "Unauthorized",
                "message": "Invalid token",
            },
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(TokiPayError, match="Unauthorized") as exc_info:
                client.payment_qr(payment_input)

            assert exc_info.value.status_code == 401
            assert exc_info.value.response["statusCode"] == 401

    def test_status_code_error_falls_back_to_message(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 403,
                "error": "",
                "message": "Forbidden access",
            },
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(TokiPayError, match="Forbidden access"):
                client.payment_qr(payment_input)

    def test_status_code_error_unknown_fallback(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {"statusCode": 500, "error": "", "message": ""},
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(TokiPayError, match="Unknown error"):
                client.payment_qr(payment_input)

    def test_network_error_raises_tokipay_error(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        client = TokiPayClient(config)

        with patch.object(
            client._client,
            "request",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(TokiPayError, match="Network error"):
                client.payment_qr(payment_input)

    def test_invalid_json_raises_tokipay_error(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = httpx.Response(
            status_code=200,
            content=b"not json",
            headers={"content-type": "application/json"},
            request=httpx.Request("POST", "https://api.tokipay.test/test"),
        )

        client = TokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(TokiPayError, match="Invalid JSON"):
                client.payment_qr(payment_input)

    def test_context_manager(self, config: TokiPayConfig) -> None:
        with TokiPayClient(config) as client:
            assert client._endpoint == "https://api.tokipay.test"

    def test_app_schema_ios_defaults_to_empty(self) -> None:
        cfg = TokiPayConfig(
            endpoint="https://api.tokipay.test",
            api_key="k",
            im_api_key="ik",
            authorization="auth",
            merchant_id="m",
            success_url="https://ok.test",
            failure_url="https://fail.test",
        )

        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"deeplink": "tokipay://"},
                "type": "DEEPLINK",
            },
        )

        client = TokiPayClient(cfg)
        inp = TokiPayPaymentInput(
            order_id="ORD-X", amount=1000, notes="test"
        )

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            client.third_party_deeplink(inp)
            body = mock.call_args.kwargs["json"]
            assert body["appSchemaIos"] == ""


# ============================================================================
# Async Client Tests
# ============================================================================


class TestAsyncTokiPayClient:
    """Tests for the asynchronous AsyncTokiPayClient."""

    @pytest.mark.asyncio
    async def test_payment_qr(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"requestId": "async-req-abc"},
                "type": "QR",
            },
        )

        client = AsyncTokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = await client.payment_qr(payment_input)

            mock.assert_called_once()
            headers = mock.call_args.kwargs["headers"]
            assert headers["api_key"] == "spos_pay_v4"
            assert headers["im_api_key"] == "test_im_api_key"

        assert result.data.request_id == "async-req-abc"

        await client.close()

    @pytest.mark.asyncio
    async def test_payment_status(self, config: TokiPayConfig) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"status": "PENDING"},
                "type": "STATUS",
            },
            method="GET",
        )

        client = AsyncTokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            result = await client.payment_status("async-req")

        assert result.data.status == "PENDING"

        await client.close()

    @pytest.mark.asyncio
    async def test_payment_cancel(self, config: TokiPayConfig) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Cancelled",
                "responseType": "CANCEL",
            },
            method="DELETE",
        )

        client = AsyncTokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            result = await client.payment_cancel("async-cancel")

        assert result.response_type == "CANCEL"

        await client.close()

    @pytest.mark.asyncio
    async def test_payment_refund(
        self, config: TokiPayConfig, refund_input: TokiPayRefundInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Refunded",
                "responseType": "REFUND",
            },
        )

        client = AsyncTokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            result = await client.payment_refund(refund_input)

        assert result.response_type == "REFUND"

        await client.close()

    @pytest.mark.asyncio
    async def test_third_party_deeplink(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"deeplink": "tokipay://async"},
                "type": "DEEPLINK",
            },
        )

        client = AsyncTokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response) as mock:
            result = await client.third_party_deeplink(payment_input)

            headers = mock.call_args.kwargs["headers"]
            assert headers["api_key"] == "third_party_pay"
            assert "im_api_key" not in headers

        assert result.data.deeplink == "tokipay://async"

        await client.close()

    @pytest.mark.asyncio
    async def test_third_party_phone_request(
        self, config: TokiPayConfig
    ) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"sent": True},
                "type": "PHONE",
            },
        )

        client = AsyncTokiPayClient(config)
        inp = TokiPayPaymentInput(
            order_id="ORD-ASYNC-PH",
            amount=1500,
            notes="Async phone",
            phone_no="88776655",
        )

        with patch.object(client._client, "request", return_value=mock_response):
            result = await client.third_party_phone_request(inp)

        assert result.status_code == 200

        await client.close()

    @pytest.mark.asyncio
    async def test_third_party_status(self, config: TokiPayConfig) -> None:
        mock_response = _make_json_response(
            200,
            {
                "statusCode": 200,
                "error": "",
                "message": "Success",
                "data": {"status": "EXPIRED"},
                "type": "STATUS",
            },
            method="GET",
        )

        client = AsyncTokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            result = await client.third_party_status("async-tp-req")

        assert result.data.status == "EXPIRED"

        await client.close()

    @pytest.mark.asyncio
    async def test_http_error_raises_tokipay_error(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        mock_response = _make_json_response(
            403,
            {"error": "Forbidden"},
        )

        client = AsyncTokiPayClient(config)

        with patch.object(client._client, "request", return_value=mock_response):
            with pytest.raises(TokiPayError, match="403"):
                await client.payment_qr(payment_input)

        await client.close()

    @pytest.mark.asyncio
    async def test_network_error_raises_tokipay_error(
        self, config: TokiPayConfig, payment_input: TokiPayPaymentInput
    ) -> None:
        client = AsyncTokiPayClient(config)

        with patch.object(
            client._client,
            "request",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(TokiPayError, match="Network error"):
                await client.payment_qr(payment_input)

        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, config: TokiPayConfig) -> None:
        async with AsyncTokiPayClient(config) as client:
            assert client._endpoint == "https://api.tokipay.test"


# ============================================================================
# Config Tests
# ============================================================================


class TestLoadConfigFromEnv:
    """Tests for load_config_from_env."""

    def test_loads_all_env_vars(self) -> None:
        env = {
            "TOKIPAY_ENDPOINT": "https://api.tokipay.test",
            "TOKIPAY_API_KEY": "env_api_key",
            "TOKIPAY_IM_API_KEY": "env_im_key",
            "TOKIPAY_AUTHORIZATION": "env_auth",
            "TOKIPAY_MERCHANT_ID": "env_merchant",
            "TOKIPAY_SUCCESS_URL": "https://ok.test",
            "TOKIPAY_FAILURE_URL": "https://fail.test",
            "TOKIPAY_APP_SCHEMA_IOS": "myapp://",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = load_config_from_env()

        assert cfg.endpoint == "https://api.tokipay.test"
        assert cfg.api_key == "env_api_key"
        assert cfg.im_api_key == "env_im_key"
        assert cfg.authorization == "env_auth"
        assert cfg.merchant_id == "env_merchant"
        assert cfg.success_url == "https://ok.test"
        assert cfg.failure_url == "https://fail.test"
        assert cfg.app_schema_ios == "myapp://"

    def test_app_schema_ios_is_optional(self) -> None:
        env = {
            "TOKIPAY_ENDPOINT": "https://api.tokipay.test",
            "TOKIPAY_API_KEY": "k",
            "TOKIPAY_IM_API_KEY": "ik",
            "TOKIPAY_AUTHORIZATION": "auth",
            "TOKIPAY_MERCHANT_ID": "m",
            "TOKIPAY_SUCCESS_URL": "https://ok.test",
            "TOKIPAY_FAILURE_URL": "https://fail.test",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TOKIPAY_APP_SCHEMA_IOS", None)
            cfg = load_config_from_env()

        assert cfg.app_schema_ios is None

    def test_missing_endpoint_raises(self) -> None:
        env = {
            "TOKIPAY_API_KEY": "k",
            "TOKIPAY_IM_API_KEY": "ik",
            "TOKIPAY_AUTHORIZATION": "auth",
            "TOKIPAY_MERCHANT_ID": "m",
            "TOKIPAY_SUCCESS_URL": "https://ok.test",
            "TOKIPAY_FAILURE_URL": "https://fail.test",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TOKIPAY_ENDPOINT", None)
            with pytest.raises(ValueError, match="TOKIPAY_ENDPOINT"):
                load_config_from_env()

    def test_missing_multiple_raises(self) -> None:
        env = {
            "TOKIPAY_ENDPOINT": "https://api.tokipay.test",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("TOKIPAY_API_KEY", None)
            os.environ.pop("TOKIPAY_IM_API_KEY", None)
            os.environ.pop("TOKIPAY_AUTHORIZATION", None)
            os.environ.pop("TOKIPAY_MERCHANT_ID", None)
            os.environ.pop("TOKIPAY_SUCCESS_URL", None)
            os.environ.pop("TOKIPAY_FAILURE_URL", None)
            with pytest.raises(ValueError, match="TOKIPAY_API_KEY"):
                load_config_from_env()


# ============================================================================
# Error Tests
# ============================================================================


class TestTokiPayError:
    """Tests for TokiPayError."""

    def test_basic_error(self) -> None:
        err = TokiPayError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.status_code is None
        assert err.response is None

    def test_error_with_status_code(self) -> None:
        err = TokiPayError("bad request", status_code=400)
        assert err.status_code == 400

    def test_error_with_response(self) -> None:
        body = {"error": "details"}
        err = TokiPayError("api error", status_code=500, response=body)
        assert err.status_code == 500
        assert err.response == body

    def test_is_exception(self) -> None:
        err = TokiPayError("test")
        assert isinstance(err, Exception)
