from dataclasses import dataclass
from typing import Any


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
