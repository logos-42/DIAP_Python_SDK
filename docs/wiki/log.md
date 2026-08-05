# Wiki 日志

## [2026-08-05] 启动 | 初始化知识系统

| 时间 | 动作 | 对象 | 结果 |
|------|------|------|------|
| 2026-08-05 | 初始化 | 知识系统 bootstrap | 建立 wiki、manifest、检查脚本和 repo 级默认规则 |
| 2026-08-05 | 依赖替换 | 模拟实现 → 真实库 | 详见 current-status.md |

## [2026-08-05] 核心依赖替换 | 模拟实现 → 真实库

| 模块 | 替换前（模拟） | 替换后（真实） | 版本 |
|------|---------------|---------------|------|
| iroh_communicator.py | 随机 node_id + 假消息路由 | iroh gossip 订阅/广播（真实 P2P） | iroh 0.31.0 |
| iroh_node.py | 随机 ID + 空操作连接 | iroh Iroh.memory/persistent 节点 | iroh 0.31.0 |
| libp2p_communicator.py | 随机 PeerID + 模拟订阅 | libp2p Ed25519 身份/签名 + asyncio TCP 传输 | libp2p 0.7.0 |
| zkp/universal_manager.py | SimplifiedBackend（hash 模拟） | PyEccBackend（BN128 Schnorr 知识证明） | py_ecc 8.0.0 |
| zkp/key_generator.py | 硬编码 demo 密钥 | py_ecc 真实 BN128 曲线密钥 | py_ecc 8.0.0 |
| utils/crypto.py keccak | pysha3（Py3.12 装不上） | pycryptodome keccak | pycryptodome 3.20+ |
| utils/crypto.py Ed25519 | cryptography 仅有 | 新增 pynacl ed25519_sign/verify | pynacl 1.6.2 |
| encrypted_iroh_id.py | ECDH bug（自交换） | 修复 X962 解析 + 正确 ECDH | cryptography <49 |
