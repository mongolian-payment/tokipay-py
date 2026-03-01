# mongolian-payment-tokipay

TokiPay payment gateway SDK for Python.

## Installation

```bash
pip install mongolian-payment-tokipay
```

## Usage

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
```

### Async usage

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

### Load config from environment

```python
from mongolian_payment_tokipay import TokiPayClient, load_config_from_env

client = TokiPayClient(load_config_from_env())
```

Required environment variables: `TOKIPAY_ENDPOINT`, `TOKIPAY_API_KEY`, `TOKIPAY_IM_API_KEY`, `TOKIPAY_AUTHORIZATION`, `TOKIPAY_MERCHANT_ID`, `TOKIPAY_SUCCESS_URL`, `TOKIPAY_FAILURE_URL`.

Optional: `TOKIPAY_APP_SCHEMA_IOS`.

## License

MIT
