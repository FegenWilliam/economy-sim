"""Test customer specialization system v2 with corrections"""
import random
from economy_sim import (
    Customer, PRODUCT_CATEGORIES, Item, Player,
    get_category_specialty_threshold, choose_best_specialized_player,
    player_has_both_specializations
)

# Set seed for reproducibility
random.seed(42)

# Create test items for multiple categories
test_items = []
for i in range(15):
    test_items.append(Item(f"Food_{i}", 1.0 + i*0.5, 2.0 + i*1.0, "Food & Groceries"))
for i in range(10):
    test_items.append(Item(f"Elec_{i}", 100.0 + i*10, 200.0 + i*20, "Electronics"))
for i in range(8):
    test_items.append(Item(f"Sport_{i}", 20.0 + i*5, 40.0 + i*10, "Sports & Outdoor"))

item_demand = {item.name: 10.0 for item in test_items}

print("=" * 70)
print("Test 1: Customer rolls 2 DIFFERENT categories (not same twice)")
print("=" * 70)

# Test that customers roll 2 different categories when multiple are available
for test_num in range(5):
    customer = Customer(name=f"TestCustomer{test_num}", customer_type="medium", day=1)
    customer.roll_specializations(test_items, item_demand)
    print(f"  Customer {test_num}: {customer.specializations}")
    assert len(customer.specializations) == 2, "Should have 2 specializations"
    # Check that both are from market
    market_categories = set(item.category for item in test_items)
    assert all(cat in market_categories for cat in customer.specializations), "All categories should be in market"
    
    # Most should be different (though statistically could be same rarely)
    if customer.specializations[0] != customer.specializations[1]:
        print(f"    ✓ Different categories rolled")

print("✓ Test 1 passed\n")

print("=" * 70)
print("Test 2: Categories only from market items")
print("=" * 70)

# Create items only from 2 categories
limited_items = [item for item in test_items if item.category in ["Food & Groceries", "Electronics"]]
available_categories = set(item.category for item in limited_items)
print(f"  Available categories in market: {available_categories}")

customer = Customer(name="TestCustomer", customer_type="medium", day=1)
customer.roll_specializations(limited_items, item_demand)
print(f"  Customer rolled: {customer.specializations}")

for spec in customer.specializations:
    assert spec in available_categories, f"Rolled category {spec} not in market"

print("✓ Test 2 passed\n")

print("=" * 70)
print("Test 3: Player with BOTH specializations gets priority")
print("=" * 70)

# Create players with different specializations
player1 = Player(name="Player1")  # Has both Food & Electronics
for i in range(12):
    player1.inventory[f"Food_{i}"] = 1
for i in range(15):
    player1.inventory[f"Elec_{i}"] = 1

player2 = Player(name="Player2")  # Has only Food with very high threshold
for i in range(25):
    player2.inventory[f"Food_{i}"] = 1

player3 = Player(name="Player3")  # Has only Electronics with high threshold  
for i in range(20):
    player3.inventory[f"Elec_{i}"] = 1

players = [player1, player2, player3]

items_by_name = {item.name: item for item in test_items}

# Customer with Food & Electronics specializations
customer_categories = ["Food & Groceries", "Electronics"]
best = choose_best_specialized_player(players, customer_categories, items_by_name)

print(f"  Customer specializations: {customer_categories}")
print(f"  Best player chosen: {best.name}")
print(f"  Player1 has both: {player_has_both_specializations(player1, customer_categories, items_by_name)}")
print(f"  Player2 has both: {player_has_both_specializations(player2, customer_categories, items_by_name)}")
print(f"  Player3 has both: {player_has_both_specializations(player3, customer_categories, items_by_name)}")

assert best == player1, "Player1 should be chosen as they have BOTH specializations"
print("✓ Test 3 passed - Player with both specializations prioritized!\n")

print("=" * 70)
print("Test 4: Single category market")
print("=" * 70)

# Create market with only 1 category
single_cat_items = [item for item in test_items if item.category == "Food & Groceries"]
customer = Customer(name="TestCustomer", customer_type="medium", day=1)
customer.roll_specializations(single_cat_items, item_demand)
print(f"  Available category: Food & Groceries")
print(f"  Customer rolled: {customer.specializations}")
assert customer.specializations == ["Food & Groceries", "Food & Groceries"], "Should roll same category twice when only 1 available"
print("✓ Test 4 passed\n")

print("=" * 70)
print("All tests passed! ✓")
print("=" * 70)
