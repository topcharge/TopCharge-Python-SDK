# TopCharge Python SDK

Python SDK for the TopCharge merchant API. The synchronous client has no external dependencies and works in Django, Flask, Celery, scripts, and WSGI apps. An optional asynchronous client works with FastAPI, Starlette, Quart, and async workers.

## Release status

This SDK is currently installed from this repository for local development. Do not treat its distribution name as a published PyPI package until an official release is announced.

## Install locally

```bash
cd /Users/chawan/Desktop/Projects/TopCharge/sdk/python
python3 -m pip install -e .
```

For async framework support:

```bash
python3 -m pip install -e '.[async]'
```

## Synchronous client: Flask, Django, Celery, scripts

```python
import os
from topcharge_sdk import TopChargeClient

client = TopChargeClient(
    client_id=os.environ["TOPCHARGE_CLIENT_ID"],
    secret_key=os.environ["TOPCHARGE_SECRET_KEY"],
)

payment = client.payments.create(
    "25000",
    description="Invoice #1001",
    redirect_url="https://merchant.example/success",
    callback_url="https://merchant.example/webhooks/payment",
)
print(payment["paymentUrl"])
```

## Asynchronous client: FastAPI, Starlette, Quart

```python
import os
from topcharge_sdk import AsyncTopChargeClient

async with AsyncTopChargeClient(
    os.environ["TOPCHARGE_CLIENT_ID"],
    os.environ["TOPCHARGE_SECRET_KEY"],
) as client:
    payment = await client.payments.create("25000", description="Invoice #1001")
    print(payment["paymentUrl"])
```

The default API host is `https://api.topcharge.app`. Responses are dictionaries. API failures raise `TopChargeApiError`, which includes `status_code` and `response_body`.

`client_id` is sent as `x-api-key` and `secret_key` as `x-api-secret`. Keep both in server-side environment variables or secret storage only; never place them in frontend code, logs, or source control.

## Services

```python
client.account.verify_credentials()
balance = client.account.get_balance()

payment = client.payments.create("25000")
status = client.payments.get_status(payment["paymentId"])
client.payments.cancel(payment["paymentId"])

client.withdrawals.create("964", "7701234567", "50000")

```

Every async method has the same name and parameters; prefix calls with `await`.

## Tests and individual integration examples

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 tests/integration.py help
```

For the live payment smoke test (create → status → cancel):

```bash
export TOPCHARGE_RUN_INTEGRATION=1
export TOPCHARGE_CLIENT_ID='mch_...'
export TOPCHARGE_SECRET_KEY='sk_...'
python3 tests/integration.py payment:smoke
```

Each operation can run independently: `payment:create`, `payment:status`, `payment:cancel`, `account:balance`, and `withdrawal:create`. Value-moving actions require their corresponding `TOPCHARGE_ALLOW_*` confirmation variable. Run `python3 tests/integration.py help` for the full list.

Keep merchant credentials in server environment variables; never commit them to source control.

## Reliability

The sync and async clients use a 30-second default timeout and do not retry automatically. Reads can generally be retried. Do not blindly retry payment creation or withdrawals after an unknown network result; resolve the original operation first.

## License

[MIT License](LICENSE)
