"""Run one TopCharge API example at a time: python tests/integration.py help."""

import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from topcharge_sdk import TopChargeApiError, TopChargeClient  # noqa: E402


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "help"
    if action == "help":
        print_help()
        return
    if os.getenv("TOPCHARGE_RUN_INTEGRATION") != "1":
        raise RuntimeError("Refusing to call the API. Set TOPCHARGE_RUN_INTEGRATION=1.")

    client = TopChargeClient(
        required("TOPCHARGE_CLIENT_ID"),
        required("TOPCHARGE_SECRET_KEY"),
        base_url=os.getenv("TOPCHARGE_BASE_URL", "https://api.topcharge.app"),
    )
    actions = {
        "account:verify": lambda: verify(client),
        "account:balance": lambda: output(client.account.get_balance()),
        "payment:create": lambda: output(client.payments.create(**payment_options("manual test"))),
        "payment:status": lambda: output(client.payments.get_status(required("TOPCHARGE_PAYMENT_ID"))),
        "payment:cancel": lambda: output(client.payments.cancel(required("TOPCHARGE_PAYMENT_ID"))),
        "payment:smoke": lambda: payment_smoke(client),
        "withdrawal:create": lambda: withdrawal(client),
    }
    try:
        actions[action]()
    except KeyError as error:
        raise RuntimeError(f"Unknown action '{action}'. Run: python tests/integration.py help") from error


def verify(client: TopChargeClient) -> None:
    client.account.verify_credentials()
    print("Credentials are valid.")


def payment_smoke(client: TopChargeClient) -> None:
    payment_id = None
    try:
        payment = client.payments.create(**payment_options(f"smoke {secrets.token_hex(8)}"))
        payment_id = payment.get("paymentId")
        if not isinstance(payment_id, str) or not payment.get("paymentUrl"):
            raise RuntimeError("Payment creation response is missing paymentId or paymentUrl.")
        if client.payments.get_status(payment_id).get("paymentId") != payment_id:
            raise RuntimeError("Payment status response does not match the created payment.")
        print(f"Payment link created and verified for payment ID: {payment_id}")
    finally:
        if payment_id:
            output(client.payments.cancel(payment_id))
            print("Test payment cancelled.")


def withdrawal(client: TopChargeClient) -> None:
    confirmation("TOPCHARGE_ALLOW_MONEY_MOVEMENT")
    output(client.withdrawals.create(required("TOPCHARGE_PHONE_COUNTRY_CODE"), required("TOPCHARGE_PHONE_NUMBER"), required("TOPCHARGE_WITHDRAWAL_AMOUNT")))


def payment_options(label: str) -> dict:
    return {
        "payment_amount": os.getenv("TOPCHARGE_TEST_PAYMENT_AMOUNT", "50000"),
        "description": os.getenv("TOPCHARGE_PAYMENT_DESCRIPTION", f"TopCharge Python SDK {label}"),
        "redirect_url": os.getenv("TOPCHARGE_REDIRECT_URL", "https://example.com/topcharge-sdk-test"),
        "callback_url": os.getenv("TOPCHARGE_CALLBACK_URL", "https://example.com/topcharge-sdk-webhook"),
    }


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


def confirmation(name: str) -> None:
    if os.getenv(name) != "1":
        raise RuntimeError(f"This action changes money or value. Set {name}=1 to continue.")


def output(value: dict) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def print_help() -> None:
    print("""TopCharge Python integration examples

Set TOPCHARGE_RUN_INTEGRATION=1, TOPCHARGE_CLIENT_ID, and TOPCHARGE_SECRET_KEY first.

Account: account:verify | account:balance
Payment: payment:create | payment:status (TOPCHARGE_PAYMENT_ID) | payment:cancel (TOPCHARGE_PAYMENT_ID) | payment:smoke
Withdrawal: withdrawal:create (TOPCHARGE_ALLOW_MONEY_MOVEMENT=1 plus recipient variables)
Run payment:smoke to create, verify, then cancel a test payment.""")


if __name__ == "__main__":
    try:
        main()
    except TopChargeApiError as error:
        print(f"TopCharge API error ({error.status_code}): {error}", file=sys.stderr)
        raise SystemExit(1)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
