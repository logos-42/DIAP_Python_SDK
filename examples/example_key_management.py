# Example: Basic Key Management
# Demonstrates key generation, signing, and verification

from diap import KeyManager, KeyPair


def main():
    print("=== DIAP SDK Basic Key Management Example ===\n")

    # Initialize key manager
    key_manager = KeyManager()

    # Generate a new key pair
    print("1. Generating new Ed25519 key pair...")
    key_pair = key_manager.generate_key_pair()
    print(f"   DID: {key_pair.did}")
    print(f"   Public key (hex): {key_pair.get_public_key_hex()[:32]}...")
    print(
        f"   Private key (hex): {key_pair.get_private_key_hex()[:32]}... (keep secret!)"
    )

    # Sign a message
    print("\n2. Signing a message...")
    message = b"Hello, DIAP!"
    signature = key_manager.sign(key_pair, message)
    print(f"   Message: {message.decode()}")
    print(f"   Signature (hex): {signature.hex()[:32]}...")

    # Verify signature
    print("\n3. Verifying signature...")
    is_valid = key_manager.verify(key_pair, message, signature)
    print(f"   Valid: {is_valid}")

    # Export and import key pair
    print("\n4. Exporting key pair...")
    backup = key_manager.export_key_pair(key_pair, password="mypassword")
    print(f"   Encrypted data: {backup.encrypted_data[:32]}...")
    print(f"   Exported at: {backup.exported_at}")

    # Save to file (optional)
    print("\n5. Saving key to file...")
    store_path = key_manager._get_key_path("default")
    print(f"   Key would be saved to: {store_path}")


if __name__ == "__main__":
    main()
