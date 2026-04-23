# Example: Encrypted Peer ID
# Demonstrates encrypting and decrypting peer IDs

from diap import KeyManager
from diap.encrypted_peer_id import (
    encrypt_peer_id,
    decrypt_peer_id_with_secret,
    verify_peer_id_signature,
)


def main():
    print("=== DIAP SDK Encrypted Peer ID Example ===\n")

    # Generate key pair using Ed25519
    print("1. Generating Ed25519 key pair...")
    signing_key = KeyManager.generate()
    print(f"   DID: {signing_key.did}")
    print(f"   Signing key length: {len(signing_key.private_key)} bytes")

    # Original peer ID
    print("\n2. Original peer ID...")
    peer_id = "QmPeerID1234567890abcdef"
    print(f"   Peer ID: {peer_id}")

    # Encrypt peer ID with Ed25519-derived AES key
    print("\n3. Encrypting peer ID (AES-256-GCM-Ed25519-V3)...")
    encrypted = encrypt_peer_id(signing_key.private_key, peer_id)
    print(f"   Ciphertext length: {len(encrypted.ciphertext)} bytes")
    print(f"   Nonce length: {len(encrypted.nonce)} bytes")
    print(f"   Signature length: {len(encrypted.signature)} bytes")
    print(f"   Method: {encrypted.method}")

    # Decrypt peer ID with private key
    print("\n4. Decrypting peer ID...")
    decrypted = decrypt_peer_id_with_secret(signing_key.private_key, encrypted)
    print(f"   Decrypted: {decrypted}")
    print(f"   Match: {decrypted == peer_id}")

    # Verify signature
    print("\n5. Verifying signature...")
    is_valid = verify_peer_id_signature(signing_key.public_key, encrypted, peer_id)
    print(f"   Signature valid: {is_valid}")


if __name__ == "__main__":
    main()
