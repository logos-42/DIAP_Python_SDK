# Example: ZKP Proof Generation
# Demonstrates zero-knowledge proof generation using snarkjs backend

from diap import NoirZKPManager, ConfigManager
from diap.zkp import UniversalZKManager


def main():
    print("=== DIAP SDK ZKP Example ===\n")

    # Initialize ZKP manager
    print("1. Initializing ZKP manager...")
    zkp_config = ConfigManager.ZKPConfig(backend="snarkjs", circuit_id="did_binding")
    zkp_manager = NoirZKPManager(zkp_config)
    print(f"   Backend: {zkp_config.backend}")

    # Prepare proof inputs
    print("\n2. Preparing proof inputs...")
    inputs = {
        "expected_did_hash": [1234567890, 987654321],
        "public_key_hash": 11111111,
        "nonce_hash": 22222222,
        "secret_key": [33333333, 44444444],
        "did_document_hash": [55555555, 66666666],
        "nonce": [77777777, 88888888],
    }
    print(f"   DID hash: {inputs['expected_did_hash']}")
    print(f"   Public key hash: {inputs['public_key_hash']}")

    # Generate proof
    print("\n3. Generating ZKP proof...")
    proof = zkp_manager.generate_proof(inputs)
    print(f"   Circuit hash: {proof.circuit_hash}")
    print(f"   Timestamp: {proof.timestamp}")
    print(f"   Proof length: {len(proof.proof)} bytes")

    # Verify proof
    print("\n4. Verifying ZKP proof...")
    is_valid = zkp_manager.verify_proof(proof)
    print(f"   Valid: {is_valid}")

    # Using Universal ZKP Manager
    print("\n5. Using Universal ZKP Manager...")
    universal_manager = UniversalZKManager(default_backend="simplified")
    available_backends = universal_manager.get_available_backends()
    print(f"   Available backends: {available_backends}")

    # Generate proof with universal manager
    proof2 = universal_manager.generate_proof(inputs)
    print(f"   Proof generated with universal manager")
    print(f"   Valid: {universal_manager.verify_proof(proof2)}")


if __name__ == "__main__":
    main()
