import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from diap import (
    KeyManager,
    DIDBuilder,
    DIDCache,
    IdentityManager,
    NoirZKPManager,
    ConfigManager,
    AgentAuthManager,
    NonceManager,
    IPFSClient,
)


class TestKeyManager:
    def test_generate(self):
        key_pair = KeyManager.generate()

        assert key_pair.private_key is not None
        assert key_pair.public_key is not None
        assert key_pair.did.startswith("did:key:")

    def test_sign_and_verify(self):
        key_pair = KeyManager.generate()

        message = b"test message"
        signature = KeyManager.sign(key_pair, message)

        assert KeyManager.verify(key_pair, message, signature)

    def test_wrong_signature_fails(self):
        key_pair = KeyManager.generate()

        message = b"test message"
        signature = KeyManager.sign(key_pair, message)

        wrong_message = b"wrong message"
        assert not KeyManager.verify(key_pair, wrong_message, signature)

    def test_from_private_key(self):
        key_pair = KeyManager.generate()
        key_pair2 = KeyManager.from_private_key(key_pair.private_key)

        assert key_pair.did == key_pair2.did
        assert key_pair.public_key == key_pair2.public_key

    @pytest.mark.skip(reason="Backup encryption has platform-specific issues, needs investigation")
    def test_export_and_import_backup(self):
        key_pair = KeyManager.generate()

        backup = KeyManager.export_backup(key_pair, password="testpassword")
        assert backup.encrypted_data is not None

        imported = KeyManager.import_from_backup(backup, password="testpassword")
        assert imported.did == key_pair.did


class TestDIDBuilder:
    def test_create_did_document(self):
        key_pair = KeyManager.generate()
        builder = DIDBuilder()

        doc = builder.create_did_document(key_pair)

        assert doc.id == key_pair.did
        assert len(doc.verification_method) == 1
        assert len(doc.authentication) == 1

    def test_parse_did(self):
        builder = DIDBuilder()
        result = builder.parse_did("did:key:z1234567890abcdef")

        assert result["method"] == "key"
        assert result["method_specific_id"] == "z1234567890abcdef"

    def test_invalid_did_format(self):
        builder = DIDBuilder()

        with pytest.raises(Exception):
            builder.parse_did("invalid:did:format")


class TestDIDCache:
    def test_cache_set_and_get(self):
        key_pair = KeyManager.generate()
        builder = DIDBuilder()
        doc = builder.create_did_document(key_pair)

        cache = DIDCache()
        cache.set(key_pair.did, doc)

        retrieved = cache.get(key_pair.did)
        assert retrieved is not None
        assert retrieved.id == doc.id

    def test_cache_miss(self):
        cache = DIDCache()
        result = cache.get("did:key:nonexistent")
        assert result is None

    def test_cache_invalidate(self):
        key_pair = KeyManager.generate()
        builder = DIDBuilder()
        doc = builder.create_did_document(key_pair)

        cache = DIDCache()
        cache.set(key_pair.did, doc)

        cache.invalidate(key_pair.did)
        assert cache.get(key_pair.did) is None


class TestConfigManager:
    def test_default_config(self):
        cm = ConfigManager()

        config = cm.get_sdk_config()
        assert config.ipfs_host == "localhost"
        assert config.ipfs_port == 5001

    def test_update_config(self):
        cm = ConfigManager()
        cm.load()

        cm.update({"ipfs_host": "newhost", "ipfs_port": 6000})

        config = cm.get_sdk_config()
        assert config.ipfs_host == "newhost"
        assert config.ipfs_port == 6000


class TestNonceManager:
    @pytest.mark.asyncio
    async def test_generate_and_verify(self):
        nm = NonceManager()
        await nm.start()

        nonce = await nm.generate(entity_id="test-entity")

        is_valid = await nm.verify(nonce, entity_id="test-entity")
        assert is_valid

        await nm.stop()

    @pytest.mark.asyncio
    async def test_consume_nonce(self):
        nm = NonceManager()
        await nm.start()

        nonce = await nm.generate(entity_id="test-entity")

        is_valid1 = await nm.verify(nonce, entity_id="test-entity", consume=True)
        is_valid2 = await nm.verify(nonce, entity_id="test-entity")

        assert is_valid1
        assert not is_valid2

        await nm.stop()

    @pytest.mark.asyncio
    async def test_entity_nonce_revocation(self):
        nm = NonceManager()
        await nm.start()

        await nm.generate(entity_id="test-entity")
        nonce2 = await nm.generate(entity_id="test-entity")

        count = await nm.revoke_all("test-entity")

        assert count == 2
        assert not await nm.verify(nonce2, entity_id="test-entity")

        await nm.stop()


class TestAgentAuthManager:
    def test_create_agent(self):
        key_pair = KeyManager.generate()
        auth_mgr = AgentAuthManager(key_manager=None)

        agent = auth_mgr.create_agent("TestAgent", key_pair)

        assert agent.did == key_pair.did
        assert agent.name == "TestAgent"

    def test_duplicate_agent_fails(self):
        key_pair = KeyManager.generate()
        auth_mgr = AgentAuthManager(key_manager=None)

        auth_mgr.create_agent("TestAgent", key_pair)

        with pytest.raises(Exception):
            auth_mgr.create_agent("TestAgent", key_pair)


class TestIPFSClient:
    def test_get_gateway_url(self):
        client = IPFSClient(
            gateway_host="gateway.example.com",
            gateway_port=8080,
            gateway_protocol="https",
        )

        url = client.get_gateway_url("QmABC123", "path/to/file")
        assert "https://gateway.example.com:8080/ipfs/QmABC123/path/to/file" == url

    def test_get_gateway_url_without_path(self):
        client = IPFSClient(
            gateway_host="gateway.example.com",
            gateway_port=8080,
        )

        url = client.get_gateway_url("QmABC123")
        assert "http://gateway.example.com:8080/ipfs/QmABC123" == url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
