import aiohttp

from typing import Any


class YooKassaError(Exception):
    pass


class YooKassaAPIError(YooKassaError):
    def __init__(
            self,
            *,
            status: int,
            response: dict[str, Any] | None,
    ) -> None:
        self.status: int = status
        self.response: dict[str, Any] | None = response

        if response:
            code = response.get("code")
            description = response.get("description")
        else:
            code = None
            description = None

        super().__init__(
            f"YooKassa API error: status={status}, code={code}, description={description}"
        )


class AsyncYooKassa:
    API_BASE_URL = "https://api.yookassa.ru/v3"

    def __init__(
            self,
            *,
            shop_id: str,
            secret_key: str,
    ) -> None:
        self.shop_id: str = shop_id
        self.secret_key: str = secret_key
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        if self._session is not None:
            return

        self._session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(
                login=self.shop_id,
                password=self.secret_key,
            ),
            timeout=aiohttp.ClientTimeout(total=20),
            headers={
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    def _require_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError("YooKassa client is not started")

        return self._session

    async def _request(
            self,
            *,
            method: str,
            path: str,
            json: dict[str, Any] | None = None,
            idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        session: aiohttp.ClientSession = self._require_session()

        headers: dict[str, str] = {}

        if idempotency_key is not None:
            headers["Idempotence-Key"] = idempotency_key

        async with session.request(
            method=method,
            url=f"{self.API_BASE_URL}{path}",
            json=json,
            headers=headers,
        ) as response:
            try:
                payload = await response.json(content_type=None)
            except Exception:
                payload = None

            if response.status != 200:
                raise YooKassaAPIError(
                    status=response.status,
                    response=payload if isinstance(payload, dict) else None,
                )

            if not isinstance(payload, dict):
                raise YooKassaError("YooKassa returned a non-object JSON response")

            return payload

    async def create_payment(
            self,
            *,
            request: dict[str, Any],
            idempotency_key: str,
    ) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/payments",
            json=request,
            idempotency_key=idempotency_key,
        )

    async def get_payment(
            self,
            *,
            payment_id: str,
    ) -> dict[str, Any]:
        return await self._request(
            method="GET",
            path=f"/payments/{payment_id}",
        )
