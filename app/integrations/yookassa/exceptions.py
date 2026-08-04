from typing import Any


class YooKassaError(Exception):
    """Base error of the YooKassa adapter"""


class YooKassaClientNotStartedError(YooKassaError):
    """Client session has not been initialized"""


class YooKassaTransportError(YooKassaError):
    """Network or timeout error while communicating with YooKassa"""


class YooKassaResponseError(YooKassaError):
    """YooKassa returned a malformed successful response"""


class YooKassaAPIError(YooKassaError):
    def __init__(
            self,
            *,
            status: int,
            response: dict[str, Any] | None,
    ) -> None:
        self.status = status
        self.code = response.get("code") if response else None
        self.description = response.get("description") if response else None

        super().__init__(
            "YooKassa API error: "
            f"status={self.status}, "
            f"code={self.code}, "
            f"description={self.description}"
        )

    @property
    def retryable(self) -> bool:
        return self.status == 429 or 500 <= self.status < 600
