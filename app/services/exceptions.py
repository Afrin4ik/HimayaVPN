class VpnKeyServiceError(Exception):
    """Base exception for VPN key service errors"""


class VpnKeyCreationInProgressError(VpnKeyServiceError):
    """VPN key is already being created"""


class VpnKeyCreationFailedError(VpnKeyServiceError):
    """Previous VPN key creation attempt failed"""


class VpnKeyDisabledError(VpnKeyServiceError):
    """VPN key exists, but it is disabled"""


class VpnKeyInvalidStateError(VpnKeyServiceError):
    """VPN key data is inconsistent with its status"""


class VpnKeyRenewalInProgressError(VpnKeyServiceError):
    """VPN key renewal is already in progress"""


class VpnKeyRenewalFailedError(VpnKeyServiceError):
    """VPN key renewal could not be completed"""


class TariffServiceError(Exception):
    """Base exception for tariff service errors"""


class TariffUnavailableError(TariffServiceError):
    """Requested tariff does not exist or is disabled"""


class TariffConfigurationError(TariffServiceError):
    """Tariff contains invalid configuration"""


class PaymentServiceError(Exception):
    """Base payment application error"""


class PaymentOrderNotFoundError(PaymentServiceError):
    """Order does not exist or does not belong to the Telegram user"""


class PaymentVerificationError(PaymentServiceError):
    """Provider payment did not pass local verification"""


class PaymentInvalidStateError(PaymentServiceError):
    """Order cannot perform the requested state transition"""


class PaymentProviderUnavailableError(PaymentServiceError):
    """Retryable provider/network failure"""


class PaymentProviderRejectedError(PaymentServiceError):
    """Non-retryable provider API rejection"""
