# Example: Encrypted Peer ID
# Demonstrates encrypting and decrypting peer IDs

from diap import EncryptedPeerIDManager


def main():
    print("=== DIAP SDK Encrypted Peer ID Example ===\n")

    # Initialize manager
    manager = EncryptedPeerIDManager()

    # Generate peer ID keypair
    print("1. Generating peer ID keypair...")
    private_key, public_key = manager.generate_peer_id_keypair()
    print(f"   Private key length: {len(private_key)} bytes")
    print(f"   Public key length: {len(public_key)} bytes")

    # Original peer ID
    print("\n2. Original peer ID...")
    peer_id = b"QmPeerID1234567890abcdef"
    print(f"   Peer ID: {peer_id.hex()[:32]}...")

    # Encrypt peer ID with ECIES
    print("\n3. Encrypting peer ID (ECIES)...")
    encrypted = manager.encrypt_peer_id(peer_id, public_key)
    print(f"   Encrypted data: {encrypted.encrypted_data[:32]}...")
    print(f"   Nonce: {encrypted.nonce[:16]}...")
    print(f"   Ephemeral public key: {encrypted.ephemeral_public_key[:32]}...")

    # Decrypt peer ID
    print("\n4. Decrypting peer ID...")
    decrypted = manager.decrypt_peer_id(encrypted, private_key=private_key)
    print(f"   Decrypted: {decrypted.hex()[:32]}...")
    print(f"   Match: {decrypted == peer_id}")

    # AES encryption (without recipient public key)
    print("\n5. AES encryption (symmetric)...")
    encrypted_aes = manager.encrypt_peer_id(peer_id)
    print(f"   Encrypted data: {encrypted_aes.encrypted_data[:32]}...")
    print(f"   No ephemeral key (AES mode): {encrypted_aes.ephemeral_public_key == ''}")


if __name__ == "__main__":
    main()
