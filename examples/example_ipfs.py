# Example: IPFS Operations
# Demonstrates IPFS client operations

from diap import IPFSClient, IPFSNodeManager, KuboInstaller


def main():
    print("=== DIAP SDK IPFS Example ===\n")

    # Check if Kubo is installed
    print("1. Checking Kubo installation...")
    installer = KuboInstaller()
    is_installed = installer.is_installed()
    print(f"   Kubo installed: {is_installed}")

    if is_installed:
        version = installer.get_installed_version()
        print(f"   Version: {version}")

    # Initialize IPFS client
    print("\n2. Initializing IPFS client...")
    ipfs_client = IPFSClient(
        host="localhost",
        port=5001,
        protocol="http",
        gateway_host="localhost",
        gateway_port=8080,
    )
    print(f"   API: {ipfs_client.protocol}://{ipfs_client.host}:{ipfs_client.port}")
    print(
        f"   Gateway: {ipfs_client.gateway_protocol}://{ipfs_client.gateway_host}:{ipfs_client.gateway_port}"
    )

    # Get gateway URL
    print("\n3. Generating gateway URLs...")
    cid = "QmXyz123abc..."
    gateway_url = ipfs_client.get_gateway_url(cid, "metadata.json")
    print(f"   Full URL: {gateway_url}")
    print(f"   Base URL: {ipfs_client.get_gateway_url(cid)}")

    # Initialize node manager
    print("\n4. Initializing IPFS node manager...")
    node_manager = IPFSNodeManager(
        api_port=5001,
        gateway_port=8080,
    )
    print(f"   Node path: {node_manager.node_path}")

    # Get status
    print("\n5. Getting node status...")
    status = node_manager.get_status()
    print(f"   Running: {status['running']}")
    print(f"   API port: {status['api_port']}")


if __name__ == "__main__":
    main()
