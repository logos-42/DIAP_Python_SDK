from .key_manager import KeyManager, KeyManagerInstance

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

from .memory_ipfs_client import MemoryIpfsClient, IpfsUploadResult

from .ipfs_node_manager import IPFSNodeManager

from .ipfs_multi_publisher import (
    IpfsMultiPublisher,
    MultiNodePublishResult,
    IpfsNodeConfig,
    GatewayCredentials,
    create_multi_publisher,
    create_pinata_publisher,
    create_infura_publisher,
    create_web3_storage_publisher,
    create_custom_publisher,
    is_kubo_installed,
)

from .ipfs_setup import (
    check_kubo_setup,
    start_local_kubo,
    ensure_local_ipfs_node,
    KuboSetupResult,
)

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

from .encrypted_peer_id import (
    EncryptedPeerID,
    encrypt_peer_id,
    decrypt_peer_id_with_secret,
    verify_peer_id_signature,
    verify_encrypted_peer_id_ownership,
)

from .encrypted_iroh_id import EncryptedIrohIDManager, EncryptedIrohID

from .iroh_communicator import IrohCommunicator, IrohMessage, IrohNodeInfo

from .iroh_node import IrohNode, IrohNodeConfig, IrohNodeStatus

from .ipfs_bidirectional_verification import (
    IPFSBidirectionalVerifier,
    VerificationChallenge,
)

from .p2p import (
    HyperswarmCommunicator,
    create_hyperswarm_communicator,
    create_topic,
    P2PMessageType,
    P2PConnection,
    P2PNodeAddr,
    P2PMessage,
    Libp2pCommunicator,
    Libp2pConfig,
    Libp2pMessage,
    Libp2pConnection,
    create_libp2p_communicator,
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

from .zkp import (
    SnarkJSBackend,
    UniversalZKManager,
    ZKPBackendType,
    SimplifiedBackend,
    PyEccBackend,
    ZKPKeyPair,
    KeyGenerationResult,
    generate_simple_zkp_keys,
    ensure_zkp_keys_exist,
    generate_noir_keys,
    create_zkp_keys,
)

__version__ = "0.1.4"

__all__ = [
    "KeyManager",
    "KeyManagerInstance",
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
    "MemoryIpfsClient",
    "IpfsUploadResult",
    "IPFSNodeManager",
    "IpfsMultiPublisher",
    "MultiNodePublishResult",
    "IpfsNodeConfig",
    "GatewayCredentials",
    "create_multi_publisher",
    "create_pinata_publisher",
    "create_infura_publisher",
    "create_web3_storage_publisher",
    "create_custom_publisher",
    "is_kubo_installed",
    "check_kubo_setup",
    "start_local_kubo",
    "ensure_local_ipfs_node",
    "KuboSetupResult",
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
    "EncryptedPeerID",
    "encrypt_peer_id",
    "decrypt_peer_id_with_secret",
    "verify_peer_id_signature",
    "verify_encrypted_peer_id_ownership",
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
    "HyperswarmCommunicator",
    "create_hyperswarm_communicator",
    "create_topic",
    "P2PMessageType",
    "P2PConnection",
    "P2PNodeAddr",
    "P2PMessage",
    "Libp2pCommunicator",
    "Libp2pConfig",
    "Libp2pMessage",
    "Libp2pConnection",
    "create_libp2p_communicator",
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
    "SnarkJSBackend",
    "UniversalZKManager",
    "ZKPBackendType",
    "SimplifiedBackend",
    "PyEccBackend",
    "ZKPKeyPair",
    "KeyGenerationResult",
    "generate_simple_zkp_keys",
    "ensure_zkp_keys_exist",
    "generate_noir_keys",
    "create_zkp_keys",
]
