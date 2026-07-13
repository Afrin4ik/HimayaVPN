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
