import os
from dotenv import load_dotenv

import asyncio
from xui import XUIConfig, AsyncXUI
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

        inbounds: list[dict[str, Any]] = await session.get_inbounds()
        for inbound in inbounds:
            print(
                inbound["id"],
                inbound.get("remark"),
                inbound.get("protocol"),
                inbound.get("port")
            )

if __name__ == "__main__":
    asyncio.run(main())
