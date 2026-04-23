from typing import Optional


class DIAPError(Exception):
    def __init__(
        self, message: str, code: str = "UNKNOWN", original_error: Optional[Exception] = None
    ):
        self.message = message
        self.code = code
        self.original_error = original_error
        super().__init__(self.message)


class KeyManagerError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "KEY_MANAGER_ERROR", original_error)


class DIDBuilderError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "DID_BUILDER_ERROR", original_error)


class IdentityError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "IDENTITY_ERROR", original_error)


class ZKPError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "ZKP_ERROR", original_error)


class IPFSError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "IPFS_ERROR", original_error)


class IPNSError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "IPNS_ERROR", original_error)


class AgentAuthError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "AGENT_AUTH_ERROR", original_error)


class CryptoError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "CRYPTO_ERROR", original_error)


class ConfigError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "CONFIG_ERROR", original_error)


class NetworkError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "NETWORK_ERROR", original_error)


class VerificationError(DIAPError):
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message, "VERIFICATION_ERROR", original_error)
