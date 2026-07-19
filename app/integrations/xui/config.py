from dataclasses import dataclass


@dataclass(frozen=True)
class XUIConfig:
    base_url: str
    web_base_path: str
    api_token: str
    subscription_base_url: str
    subscription_path: str
    default_inbound_ids: list[int]
    default_limit_ip: int
    default_total_gb: int
