# mongolian-payment-tokipay

TokiPay payment gateway SDK for Python (sync + async) — QR payments, send-to-user, deeplinks, and refunds.

[![PyPI version](https://img.shields.io/pypi/v/mongolian-payment-tokipay.svg)](https://pypi.org/project/mongolian-payment-tokipay/)
[![Python versions](https://img.shields.io/pypi/pyversions/mongolian-payment-tokipay.svg)](https://pypi.org/project/mongolian-payment-tokipay/)
[![license](https://img.shields.io/pypi/l/mongolian-payment-tokipay.svg)](./LICENSE)

> Part of the **[mongolian-payment](https://github.com/mongolian-payment)** SDK suite.
> Also available for Node.js: **[@mongolian-payment/tokipay](https://www.npmjs.com/package/@mongolian-payment/tokipay)** ([source](https://github.com/mongolian-payment/tokipay-js)).

## Requirements

- Python >= 3.8 (depends on `httpx`)

## Installation

```bash
pip install mongolian-payment-tokipay
```

## Quick Start

```python
from mongolian_payment_tokipay import TokiPayClient, TokiPayConfig, TokiPayPaymentInput

client = TokiPayClient(TokiPayConfig(
    endpoint="https://api.tokipay.mn",
    api_key="YOUR_API_KEY",
    im_api_key="YOUR_IM_API_KEY",
    authorization="YOUR_AUTH_TOKEN",
    merchant_id="YOUR_MERCHANT_ID",
    success_url="https://example.com/success",
    failure_url="https://example.com/failure",
))

# Create a QR payment
result = client.payment_qr(TokiPayPaymentInput(
    order_id="order_123",
    amount=10000,
    notes="Payment for order #123",
))
print(result.data.request_id)

# Check payment status
status = client.payment_status(result.data.request_id)
print(status.data.status)  # APPROVED, COMPLETED, PENDING, EXPIRED
```

### Async

```python
import asyncio
from mongolian_payment_tokipay import AsyncTokiPayClient, TokiPayConfig, TokiPayPaymentInput

async def main():
    async with AsyncTokiPayClient(TokiPayConfig(
        endpoint="https://api.tokipay.mn",
        api_key="YOUR_API_KEY",
        im_api_key="YOUR_IM_API_KEY",
        authorization="YOUR_AUTH_TOKEN",
        merchant_id="YOUR_MERCHANT_ID",
        success_url="https://example.com/success",
        failure_url="https://example.com/failure",
    )) as client:
        result = await client.payment_qr(TokiPayPaymentInput(
            order_id="order_123",
            amount=10000,
            notes="Payment for order #123",
        ))
        print(result.data.request_id)

asyncio.run(main())
```

## Configuration from Environment Variables

```python
from mongolian_payment_tokipay import TokiPayClient, load_config_from_env

client = TokiPayClient(load_config_from_env())
```

| Variable                 | Description                                  |
| ------------------------ | -------------------------------------------- |
| `TOKIPAY_ENDPOINT`       | API base URL                                 |
| `TOKIPAY_API_KEY`        | API key provided by TokiPay                  |
| `TOKIPAY_IM_API_KEY`     | IM API key for POS endpoints                 |
| `TOKIPAY_AUTHORIZATION`  | Authorization token string                   |
| `TOKIPAY_MERCHANT_ID`    | Merchant ID assigned by TokiPay              |
| `TOKIPAY_SUCCESS_URL`    | Default success redirect URL                 |
| `TOKIPAY_FAILURE_URL`    | Default failure redirect URL                 |
| `TOKIPAY_APP_SCHEMA_IOS` | iOS app schema for deeplinks (optional)      |

> Never hard-code credentials — load them from the environment or a secrets vault.

## API Reference

`TokiPayClient` and `AsyncTokiPayClient` share identical method signatures (the async
client uses `async`/`await`). POS methods authenticate with the `spos_pay_v4` API key;
third-party methods use the `third_party_pay` API key. Both are applied automatically.

| Method | Description |
|--------|-------------|
| `payment_qr(input_)` | Create a QR payment |
| `payment_send_to_user(input_)` | Send a payment request to a user by phone number |
| `payment_scan_user(input_)` | Create a payment by scanning a user's QR |
| `payment_status(request_id)` | Check POS payment status |
| `payment_cancel(request_id)` | Cancel a POS payment |
| `payment_refund(input_)` | Refund a POS payment |
| `third_party_deeplink(input_)` | Create a third-party deeplink payment |
| `third_party_phone_request(input_)` | Create a third-party payment request by phone |
| `third_party_status(request_id)` | Check third-party payment status |

Payment status values: `APPROVED` (paid), `COMPLETED`, `PENDING`, `EXPIRED`
(canceled/expired). These are exported as `ORDER_STATUS_PAID`,
`ORDER_STATUS_COMPLETED`, `ORDER_STATUS_PENDING`, `ORDER_STATUS_CANCELED`, and
`ORDER_STATUS_EXPIRED`.

## Error Handling

All API errors raise `TokiPayError`, which includes the HTTP status code and response body:

```python
from mongolian_payment_tokipay import TokiPayError

try:
    client.payment_status("invalid_id")
except TokiPayError as err:
    print(err)              # Human-readable message
    print(err.status_code)  # HTTP status code (e.g. 404)
    print(err.response)     # Raw response body
```

## License

MIT
