---
title: DIAP Python SDK 项目概览
source: session
created: 2026-08-05
updated: 2026-08-05
tags: [overview]
status: current
---

# DIAP Python SDK 项目概览

## 一句话定义

DIAP（Decentralized Intelligent Agent Protocol）Python SDK —— TypeScript 版本 `@diap/sdk` 的 Python 移植，为去中心化智能体提供身份（DID）、加密（ECIES/Ed25519）、P2P 通信（iroh/libp2p）、ZKP 证明、IPFS 存储等能力。

## 主线目标

- 与 TS 版 @diap/sdk API 对齐（身份、DID、ZKP、P2P、IPFS、Agent 认证）
- 用 Python 生态真实库替换模拟实现（iroh / libp2p / pynacl / py_ecc）
- 发布到 PyPI，开源（MIT）

## 技术栈（真实依赖）

| 领域 | 依赖 |
|------|------|
| P2P | iroh 0.31.0（gossip）、libp2p 0.7.0（身份/签名）、hyperswarm（TCP 适配） |
| 密码学 | cryptography <49、pycryptodome 3.20+、pynacl 1.6.2、base58 2.1.1 |
| ZKP | py_ecc 8.0.0（BN128 Schnorr） |
| IPFS | ipfshttpclient、aiohttp、Kubo（自动安装） |
| 数据 | pydantic 2、cachetools、python-dotenv |

## 交付边界

- 提供：SDK 包（diap-sdk）、示例（examples/）、测试（tests/）、wiki 知识系统（docs/wiki/）
- 不含：真实 snarkjs 电路（需 Node 环境，保留为可选后端）、hyperswarm 官方协议（无 Python 包）

## 关键历史

- 2026-08-05：模拟实现 → 真实库替换完成（见 current-status.md）
