"""TokiPay payment client implementations (sync and async)."""

import re
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx

from .errors import TokiPayError
from .types import (
    TokiPayConfig,
    TokiPayDeeplinkDataResponse,
    TokiPayDeeplinkResponse,
    TokiPayPaymentInput,
    TokiPayPaymentRequestResponse,
    TokiPayPaymentResponse,
    TokiPayPaymentResponseExt,
    TokiPayPaymentStatusDataResponse,
    TokiPayPaymentStatusResponse,
    TokiPayRefundInput,
    TokiPayThirdPartyPhoneResponse,
)

# API key value used for POS endpoints.
POS_API_KEY = "spos_pay_v4"

# API key value used for third-party endpoints.
THIRD_PARTY_API_KEY = "third_party_pay"


def _check_status_code(data: Any, method: str, path: str) -> None:
    """Check the TokiPay-specific statusCode field in the response body.

    TokiPay signals errors via a statusCode field in the JSON body even when
    the HTTP status is 200. A statusCode !== 200 is treated as an error.
    """
    if (
        isinstance(data, dict)
        and "statusCode" in data
        and data["statusCode"] != 200
    ):
        error_msg = data.get("error") or data.get("message") or "Unknown error"
        raise TokiPayError(
            f"TokiPay API error: {error_msg} (statusCode: {data['statusCode']})",
            status_code=data["statusCode"],
            response=data,
        )


class TokiPayClient:
    """TokiPay payment client (synchronous).

    Provides methods for POS payments (QR, send-to-user, scan-user, status,
    cancel, refund) and third-party payments (deeplink, phone request, status).

    Example::

        from mongolian_payment_tokipay import TokiPayClient, TokiPayConfig

        client = TokiPayClient(TokiPayConfig(
            endpoint="https://api.tokipay.mn",
            api_key="MY_API_KEY",
            im_api_key="MY_IM_API_KEY",
            authorization="MY_AUTH_TOKEN",
            merchant_id="MY_MERCHANT_ID",
            success_url="https://example.com/success",
            failure_url="https://example.com/failure",
        ))

        result = client.payment_qr(TokiPayPaymentInput(
            order_id="order_123",
            amount=10000,
            notes="Test payment",
        ))
    """

    def __init__(self, config: TokiPayConfig) -> None:
        if not config.endpoint:
            raise ValueError("TokiPayClient: endpoint is required")
        if not config.authorization:
            raise ValueError("TokiPayClient: authorization is required")

        self._config = config
        self._endpoint = re.sub(r"/+$", "", config.endpoint)
        self._client = httpx.Client()

    # ── HTTP helpers ──

    def _pos_headers(self) -> Dict[str, str]:
        """Build headers for POS endpoints."""
        return {
            "Content-Type": "application/json",
            "Authorization": self._config.authorization,
            "api_key": POS_API_KEY,
            "im_api_key": self._config.im_api_key,
        }

    def _third_party_headers(self) -> Dict[str, str]:
        """Build headers for third-party endpoints."""
        return {
            "Content-Type": "application/json",
            "Authorization": self._config.authorization,
            "api_key": THIRD_PARTY_API_KEY,
        }

    def _do_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute an HTTP request and handle errors."""
        url = f"{self._endpoint}{path}"

        try:
            if method == "GET":
                res = self._client.request(method, url, headers=headers)
            elif method == "DELETE":
                res = self._client.request(method, url, headers=headers)
            else:
                res = self._client.request(
                    method, url, headers=headers, json=body
                )
        except httpx.HTTPError as exc:
            raise TokiPayError(
                f"Network error calling {method} {path}: {exc}"
            ) from exc

        content_type = res.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                response_body = res.json()
            except Exception:
                raise TokiPayError(
                    f"Invalid JSON response from {method} {path}",
                    status_code=res.status_code,
                )
        else:
            response_body = res.text

        if res.status_code < 200 or res.status_code >= 300:
            raise TokiPayError(
                f"TokiPay API error: {method} {path} ({res.status_code})",
                status_code=res.status_code,
                response=response_body,
            )

        _check_status_code(response_body, method, path)

        return response_body

    def _pos_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated request to a POS endpoint."""
        return self._do_request(method, path, self._pos_headers(), body)

    def _third_party_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated request to a third-party endpoint."""
        return self._do_request(
            method, path, self._third_party_headers(), body
        )

    # ── POS Methods ──

    def payment_qr(
        self, input: TokiPayPaymentInput
    ) -> TokiPayPaymentResponse:
        """Create a QR payment request.

        Args:
            input: Payment parameters (order_id, amount, notes).

        Returns:
            Payment response with request_id.
        """
        body = {
            "successUrl": self._config.success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "authorization": self._config.authorization,
        }

        raw = self._pos_request(
            "POST", "/jump/v4/spose/payment/request", body
        )
        return _parse_payment_response(raw)

    def payment_send_to_user(
        self, input: TokiPayPaymentInput
    ) -> TokiPayPaymentResponse:
        """Send a payment request to a specific user by phone number.

        Args:
            input: Payment parameters including phone_no and country_code.

        Returns:
            Payment response with request_id.
        """
        body = {
            "successUrl": self._config.success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "authorization": self._config.authorization,
            "phoneNo": input.phone_no,
            "countryCode": input.country_code,
        }

        raw = self._pos_request(
            "POST", "/jump/v4/spose/payment/user-request", body
        )
        return _parse_payment_response(raw)

    def payment_scan_user(
        self, input: TokiPayPaymentInput
    ) -> TokiPayPaymentResponse:
        """Create a payment request by scanning a user's QR code.

        Args:
            input: Payment parameters including request_id from scanned QR.

        Returns:
            Payment response with request_id.
        """
        body = {
            "successUrl": self._config.success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "authorization": self._config.authorization,
            "requestId": input.request_id,
        }

        raw = self._pos_request(
            "POST", "/jump/v4/spose/payment/scan/user-request", body
        )
        return _parse_payment_response(raw)

    def payment_status(
        self, request_id: str
    ) -> TokiPayPaymentStatusResponse:
        """Check the status of a POS payment.

        Args:
            request_id: The request ID returned from a payment request.

        Returns:
            Payment status response.
        """
        path = f"/jump/v4/spose/payment/status?requestId={_encode(request_id)}"
        raw = self._pos_request("GET", path)
        return _parse_payment_status_response(raw)

    def payment_cancel(
        self, request_id: str
    ) -> TokiPayPaymentResponseExt:
        """Cancel a POS payment.

        Args:
            request_id: The request ID of the payment to cancel.

        Returns:
            Extended payment response.
        """
        path = f"/jump/v4/spose/payment/request?requestId={_encode(request_id)}"
        raw = self._pos_request("DELETE", path)
        return _parse_payment_response_ext(raw)

    def payment_refund(
        self, input: TokiPayRefundInput
    ) -> TokiPayPaymentResponseExt:
        """Refund a POS payment.

        Args:
            input: Refund parameters (request_id, refund_amount).

        Returns:
            Extended payment response.
        """
        body = {
            "requestId": input.request_id,
            "refundAmount": input.refund_amount,
            "merchantId": self._config.merchant_id,
        }

        raw = self._pos_request(
            "PUT", "/jump/v4/spose/payment/refund", body
        )
        return _parse_payment_response_ext(raw)

    # ── Third-Party Methods ──

    def third_party_deeplink(
        self, input: TokiPayPaymentInput
    ) -> TokiPayDeeplinkResponse:
        """Create a third-party deeplink payment.

        Args:
            input: Payment parameters (order_id, amount, notes, optional success_url).

        Returns:
            Deeplink response containing the payment deeplink URL.
        """
        effective_success_url = (
            input.success_url
            if input.success_url is not None
            else self._config.success_url
        )

        body = {
            "successUrl": effective_success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "appSchemaIos": self._config.app_schema_ios or "",
            "authorization": self._config.authorization,
            "tokiWebSuccessUrl": effective_success_url,
            "tokiWebFailureUrl": self._config.failure_url,
        }

        raw = self._third_party_request(
            "POST", "/jump/v1/third-party/payment/deeplink", body
        )
        return _parse_deeplink_response(raw)

    def third_party_phone_request(
        self, input: TokiPayPaymentInput
    ) -> TokiPayThirdPartyPhoneResponse:
        """Create a third-party payment request via phone number.

        Args:
            input: Payment parameters including phone_no.

        Returns:
            Third-party phone response.
        """
        body = {
            "successUrl": self._config.success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "phoneNo": input.phone_no,
            "countryCode": "+976",
            "authorization": self._config.authorization,
            "tokiWebSuccessUrl": self._config.success_url,
            "tokiWebFailureUrl": self._config.failure_url,
        }

        raw = self._third_party_request(
            "POST", "/jump/v1/third-party/payment/request", body
        )
        return _parse_third_party_phone_response(raw)

    def third_party_status(
        self, request_id: str
    ) -> TokiPayPaymentStatusResponse:
        """Check the status of a third-party payment.

        Args:
            request_id: The request ID returned from a payment request.

        Returns:
            Payment status response.
        """
        path = f"/jump/v1/third-party/payment/status?requestId={_encode(request_id)}"
        raw = self._third_party_request("GET", path)
        return _parse_payment_status_response(raw)

    # ── Lifecycle ──

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "TokiPayClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncTokiPayClient:
    """TokiPay payment client (asynchronous).

    Provides methods for POS payments (QR, send-to-user, scan-user, status,
    cancel, refund) and third-party payments (deeplink, phone request, status).

    Example::

        import asyncio
        from mongolian_payment_tokipay import AsyncTokiPayClient, TokiPayConfig

        async def main():
            client = AsyncTokiPayClient(TokiPayConfig(
                endpoint="https://api.tokipay.mn",
                api_key="MY_API_KEY",
                im_api_key="MY_IM_API_KEY",
                authorization="MY_AUTH_TOKEN",
                merchant_id="MY_MERCHANT_ID",
                success_url="https://example.com/success",
                failure_url="https://example.com/failure",
            ))

            result = await client.payment_qr(TokiPayPaymentInput(
                order_id="order_123",
                amount=10000,
                notes="Test payment",
            ))

            await client.close()
    """

    def __init__(self, config: TokiPayConfig) -> None:
        if not config.endpoint:
            raise ValueError("AsyncTokiPayClient: endpoint is required")
        if not config.authorization:
            raise ValueError("AsyncTokiPayClient: authorization is required")

        self._config = config
        self._endpoint = re.sub(r"/+$", "", config.endpoint)
        self._client = httpx.AsyncClient()

    # ── HTTP helpers ──

    def _pos_headers(self) -> Dict[str, str]:
        """Build headers for POS endpoints."""
        return {
            "Content-Type": "application/json",
            "Authorization": self._config.authorization,
            "api_key": POS_API_KEY,
            "im_api_key": self._config.im_api_key,
        }

    def _third_party_headers(self) -> Dict[str, str]:
        """Build headers for third-party endpoints."""
        return {
            "Content-Type": "application/json",
            "Authorization": self._config.authorization,
            "api_key": THIRD_PARTY_API_KEY,
        }

    async def _do_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute an HTTP request and handle errors."""
        url = f"{self._endpoint}{path}"

        try:
            if method == "GET":
                res = await self._client.request(method, url, headers=headers)
            elif method == "DELETE":
                res = await self._client.request(method, url, headers=headers)
            else:
                res = await self._client.request(
                    method, url, headers=headers, json=body
                )
        except httpx.HTTPError as exc:
            raise TokiPayError(
                f"Network error calling {method} {path}: {exc}"
            ) from exc

        content_type = res.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                response_body = res.json()
            except Exception:
                raise TokiPayError(
                    f"Invalid JSON response from {method} {path}",
                    status_code=res.status_code,
                )
        else:
            response_body = res.text

        if res.status_code < 200 or res.status_code >= 300:
            raise TokiPayError(
                f"TokiPay API error: {method} {path} ({res.status_code})",
                status_code=res.status_code,
                response=response_body,
            )

        _check_status_code(response_body, method, path)

        return response_body

    async def _pos_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated request to a POS endpoint."""
        return await self._do_request(
            method, path, self._pos_headers(), body
        )

    async def _third_party_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated request to a third-party endpoint."""
        return await self._do_request(
            method, path, self._third_party_headers(), body
        )

    # ── POS Methods ──

    async def payment_qr(
        self, input: TokiPayPaymentInput
    ) -> TokiPayPaymentResponse:
        """Create a QR payment request.

        Args:
            input: Payment parameters (order_id, amount, notes).

        Returns:
            Payment response with request_id.
        """
        body = {
            "successUrl": self._config.success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "authorization": self._config.authorization,
        }

        raw = await self._pos_request(
            "POST", "/jump/v4/spose/payment/request", body
        )
        return _parse_payment_response(raw)

    async def payment_send_to_user(
        self, input: TokiPayPaymentInput
    ) -> TokiPayPaymentResponse:
        """Send a payment request to a specific user by phone number.

        Args:
            input: Payment parameters including phone_no and country_code.

        Returns:
            Payment response with request_id.
        """
        body = {
            "successUrl": self._config.success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "authorization": self._config.authorization,
            "phoneNo": input.phone_no,
            "countryCode": input.country_code,
        }

        raw = await self._pos_request(
            "POST", "/jump/v4/spose/payment/user-request", body
        )
        return _parse_payment_response(raw)

    async def payment_scan_user(
        self, input: TokiPayPaymentInput
    ) -> TokiPayPaymentResponse:
        """Create a payment request by scanning a user's QR code.

        Args:
            input: Payment parameters including request_id from scanned QR.

        Returns:
            Payment response with request_id.
        """
        body = {
            "successUrl": self._config.success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "authorization": self._config.authorization,
            "requestId": input.request_id,
        }

        raw = await self._pos_request(
            "POST", "/jump/v4/spose/payment/scan/user-request", body
        )
        return _parse_payment_response(raw)

    async def payment_status(
        self, request_id: str
    ) -> TokiPayPaymentStatusResponse:
        """Check the status of a POS payment.

        Args:
            request_id: The request ID returned from a payment request.

        Returns:
            Payment status response.
        """
        path = f"/jump/v4/spose/payment/status?requestId={_encode(request_id)}"
        raw = await self._pos_request("GET", path)
        return _parse_payment_status_response(raw)

    async def payment_cancel(
        self, request_id: str
    ) -> TokiPayPaymentResponseExt:
        """Cancel a POS payment.

        Args:
            request_id: The request ID of the payment to cancel.

        Returns:
            Extended payment response.
        """
        path = f"/jump/v4/spose/payment/request?requestId={_encode(request_id)}"
        raw = await self._pos_request("DELETE", path)
        return _parse_payment_response_ext(raw)

    async def payment_refund(
        self, input: TokiPayRefundInput
    ) -> TokiPayPaymentResponseExt:
        """Refund a POS payment.

        Args:
            input: Refund parameters (request_id, refund_amount).

        Returns:
            Extended payment response.
        """
        body = {
            "requestId": input.request_id,
            "refundAmount": input.refund_amount,
            "merchantId": self._config.merchant_id,
        }

        raw = await self._pos_request(
            "PUT", "/jump/v4/spose/payment/refund", body
        )
        return _parse_payment_response_ext(raw)

    # ── Third-Party Methods ──

    async def third_party_deeplink(
        self, input: TokiPayPaymentInput
    ) -> TokiPayDeeplinkResponse:
        """Create a third-party deeplink payment.

        Args:
            input: Payment parameters (order_id, amount, notes, optional success_url).

        Returns:
            Deeplink response containing the payment deeplink URL.
        """
        effective_success_url = (
            input.success_url
            if input.success_url is not None
            else self._config.success_url
        )

        body = {
            "successUrl": effective_success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "appSchemaIos": self._config.app_schema_ios or "",
            "authorization": self._config.authorization,
            "tokiWebSuccessUrl": effective_success_url,
            "tokiWebFailureUrl": self._config.failure_url,
        }

        raw = await self._third_party_request(
            "POST", "/jump/v1/third-party/payment/deeplink", body
        )
        return _parse_deeplink_response(raw)

    async def third_party_phone_request(
        self, input: TokiPayPaymentInput
    ) -> TokiPayThirdPartyPhoneResponse:
        """Create a third-party payment request via phone number.

        Args:
            input: Payment parameters including phone_no.

        Returns:
            Third-party phone response.
        """
        body = {
            "successUrl": self._config.success_url,
            "failureUrl": self._config.failure_url,
            "orderId": input.order_id,
            "merchantId": self._config.merchant_id,
            "amount": input.amount,
            "notes": input.notes,
            "phoneNo": input.phone_no,
            "countryCode": "+976",
            "authorization": self._config.authorization,
            "tokiWebSuccessUrl": self._config.success_url,
            "tokiWebFailureUrl": self._config.failure_url,
        }

        raw = await self._third_party_request(
            "POST", "/jump/v1/third-party/payment/request", body
        )
        return _parse_third_party_phone_response(raw)

    async def third_party_status(
        self, request_id: str
    ) -> TokiPayPaymentStatusResponse:
        """Check the status of a third-party payment.

        Args:
            request_id: The request ID returned from a payment request.

        Returns:
            Payment status response.
        """
        path = f"/jump/v1/third-party/payment/status?requestId={_encode(request_id)}"
        raw = await self._third_party_request("GET", path)
        return _parse_payment_status_response(raw)

    # ── Lifecycle ──

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTokiPayClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


# ============================================================================
# Response parsers
# ============================================================================


def _encode(value: str) -> str:
    """URL-encode a single query parameter value."""
    return urlencode({"v": value})[2:]


def _parse_payment_response(raw: Dict[str, Any]) -> TokiPayPaymentResponse:
    """Parse a raw dict into a TokiPayPaymentResponse."""
    data = raw.get("data", {})
    return TokiPayPaymentResponse(
        status_code=raw.get("statusCode", 0),
        error=raw.get("error", ""),
        message=raw.get("message", ""),
        data=TokiPayPaymentRequestResponse(
            request_id=data.get("requestId", ""),
        ),
        type=raw.get("type", ""),
    )


def _parse_payment_status_response(
    raw: Dict[str, Any],
) -> TokiPayPaymentStatusResponse:
    """Parse a raw dict into a TokiPayPaymentStatusResponse."""
    data = raw.get("data", {})
    return TokiPayPaymentStatusResponse(
        status_code=raw.get("statusCode", 0),
        error=raw.get("error", ""),
        message=raw.get("message", ""),
        data=TokiPayPaymentStatusDataResponse(
            status=data.get("status", ""),
        ),
        type=raw.get("type", ""),
    )


def _parse_payment_response_ext(
    raw: Dict[str, Any],
) -> TokiPayPaymentResponseExt:
    """Parse a raw dict into a TokiPayPaymentResponseExt."""
    return TokiPayPaymentResponseExt(
        status_code=raw.get("statusCode", 0),
        error=raw.get("error", ""),
        message=raw.get("message", ""),
        response_type=raw.get("responseType", ""),
    )


def _parse_deeplink_response(
    raw: Dict[str, Any],
) -> TokiPayDeeplinkResponse:
    """Parse a raw dict into a TokiPayDeeplinkResponse."""
    data = raw.get("data", {})
    return TokiPayDeeplinkResponse(
        status_code=raw.get("statusCode", 0),
        error=raw.get("error", ""),
        message=raw.get("message", ""),
        data=TokiPayDeeplinkDataResponse(
            deeplink=data.get("deeplink", ""),
        ),
        type=raw.get("type", ""),
    )


def _parse_third_party_phone_response(
    raw: Dict[str, Any],
) -> TokiPayThirdPartyPhoneResponse:
    """Parse a raw dict into a TokiPayThirdPartyPhoneResponse."""
    return TokiPayThirdPartyPhoneResponse(
        status_code=raw.get("statusCode", 0),
        error=raw.get("error", ""),
        message=raw.get("message", ""),
        data=raw.get("data"),
        type=raw.get("type", ""),
    )
