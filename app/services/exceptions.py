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
