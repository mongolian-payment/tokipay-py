"""Type definitions for the TokiPay payment SDK."""

from dataclasses import dataclass
from typing import Any, Optional

# ============================================================================
# Constants
# ============================================================================

ORDER_STATUS_PAID = "APPROVED"
"""Payment has been approved."""

ORDER_STATUS_COMPLETED = "COMPLETED"
"""Payment has been completed."""

ORDER_STATUS_PENDING = "PENDING"
"""Payment is pending."""

ORDER_STATUS_CANCELED = "EXPIRED"
"""Payment has been canceled."""

ORDER_STATUS_EXPIRED = "EXPIRED"
"""Payment has expired."""

# ============================================================================
# Configuration
# ============================================================================


@dataclass
class TokiPayConfig:
    """Configuration for the TokiPay client.

    Attributes:
        endpoint: Base URL of the TokiPay API (e.g. https://api.tokipay.mn).
        api_key: API key provided by TokiPay.
        im_api_key: IM API key for POS endpoints.
        authorization: Authorization token string.
        merchant_id: Merchant ID assigned by TokiPay.
        success_url: Default success redirect URL.
        failure_url: Default failure redirect URL.
        app_schema_ios: iOS app schema for deeplink generation (optional).
    """

    endpoint: str
    api_key: str
    im_api_key: str
    authorization: str
    merchant_id: str
    success_url: str
    failure_url: str
    app_schema_ios: Optional[str] = None


# ============================================================================
# SDK Input Types (user-facing)
# ============================================================================


@dataclass
class TokiPayPaymentInput:
    """Input for creating a payment.

    Attributes:
        order_id: Unique order identifier.
        amount: Payment amount in MNT.
        notes: Payment description/notes.
        phone_no: Phone number (for send-to-user).
        country_code: Country code (for send-to-user, e.g. "+976").
        request_id: Request ID (for scan user).
        success_url: Success URL override.
    """

    order_id: str
    amount: float
    notes: str
    phone_no: Optional[str] = None
    country_code: Optional[str] = None
    request_id: Optional[str] = None
    success_url: Optional[str] = None


@dataclass
class TokiPayRefundInput:
    """Input for refunding a payment.

    Attributes:
        request_id: Request ID of the payment to refund.
        refund_amount: Amount to refund.
    """

    request_id: str
    refund_amount: float


# ============================================================================
# Response Types
# ============================================================================


@dataclass
class TokiPayPaymentRequestResponse:
    """Data returned from a payment request.

    Attributes:
        request_id: The unique request identifier.
    """

    request_id: str


@dataclass
class TokiPayPaymentResponse:
    """Standard payment response.

    Attributes:
        status_code: API status code.
        error: Error string.
        message: Message string.
        data: Payment request response data.
        type: Response type.
    """

    status_code: int
    error: str
    message: str
    data: TokiPayPaymentRequestResponse
    type: str


@dataclass
class TokiPayPaymentStatusDataResponse:
    """Data returned from a payment status check.

    Attributes:
        status: The payment status string.
    """

    status: str


@dataclass
class TokiPayPaymentStatusResponse:
    """Payment status response.

    Attributes:
        status_code: API status code.
        error: Error string.
        message: Message string.
        data: Payment status data.
        type: Response type.
    """

    status_code: int
    error: str
    message: str
    data: TokiPayPaymentStatusDataResponse
    type: str


@dataclass
class TokiPayPaymentResponseExt:
    """Extended payment response (for cancel, refund).

    Attributes:
        status_code: API status code.
        error: Error string.
        message: Message string.
        response_type: Response type string.
    """

    status_code: int
    error: str
    message: str
    response_type: str


@dataclass
class TokiPayDeeplinkDataResponse:
    """Data returned from a deeplink request.

    Attributes:
        deeplink: The deeplink URL string.
    """

    deeplink: str


@dataclass
class TokiPayDeeplinkResponse:
    """Deeplink response.

    Attributes:
        status_code: API status code.
        error: Error string.
        message: Message string.
        data: Deeplink data.
        type: Response type.
    """

    status_code: int
    error: str
    message: str
    data: TokiPayDeeplinkDataResponse
    type: str


@dataclass
class TokiPayThirdPartyPhoneResponse:
    """Third-party phone response.

    Attributes:
        status_code: API status code.
        error: Error string.
        message: Message string.
        data: Response data (varies).
        type: Response type.
    """

    status_code: int
    error: str
    message: str
    data: Any
    type: str
