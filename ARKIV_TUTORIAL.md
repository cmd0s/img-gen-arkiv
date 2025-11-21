# Arkiv SDK Tutorial (Python)

This tutorial will guide you through setting up and using the Arkiv SDK for Python to interact with the Arkiv blockchain network. You'll learn how to query existing data and create new entities on the blockchain.

## What is Arkiv?

Arkiv is a blockchain network that allows you to store and query structured data with attributes and expiration times. Think of it as a decentralized database where each entry (entity) has:
- A unique key
- Binary payload data (images, JSON, text, etc.)
- Key-value attributes for filtering
- Optional expiration time
- Owner information

## Prerequisites

- **Python 3.11+** (3.12+ recommended)
- Virtual environment (venv)
- Ethereum wallet with test ETH
- Basic knowledge of Python

## Step 1: Project Setup

Create a new project directory:

```bash
mkdir arkiv-tutorial
cd arkiv-tutorial
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

Install the Arkiv SDK:

```bash
pip install --pre arkiv-sdk
pip install python-dotenv
```

## Step 2: Environment Configuration

Create a `.env` file:

```env
RPC_URL=https://mendoza.hoodi.arkiv.network/rpc
WS_URL=wss://mendoza.hoodi.arkiv.network/rpc/ws
ARKIV_CHAIN_ID=60138453056

ACCOUNT_ADR=0xYOUR_WALLET_ADDRESS
PRIVATE_KEY=0xYOUR_PRIVATE_KEY
```

## Step 3: Creating the Client

Create `arkiv_client.py`:

```python
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from arkiv import Arkiv

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


if __name__ == "__main__":
    arkiv = get_arkiv_client()
    print(f"Connected: {arkiv.is_connected()}")
```

## Step 4: Creating Entities

### Simple Text Entity

```python
from arkiv import Arkiv

arkiv = get_arkiv_client()

# Create a text entity
entity_key, tx_hash = arkiv.arkiv.create_entity(
    payload=b"Hello from Arkiv!",
    content_type="text/plain",
    attributes={
        "type": "message",
        "app": "my-app",
    },
    expires_in=arkiv.arkiv.to_seconds(days=30),
)

print(f"Entity created: {entity_key}")
print(f"Transaction: {tx_hash}")
```

### JSON Entity

```python
import json

data = {
    "title": "My Document",
    "content": "Document content here...",
    "author": "Jane Doe"
}

entity_key, tx_hash = arkiv.arkiv.create_entity(
    payload=json.dumps(data).encode("utf-8"),
    content_type="application/json",
    attributes={
        "type": "document",
        "author": "jane-doe",
    },
    expires_in=arkiv.arkiv.to_seconds(days=365),
)
```

### Binary Data (Images)

```python
# Read image file
with open("image.png", "rb") as f:
    image_data = f.read()

entity_key, tx_hash = arkiv.arkiv.create_entity(
    payload=image_data,
    content_type="image/png",
    attributes={
        "type": "image",
        "app": "my-gallery",
        "description": "A beautiful sunset",
    },
    expires_in=arkiv.arkiv.to_seconds(days=365),
)
```

## Step 5: Querying Entities

### Get Entity by Key

```python
entity = arkiv.arkiv.get_entity(
    "0xcadb830a3414251d65e5c92cd28ecb648d9e73d85f2203eff631839d5421f9d7"
)
print(f"Entity: {entity}")
```

### Query with Filters

```python
# Query entities by attributes
query = 'type = "image" and app = "my-gallery"'
entities = list(arkiv.arkiv.query_entities(query))

for entity in entities:
    print(f"Key: {entity.key}")
    print(f"Attributes: {entity.attributes}")
```

## Step 6: Batch Operations

Create multiple entities in a single transaction:

```python
from arkiv import CreateOp, Operations

creates = []
for i in range(5):
    creates.append(CreateOp(
        payload=f"Item #{i+1}".encode("utf-8"),
        content_type="text/plain",
        attributes={
            "type": "batch-item",
            "index": str(i),
        },
        expires_in=arkiv.arkiv.to_seconds(days=7),
    ))

batch_receipt = arkiv.arkiv.execute(Operations(creates=creates))
print(f"Batch transaction: {batch_receipt}")
```

## Step 7: Extending Entity Expiration

```python
# Extend entity lifetime by 30 more days
receipt = arkiv.arkiv.extend_entity(
    entity_key,
    extend_by=arkiv.arkiv.to_seconds(days=30)
)
```

## Step 8: Watching Events (Real-time)

```python
def on_created(event, tx_hash):
    entity = arkiv.arkiv.get_entity(event.key)
    print(f"[Created] key={event.key}")

# Watch for new entities
filter_created = arkiv.arkiv.watch_entity_created(
    on_created,
    from_block="latest",
    auto_start=True
)

# Clean up when done
arkiv.arkiv.cleanup_filters()
```

## Getting Test Funds

To create entities, you need a funded wallet:

1. **Generate a Private Key**: Use [vanity-eth.tk](https://vanity-eth.tk/) or any key generator
2. **Fund Your Address**: Visit the [Arkiv Mendoza Faucet](https://mendoza.hoodi.arkiv.network/faucet/)
3. **Update .env**: Add your private key

## Common Use Cases

### Image Storage with Metadata

```python
def upload_image(filepath: str, description: str, tags: list):
    with open(filepath, "rb") as f:
        image_data = f.read()

    entity_key, tx_hash = arkiv.arkiv.create_entity(
        payload=image_data,
        content_type="image/png",
        attributes={
            "type": "image",
            "description": description,
            "tags": ",".join(tags),
        },
        expires_in=arkiv.arkiv.to_seconds(days=365),
    )
    return entity_key
```

### Event Logging

```python
from datetime import datetime

def log_event(event_type: str, user_id: str, data: dict):
    payload = {
        "event": event_type,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }

    entity_key, _ = arkiv.arkiv.create_entity(
        payload=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        attributes={
            "type": "event",
            "event_type": event_type,
            "user_id": user_id,
        },
        expires_in=arkiv.arkiv.to_seconds(days=90),
    )
    return entity_key
```

## Troubleshooting

### Common Issues:

1. **"No module named 'arkiv'"**: Install with `pip install --pre arkiv-sdk`
2. **"PRIVATE_KEY not found"**: Create `.env` file with your credentials
3. **"Insufficient funds"**: Fund your wallet using the testnet faucet
4. **Connection errors**: Check RPC_URL in your `.env` file

### Getting Help:

- Check existing [GitHub Issues](https://github.com/arkiv-network/arkiv-sdk-python/issues)
- Visit [arkiv.network](https://arkiv.network) for documentation
- Review the [Getting Started Guide](https://arkiv.network/getting-started/python)

## Next Steps

- Explore the [Python SDK repository](https://github.com/arkiv-network/arkiv-sdk-python)
- Read the [API documentation](https://arkiv.network/docs)
- Join the Arkiv community for support and discussions
