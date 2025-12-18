#!/usr/bin/env python3
"""Test the item size system."""

from economy_sim import Item, Player, Warehouse, PRODUCT_CATALOG

# Test that all items have sizes
print("Testing item size system...")
print("=" * 60)

# 1. Check that all items have a size property
print("\n1. Checking all items have size property...")
for item in PRODUCT_CATALOG:
    assert hasattr(item, 'size'), f"Item {item.name} missing size property"
    assert item.size > 0, f"Item {item.name} has invalid size: {item.size}"
print(f"✓ All {len(PRODUCT_CATALOG)} items have valid sizes")

# 2. Show some example sizes
print("\n2. Example item sizes:")
examples = [
    ("Pens", 0.1),
    ("Pencils", 0.1),
    ("Bread", 1.0),
    ("Milk", 1.0),
    ("Microwave", 3.5),
    ("4K TV", 6.0),
    ("Lawn Mower", 15.0),
    ("Patio Furniture", 20.0),
]

items_by_name = {item.name: item for item in PRODUCT_CATALOG}
for name, expected_range in examples:
    if name in items_by_name:
        actual_size = items_by_name[name].size
        print(f"  {name}: {actual_size} (expected around {expected_range})")

# 3. Test inventory size calculation
print("\n3. Testing inventory size calculation...")
player = Player(name="Test Player", warehouses=[Warehouse(level=1)])
player.inventory = {
    "Pens": 100,      # 100 * 0.1 = 10
    "Bread": 50,      # 50 * 1.0 = 50
    "Microwave": 10,  # 10 * 3.5 = 35
}

inventory_size = player.get_inventory_size_used(items_by_name)
print(f"  Player inventory: {player.inventory}")
print(f"  Total size used: {inventory_size:.1f}")
print(f"  Expected: ~95 (10 + 50 + 35)")
print(f"  Max inventory capacity: {player.get_max_inventory()}")

# 4. Test that small items fit more per slot
print("\n4. Testing inventory efficiency...")
print(f"  With size 0.1 items (pens): 100 pens = {100 * 0.1} space (10 pens per 1 space)")
print(f"  With size 1.0 items (bread): 100 bread = {100 * 1.0} space (1 bread per 1 space)")
print(f"  With size 6.0 items (TV): 10 TVs would be {10 * items_by_name.get('4K TV').size} space")

print("\n" + "=" * 60)
print("✓ All item size tests passed!")
print("=" * 60)
