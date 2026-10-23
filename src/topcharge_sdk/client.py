from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .exceptions import TopChargeApiError

DEFAULT_BASE_URL = "https://api.topcharge.app"


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: str


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[str],
        timeout: float,
    ) -> HttpResponse: ...


class UrllibTransport:
    """Dependency-free default transport based on Python's standard library."""

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[str],
        timeout: float,
    ) -> HttpResponse:
        request = Request(
            url,
            data=body.encode("utf-8") if body is not None else None,
            headers=dict(headers),
            method=method,
        )
        try:
            with urlopen(request, timeout=timeout) as response:  # nosec B310: URL is supplied by the SDK caller.
                return HttpResponse(response.status, response.read().decode("utf-8"))
        except HTTPError as error:
            return HttpResponse(error.code, error.read().decode("utf-8"))


class TopChargeClient:
    """Synchronous TopCharge client for Django, Flask, Celery, scripts, and WSGI apps."""

    def __init__(
        self,
        client_id: str,
        secret_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        transport: Optional[HttpTransport] = None,
    ) -> None:
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError("TopCharge client_id must not be empty.")
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("TopCharge base_url must not be empty.")
        if timeout <= 0:
            raise ValueError("TopCharge timeout must be greater than zero.")

        self._client_id = client_id
        self._secret_key = secret_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport or UrllibTransport()
        self.account = AccountService(self)
        self.payments = PaymentService(self)
        self.withdrawals = WithdrawalService(self)

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        headers = {"Accept": "application/json", "x-api-key": self._client_id}
        if self._secret_key:
            headers["x-api-secret"] = self._secret_key

        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload, separators=(",", ":"))

        response = self._transport.request(method, self._build_url(path, query), headers, body, self._timeout)
        if not 200 <= response.status_code < 300:
            raise TopChargeApiError(_error_message(response.body, response.status_code), response.status_code, response.body)
        if not response.body:
            return None
        try:
            decoded = json.loads(response.body)
        except json.JSONDecodeError as error:
            raise ValueError("TopCharge returned an invalid JSON response.") from error
        if not isinstance(decoded, dict):
            raise ValueError("TopCharge returned a JSON response that is not an object.")
        return decoded

    def _build_url(self, path: str, query: Optional[Mapping[str, Any]]) -> str:
        url = f"{self._base_url}/{path.strip('/')}/"
        if not query:
            return url
        values = {
            key: _query_value(value)
            for key, value in query.items()
            if value is not None and value != ""
        }
        return f"{url}?{urlencode(values)}" if values else url


class AccountService:
    def __init__(self, client: TopChargeClient) -> None:
        self._client = client

    def verify_credentials(self) -> None:
        self._client._request("GET", "/api/v1/account/verify-credentials")

    def get_balance(self) -> Dict[str, Any]:
        return _response(self._client._request("GET", "/api/v1/account/balance"))


class PaymentService:
    def __init__(self, client: TopChargeClient) -> None:
        self._client = client

    def create(
        self,
        payment_amount: str,
        *,
        description: Optional[str] = None,
        redirect_url: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        return _response(self._client._request("POST", "/api/v1/payment/create", _compact({
            "paymentAmount": payment_amount,
            "description": description,
            "redirectUrl": redirect_url,
            "callbackUrl": callback_url,
        })))

    def get_status(self, payment_id: str) -> Dict[str, Any]:
        return _response(self._client._request("GET", f"/api/v1/payment/status/{payment_id}"))

    def cancel(self, payment_id: str) -> Dict[str, Any]:
        return _response(self._client._request("POST", f"/api/v1/payment/cancel/{payment_id}"))


class WithdrawalService:
    def __init__(self, client: TopChargeClient) -> None:
        self._client = client

    def create(self, phone_number_country_code: str, phone_number: str, amount: str) -> Dict[str, Any]:
        return _response(self._client._request("POST", "/api/v1/withdrawal/create", {
            "phoneNumberCountryCode": phone_number_country_code,
            "phoneNumber": phone_number,
            "amount": amount,
        }))


def _response(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return value if value is not None else {}


def _compact(values: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _error_message(body: str, status_code: int) -> str:
    try:
        decoded = json.loads(body)
        if isinstance(decoded, dict):
            if isinstance(decoded.get("message"), str):
                return decoded["message"]
            error = decoded.get("err")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"]
    except json.JSONDecodeError:
        pass
    return f"TopCharge API request failed with HTTP status {status_code}."
