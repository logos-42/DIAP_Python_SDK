class DIAPError(Exception):
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class KeyManagerError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "KEY_MANAGER_ERROR")


class DIDBuilderError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "DID_BUILDER_ERROR")


class IdentityError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "IDENTITY_ERROR")


class ZKPError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "ZKP_ERROR")


class IPFSError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "IPFS_ERROR")


class IPNSError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "IPNS_ERROR")


class AgentAuthError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "AGENT_AUTH_ERROR")


class CryptoError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "CRYPTO_ERROR")


class ConfigError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "CONFIG_ERROR")


class NetworkError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "NETWORK_ERROR")


class VerificationError(DIAPError):
    def __init__(self, message: str):
        super().__init__(message, "VERIFICATION_ERROR")
