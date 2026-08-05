"""检查所有 diap 模块能否正常导入"""
import sys
sys.path.insert(0, ".")

failed = []

# 逐个导入核心模块
modules = [
    "diap.key_manager",
    "diap.config_manager",
    "diap.did_builder",
    "diap.did_cache",
    "diap.identity_manager",
    "diap.noir_zkp",
    "diap.ipfs_client",
    "diap.memory_ipfs_client",
    "diap.ipfs_node_manager",
    "diap.ipfs_multi_publisher",
    "diap.ipfs_setup",
    "diap.ipns_manager",
    "diap.kubo_installer",
    "diap.agent_auth",
    "diap.agent_verification",
    "diap.real_name_auth",
    "diap.pubsub_authenticator",
    "diap.nonce_manager",
    "diap.encrypted_peer_id",
    "diap.encrypted_iroh_id",
    "diap.iroh_communicator",
    "diap.iroh_node",
    "diap.ipfs_bidirectional_verification",
    "diap.p2p.hyperswarm_communicator",
    "diap.p2p.libp2p_communicator",
    "diap.zkp.snarkjs_backend",
    "diap.zkp.universal_manager",
    "diap.zkp.key_generator",
    "diap.zkp.simplified_backend",
    "diap.types",
    "diap.utils",
]

for mod in modules:
    try:
        __import__(mod)
        print(f"✅ {mod}")
    except Exception as e:
        print(f"❌ {mod}: {type(e).__name__}: {e}")
        failed.append((mod, str(e)))

# 测试完整包导入
try:
    import diap
    print(f"✅ diap package (version {diap.__version__})")
except Exception as e:
    print(f"❌ diap package: {type(e).__name__}: {e}")
    failed.append(("diap", str(e)))

print()
if failed:
    print(f"❌ {len(failed)} modules failed:")
    for mod, err in failed:
        print(f"  - {mod}: {err}")
else:
    print("🎉 All modules imported successfully!")