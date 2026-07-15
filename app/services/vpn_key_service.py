import logging

from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram.types import User as TelegramUser
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.xui import AsyncXUI, CreatedXUIClient, XUIConfig
from app.database.models import (
    User,
    Tariff,
    VpnKey,
    VPN_KEY_CREATING,
    VPN_KEY_ACTIVE,
    VPN_KEY_FAILED,
    VPN_KEY_DISABLED,
    VPN_KEY_RENEWING,
)
from app.repositories.tariff_repository import TariffRepository
from app.repositories.vpn_key_repository import VpnKeyRepository
from app.services.user_service import UserService

from app.services.exceptions import (
    VpnKeyCreationInProgressError,
    VpnKeyCreationFailedError,
    VpnKeyDisabledError,
    VpnKeyInvalidStateError,
    VpnKeyRenewalInProgressError,
    VpnKeyRenewalFailedError,
)


logger = logging.getLogger(__name__)


VPN_KEY_CREATING_TIMEOUT = timedelta(minutes=2)
VPN_KEY_RENEWING_TIMEOUT = timedelta(minutes=2)

TRIAL_TARIFF_CODE = "trial_3_days"


class VpnKeyService:
    def __init__(self, session: AsyncSession, xui: AsyncXUI, xui_config: XUIConfig) -> None:
        self.session: AsyncSession = session
        self.xui: AsyncXUI = xui
        self.xui_config: XUIConfig = xui_config
        self.tariffs_repository = TariffRepository(session=session)
        self.vpn_keys_repository = VpnKeyRepository(session=session)
        self.user_service = UserService(session=session)

    @staticmethod
    def _require_usable_active_vpn_key(
        vpn_key: VpnKey,
    ) -> VpnKey:
        if vpn_key.status != VPN_KEY_ACTIVE:
            raise VpnKeyInvalidStateError(f"VPN key {vpn_key.id} is not active (status={vpn_key.status})")

        if not isinstance(vpn_key.subscription_url, str) or not vpn_key.subscription_url.strip():
            raise VpnKeyInvalidStateError(f"Active VPN key {vpn_key.id} dose not have subscription_url")

        if not isinstance(vpn_key.xui_email, str) or not vpn_key.xui_email.strip():
            raise VpnKeyInvalidStateError(f"Active VPN key {vpn_key.id} dose not have xui_email")

        if not isinstance(vpn_key.xui_uuid, str) or not vpn_key.xui_uuid.strip():
            raise VpnKeyInvalidStateError(f"Active VPN key {vpn_key.id} dose not have xui_uuid")

        if not isinstance(vpn_key.xui_sub_id, str) or not vpn_key.xui_sub_id.strip():
            raise VpnKeyInvalidStateError(f"Active VPN key {vpn_key.id} dose not have xui_sub_id")

        return vpn_key

    @staticmethod
    def _calculate_renewal_expires_at(
            *,
            current_expires_at: datetime | None,
            duration_days: int,
    ) -> datetime:
        if duration_days <= 0:
            raise ValueError("duration_days must be positive")

        now: datetime = datetime.now(timezone.utc)

        if (current_expires_at is not None and current_expires_at > now):
            base: datetime = current_expires_at
        else:
            base: datetime = now

        return base + timedelta(days=duration_days)

    def _resolve_vpn_key_after_integrity_error(
            self,
            *,
            vpn_key: VpnKey,
    ) -> VpnKey:
        if vpn_key.status == VPN_KEY_ACTIVE:
            logger.info(
                "Concurrent VPN key creation already completed (vpn_key_id=%s, user_id=%s)",
                vpn_key.id,
                vpn_key.user_id,
            )
            return self._require_usable_active_vpn_key(vpn_key=vpn_key)

        if vpn_key.status == VPN_KEY_CREATING:
            raise VpnKeyCreationInProgressError(f"VPN key {vpn_key.id} is being created by another request")

        if vpn_key.status == VPN_KEY_FAILED:
            raise VpnKeyCreationFailedError(f"Concurrent VPN key creation failed (vpn_key_id={vpn_key.id}, error={vpn_key.error_message})")

        if vpn_key.status == VPN_KEY_DISABLED:
            raise VpnKeyDisabledError(f"VPN key {vpn_key.id} is disabled")

        raise VpnKeyInvalidStateError(f"VPN key {vpn_key.id} has unexpected status: {vpn_key.status}")

    async def _delete_untracked_xui_clients_for_user(
            self,
            *,
            telegram_id: int,
    ) -> None:
        email_prefix = f"tg_{telegram_id}_"

        xui_clients: list[dict[str, Any]] = await self.xui.get_clients_list()

        matching_emails: list[str] = []

        for xui_client in xui_clients:
            email = xui_client.get("email")
            if not isinstance(email, str):
                continue

            if email.startswith(email_prefix):
                matching_emails.append(email)

        for email in matching_emails:
            logger.warning(
                "Deleting stale XUI client before retry: telegram_id=%s, email=%s",
                telegram_id,
                email,
            )

            await self.xui.delete_client(
                email=email,
                keep_traffic=False,
            )

            logger.info(
                "Deleted stale XUI client: telegram_id=%s, email=%s",
                telegram_id,
                email,
            )

    async def create_trial_vpn_key_for_new_user(
            self,
            *,
            telegram_user: TelegramUser,
    ) -> VpnKey | None:
        return await self._get_create_or_renew_vpn_key(
            telegram_user=telegram_user,
            tariff_code=TRIAL_TARIFF_CODE,
            allow_renewal=False,
            require_trial=True,
        )

    async def get_or_create_vpn_key_for_user(
            self,
            *,
            telegram_user: TelegramUser,
            tariff_code: str,
    ) -> VpnKey:
        vpn_key: VpnKey | None = await self._get_create_or_renew_vpn_key(
            telegram_user=telegram_user,
            tariff_code=tariff_code,
            allow_renewal=True,
            require_trial=False,
        )

        if vpn_key is None:
            raise VpnKeyInvalidStateError("Paid VPN key operation unexpectedly returned None")

        return vpn_key

    async def _get_create_or_renew_vpn_key(
            self,
            *,
            telegram_user: TelegramUser,
            tariff_code: str,
            allow_renewal: bool,
            require_trial: bool,
    ) -> VpnKey | None:
        user: User = await self.user_service.sync_telegram_user(telegram_user=telegram_user)

        selected_tariff: Tariff | None = await self.tariffs_repository.get_active_tariff_by_code(code=tariff_code)
        if selected_tariff is None:
            raise ValueError("No tariff found or tariff disabled")

        existing_vpn_key: VpnKey | None = await self.vpn_keys_repository.get_vpn_key_by_user_id(user_id=user.id)

        if require_trial:
            if existing_vpn_key is None:
                trial_consumed: bool = await self.user_service.consume_trial_if_available(user_id=user.id)
                if not trial_consumed:
                    await self.session.rollback()
                    return None

            elif existing_vpn_key.tariff_id != selected_tariff.id:
                await self.session.commit()
                return None

        recovering_stale_creation = False

        if existing_vpn_key is not None and existing_vpn_key.status in {VPN_KEY_ACTIVE, VPN_KEY_DISABLED}:
            if not allow_renewal:
                if existing_vpn_key.status == VPN_KEY_ACTIVE:
                    usable_vpn_key: VpnKey = self._require_usable_active_vpn_key(vpn_key=existing_vpn_key)
                    await self.session.commit()
                    return usable_vpn_key
                if existing_vpn_key.status == VPN_KEY_DISABLED:
                    raise VpnKeyDisabledError(f"Trial VPN key {existing_vpn_key.id} has expired")

            if not isinstance(existing_vpn_key.xui_email, str) or not existing_vpn_key.xui_email.strip():
                raise VpnKeyInvalidStateError(f"VPN key {existing_vpn_key.id} does not have xui_email")
            if not isinstance(existing_vpn_key.subscription_url, str) or not existing_vpn_key.subscription_url.strip():
                raise VpnKeyInvalidStateError(f"VPN key {existing_vpn_key.id} does not have subscription_url")
            if not isinstance(existing_vpn_key.xui_uuid, str) or not existing_vpn_key.xui_uuid.strip():
                raise VpnKeyInvalidStateError(f"VPN key {existing_vpn_key.id} does not have xui_uuid")
            if not isinstance(existing_vpn_key.xui_sub_id, str) or not existing_vpn_key.xui_sub_id.strip():
                raise VpnKeyInvalidStateError(f"VPN key {existing_vpn_key.id} does not have xui_sub_id")

            target_expires_at: datetime = self._calculate_renewal_expires_at(
                current_expires_at=existing_vpn_key.expires_at,
                duration_days=selected_tariff.duration_days,
            )

            renewal: VpnKey | None = await self.vpn_keys_repository.begin_renewal(
                vpn_key_id=existing_vpn_key.id,
                pending_tariff_id=selected_tariff.id,
                pending_expires_at=target_expires_at,
            )

            if renewal is None:
                await self.session.rollback()
                raise VpnKeyRenewalInProgressError(f"VPN key {existing_vpn_key.id} is already being renewed")

            await self.session.commit()

            return await self._execute_pending_renewal(
                vpn_key=renewal,
                tariff=selected_tariff,
            )

        if existing_vpn_key is not None and existing_vpn_key.status == VPN_KEY_RENEWING:
            if not allow_renewal:
                raise VpnKeyRenewalInProgressError(f"VPN key {existing_vpn_key.id} is currently being renewed")

            renewal_stale_before: datetime = datetime.now(timezone.utc) - VPN_KEY_RENEWING_TIMEOUT

            renewed_vpn_key: VpnKey | None = await self.resume_stale_renewal(
                vpn_key_id=existing_vpn_key.id,
                stale_before=renewal_stale_before,
            )

            if renewed_vpn_key is None:
                raise VpnKeyRenewalInProgressError(f"VPN key {existing_vpn_key.id} is currently being renewed")

            return renewed_vpn_key

        if existing_vpn_key is not None and existing_vpn_key.status == VPN_KEY_CREATING:
            creation_stale_before: datetime = datetime.now(timezone.utc) - VPN_KEY_CREATING_TIMEOUT

            placeholder: VpnKey | None = await self.vpn_keys_repository.claim_stale_creating(
                vpn_key_id=existing_vpn_key.id,
                tariff_id=selected_tariff.id,
                stale_before=creation_stale_before,
            )

            if placeholder is None:
                await self.session.rollback()
                raise VpnKeyCreationInProgressError(f"The VPN key {existing_vpn_key.id} is currently being created. Please try again later")

            await self.session.commit()
            recovering_stale_creation = True

            logger.warning(
                "Claimed stale VPN key creation: "
                "vpn_key_id=%s, user_id=%s, telegram_id=%s, previous_updated_at=%s",
                placeholder.id, user.id, user.telegram_id, existing_vpn_key.updated_at,
            )

        elif existing_vpn_key is not None and existing_vpn_key.status == VPN_KEY_FAILED:
            placeholder = await self.vpn_keys_repository.set_creating(
                vpn_key_id=existing_vpn_key.id,
                tariff_id=selected_tariff.id,
            )
            await self.session.commit()

        else:
            try:
                placeholder = await self.vpn_keys_repository.create_placeholder(
                    user_id=user.id,
                    tariff_id=selected_tariff.id,
                )
                await self.session.commit()

            except IntegrityError:
                await self.session.rollback()

                logger.warning(
                    "Concurrent VPN key placeholder creation detected (user_id=%s, telegram_id=%s)",
                    user.id,
                    user.telegram_id,
                )

                concurrent_vpn_key: VpnKey | None = await self.vpn_keys_repository.get_vpn_key_by_user_id(user_id=user.id)
                if concurrent_vpn_key is None:
                    logger.error(
                        "IntegrityError occurred, but VPN key was not found after rollback (user_id=%s)",
                        user.id,
                    )
                    raise

                return self._resolve_vpn_key_after_integrity_error(vpn_key=concurrent_vpn_key)

        created_xui_client: CreatedXUIClient | None = None
        database_commit_started = False

        try:
            if recovering_stale_creation:
                await self._delete_untracked_xui_clients_for_user(telegram_id=user.telegram_id)

            created_xui_client = await self.xui.add_client(
                email=f"tg_{user.telegram_id}",
                inbound_ids=self.xui_config.default_inbound_ids,
                limit_ip=selected_tariff.limit_ip,
                total_gb=selected_tariff.total_gb,
                expiry_days=selected_tariff.duration_days,
                tg_id=user.telegram_id,
                comment=f"HimayaVPN user, tg_id: {user.telegram_id}",
            )

            subscription_url: str = await self.xui.get_client_subscription_link(email=created_xui_client.email)

            expires_at: datetime = datetime.now(timezone.utc) + timedelta(days=selected_tariff.duration_days)

            vpn_key: VpnKey = await self.vpn_keys_repository.activate(
                vpn_key_id=placeholder.id,
                xui_email=created_xui_client.email,
                xui_uuid=created_xui_client.uuid,
                xui_sub_id=created_xui_client.sub_id,
                inbound_ids=created_xui_client.inbound_ids,
                subscription_url=subscription_url,
                expires_at=expires_at,
            )

            database_commit_started = True
            await self.session.commit()

            return self._require_usable_active_vpn_key(vpn_key=vpn_key)

        except Exception as original_exc:
            logger.exception(
                "VPN key creation failed: user_id=%s, telegram_id=%s",
                user.id,
                user.telegram_id,
            )

            await self.session.rollback()

            cleanup_error: Exception | None = None

            if created_xui_client is not None and not database_commit_started:
                try:
                    await self.xui.delete_client(
                        email=created_xui_client.email,
                        keep_traffic=False,
                    )

                    logger.info(
                        "Compensation completed: deleted XUI client (email: %s)",
                        created_xui_client.email,
                    )

                except Exception as exc:
                    cleanup_error = exc

                    logger.exception(
                        "Compensation failed: cannot delete XUI client (email: %s)",
                        created_xui_client.email,
                    )

            error_message: str = f"{type(original_exc).__name__}: {original_exc}"

            if cleanup_error is not None:
                error_message += f"; cleanup failed: {type(cleanup_error).__name__}: {cleanup_error}"

            try:
                await self.vpn_keys_repository.mark_failed(
                    vpn_key_id=placeholder.id,
                    error_message=error_message,
                )
                await self.session.commit()

            except Exception:
                await self.session.rollback()

                logger.exception(
                    "Cannot mark VPN key %s as failed",
                    placeholder.id,
                )

            raise

    async def resume_stale_renewal(
            self,
            *,
            vpn_key_id: int,
            stale_before: datetime,
    ) -> VpnKey | None:
        renewal: VpnKey | None = await self.vpn_keys_repository.claim_stale_renewing(
            vpn_key_id=vpn_key_id,
            stale_before=stale_before,
        )

        if renewal is None:
            await self.session.rollback()
            return None

        await self.session.commit()

        if renewal.pending_tariff_id is None:
            raise VpnKeyInvalidStateError(f"Renewing VPN key {renewal.id} does not have pending_tariff_id")

        if renewal.pending_expires_at is None:
            raise VpnKeyInvalidStateError(f"Renewing VPN key {renewal.id} does not have pending_expires_at")

        pending_tariff: Tariff | None = await self.tariffs_repository.get_tariff_by_id(tariff_id=renewal.pending_tariff_id)

        if pending_tariff is None:
            error_message = f"Pending tariff {renewal.pending_tariff_id} was not found"

            await self.vpn_keys_repository.record_renewal_error(
                vpn_key_id=renewal.id,
                error_message=error_message,
            )
            await self.session.commit()

            raise VpnKeyInvalidStateError(error_message)

        logger.warning(
            "Resuming stale VPN key renewal (vpn_key_id=%s, tariff_id=%s, target_expires_at=%s)",
            renewal.id,
            pending_tariff.id,
            renewal.pending_expires_at,
        )

        return await self._execute_pending_renewal(
            vpn_key=renewal,
            tariff=pending_tariff,
        )

    async def _execute_pending_renewal(
            self,
            *,
            vpn_key: VpnKey,
            tariff: Tariff,
    ) -> VpnKey:
        if vpn_key.status != VPN_KEY_RENEWING:
            raise VpnKeyInvalidStateError(f"VPN key {vpn_key.id} is not renewing")

        if not isinstance(vpn_key.xui_email, str) or not vpn_key.xui_email.strip():
            raise VpnKeyInvalidStateError(f"Renewing VPN key {vpn_key.id} does not have xui_email")

        if vpn_key.pending_tariff_id is None:
            raise VpnKeyInvalidStateError(f"Renewing VPN key {vpn_key.id} does not have pending_tariff_id")

        if vpn_key.pending_expires_at is None:
            raise VpnKeyInvalidStateError(f"Renewing VPN key {vpn_key.id} does not have pending_expires_at")

        target_expires_at: datetime = vpn_key.pending_expires_at
        target_expiry_time_ms = int(target_expires_at.timestamp() * 1000)

        database_commit_started = False

        try:
            await self.xui.renew_client_until(
                email=vpn_key.xui_email,
                target_expiry_time_ms=target_expiry_time_ms,
                limit_ip=tariff.limit_ip,
                total_gb=tariff.total_gb,
                reset_traffic=True,
            )

            renewed_vpn_key: VpnKey = await self.vpn_keys_repository.complete_renewal(
                vpn_key_id=vpn_key.id,
                tariff_id=tariff.id,
                expires_at=target_expires_at,
            )

            database_commit_started = True
            await self.session.commit()

            logger.info(
                "VPN key renewal completed (vpn_key_id=%s, tariff_id=%s, expires_at=%s)",
                renewed_vpn_key.id,
                tariff.id,
                renewed_vpn_key.expires_at,
            )

            return self._require_usable_active_vpn_key(vpn_key=renewed_vpn_key)

        except Exception as original_exc:
            await self.session.rollback()

            if database_commit_started:
                refreshed_vpn_key: VpnKey | None = await self.vpn_keys_repository.get_vpn_key_by_user_id(user_id=vpn_key.user_id)

                if (
                    refreshed_vpn_key is not None
                    and refreshed_vpn_key.status == VPN_KEY_ACTIVE
                    and refreshed_vpn_key.expires_at is not None
                    and refreshed_vpn_key.expires_at >= target_expires_at
                ):
                    logger.warning(
                        "Renewal commit returned an error, but database already contains the result (vpn_key_id=%s)",
                        refreshed_vpn_key.id,
                    )

                    return self._require_usable_active_vpn_key(vpn_key=refreshed_vpn_key)

            error_message = f"{type(original_exc).__name__}: {original_exc}"

            try:
                await self.vpn_keys_repository.record_renewal_error(
                    vpn_key_id=vpn_key.id,
                    error_message=error_message,
                )
                await self.session.commit()

            except Exception:
                await self.session.rollback()

                logger.exception(
                    "Cannot record renewal error (vpn_key_id=%s)",
                    vpn_key.id,
                )

            raise VpnKeyRenewalFailedError(f"Cannot renew VPN key {vpn_key.id}") from original_exc
