import aiohttp
import json
import uuid
import time
import secrets
from dataclasses import dataclass
from typing import Self, Any


@dataclass(frozen=True)
class XUIConfig:
    base_url: str
    web_base_path: str
    api_token: str


@dataclass(frozen=True)
class CreatedXUIClient:
    email: str
    uuid: str
    password: str
    hysteria_auth: str
    sub_id: str
    inbound_ids: list[int]
    raw_response: dict[str, Any]


class XUIException(Exception):
    pass


class AsyncXUI:
    def __init__(self, config: XUIConfig) -> None:
        self.config: XUIConfig = config
        self.base_url: str = self._normalize_base_url(config.base_url, config.web_base_path)
        self.session: aiohttp.ClientSession | None = None

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

    @staticmethod
    def _normalize_base_url(base_url: str, web_base_path: str) -> str:
        base: str = base_url.rstrip("/")
        path: str = web_base_path.strip("/")
        if path:
            return f"{base}/{path}"
        else:
            return base

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.strip('/')}"

    def _require_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            raise XUIException("Session is not started. Use `async with AsyncXUI(...)` or call `start()`")
        return self.session

    @staticmethod
    def _gb_to_bytes(gb: int) -> int:
        return int(gb * 1024 ** 3)

    @staticmethod
    def _expiry_days_to_ms(expiry_days: int) -> int:
        if expiry_days == 0:
            return 0
        return int((time.time() + expiry_days * 24 * 60 * 60) * 1000)

    @staticmethod
    def _generate_uuid() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _generate_password() -> str:
        return secrets.token_hex(16)

    @staticmethod
    def _generate_hysteria_auth() -> str:
        return secrets.token_hex(16)

    @staticmethod
    def _generate_sub_id() -> str:
        return secrets.token_hex(16)

    @staticmethod
    def _check_adding_client_data(inbound_ids: list[int], email: str, limit_ip: int, total_gb: int, expiry_days: int) -> None:
        if not inbound_ids:
            raise XUIException("inbound_ids cannot be empty")

        if not email.strip():
            raise XUIException("email cannot be empty")

        if limit_ip < 0:
            raise XUIException("limit_ip cannot be negative")

        if total_gb < 0:
            raise XUIException("total_gb cannot be negative")

        if expiry_days < 0:
            raise XUIException("expiry_days cannot be negative")

    @staticmethod
    async def _read_json_response(response: aiohttp.ClientResponse) -> dict[str, Any]:
        if response.status >= 400:
            text: str = await response.text()
            raise XUIException(f"HTTP error. Status: {response.status}. Message: {text[:500]}")

        text: str = await response.text()
        if not text.strip():
            return {}

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise XUIException(f"Unexpected response type: {type(data).__name__}")
            return data
        except json.JSONDecodeError as exc:
            raise XUIException(f"Invalid JSON response: {text[:500]}") from exc

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

    async def add_client_to_inbounds(
            self,
            inbound_ids: list[int],
            email: str,
            *,
            flow: str = "", # "xtls-rprx-vision" -- для inbound с конфигурацией VLESS + TCP + REALITY/TLS
            limit_ip: int = 0,
            total_gb: int = 0,
            expiry_days: int = 0,
            enable: bool = True,
            tg_id: int = 0,
            comment: str = "",
            group: str = "",
    ) -> CreatedXUIClient:

        self._check_adding_client_data(
            inbound_ids=inbound_ids,
            email=email,
            limit_ip=limit_ip,
            total_gb=total_gb,
            expiry_days=expiry_days,
        )

        session: aiohttp.ClientSession = self._require_session()

        client_uuid: str = self._generate_uuid()
        client_password: str = self._generate_password()
        client_hysteria_auth: str = self._generate_hysteria_auth()
        client_sub_id: str = self._generate_sub_id()

        email = f"{email}_{client_uuid}"

        client: dict[str, Any] = {
            "id": client_uuid,
            "email": email,
            "password": client_password,
            "auth": client_hysteria_auth,
            "flow": flow,
            "limitIp": limit_ip,
            "totalGB": self._gb_to_bytes(gb=total_gb),
            "expiryTime": self._expiry_days_to_ms(expiry_days=expiry_days),
            "enable": enable,
            "tgId": tg_id,
            "subId": client_sub_id,
            "comment": comment,
            "reset": 0,
            "group": group,
        }

        payload: dict[str, Any] = {
            "client": client,
            "inboundIds": inbound_ids,
        }

        async with session.post(
            url=self._url(path="/panel/api/clients/add"),
            json=payload,
        ) as response:
            data: dict[str, Any] = await self._read_json_response(response=response)

            if not data.get("success", False):
                raise XUIException(f"Cannot add client {email}: {data}")

            return CreatedXUIClient(
                email=email,
                uuid=client_uuid,
                password=client_password,
                hysteria_auth=client_hysteria_auth,
                sub_id=client_sub_id,
                inbound_ids=inbound_ids,
                raw_response=data,
            )

    async def add_one_client(
            self,
            inbound_id: int,
            email: str,
            *,
            flow: str = "",
            limit_ip: int = 0,
            total_gb: int = 0,
            expiry_days: int = 0,
            enable: bool = True,
            tg_id: int = 0,
            comment: str = "",
            group: str = "",
    ) -> CreatedXUIClient:

        return await self.add_client_to_inbounds(
            inbound_ids=[inbound_id],
            email=email,
            flow=flow,
            limit_ip=limit_ip,
            total_gb=total_gb,
            expiry_days=expiry_days,
            enable=enable,
            tg_id=tg_id,
            comment=comment,
            group=group,
        )
