import os
from dotenv import load_dotenv

import asyncio
from xui import CreatedXUIClient, UpdatedXUIClient, XUIConfig, AsyncXUI
from typing import Any

load_dotenv()
BASE_URL: str | None = os.getenv(key="XUI_BASE_URL")
WEB_BASE_PATH: str | None = os.getenv(key="XUI_WEB_BASE_PATH")
API_TOKEN: str | None = os.getenv("XUI_API_TOKEN")
# USERNAME: str | None = os.getenv(key="XUI_USERNAME")
# PASSWORD: str | None = os.getenv(key="XUI+PASSWORD")

async def main():
    config = XUIConfig(
        base_url=BASE_URL,
        web_base_path=WEB_BASE_PATH,
        api_token=API_TOKEN
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
            email="python_test_2_5e001dc6-4632-4e59-95b3-5a16dd88636e",
            days=2,
        )

        print(f"email: {updated_client.email}")
        print(f"expiryTime (ms): {updated_client.client["expiryTime"]}")
        print(f"enable: {updated_client.client["enable"]}")
        print(f"totalGB (bytes): {updated_client.client["totalGB"]}")


if __name__ == "__main__":
    asyncio.run(main())
