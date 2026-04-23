# Example: DID Document Creation
# Demonstrates creating and managing W3C DID Documents

from diap import KeyManager, DIDBuilder, DIDCache, KeyPair
from diap.types.did_types import AgentProfile, Service


def main():
    print("=== DIAP SDK DID Document Example ===\n")

    # Initialize components
    key_manager = KeyManager()
    did_builder = DIDBuilder(key_manager)
    did_cache = DIDCache()

    # Generate key pair
    print("1. Generating key pair...")
    key_pair = key_manager.generate_key_pair()
    print(f"   DID: {key_pair.did}")

    # Create agent profile
    print("\n2. Creating agent profile...")
    profile = AgentProfile(
        name="MyAgent",
        description="A test agent",
        homepage="https://example.com/agent",
        avatar="https://example.com/avatar.png",
    )
    print(f"   Name: {profile.name}")
    print(f"   Description: {profile.description}")

    # Create custom service
    print("\n3. Adding custom service...")
    custom_service = Service(
        id=f"{key_pair.did}/custom-service",
        service_type="CustomService",
        service_endpoint={"url": "https://api.example.com"},
    )
    print(f"   Service ID: {custom_service.id}")
    print(f"   Service Type: {custom_service.service_type}")

    # Create DID document
    print("\n4. Creating DID document...")
    doc = did_builder.create_did_document(
        key_pair=key_pair,
        services=[custom_service],
        agent_profile=profile,
    )
    print(f"   Context: {doc.context}")
    print(f"   ID: {doc.id}")
    print(f"   Verification Methods: {len(doc.verification_method)}")
    print(f"   Services: {len(doc.service) if doc.service else 0}")

    # Cache the document
    print("\n5. Caching DID document...")
    did_cache.set(key_pair.did, doc)
    print(f"   Cached for DID: {key_pair.did}")

    # Retrieve from cache
    print("\n6. Retrieving from cache...")
    cached_doc = did_cache.get(key_pair.did)
    if cached_doc:
        print(f"   Retrieved successfully!")
        print(f"   Services: {len(cached_doc.service) if cached_doc.service else 0}")

    # Compute document hash
    print("\n7. Computing document hash...")
    doc_hash = did_builder.compute_document_hash(doc)
    print(f"   Hash: {doc_hash}")

    # Parse DID
    print("\n8. Parsing DID...")
    parsed = did_builder.parse_did(key_pair.did)
    print(f"   Method: {parsed['method']}")
    print(f"   Method Specific ID: {parsed['method_specific_id'][:20]}...")

    # Export document
    print("\n9. Exporting document to JSON...")
    doc_dict = doc.to_dict()
    import json

    print(f"   JSON keys: {list(doc_dict.keys())}")


if __name__ == "__main__":
    main()
