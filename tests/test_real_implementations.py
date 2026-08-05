"""
测试真实实现替换后的核心功能：
- Iroh gossip 双节点通信（真实 iroh 0.31）
- Libp2p 身份/签名（真实 libp2p 组件）
- PyEcc BN128 Schnorr ZKP（真实椭圆曲线证明）
- ECIES 加解密（encrypted_iroh_id）
- pynacl Ed25519 签名互操作
"""

import asyncio
import json

import pytest


class TestPyEccZKP:
    """真实椭圆曲线 ZKP（BN128 Schnorr 知识证明）"""

    def _inputs(self):
        return {
            "expected_did_hash": [1234567890, 987654321],
            "public_key_hash": 11111111,
            "nonce_hash": 22222222,
            "secret_key": [33333333, 44444444],
            "did_document_hash": [55555555, 66666666],
            "nonce": [77777777, 88888888],
        }

    def test_generate_and_verify(self):
        from diap.zkp import PyEccBackend

        backend = PyEccBackend()
        proof = backend.generate_proof(self._inputs())

        assert proof["format"] == "bn128_schnorr"
        assert proof["version"] == 2
        assert len(proof["public_key"]) == 128  # 64 bytes hex
        assert len(proof["response"]) == 64  # 32 bytes hex

        assert backend.verify_proof(proof, proof["public_binding"])

    def test_tampered_proof_rejected(self):
        from diap.zkp import PyEccBackend

        backend = PyEccBackend()
        proof = backend.generate_proof(self._inputs())

        bad = dict(proof)
        bad["response"] = "00" * 32
        assert not backend.verify_proof(bad, bad["public_binding"])

    def test_bytes_io(self):
        from diap.zkp import PyEccBackend

        backend = PyEccBackend()
        proof = backend.generate_proof(self._inputs())
        proof_bytes = json.dumps(proof).encode()

        assert backend.verify_proof(proof_bytes, proof["public_binding"].encode())

    def test_universal_manager_py_ecc_default(self):
        from diap.zkp import UniversalZKManager

        mgr = UniversalZKManager()
        assert "py_ecc" in mgr.get_available_backends()

        result = mgr.generate_proof(self._inputs())
        assert mgr.verify_proof(result)
        assert result.circuit_hash == "bn128_schnorr"

    def test_key_generation_real_ec(self):
        from diap.zkp import generate_simple_zkp_keys

        keys = generate_simple_zkp_keys()
        assert len(keys.proving_key) == 32
        assert len(keys.verification_key) == 64

        # 生成两次应不同（随机标量）
        keys2 = generate_simple_zkp_keys()
        assert keys.proving_key != keys2.proving_key


class TestPynaclEd25519:
    """pynacl Ed25519（对应 TS @noble/ed25519）"""

    def test_sign_verify_roundtrip(self):
        from diap.utils.crypto import ed25519_sign, ed25519_verify
        from diap.utils.crypto import ed25519_keypair_from_seed

        seed = bytes(range(32))
        msg = b"test message"
        sig = ed25519_sign(seed, msg)
        _, pub = ed25519_keypair_from_seed(seed)

        assert len(sig) == 64
        assert ed25519_verify(pub, msg, sig)

    def test_cross_compat_with_cryptography(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from diap.utils.crypto import ed25519_sign, ed25519_verify

        seed = bytes(range(32))
        crypto_key = Ed25519PrivateKey.from_private_bytes(seed)
        msg = b"cross-compat"

        sig_pynacl = ed25519_sign(seed, msg)
        sig_crypto = crypto_key.sign(msg)

        # 签名格式一致（RFC 8032 确定性）
        assert sig_pynacl == sig_crypto

        # cryptography 可验证 pynacl 签名
        crypto_key.public_key().verify(sig_pynacl, msg)

        # pynacl 可验证 cryptography 签名
        pub = bytes(crypto_key.public_key().public_bytes_raw())
        assert ed25519_verify(pub, msg, sig_crypto)

    def test_wrong_message_fails(self):
        from diap.utils.crypto import ed25519_sign, ed25519_verify, ed25519_keypair_from_seed

        seed = bytes(range(32))
        _, pub = ed25519_keypair_from_seed(seed)
        sig = ed25519_sign(seed, b"right")
        assert not ed25519_verify(pub, b"wrong", sig)


class TestEncryptedIrohID:
    """ECIES 加解密（修复后的 encrypted_iroh_id）"""

    def test_ecies_roundtrip(self):
        from diap.encrypted_iroh_id import EncryptedIrohIDManager

        mgr = EncryptedIrohIDManager()
        priv, pub = mgr.generate_iroh_id_keypair()

        secret = b"secret-iroh-id-data"
        encrypted = mgr.encrypt_iroh_id(secret, pub)
        decrypted = mgr.decrypt_iroh_id(encrypted, private_key=priv)

        assert decrypted == secret

    def test_wrong_key_rejected(self):
        from diap.encrypted_iroh_id import EncryptedIrohIDManager
        from diap.types.errors import CryptoError

        mgr = EncryptedIrohIDManager()
        priv, pub = mgr.generate_iroh_id_keypair()
        priv2, _ = mgr.generate_iroh_id_keypair()

        encrypted = mgr.encrypt_iroh_id(b"secret", pub)
        with pytest.raises(CryptoError):
            mgr.decrypt_iroh_id(encrypted, private_key=priv2)

    def test_shared_key_symmetric(self):
        from diap.encrypted_iroh_id import EncryptedIrohIDManager

        mgr = EncryptedIrohIDManager()
        priv1, pub1 = mgr.generate_iroh_id_keypair()
        priv2, pub2 = mgr.generate_iroh_id_keypair()

        shared1 = mgr.derive_shared_key(priv1, pub2)
        shared2 = mgr.derive_shared_key(priv2, pub1)

        assert shared1 == shared2


class TestLibp2pIdentity:
    """真实 libp2p 组件（身份 / 签名）"""

    def test_keypair_and_peer_id(self):
        from libp2p.crypto.ed25519 import create_new_key_pair
        from libp2p.peer.id import ID

        kp = create_new_key_pair()
        peer_id = ID.from_pubkey(kp.public_key)

        assert str(peer_id).startswith("12D3KooW")  # libp2p PeerID 格式
        assert len(str(peer_id)) > 40

    def test_sign_verify(self):
        from libp2p.crypto.ed25519 import create_new_key_pair

        kp = create_new_key_pair()
        data = b"libp2p signed message"
        sig = kp.private_key.sign(data)

        assert kp.public_key.verify(data, sig)
        assert not kp.public_key.verify(b"tampered", sig)

    def test_communicator_peer_id(self):
        from diap.p2p import create_libp2p_communicator

        comm = create_libp2p_communicator()
        assert comm is not None
        assert comm.get_peer_id() is None  # 未启动时无 ID


@pytest.mark.asyncio
class TestIrohCommunicator:
    """真实 iroh gossip 通信（双节点）"""

    @pytest.mark.timeout(60)
    async def test_two_node_message(self):
        from diap.iroh_communicator import IrohCommunicator

        c1 = IrohCommunicator()
        c2 = IrohCommunicator()
        await c1.start()
        await c2.start()

        received = []
        c2.add_message_handler("default", lambda m: received.append(m))

        relay1 = await c1._iroh_node.net().home_relay()
        relay2 = await c2._iroh_node.net().home_relay()
        await c1.connect(f"{c2.node_id}@{relay2}")
        await c2.connect(f"{c1.node_id}@{relay1}")

        # 等待 gossip 成员关系建立（relay 网络延迟不定）
        await asyncio.sleep(5)

        # 重试发送（最多 3 次，gossip 传播可能丢）
        sent = False
        for _ in range(3):
            if await c1.send_message(c2.node_id, b"hello iroh", message_type="default"):
                sent = True
            for _ in range(8):
                if received:
                    break
                await asyncio.sleep(1)
            if received:
                break
        assert sent

        assert len(received) >= 1
        assert received[0].payload == b"hello iroh"
        assert received[0].from_node == c1.node_id

        await c1.stop()
        await c2.stop()


class TestIrohNode:
    """真实 iroh 节点"""

    @pytest.mark.asyncio
    async def test_start_status(self):
        from diap.iroh_node import IrohNode

        node = IrohNode()
        status = await node.start()

        assert status.is_running
        assert len(status.node_id) == 64  # hex node id
        assert status.peer_count == 0

        await node.stop()
        assert not node.get_status().is_running
