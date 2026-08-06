import logging
import secrets

from aiohttp import web

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.integrations.yookassa import AsyncYooKassa
from app.services.payment_service import PaymentService
from app.services.exceptions import (
    PaymentServiceError,
    PaymentInvalidStateError,
    PaymentProviderRejectedError,
    PaymentProviderUnavailableError,
    PaymentVerificationError,
)


logger = logging.getLogger(__name__)


def build_yookassa_http_app(
        *,
        session_factory: async_sessionmaker[AsyncSession],
        yookassa: AsyncYooKassa,
        settings: Settings,
) -> web.Application:
    app = web.Application(
        client_max_size=64 * 1024,
    )

    async def health(_: web.Request) -> web.Response:
        return web.json_response(
            data={
                "status": "ok",
            }
        )

    async def yookassa_webhook(request: web.Request) -> web.Response:
        received_secret: str = request.match_info["secret"]
        if not secrets.compare_digest(received_secret, settings.yookassa_webhook_secret):
            raise web.HTTPNotFound()

        try:
            body = await request.json()

        except Exception:
            raise web.HTTPBadRequest(
                text="Invalid JSON",
            )

        if not isinstance(body, dict):
            raise web.HTTPBadRequest(
                text="Invalid request body",
            )

        if body.get("type") != "notification":
            raise web.HTTPBadRequest(
                text="Invalid notification type",
            )

        event = body.get("event")
        if event not in {"payment.succeeded", "payment.canceled"}:
            return web.Response(status=200)

        payment_object = body.get("object")
        if not isinstance(payment_object, dict):
            raise web.HTTPBadRequest(
                text="Notification does not contain object",
            )

        payment_id = payment_object.get("id")
        if not isinstance(payment_id, str) or not payment_id:
            raise web.HTTPBadRequest(
                text="Notification object does not contain payment id",
            )

        async with session_factory() as session:
            payment_service = PaymentService(
                session=session,
                yookassa=yookassa,
                settings=settings,
            )

            try:
                await payment_service.synchronize_payment(payment_id=payment_id)

            except (
                PaymentVerificationError,
                PaymentProviderRejectedError,
                PaymentInvalidStateError,
            ):
                await session.rollback()

                logger.warning(
                    "Rejected YooKassa notification (payment_id=%s, event=%s)",
                    payment_id,
                    event,
                    exc_info=True,
                )

                return web.Response(status=200)

            except PaymentProviderUnavailableError:
                await session.rollback()

                logger.exception(
                    "YooKassa is unavailable while processing webhook (payment_id=%s)",
                    payment_id,
                )

                return web.Response(status=503)

            except PaymentServiceError:
                await session.rollback()

                logger.exception(
                    "Payment service failed while processing webhook (payment_id=%s)",
                    payment_id,
                )

                return web.Response(status=503)

            except Exception:
                await session.rollback()

                logger.exception(
                    "Unexpected error while processing YooKassa webhook (payment_id=%s)",
                    payment_id,
                )

                return web.Response(status=503)

        return web.Response(status=200)

    app.router.add_get(
        path="/health",
        handler=health,
    )

    app.router.add_post(
        path="/webhooks/yookassa/{secret}",
        handler=yookassa_webhook,
    )

    return app
