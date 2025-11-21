"""
Script to fix ARKIV entities that have ID stored as string instead of integer.
Run this once after stopping the main generator, then restart the generator.
"""

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

    provider = Web3.HTTPProvider(RPC_URL)
    account = Account.from_key(PRIVATE_KEY)
    return Arkiv(provider=provider, account=account)


def fix_string_ids():
    """Find and fix all CCats entities with string IDs."""
    print("=" * 60)
    print("FIX STRING IDs IN ARKIV")
    print("=" * 60)

    arkiv = get_arkiv_client()
    print(f"Connected: {arkiv.is_connected()}")

    # Query all CCats entities
    print("\nQuerying CCats entities...")
    query = 'app = "CCats" and type = "image"'

    entities_to_fix = []
    total_count = 0

    try:
        for entity in arkiv.arkiv.query_entities(query):
            total_count += 1
            attrs = entity.attributes if hasattr(entity, 'attributes') else {}

            # Check if 'id' attribute exists and is a string that looks like a number
            entity_id = attrs.get('id')

            if entity_id is not None:
                # Check if it's a string (not int)
                if isinstance(entity_id, str):
                    try:
                        int_id = int(entity_id)
                        entities_to_fix.append({
                            'key': entity.key,
                            'old_id': entity_id,
                            'new_id': int_id,
                            'attrs': attrs,
                        })
                    except ValueError:
                        print(f"  Warning: ID '{entity_id}' is not a valid number, skipping")

            if total_count % 10 == 0:
                print(f"  Scanned {total_count} entities...")

    except Exception as e:
        print(f"Error querying entities: {e}")
        return

    print(f"\nTotal entities scanned: {total_count}")
    print(f"Entities with string IDs to fix: {len(entities_to_fix)}")

    if not entities_to_fix:
        print("\nNo entities need fixing. All IDs are already integers.")
        return

    # Show what will be fixed
    print("\nEntities to fix:")
    for item in entities_to_fix[:10]:  # Show first 10
        print(f"  Key: {item['key'][:20]}... | ID: '{item['old_id']}' -> {item['new_id']}")
    if len(entities_to_fix) > 10:
        print(f"  ... and {len(entities_to_fix) - 10} more")

    # Confirm before proceeding
    print(f"\nThis will update {len(entities_to_fix)} entities on ARKIV blockchain.")
    confirm = input("Proceed? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Aborted.")
        return

    # Fix each entity
    print("\nFixing entities...")
    fixed_count = 0
    failed_count = 0

    for i, item in enumerate(entities_to_fix, 1):
        try:
            # Update entity with integer ID
            new_attrs = dict(item['attrs'])
            new_attrs['id'] = item['new_id']

            receipt = arkiv.arkiv.update_entity(
                entity_key=item['key'],
                attributes=new_attrs,
            )

            fixed_count += 1
            print(f"  [{i}/{len(entities_to_fix)}] Fixed: {item['key'][:20]}... | ID: {item['new_id']}")

        except Exception as e:
            failed_count += 1
            print(f"  [{i}/{len(entities_to_fix)}] FAILED: {item['key'][:20]}... | Error: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total entities processed: {len(entities_to_fix)}")
    print(f"Successfully fixed: {fixed_count}")
    print(f"Failed: {failed_count}")

    if fixed_count > 0:
        print("\nYou can now restart the main generator with: python main.py")


if __name__ == "__main__":
    fix_string_ids()
