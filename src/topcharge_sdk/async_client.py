from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlencode

from .client import DEFAULT_BASE_URL, _compact, _error_message, _query_value, _response
from .exceptions import TopChargeApiError

try:
    import httpx
except ImportError:  # pragma: no cover - exercised only without the async extra installed.
    httpx = None  # type: ignore[assignment]


class AsyncTopChargeClient:
    """Async TopCharge client for FastAPI, Starlette, Quart, and async workers.

    Install the optional dependency first: ``pip install 'topcharge-sdk[async]'``.
    """

    def __init__(
        self,
        client_id: str,
        secret_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        http_client: Any = None,
    ) -> None:
        if httpx is None:
            raise ImportError("AsyncTopChargeClient requires httpx. Install it with: pip install 'topcharge-sdk[async]'.")
        if not client_id.strip() or not base_url.strip():
            raise ValueError("TopCharge client_id and base_url must not be empty.")
        self._client_id, self._secret_key, self._base_url = client_id, secret_key, base_url.rstrip("/")
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout)
        self.account = AsyncAccountService(self)
        self.payments = AsyncPaymentService(self)
        self.withdrawals = AsyncWithdrawalService(self)

    async def __aenter__(self) -> "AsyncTopChargeClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def _request(self, method: str, path: str, payload: Optional[Mapping[str, Any]] = None, query: Optional[Mapping[str, Any]] = None) -> Optional[Dict[str, Any]]:
        headers = {"Accept": "application/json", "x-api-key": self._client_id}
        if self._secret_key:
            headers["x-api-secret"] = self._secret_key
        response = await self._http_client.request(method, self._build_url(path, query), headers=headers, json=payload)
        if not response.is_success:
            raise TopChargeApiError(_error_message(response.text, response.status_code), response.status_code, response.text)
        if not response.text:
            return None
        decoded = response.json()
        if not isinstance(decoded, dict):
            raise ValueError("TopCharge returned a JSON response that is not an object.")
        return decoded

    def _build_url(self, path: str, query: Optional[Mapping[str, Any]]) -> str:
        url = f"{self._base_url}/{path.strip('/')}/"
        values = {key: _query_value(value) for key, value in (query or {}).items() if value is not None and value != ""}
        return f"{url}?{urlencode(values)}" if values else url


class AsyncAccountService:
    def __init__(self, client: AsyncTopChargeClient) -> None: self._client = client
    async def verify_credentials(self) -> None: await self._client._request("GET", "/api/v1/account/verify-credentials")
    async def get_balance(self) -> Dict[str, Any]: return _response(await self._client._request("GET", "/api/v1/account/balance"))


class AsyncPaymentService:
    def __init__(self, client: AsyncTopChargeClient) -> None: self._client = client
    async def create(self, payment_amount: str, *, description: Optional[str] = None, redirect_url: Optional[str] = None, callback_url: Optional[str] = None) -> Dict[str, Any]:
        return _response(await self._client._request("POST", "/api/v1/payment/create", _compact({"paymentAmount": payment_amount, "description": description, "redirectUrl": redirect_url, "callbackUrl": callback_url})))
    async def get_status(self, payment_id: str) -> Dict[str, Any]: return _response(await self._client._request("GET", f"/api/v1/payment/status/{payment_id}"))
    async def cancel(self, payment_id: str) -> Dict[str, Any]: return _response(await self._client._request("POST", f"/api/v1/payment/cancel/{payment_id}"))


class AsyncWithdrawalService:
    def __init__(self, client: AsyncTopChargeClient) -> None: self._client = client
    async def create(self, phone_number_country_code: str, phone_number: str, amount: str) -> Dict[str, Any]:
        return _response(await self._client._request("POST", "/api/v1/withdrawal/create", {"phoneNumberCountryCode": phone_number_country_code, "phoneNumber": phone_number, "amount": amount}))


