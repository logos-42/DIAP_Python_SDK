from .key_manager import KeyManager

from .config_manager import ConfigManager, SDKConfig, IPFSConfig, P2PConfig, ZKPConfig

from .did_builder import DIDBuilder

from .did_cache import DIDCache, PersistentDIDCache

from .identity_manager import (
    IdentityManager,
    IdentityRegistration,
    AgentInfo,
    ServiceInfo,
)

from .noir_zkp import NoirZKPManager

from .ipfs_client import IPFSClient, MultiAddrIPFSClient

from .ipfs_node_manager import IPFSNodeManager

from .ipns_manager import IPNSManager

from .kubo_installer import KuboInstaller

from .agent_auth import AgentAuthManager, Agent, AgentCredentials

from .agent_verification import (
    AgentVerificationManager,
    VerificationRequest,
    VerificationResult,
)

from .real_name_auth import (
    RealNameAuthenticator,
    RealNameCredential,
    RealNameVerificationRequest,
)

from .pubsub_authenticator import PubSubAuthenticator, PubSubMessage, PubSubTopic

from .nonce_manager import NonceManager, DistributedNonceManager

from .encrypted_peer_id import EncryptedPeerIDManager, EncryptedPeerID

from .encrypted_iroh_id import EncryptedIrohIDManager, EncryptedIrohID

from .iroh_communicator import IrohCommunicator, IrohMessage, IrohNodeInfo

from .iroh_node import IrohNode, IrohNodeConfig, IrohNodeStatus

from .ipfs_bidirectional_verification import (
    IPFSBidirectionalVerifier,
    VerificationChallenge,
    VerificationResult as BidirectionalVerificationResult,
)

from .types import (
    KeyPair,
    KeyBackup,
    KeyStoreConfig,
    DIDDocument,
    VerificationMethod,
    Service,
    AgentProfile,
    CryptoWallets,
    AgentWallet,
    NoirProverInputs,
    NoirProofResult,
    ProofResult,
    ZKPProof,
    DIAPError,
    KeyManagerError,
    DIDBuilderError,
    IdentityError,
    ZKPError,
    IPFSError,
    IPNSError,
    AgentAuthError,
    CryptoError,
)

__version__ = "0.1.0"

__all__ = [
    "KeyManager",
    "ConfigManager",
    "SDKConfig",
    "IPFSConfig",
    "P2PConfig",
    "ZKPConfig",
    "DIDBuilder",
    "DIDCache",
    "PersistentDIDCache",
    "IdentityManager",
    "IdentityRegistration",
    "AgentInfo",
    "ServiceInfo",
    "NoirZKPManager",
    "IPFSClient",
    "MultiAddrIPFSClient",
    "IPFSNodeManager",
    "IPNSManager",
    "KuboInstaller",
    "AgentAuthManager",
    "Agent",
    "AgentCredentials",
    "AgentVerificationManager",
    "VerificationRequest",
    "VerificationResult",
    "RealNameAuthenticator",
    "RealNameCredential",
    "RealNameVerificationRequest",
    "PubSubAuthenticator",
    "PubSubMessage",
    "PubSubTopic",
    "NonceManager",
    "DistributedNonceManager",
    "EncryptedPeerIDManager",
    "EncryptedPeerID",
    "EncryptedIrohIDManager",
    "EncryptedIrohID",
    "IrohCommunicator",
    "IrohMessage",
    "IrohNodeInfo",
    "IrohNode",
    "IrohNodeConfig",
    "IrohNodeStatus",
    "IPFSBidirectionalVerifier",
    "VerificationChallenge",
    "KeyPair",
    "KeyBackup",
    "KeyStoreConfig",
    "DIDDocument",
    "VerificationMethod",
    "Service",
    "AgentProfile",
    "CryptoWallets",
    "AgentWallet",
    "NoirProverInputs",
    "NoirProofResult",
    "ProofResult",
    "ZKPProof",
    "DIAPError",
    "KeyManagerError",
    "DIDBuilderError",
    "IdentityError",
    "ZKPError",
    "IPFSError",
    "IPNSError",
    "AgentAuthError",
    "CryptoError",
]
