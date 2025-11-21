import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from arkiv import Arkiv

# Load environment variables
load_dotenv()

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")


def get_arkiv_client() -> Arkiv:
    """Create and return ARKIV client."""
    if not PRIVATE_KEY:
        raise RuntimeError("PRIVATE_KEY not found in .env file")
    if not RPC_URL:
        raise RuntimeError("RPC_URL not found in .env file")

    # Create Web3 provider
    provider = Web3.HTTPProvider(RPC_URL)

    # Create account from private key
    account = Account.from_key(PRIVATE_KEY)

    return Arkiv(provider=provider, account=account)


def upload_image_to_arkiv(
    image_data: bytes,
    prompt: str,
    image_id: int,
    content_type: str = "image/jpeg"
) -> dict:
    """
    Upload image to ARKIV blockchain.

    Args:
        image_data: Raw image bytes
        prompt: The prompt used to generate the image
        image_id: Unique identifier for the image
        content_type: MIME type (image/jpeg or image/png)

    Returns:
        dict with entityKey and txHash
    """
    arkiv = get_arkiv_client()

    # Create entity with image as payload
    entity_key, tx_hash = arkiv.arkiv.create_entity(
        payload=image_data,
        content_type=content_type,
        attributes={
            "type": "image",
            "app": "CCats",
            "prompt": prompt[:500],  # Limit prompt length
            "id": image_id,
        },
        expires_in=arkiv.arkiv.to_seconds(days=128),  # 128 days expiration
    )

    return {
        "success": True,
        "entityKey": entity_key,
        "txHash": tx_hash,
    }


if __name__ == "__main__":
    # Test connection
    try:
        arkiv = get_arkiv_client()
        print("ARKIV client created successfully")
        print(f"RPC URL: {RPC_URL}")
        print(f"Connected: {arkiv.is_connected()}")
    except Exception as e:
        print(f"Error: {e}")
