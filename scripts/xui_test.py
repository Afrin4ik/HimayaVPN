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
        subscription_base_url=settings.xui_subscription_base_url,
        subscription_path=settings.xui_subscription_path,
        default_inbound_ids=settings.xui_default_inbound_ids,
        default_limit_ip=settings.xui_default_limit_ip,
        default_total_gb=settings.xui_default_total_gb,
    )

    async with AsyncXUI(config=config) as session:
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
        # updated_client: UpdatedXUIClient = await session.renew_client(
        #     email="python_test_b7935034-a0ca-4da1-a30b-eb1e7d8653f1",
        #     days=1,
        # )

        # print(f"email: {updated_client.email}")
        # print(f"uuid: {updated_client.uuid}")
        # print(f"inbound_ids: {updated_client.inbound_ids}")
        # print(f"client: {updated_client.client}")
        # print(f"raw_response: {updated_client.raw_response}")
        # print(f"traffic_reset_response: {updated_client.traffic_reset_response}")
        # print("-"*15)
        # print(f"expiryTime (ms): {updated_client.client['expiryTime']}")
        # print(f"totalGB (bytes): {updated_client.client['totalGB']}")
        # print(f"enable: {updated_client.client['enable']}")



        # тест 4 (get_client_subscription_link)
        # sub_link: str = await session.get_client_subscription_link(email="python_test_b7935034-a0ca-4da1-a30b-eb1e7d8653f1")

        # print(f"sub_link: {sub_link}")



        # тест 5 (add_client; get_client_subscription_link)
        # client: CreatedXUIClient = await session.add_client(
        #     email="python_test_5",
        #     expiry_days=20,
        # )
        # sub_link: str = await session.get_client_subscription_link(email=client.email)

        # print("Client info:")
        # print(f"email: {client.email}")
        # print(f"uuid: {client.uuid}")
        # print(f"password: {client.password}")
        # print(f"hysteria_auth: {client.hysteria_auth}")
        # print(f"sub_id: {client.sub_id}")
        # print(f"inbound_ids: {client.inbound_ids}")
        # print(f"raw_response:\n{client.raw_response}")
        # print("Sub_link info:")
        # print(f"sub_link: {sub_link}")



        # тест 6 (delete_client)
        # data: dict[str, Any] = await session.delete_client(
        #     email="python_test_2_5e001dc6-4632-4e59-95b3-5a16dd88636e",
        # )

        # print(f"data:\n{data}")



        # тест 7 (get_clients_list)
        clients: list[dict[str, Any]] = await session.get_clients_list()

        # print(f"Clients: {clients}")
        for i in range(len(clients)):
            print(f"Client {i + 1}:\n{clients[i]}")
            print("-" * 15)


if __name__ == "__main__":
    asyncio.run(main=main())
