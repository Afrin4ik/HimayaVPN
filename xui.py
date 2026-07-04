import aiohttp
import json
import uuid
import time
import secrets
from dataclasses import dataclass
from urllib.parse import quote
from copy import deepcopy
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


@dataclass(frozen=True)
class UpdatedXUIClient:
    email: str
    uuid: str | None
    inbound_ids: list[int]
    client: dict[str, Any]
    raw_response: dict[str, Any]
    traffic_reset_response: dict[str, Any] | None = None


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
    def _gb_to_bytes(total_gb: int) -> int:
        if total_gb < 0:
            raise XUIException("total_gb cannot be negative")
        return int(total_gb * 1024 ** 3)

    @staticmethod
    def _expiry_days_to_ms(expiry_days: int) -> int:
        if expiry_days < 0:
            raise XUIException("expiry_days cannot be negative")
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

    @staticmethod
    def _quote_path(path: str) -> str:
        return quote(string=path, safe="")

    @staticmethod
    def _expiry_days_to_ms_from_base(days: int, current_expiry_ms: int | None = None) -> int:
        if days < 0:
            raise XUIException("days cannot be negative")

        if days == 0:
            return 0

        now_ms = int(time.time() * 1000)
        base_ms = now_ms

        if current_expiry_ms is not None and current_expiry_ms > now_ms:
            base_ms = current_expiry_ms

        return base_ms + days * 24 * 60 * 60 * 1000

    @staticmethod
    def _client_record_to_update_payload(client_record: dict[str, Any]) -> dict[str, Any]:
        client: dict[str, Any] = deepcopy(client_record)

        client_uuid = client.get("uuid")
        if client_uuid is None:
            raw_id = client.get("id")
            if isinstance(raw_id, str):
                client_uuid = raw_id

        if client_uuid is None:
            raise XUIException(f"Client uuid is missing: {client_record}")

        client["id"] = str(client_uuid)

        client.pop("uuid", None)
        client.pop("usedTraffic", None)
        client.pop("traffic", None)
        client.pop("createdAt", None)
        client.pop("updatedAt", None)
        client.pop("created_at", None)
        client.pop("updated_at", None)

        return client

    @staticmethod
    def _extract_client_payload(obj: dict[str, Any]) -> tuple[dict[str, Any], list[int]]:
        client: dict[str, Any] = obj.get("client")
        if not isinstance(client, dict):
            raise XUIException(f"Unexpected client payload: {obj}")

        inbound_ids: list[int] = obj.get("inboundIds", [])
        if inbound_ids is None:
            inbound_ids = []
        if not isinstance(inbound_ids, list) or not all(isinstance(inbound_id, int) for inbound_id in inbound_ids):
            raise XUIException(f"Unexpected inboundIds payload: {obj}")

        return client, inbound_ids

    async def _post_update_client_payload(
            self,
            email: str,
            client: dict[str, Any],
            inbound_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        if not email.strip():
            raise XUIException("email cannot be empty")

        session: aiohttp.ClientSession = self._require_session()

        params: dict[str, str] = {}
        if inbound_ids is not None:
            params["inboundIds"] = ",".join(str(inbound_id) for inbound_id in inbound_ids)

        async with session.post(
            url=self._url(path=f"/panel/api/clients/update/{self._quote_path(path=email)}"),
            json=client,
            params=params,
        ) as response:
            data: dict[str, Any] = await self._read_json_response(response=response)

            if not data.get("success", False):
                raise XUIException(f"Cannot update client {email}: {data}")

            return data

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
        if not isinstance(email, str):
            raise XUIException("email must be an str")
        if not email.strip():
            raise XUIException("email cannot be empty")

        if not isinstance(inbound_ids, list):
            raise XUIException("inbound_ids must be a list")
        if not inbound_ids:
            raise XUIException("inbound_ids cannot be empty")
        if not all(isinstance(inbound_id, int) for inbound_id in inbound_ids):
            raise XUIException("in inbound_ids must be ints")

        if not isinstance(flow, str):
            raise XUIException("flow must be a str")

        if not isinstance(limit_ip, int):
            raise XUIException("limit_ip must be an int")
        if limit_ip < 0:
            raise XUIException("limit_ip cannot be negative")

        if not isinstance(total_gb, int):
            raise XUIException("total_gb must be an int")
        if total_gb < 0:
            raise XUIException("total_gb cannot be negative")

        if not isinstance(expiry_days, int):
            raise XUIException("expiry_time must be an int")
        if expiry_days < 0:
            raise XUIException("expiry_time_ms cannot be negative")

        if not isinstance(enable, bool):
            raise XUIException("enable must be bool")

        if not isinstance(tg_id, int):
            raise XUIException("tg_id must be an int")
        if tg_id < 0:
            raise XUIException("tg_id cannot be negative")

        if not isinstance(comment, str):
            raise XUIException("comment must be a str")

        if not isinstance(group, str):
            raise XUIException("group must be a str")

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
            "totalGB": self._gb_to_bytes(total_gb=total_gb),
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

    async def get_client_by_email(self, email: str) -> dict[str, Any]:
        if not email.strip():
            raise XUIException("email cannot be empty")

        session: aiohttp.ClientSession = self._require_session()

        async with session.get(
            url=self._url(path=f"/panel/api/clients/get/{self._quote_path(path=email)}"),
        ) as response:
            data: dict[str, Any] = await self._read_json_response(response=response)

            if not data.get("success", False):
                raise XUIException(f"Cannot get client {email}: {data}")

            obj: dict[str, Any] = data.get("obj")
            if not isinstance(obj, dict):
                raise XUIException(f"Unexpected client payload: {data}")

            return obj

    async def update_client_data(
            self,
            email: str,
            *,
            inbound_ids: list[int] | None = None,
            flow: str | None = None,
            limit_ip: int | None = None,
            total_gb: int | None = None,
            expiry_time_ms: int | None = None,
            enable: bool | None = None,
            tg_id: int | None = None,
            comment: str | None = None,
            group: str | None = None,
            reset: int | None = None,
    ) -> UpdatedXUIClient:
        if not isinstance(email, str):
            raise XUIException("email must be an str")
        elif not email.strip():
            raise XUIException("email cannot be empty")

        if inbound_ids is not None:
            if not isinstance(inbound_ids, list):
                raise XUIException("inbound_ids must be a list")
            if not inbound_ids:
                raise XUIException("inbound_ids cannot be empty")
            if not all(isinstance(inbound_id, int) for inbound_id in inbound_ids):
                raise XUIException("in inbound_ids must be ints")

        if flow is not None:
            if not isinstance(flow, str):
                raise XUIException("flow must be a str")

        if limit_ip is not None:
            if not isinstance(limit_ip, int):
                raise XUIException("limit_ip must be an int")
            if limit_ip < 0:
                raise XUIException("limit_ip cannot be negative")

        if total_gb is not None:
            if not isinstance(total_gb, int):
                raise XUIException("total_gb must be an int")
            if total_gb < 0:
                raise XUIException("total_gb cannot be negative")

        if expiry_time_ms is not None:
            if not isinstance(expiry_time_ms, int):
                raise XUIException("expiry_time must be an int")
            if expiry_time_ms < 0:
                raise XUIException("expiry_time_ms cannot be negative")

        if enable is not None:
            if not isinstance(enable, bool):
                raise XUIException("enable must be bool")

        if tg_id is not None:
            if not isinstance(tg_id, int):
                raise XUIException("tg_id must be an int")
            if tg_id < 0:
                raise XUIException("tg_id cannot be negative")

        if comment is not None:
            if not isinstance(comment, str):
                raise XUIException("comment must be a str")

        if group is not None:
            if not isinstance(group, str):
                raise XUIException("group must be a str")

        if reset is not None:
            if not isinstance(reset, int):
                raise XUIException("reset must be an int")

        current_obj: dict[str, Any] = await self.get_client_by_email(email=email)
        current_client, current_inbound_ids = self._extract_client_payload(obj=current_obj)

        updated_client: dict[str, Any] = self._client_record_to_update_payload(client_record=current_client)

        client_uuid = updated_client.get("id")

        if flow is not None:
            updated_client["flow"] = flow

        if limit_ip is not None:
            updated_client["limitIp"] = limit_ip

        if total_gb is not None:
            updated_client["totalGB"] = self._gb_to_bytes(total_gb=total_gb)

        if expiry_time_ms is not None:
            updated_client["expiryTime"] = expiry_time_ms

        if enable is not None:
            updated_client["enable"] = enable

        if tg_id is not None:
            updated_client["tgId"] = tg_id

        if comment is not None:
            updated_client["comment"] = comment

        if group is not None:
            updated_client["group"] = group

        if reset is not None:
            updated_client["reset"] = reset

        if inbound_ids is not None:
            target_inbound_ids = inbound_ids
        else:
            target_inbound_ids = current_inbound_ids

        data: dict[str, Any] = await self._post_update_client_payload(
            email=email,
            client=updated_client,
            inbound_ids=target_inbound_ids,
        )

        return UpdatedXUIClient(
            email=email,
            uuid=client_uuid,
            inbound_ids=target_inbound_ids,
            client=updated_client,
            raw_response=data,
        )

    async def reset_client_traffic(self, email: str) -> dict[str, Any]:
        if not email.strip():
            raise XUIException("email cannot be empty")

        session: aiohttp.ClientSession = self._require_session()

        async with session.post(
            url=self._url(path=f"/panel/api/clients/resetTraffic/{self._quote_path(path=email)}"),
        ) as response:
            data: dict[str, Any] = await self._read_json_response(response=response)

            if not data.get("success", False):
                raise XUIException(f"Cannot reset traffic for client {email}: {data}")

            return data

    async def renew_client(
            self,
            email: str,
            days: int,
            reset_traffic_bool: bool = True,
    ) -> UpdatedXUIClient:
        if not isinstance(days, int):
            raise XUIException("days must be an int")
        if days < 0:
            raise XUIException("days cannot be negative")

        current_obj: dict[str, Any] = await self.get_client_by_email(email)
        current_client, _ = self._extract_client_payload(current_obj)

        current_expiry_ms_raw = current_client.get("expiryTime")
        try:
            if current_expiry_ms_raw is None:
                current_expiry_ms = 0
            else:
                current_expiry_ms = int(current_expiry_ms_raw)
        except (TypeError, ValueError):
            raise XUIException(f"Unexpected expiryTime value: {current_expiry_ms_raw}")

        new_expiry_time_ms: int = self._expiry_days_to_ms_from_base(days=days, current_expiry_ms=current_expiry_ms)

        updated_client: UpdatedXUIClient = await self.update_client_data(
            email=email,
            expiry_time_ms=new_expiry_time_ms,
            enable=True,
        )

        traffic_reset_response: dict[str, Any] | None = None
        if reset_traffic_bool:
            traffic_reset_response = await self.reset_client_traffic(email=email)

        return UpdatedXUIClient(
            email=updated_client.email,
            uuid=updated_client.uuid,
            inbound_ids=updated_client.inbound_ids,
            client=updated_client.client,
            raw_response=updated_client.raw_response,
            traffic_reset_response=traffic_reset_response,
        )
