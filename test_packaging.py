#!/usr/bin/env python3
"""Test the product packaging system."""

from economy_sim import (
    Item, Player, Vendor, PRODUCT_CATALOG, Warehouse,
    get_package_info, parse_package_name, is_package,
    refresh_vendor_inventory, initialize_market_prices
)

print("Testing Product Packaging System")
print("=" * 70)

# Test 1: Package info generation
print("\n1. Testing package info generation...")
pens = next(item for item in PRODUCT_CATALOG if item.name == "Pens")
batteries = next(item for item in PRODUCT_CATALOG if item.name == "Batteries")
bread = next(item for item in PRODUCT_CATALOG if item.name == "Bread")

# Standard packages (5 size)
pens_package, pens_qty, pens_size = get_package_info(pens, "standard")
print(f"  Pens (size {pens.size}): {pens_package} contains {pens_qty} pens (total size: {pens_size})")

batteries_package, batteries_qty, batteries_size = get_package_info(batteries, "standard")
print(f"  Batteries (size {batteries.size}): {batteries_package} contains {batteries_qty} batteries (total size: {batteries_size})")

# Bulk packages (20 size)
pens_bulk, pens_bulk_qty, pens_bulk_size = get_package_info(pens, "bulk")
print(f"  Pens (size {pens.size}): {pens_bulk} contains {pens_bulk_qty} pens (total size: {pens_bulk_size})")

# Items >= 5 size should not be packaged, items < 5 should be
bread_package, bread_qty, bread_size = get_package_info(bread, "standard")
print(f"  Bread (size {bread.size}): {bread_package} contains {bread_qty} bread (total size: {bread_size})")

# Find an item with size >= 5 for testing
large_item = next(item for item in PRODUCT_CATALOG if item.size >= 5.0)
large_package, large_qty, large_size = get_package_info(large_item, "standard")
print(f"  {large_item.name} (size {large_item.size}): {large_package} (no packaging, size: {large_size})")

# Luxury items should NOT be packaged regardless of size
luxury_item = next(item for item in PRODUCT_CATALOG if item.category == "Luxury" and item.size < 5.0)
luxury_package, luxury_qty, luxury_size = get_package_info(luxury_item, "standard")
print(f"  {luxury_item.name} (size {luxury_item.size}, Luxury): {luxury_package} (no packaging, size: {luxury_size})")

assert pens_qty == 50, f"Expected 50 pens in package, got {pens_qty}"
assert batteries_qty == 16, f"Expected 16 batteries in package, got {batteries_qty}"
assert pens_bulk_qty == 200, f"Expected 200 pens in bulk package, got {pens_bulk_qty}"
assert bread_qty == 5, f"Expected 5 bread in package, got {bread_qty}"
assert large_package == large_item.name, "Large items should not be packaged"
assert large_qty == 1, "Large items should have quantity of 1"
assert luxury_package == luxury_item.name, "Luxury items should not be packaged"
assert luxury_qty == 1, "Luxury items should have quantity of 1"
print("  ✓ Package info generation works correctly")

# Test 2: Package name parsing
print("\n2. Testing package name parsing...")
assert parse_package_name("Box of Pens") == "Pens"
assert parse_package_name("Pack of Batteries") == "Batteries"
assert parse_package_name("Case of Pens") == "Pens"
assert parse_package_name("Bread") is None
assert is_package("Box of Pens") is True
assert is_package("Bread") is False
print("  ✓ Package name parsing works correctly")

# Test 3: Vendor inventory with packaging
print("\n3. Testing vendor inventory with packaging...")
market_prices = initialize_market_prices(PRODUCT_CATALOG)

# Create test vendors
test_vendor = Vendor(
    name="Test Vendor",
    pricing_multiplier=1.0,
    selection_type="all",
    selection_params=0
)

bulk_master = Vendor(
    name="Bulk Master Co.",
    pricing_multiplier=1.1,
    selection_type="price_threshold",
    selection_params=100.0,
    lead_time=1
)

vendors = [test_vendor, bulk_master]
refresh_vendor_inventory(vendors, PRODUCT_CATALOG, market_prices)

# Check that small items are packaged
assert "Box of Pens" in test_vendor.items, "Test vendor should have packaged pens"
assert "Pens" not in test_vendor.items, "Test vendor should not have individual pens"
assert "Bundle of Batteries" in test_vendor.items, "Test vendor should have packaged batteries"
assert "Tray of Bread" in test_vendor.items, "Test vendor should have packaged bread"
assert "Bread" not in test_vendor.items, "Test vendor should not have individual bread"

# Check that large items are not packaged
assert large_item.name in test_vendor.items, f"Test vendor should have unpacked {large_item.name}"

# Check that luxury items are not packaged
assert luxury_item.name in test_vendor.items, f"Test vendor should have unpacked {luxury_item.name}"
print(f"  Luxury item ({luxury_item.name}) correctly NOT packaged")

# Check package pricing
pens_market_price = market_prices["Pens"]
expected_pens_package_price = pens_market_price * pens_qty * test_vendor.pricing_multiplier
actual_pens_package_price = test_vendor.items["Box of Pens"]
print(f"  Box of Pens price: ${actual_pens_package_price:.2f} (expected: ${expected_pens_package_price:.2f})")
assert abs(actual_pens_package_price - expected_pens_package_price) < 0.01, "Package pricing incorrect"

# Check that Bulk Master Co. has both standard and bulk packages
assert "Box of Pens" in bulk_master.items, "Bulk Master should have standard pens package"
assert "Case of Pens" in bulk_master.items, "Bulk Master should have bulk pens package"
print(f"  Bulk Master has {len([k for k in bulk_master.items.keys() if 'Pens' in k])} pen package types")
print("  ✓ Vendor inventory packaging works correctly")

# Test 4: Purchasing packages
print("\n4. Testing package purchases...")
player = Player(name="Test Player", cash=10000.0, warehouses=[Warehouse(level=1)])

# Buy 2 boxes of pens (should add 100 individual pens to inventory)
success = player.purchase_from_vendor(test_vendor, "Box of Pens", 2, pens_market_price)
assert success, "Purchase should succeed"
assert player.inventory.get("Pens", 0) == 100, f"Should have 100 pens, got {player.inventory.get('Pens', 0)}"
assert "Box of Pens" not in player.inventory, "Should not have package in inventory"
print(f"  Bought 2 boxes of pens, now have {player.inventory['Pens']} individual pens")

# Check cost calculation
cost_per_individual_pen = player.item_costs["Pens"]
expected_cost = pens_market_price * test_vendor.pricing_multiplier
print(f"  Cost per pen: ${cost_per_individual_pen:.4f} (expected: ${expected_cost:.4f})")
assert abs(cost_per_individual_pen - expected_cost) < 0.01, "Cost tracking incorrect"

# Buy bulk package
initial_cash = player.cash
success = player.purchase_from_vendor(bulk_master, "Case of Pens", 1, pens_market_price)
assert success, "Bulk purchase should succeed"
expected_pens = 100 + pens_bulk_qty
assert player.inventory.get("Pens", 0) == expected_pens, f"Should have {expected_pens} pens, got {player.inventory.get('Pens', 0)}"
print(f"  Bought 1 case of pens, now have {player.inventory['Pens']} individual pens")

# Verify cash deduction
expected_bulk_price = pens_market_price * pens_bulk_qty * bulk_master.pricing_multiplier
actual_spent = initial_cash - player.cash
print(f"  Spent: ${actual_spent:.2f} (expected: ${expected_bulk_price:.2f})")
assert abs(actual_spent - expected_bulk_price) < 0.01, "Cash deduction incorrect"

print("  ✓ Package purchases work correctly")

# Test 5: Inventory size calculation with packages
print("\n5. Testing inventory size with packaged items...")
items_by_name = {item.name: item for item in PRODUCT_CATALOG}
inventory_size = player.get_inventory_size_used(items_by_name)
expected_size = player.inventory["Pens"] * pens.size
print(f"  Inventory size: {inventory_size:.1f} (expected: {expected_size:.1f})")
assert abs(inventory_size - expected_size) < 0.1, "Inventory size calculation incorrect"
print("  ✓ Inventory size calculation works correctly")

# Test 6: Compare package types
print("\n6. Package types comparison...")
print(f"  Standard packages (5 size):")
print(f"    - Box of Pens: {pens_qty} items, ${test_vendor.items['Box of Pens']:.2f}")
print(f"    - Bundle of Batteries: {batteries_qty} items, ${test_vendor.items['Bundle of Batteries']:.2f}")
print(f"  Bulk packages (20 size) - Bulk Master Co. only:")
print(f"    - Case of Pens: {pens_bulk_qty} items, ${bulk_master.items['Case of Pens']:.2f}")

# Test 7: Show various package names
print("\n7. Sample package names by category...")
sample_items = [
    ("Pens", "Office Supplies"),
    ("Batteries", "Household Essentials"),
    ("Toothbrush", "Personal Care"),
    ("USB Cable", "Electronics"),
    ("Salt", "Food & Groceries"),
]

for item_name, category in sample_items:
    item = next((i for i in PRODUCT_CATALOG if i.name == item_name), None)
    if item and item.size < 5.0:
        std_pkg, std_qty, _ = get_package_info(item, "standard")
        bulk_pkg, bulk_qty, _ = get_package_info(item, "bulk")
        print(f"  {item_name} ({category}):")
        print(f"    Standard: {std_pkg} ({std_qty} items)")
        print(f"    Bulk: {bulk_pkg} ({bulk_qty} items)")

print("\n" + "=" * 70)
print("✓ All packaging system tests passed!")
print("=" * 70)
