# DIAP Python SDK（中文版）

> **Decentralized Intelligent Agent Protocol** —— Python 实现
>
> English version: [README.md](./README.md)

DIAP（去中心化智能体协议）的 Python SDK。面向去中心化身份管理、基于零知识证明的 Agent 认证，与 TypeScript / Rust 版本协议对齐，支持跨语言互通。

## 语言实现

| 语言 | 仓库 | 包 |
|------|------|-----|
| 协议规范 | [DIAP](https://github.com/logos-42/DIAP) | — |
| **Python（本仓库）** | [DIAP_Python_SDK](https://github.com/logos-42/DIAP_Python_SDK) | PyPI `diap-sdk` |
| TypeScript | [DIAP_TS_SDK](https://github.com/logos-42/DIAP_TS_SDK) | npm `@diap/sdk` |
| Rust | [DIAP_Rust_SDK](https://github.com/logos-42/DIAP_Rust_SDK) | crates.io `diap-sdk` |

## 功能特性

- **去中心化身份**：W3C `did:key` 实现（Ed25519）
- **零知识证明（ZKP）**：基于 [py_ecc](https://github.com/ethereum/py_ecc) 的 **BN128 椭圆曲线 Schnorr 知识证明**（真实密码学证明，非哈希模拟；可选 snarkjs CLI 后端）
- **IPFS 集成**：去中心化存储 + IPNS 支持（自动安装 Kubo 节点）
- **P2P 网络**：真实 [iroh](https://iroh.computer) gossip 通信 + libp2p 身份/签名
- **Agent 认证**：安全的智能体身份注册与验证
- **加密**：Ed25519 密钥（[PyNaCl](https://github.com/pyca/pynacl)，RFC 8032）+ AES-256-GCM + ECIES 非对称加密

## 安装

```bash
pip install diap-sdk
```

从源码安装：

```bash
git clone https://github.com/logos-42/DIAP_Python_SDK.git
cd DIAP_Python_SDK
pip install -e .
```

国内镜像加速：

```bash
pip install diap-sdk -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 快速开始

```python
from diap import KeyManager, DIDBuilder

# 生成密钥对
km = KeyManager()
key_pair = km.generate()

# 创建 DID 文档
builder = DIDBuilder()
doc = builder.create_did_document(key_pair)
print(f"DID: {doc.id}")
```

## 零知识证明（ZKP）

默认后端 `py_ecc`：在 **BN128 曲线**上实现真实的 **Schnorr 知识证明**（Fiat-Shamir 变换）。

**证明原理**：
- 证明者知道秘密标量 x（由输入派生），公钥 X = x·G
- 承诺 R = r·G（r 为随机数）
- challenge c = H(R ‖ X ‖ 公开输入)
- 响应 s = r + c·x
- 验证方程：**s·G == R + c·X**

这是 honest-verifier 零知识知识证明，**篡改任何证明字段都会验证失败**。

```python
from diap.zkp import UniversalZKManager

mgr = UniversalZKManager()  # 默认后端: py_ecc (BN128 Schnorr)
inputs = {
    "expected_did_hash": [1234567890, 987654321],
    "public_key_hash": 11111111,
    "nonce_hash": 22222222,
}
proof = mgr.generate_proof(inputs)
assert mgr.verify_proof(proof)   # True：合法证明通过验证
```

真实密钥生成（BN128 随机标量 + 公钥点）：

```python
from diap.zkp import generate_simple_zkp_keys
keys = generate_simple_zkp_keys()          # proving_key: 32B 标量, verification_key: 64B 公钥点
```

## Iroh P2P 通信（真实 gossip）

```python
import asyncio
from diap import IrohCommunicator

async def main():
    node = IrohCommunicator()
    await node.start()
    node.add_message_handler("default", lambda m: print(f"收到: {m.payload}"))
    await node.connect(f"<peer_node_id>@<relay_url>")   # 格式: node_id@relay
    await node.broadcast(b"hello")
    await node.stop()

asyncio.run(main())
```

> 说明：iroh 0.31.0（0.35.0 在 Intel Mac 上有段错误问题，故锁定 0.31.0）。gossip 消息经 iroh relay 网络传播，时延不定。

## 开发

```bash
pip install -e ".[dev]"
pytest tests/
```

## 项目结构

```
diap/
├── __init__.py           # 主包导出
├── key_manager.py         # Ed25519 密钥生成与管理
├── did_builder.py         # W3C DID 文档创建
├── did_cache.py          # DID 文档缓存
├── identity_manager.py   # 身份注册与 ZKP 验证
├── noir_zkp.py          # ZKP 电路集成
├── ipfs_client.py       # IPFS HTTP API 客户端
├── ipfs_node_manager.py # 本地 Kubo 节点管理
├── ipns_manager.py      # IPNS 发布/解析
├── kubo_installer.py    # 自动安装 Kubo IPFS 守护进程
├── agent_auth.py        # Agent 认证
├── agent_verification.py # Agent 验证
├── real_name_auth.py    # 实名认证
├── pubsub_authenticator.py # PubSub 认证
├── nonce_manager.py     # Nonce 管理
├── encrypted_peer_id.py # PeerID 加密
├── encrypted_iroh_id.py # Iroh ID 加密（ECIES）
├── iroh_communicator.py # Iroh P2P 通信（真实 gossip）
├── iroh_node.py         # Iroh 节点管理
├── p2p/
│   ├── hyperswarm_communicator.py  # Hyperswarm P2P（TCP 适配）
│   └── libp2p_communicator.py      # libp2p 身份/签名 + TCP 传输
├── types/               # 类型定义
├── utils/               # 工具（crypto, encoding, logger）
└── zkp/                 # ZKP 后端（py_ecc, snarkjs, simplified）
```

## 发布（维护者）

一键发布（需 `~/.pypirc` 配置 PyPI token）：

```bash
bash scripts/release.sh
```

## 许可证

MIT License

---

**相关仓库**：协议规范 [DIAP](https://github.com/logos-42/DIAP) · TypeScript [DIAP_TS_SDK](https://github.com/logos-42/DIAP_TS_SDK) · Rust [DIAP_Rust_SDK](https://github.com/logos-42/DIAP_Rust_SDK)
