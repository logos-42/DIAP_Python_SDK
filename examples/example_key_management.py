# Example: Basic Key Management
# Demonstrates key generation, signing, and verification

from diap import KeyManager


def main():
    print("=== DIAP SDK Basic Key Management Example ===\n")

    # Generate a new key pair (static method)
    print("1. Generating new Ed25519 key pair...")
    key_pair = KeyManager.generate()
    print(f"   DID: {key_pair.did}")
    print(f"   Public key (hex): {key_pair.public_key.hex()[:32]}...")
    print(f"   Private key (hex): {key_pair.private_key.hex()[:32]}... (keep secret!)")

    # Sign a message
    print("\n2. Signing a message...")
    message = b"Hello, DIAP!"
    signature = KeyManager.sign(key_pair, message)
    print(f"   Message: {message.decode()}")
    print(f"   Signature (hex): {signature.hex()[:32]}...")

    # Verify signature
    print("\n3. Verifying signature...")
    is_valid = KeyManager.verify(key_pair, message, signature)
    print(f"   Valid: {is_valid}")

    # Export and import key pair
    print("\n4. Exporting key pair...")
    backup = KeyManager.export_backup(key_pair, password="mypassword")
    print(f"   Encrypted data: {backup.encrypted_data[:32]}...")
    print(f"   Exported at: {backup.exported_at}")

    # From private key
    print("\n5. Loading from private key...")
    key_pair2 = KeyManager.from_private_key(key_pair.private_key)
    print(f"   Same DID: {key_pair.did == key_pair2.did}")


if __name__ == "__main__":
    main()
