# DIAP Python SDK

> **Decentralized Intelligent Agent Protocol** — Python implementation.
>
> 中文说明：DIAP（去中心化智能体协议）的 Python SDK，与 TypeScript / Rust 版本协议对齐。核心能力：去中心化身份（DID）、零知识证明（ZKP）、P2P 通信、IPFS 存储。安装与示例见下文英文文档。

[![PyPI version](https://img.shields.io/pypi/v/diap-sdk.svg)](https://pypi.org/project/diap-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python >= 3.10](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python implementation of the DIAP protocol for decentralized identity management and agent authentication using zero-knowledge proofs.

## Implementations

| Language | Repository | Package |
|----------|-----------|---------|
| Protocol Spec | [DIAP](https://github.com/logos-42/DIAP) | — |
| **Python (this repo)** | [DIAP_Python_SDK](https://github.com/logos-42/DIAP_Python_SDK) | `diap-sdk` on PyPI |
| TypeScript | [DIAP_TS_SDK](https://github.com/logos-42/DIAP_TS_SDK) | `@diap/sdk` on npm |
| Rust | [DIAP_Rust_SDK](https://github.com/logos-42/DIAP_Rust_SDK) | `diap-sdk` on crates.io |

> 各语言实现保持协议一致，可在不同语言 agent 之间互通（DID 兼容、ZKP 可交叉验证、P2P 共享 iroh/libp2p 网络）。

## Features

- **Decentralized Identity**: W3C `did:key` implementation (Ed25519)
- **Zero-Knowledge Proofs**: Real BN128 elliptic-curve Schnorr proofs via [py_ecc](https://github.com/ethereum/py_ecc) (snarkjs CLI as optional backend)
- **IPFS Integration**: Decentralized storage with IPNS support (auto-installs Kubo)
- **P2P Networking**: Real [iroh](https://iroh.computer) gossip communication + libp2p identity/signing
- **Agent Authentication**: Secure agent identity and verification
- **Encryption**: Ed25519 keys ([PyNaCl](https://github.com/pyca/pynacl), RFC 8032) with AES-256-GCM + ECIES encryption

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

> 国内用户可使用镜像加速：`pip install diap-sdk -i https://pypi.tuna.tsinghua.edu.cn/simple`

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

### ZKP Proof (real elliptic-curve, py_ecc)

```python
from diap.zkp import UniversalZKManager

mgr = UniversalZKManager()  # default backend: py_ecc (BN128 Schnorr)
inputs = {
    "expected_did_hash": [1234567890, 987654321],
    "public_key_hash": 11111111,
    "nonce_hash": 22222222,
}
proof = mgr.generate_proof(inputs)
assert mgr.verify_proof(proof)  # True
```

### Iroh P2P Communication (real gossip)

```python
import asyncio
from diap import IrohCommunicator

async def main():
    node = IrohCommunicator()
    await node.start()
    node.add_message_handler("default", lambda m: print(f"got: {m.payload}"))
    await node.connect(f"<peer_node_id>@<relay_url>")  # node_id@relay
    await node.broadcast(b"hello")
    await node.stop()

asyncio.run(main())
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
├── encrypted_iroh_id.py # Iroh ID encryption (ECIES)
├── iroh_communicator.py # Iroh P2P communication (real gossip)
├── iroh_node.py         # Iroh node management
├── p2p/
│   ├── hyperswarm_communicator.py  # Hyperswarm P2P (TCP adaptation)
│   └── libp2p_communicator.py      # libp2p identity/signing + TCP transport
├── types/               # Type definitions
├── utils/               # Utilities (crypto, encoding, logger)
└── zkp/                 # ZKP backends (py_ecc, snarkjs, simplified)
```

## Publish (维护者)

One-command release (requires `~/.pypirc` with PyPI token):

```bash
bash scripts/release.sh
```

## License

MIT License

---

**相关仓库**：协议规范 [DIAP](https://github.com/logos-42/DIAP) · TypeScript [DIAP_TS_SDK](https://github.com/logos-42/DIAP_TS_SDK) · Rust [DIAP_Rust_SDK](https://github.com/logos-42/DIAP_Rust_SDK)
