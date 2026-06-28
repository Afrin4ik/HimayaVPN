import aiohttp
import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Self, Any
from http.cookies import BaseCookie


@dataclass
class XUIConfig:
    base_url: str
    web_base_path: str
    api_token: str


class XUIException(Exception):
    pass


class AsyncXUI:
    def __init__(self, config: XUIConfig) -> None:
        self.config: XUIConfig = config
        self.base_url: str = self._normalize_base_url(config.base_url, config.web_base_path)
        self.session: aiohttp.ClientSession | None = None

    @staticmethod
    def _normalize_base_url(base_url: str, web_base_path: str) -> str:
        base: str = base_url.rstrip("/")
        path: str = web_base_path.strip("/")
        if path:
            return f"{base}/{path}"
        else:
            return base

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def start(self) -> None:
        if self.session is not None and not self.session.closed:
            return

        if not self.config.api_token:
            raise XUIException("API Token is empty")

        timeout = aiohttp.ClientTimeout(total=20)

        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config.api_token}",
            },
        )

    async def close(self) -> None:
        if self.session is not None and not self.session.closed:
            await self.session.close()
        self.session = None

    def _require_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            raise XUIException("Session is not started. Use `async with AsyncXUI(...)` or call `start()`")
        return self.session

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.strip('/')}"

    @staticmethod
    async def _read_json_response(response: aiohttp.ClientResponse) -> dict[str, Any]:
        try:
            response.raise_for_status()
            return await response.json()
        except aiohttp.ClientResponseError as exc:
            raise XUIException(f"HTTP error: {exc.status} - {exc.message}") from exc
        except aiohttp.ContentTypeError as exc:
            text = await response.text()
            raise XUIException(f"Invalid JSON response: {text[:500]}") from exc
        except json.JSONDecodeError as exc:
            text = await response.text()
            raise XUIException(f"Invalid JSON response: {text[:500]}") from exc

        # if response.status >= 400:
        #     text: str = await response.text()
        #     raise XUIException(f"HTTP {response.status}: {text}")

        # text: str = await response.text()
        # if not text.strip():
        #     return {}

        # try:
        #     data = json.loads(text)
        #     if not isinstance(data, dict):
        #         raise XUIException(f"Unexpected response type: {type(data).__name__}")
        #     return data
        # except json.JSONDecodeError as exc:
        #     raise XUIException(f"Invalid json response: {text}") from exc

    async def get_inbounds(self) -> list[dict[str, Any]]:
        session: aiohttp.ClientSession = self._require_session()

        async with session.get(url=self._url(path="/panel/api/inbounds/list")) as response:
            data: dict[str, Any] = await self._read_json_response(response=response)

            if not data.get("success", False):
                raise XUIException(f"Cannot get inbounds list: {data}")

            obj = data.get("obj", [])
            if not isinstance(obj, list):
                raise XUIException(f"Unexpected inbounds payload: {data}")

            return obj

    async def get_inbound(self, inbound_id: int) -> dict[str, Any]:
        session: aiohttp.ClientSession = self._require_session()

        async with session.get(url=self._url(path=f"/panel/api/inbounds/get/{inbound_id}")) as response:
            data: dict[str, Any] = await self._read_json_response(response=response)

            if not data.get("success", False):
                raise XUIException(f"Cannot get inbound {inbound_id}: {data}")

            obj = data.get("obj", {})
            if not isinstance(obj, dict):
                raise XUIException(f"Unexpected inbound payload: {data}")

            return obj
