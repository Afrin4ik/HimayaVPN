from app.config import Settings, get_settings

import asyncio
from app.integrations.xui import CreatedXUIClient, UpdatedXUIClient, XUIConfig, AsyncXUI
from typing import Any

# BASE_URL: str | None = os.getenv(key="XUI_BASE_URL")
# WEB_BASE_PATH: str | None = os.getenv(key="XUI_WEB_BASE_PATH")
# API_TOKEN: str | None = os.getenv(key="XUI_API_TOKEN")
# USERNAME: str | None = os.getenv(key="XUI_USERNAME")
# PASSWORD: str | None = os.getenv(key="XUI+PASSWORD")

async def main():
    settings: Settings = get_settings()

    config = XUIConfig(
        base_url=settings.xui_base_url,
        web_base_path=settings.xui_web_base_path,
        api_token=settings.xui_api_token,
    )

    async with AsyncXUI(config) as session:
        # await session.login()


        # тест 1 (get inbounds)
        # inbounds: list[dict[str, Any]] = await session.get_inbounds()
        # for inbound in inbounds:
        #     print(
        #         inbound["id"],
        #         inbound.get("remark"),
        #         inbound.get("protocol"),
        #         inbound.get("port")
        #     )


        # тест 2 (add client to inbounds)
        # client: CreatedXUIClient = await session.add_client_to_inbounds(
        #     inbound_ids=[2, 3],
        #     email="python_test_2",
        #     limit_ip=1,
        #     total_gb=25,
        #     expiry_days=10,
        #     comment="test 2 create client from python",
        # )

        # print(f"email: {client.email}")
        # print(f"uuid: {client.uuid}")
        # print(f"password: {client.password}")
        # print(f"hysteria_auth: {client.hysteria_auth}")
        # print(f"sub_id: {client.sub_id}")
        # print(f"inbound_ids: {client.inbound_ids}")
        # print(f"raw_response:\n{client.raw_response}")


        # тест 3 (update client data; renew client)
        updated_client: UpdatedXUIClient = await session.renew_client(
            email="python_test_b7935034-a0ca-4da1-a30b-eb1e7d8653f1",
            days=1,
        )

        print(f"email: {updated_client.email}")
        print(f"uuid: {updated_client.uuid}")
        print(f"inbound_ids: {updated_client.inbound_ids}")
        print(f"client: {updated_client.client}")
        print(f"raw_response: {updated_client.raw_response}")
        print(f"traffic_reset_response: {updated_client.traffic_reset_response}")
        print("-"*15)
        print(f"expiryTime (ms): {updated_client.client['expiryTime']}")
        print(f"totalGB (bytes): {updated_client.client['totalGB']}")
        print(f"enable: {updated_client.client['enable']}")


if __name__ == "__main__":
    asyncio.run(main())
