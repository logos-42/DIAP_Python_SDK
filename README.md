# DIAP Python SDK

Decentralized Intelligent Agent Protocol (DIAP) SDK for Python.

A Python implementation of the DIAP protocol for decentralized identity management and agent authentication using zero-knowledge proofs.

## Features

- **Decentralized Identity**: W3C DID:key implementation
- **Zero-Knowledge Proofs**: Real BN128 elliptic-curve Schnorr proofs via py_ecc (snarkjs CLI as optional backend)
- **IPFS Integration**: Decentralized storage with IPNS support
- **P2P Networking**: Real iroh gossip communication + libp2p identity/signing
- **Agent Authentication**: Secure agent identity and verification
- **Encryption**: Ed25519 keys (pynacl, RFC 8032) with AES-256-GCM + ECIES encryption

## Installation

```bash
pip install diap-sdk
```

Or install from source:

```bash
git clone https://github.com/logos-42/DIAP_Python_SDK.git
cd DIAP_Python_SDK
pip install -e .
```

## Quick Start

```python
from diap import KeyManager, DIDBuilder

# Generate a key pair
km = KeyManager()
key_pair = km.generate()

# Create DID document
builder = DIDBuilder()
doc = builder.create_did_document(key_pair)
print(f"DID: {doc.id}")
```

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest tests/
```

## Project Structure

```
diap/
├── __init__.py           # Main package exports
├── key_manager.py         # Ed25519 key generation and management
├── did_builder.py         # W3C DID Document creation
├── did_cache.py          # DID document caching
├── identity_manager.py   # Identity registration and ZKP verification
├── noir_zkp.py          # ZKP circuit integration
├── ipfs_client.py       # IPFS HTTP API client
├── ipfs_node_manager.py # Local Kubo node management
├── ipns_manager.py      # IPNS publishing/resolution
├── kubo_installer.py    # Auto-install Kubo IPFS daemon
├── agent_auth.py        # Agent authentication
├── agent_verification.py # Agent verification
├── real_name_auth.py    # Real-name authentication
├── pubsub_authenticator.py # PubSub authentication
├── nonce_manager.py     # Nonce management
├── encrypted_peer_id.py # PeerID encryption
├── iroh_communicator.py # Iroh P2P communication
├── p2p/
│   └── hyperswarm_communicator.py  # Hyperswarm P2P
├── types/               # Type definitions
├── utils/               # Utilities
└── zkp/                 # ZKP backends
```

## License

MIT License
