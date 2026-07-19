from app.config import Settings
from app.integrations.xui.config import XUIConfig


def build_xui_config(settings: Settings) -> XUIConfig:
    return XUIConfig(
        base_url=settings.xui_base_url,
        web_base_path=settings.xui_web_base_path,
        api_token=settings.xui_api_token,
        subscription_base_url=settings.xui_subscription_base_url,
        subscription_path=settings.xui_subscription_path,
        default_inbound_ids=settings.xui_default_inbound_ids,
        default_limit_ip=settings.xui_default_limit_ip,
        default_total_gb=settings.xui_default_total_gb,
    )
