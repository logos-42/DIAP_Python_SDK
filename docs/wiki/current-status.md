---
title: DIAP Python SDK 当前状态
source: session
created: 2026-08-05
updated: 2026-08-05
tags: [status]
status: current
---

# 当前状态

## 一句话

DIAP（去中心化智能体协议）Python SDK：TS 版本 @diap/sdk 的 Python 移植，核心能力已从模拟实现切换到真实密码学/P2P 库。

## 已支持（真实实现）

| 能力 | 实现 | 说明 |
|------|------|------|
| P2P gossip 消息 | iroh 0.31.0 | 真实 gossip 订阅/广播，relay 网络双节点互通已验证 |
| P2P 身份/签名 | libp2p 0.7.0 | Ed25519 KeyPair → PeerID（12D3KooW...），签名/验签 |
| ZKP 证明 | py_ecc 8.0.0 | BN128 Schnorr 知识证明（Fiat-Shamir），篡改即拒 |
| ZKP 密钥 | py_ecc 8.0.0 | 真实 BN128 曲线随机标量 + 公钥点 |
| Ed25519 签名 | pynacl 1.6.2 | 与 cryptography 签名格式互通（RFC 8032） |
| keccak256 | pycryptodome 3.20+ | 替换 pysha3（Python 3.12 不可装） |
| ECIES 加密 | cryptography <49 | 修复 X962 公钥解析 + ECDH 自交换 bug |
| Base58 / DID | base58 2.1.1 | did:key:z... 派生 |

## 关键决策

1. **iroh 锁 0.31.0**：0.35.0 在 Intel Mac (x86_64) 上 `Iroh.memory()` 段错误；0.31.0 稳定且 gossip API 可用（需 `uniffi_set_event_loop` + 32 字节 topic + base32 bootstrap）。
2. **cryptography 锁 <49**：libp2p 依赖链（aioquic）会拉 cryptography 50，Intel Mac 无 wheel 源码编译失败。
3. **libp2p 传输层用 asyncio TCP**：libp2p 0.7 的 `BasicHost.run()` 依赖 trio（RunContext.runner bug），asyncio 环境不可用；身份/签名/编码用真实 libp2p 组件。
4. **fastecdsa 需 GMP**：libp2p 硬依赖，Intel Mac 源码编译需 gmp.h（已编译到 ~/.local，PIC + ARCHFLAGS=x86_64）。

## 测试

- 35 passed + 1 skipped（0 failed），含真实 iroh 双节点 gossip 互通测试。
- 新增 tests/test_real_implementations.py：PyEcc ZKP、pynacl 互操作、ECIES、libp2p 身份、iroh 双节点。

## 未支持 / 已知风险

- HyperswarmCommunicator 仍为纯 TCP 实现（Python 无官方 hyperswarm 包）。
- snarkjs_backend 依赖外部 snarkjs CLI（Node 环境），默认后端已是 py_ecc。
- 测试中 backup 加密（test_export_and_import_backup）因平台问题跳过。
- iroh gossip 消息经公共 relay 网络传播，时延不定（测试已加重试）。

## 版本

- 0.1.4
