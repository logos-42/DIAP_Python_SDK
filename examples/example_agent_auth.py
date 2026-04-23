# Example: Agent Authentication
# Demonstrates creating agents and managing authentication

from diap import KeyManager, AgentAuthManager, NonceManager
from diap.zkp import UniversalZKManager


def main():
    print("=== DIAP SDK Agent Authentication Example ===\n")

    # Initialize components
    key_manager = KeyManager()
    nonce_manager = NonceManager()
    zkp_manager = UniversalZKManager()
    auth_manager = AgentAuthManager(
        key_manager=key_manager, nonce_manager=nonce_manager
    )

    # Create agent
    print("1. Creating agent...")
    key_pair = key_manager.generate_key_pair()
    agent = auth_manager.create_agent(
        name="TestAgent", key_pair=key_pair, metadata={"role": "test"}
    )
    print(f"   Agent DID: {agent.did}")
    print(f"   Name: {agent.name}")
    print(f"   Created at: {agent.created_at}")

    # List agents
    print("\n2. Listing agents...")
    agents = auth_manager.list_agents()
    print(f"   Total agents: {len(agents)}")

    # Generate authentication challenge
    print("\n3. Generating authentication challenge...")
    challenge = auth_manager.generate_challenge(agent.did)
    print(f"   Challenge: {challenge[:32]}...")

    # Get agent stats
    print("\n4. Getting agent authentication stats...")
    stats = auth_manager.get_auth_stats(agent.did)
    print(f"   Auth count: {stats.get('auth_count', 0)}")
    print(f"   Last authenticated: {stats.get('last_authenticated', 'Never')}")

    # Generate ZKP proof
    print("\n5. Generating authentication proof...")
    proof = auth_manager.generate_proof(agent.did, zkp_manager)
    print(f"   Circuit hash: {proof.circuit_hash}")
    print(f"   Timestamp: {proof.timestamp}")

    # Verify identity with ZKP
    print("\n6. Verifying agent identity...")
    is_valid = auth_manager.verify_identity(agent.did, proof, zkp_manager)
    print(f"   Identity valid: {is_valid}")

    # Get updated stats
    print("\n7. Updated agent stats...")
    stats = auth_manager.get_auth_stats(agent.did)
    print(f"   Auth count: {stats.get('auth_count', 0)}")


if __name__ == "__main__":
    main()
