import aiohttp
import asyncio

from typing import Any

from app.integrations.yookassa.exceptions import (
    YooKassaAPIError,
    YooKassaClientNotStartedError,
    YooKassaResponseError,
    YooKassaTransportError,
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
            raise YooKassaClientNotStartedError("YooKassa client is not started")

        return self._session

    async def _request_once(
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

        try:
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

                if not 200 <= response.status < 300:
                    raise YooKassaAPIError(
                        status=response.status,
                        response=payload if isinstance(payload, dict) else None,
                    )

        except asyncio.TimeoutError as exc:
            raise YooKassaTransportError(
                "YooKassa request timed out"
            ) from exc

        except aiohttp.ClientError as exc:
            raise YooKassaTransportError(
                "YooKassa transport error"
            ) from exc

        if not isinstance(payload, dict):
            raise YooKassaResponseError("YooKassa returned a non-object JSON response")

        return payload

    async def _request_with_retry(
            self,
            *,
            method: str,
            path: str,
            json: dict[str, Any] | None = None,
            idempotency_key: str | None = None,
            attempts: int = 3,
    ) -> dict[str, Any]:
        if attempts <= 0:
            raise ValueError("attempts must be positive")

        for attempt in range(attempts):
            try:
                return await self._request_once(
                    method=method,
                    path=path,
                    json=json,
                    idempotency_key=idempotency_key,
                )

            except YooKassaAPIError as exc:
                if not exc.retryable or attempt == attempts - 1:
                    raise

            except (YooKassaTransportError, YooKassaResponseError):
                if attempt == attempts - 1:
                    raise

            await asyncio.sleep(2 ** attempt)

        raise RuntimeError("Unreachable YooKassa retry state")

    async def create_payment(
            self,
            *,
            request: dict[str, Any],
            idempotency_key: str,
    ) -> dict[str, Any]:
        return await self._request_with_retry(
            method="POST",
            path="/payments",
            json=request,
            idempotency_key=idempotency_key,
            attempts=3,
        )

    async def get_payment(
            self,
            *,
            payment_id: str,
    ) -> dict[str, Any]:
        return await self._request_with_retry(
            method="GET",
            path=f"/payments/{payment_id}",
            attempts=3,
        )
