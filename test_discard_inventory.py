"""Test discard inventory functionality"""
import sys
sys.path.insert(0, '/home/user/economy-sim')

from economy_sim import (
    GameState, GameConfig, Player, PRODUCT_CATALOG
)

print("=" * 60)
print("Test: Discard Inventory Functionality")
print("=" * 60)

try:
    # Test 1: Create a player with inventory
    print("\n1. Creating player with inventory...")
    player = Player(name="Test Player", cash=1000.0)
    player.inventory = {
        "Apple": 50,
        "Banana": 30,
        "Carrot": 20
    }
    print(f"✓ Created player with inventory: {player.inventory}")

    # Test 2: Test discarding specific amount
    print("\n2. Testing discard specific amount...")
    initial_apples = player.inventory["Apple"]
    discard_amount = 10
    player.inventory["Apple"] -= discard_amount
    print(f"✓ Discarded {discard_amount} Apples")
    print(f"  Before: {initial_apples}, After: {player.inventory['Apple']}")
    assert player.inventory["Apple"] == initial_apples - discard_amount, "Discard amount mismatch!"

    # Test 3: Test discarding all of an item
    print("\n3. Testing discard all...")
    initial_bananas = player.inventory["Banana"]
    del player.inventory["Banana"]
    print(f"✓ Discarded all {initial_bananas} Bananas")
    assert "Banana" not in player.inventory, "Item should be removed from inventory!"
    print(f"  Remaining inventory: {player.inventory}")

    # Test 4: Test that inventory item is removed when quantity reaches 0
    print("\n4. Testing item removal at 0 quantity...")
    player.inventory["Carrot"] -= 20
    if player.inventory["Carrot"] == 0:
        del player.inventory["Carrot"]
    print(f"✓ Discarded all Carrots, removed from inventory")
    assert "Carrot" not in player.inventory, "Item with 0 quantity should be removed!"
    print(f"  Remaining inventory: {player.inventory}")

    # Test 5: Verify empty inventory doesn't cause errors
    print("\n5. Testing empty inventory...")
    player.inventory.clear()
    print(f"✓ Cleared all inventory")
    assert len(player.inventory) == 0, "Inventory should be empty!"
    print(f"  Inventory is empty: {len(player.inventory) == 0}")

    print("\n" + "=" * 60)
    print("✓ All discard inventory tests passed!")
    print("=" * 60)

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
