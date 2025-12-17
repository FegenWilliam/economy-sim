"""Test customer specialization system"""
import random
from economy_sim import (
    Customer, PRODUCT_CATEGORIES, Item, GameState, Player,
    get_category_specialty_threshold, choose_best_specialized_player
)

# Set seed for reproducibility
random.seed(42)

# Create test items for Food & Groceries (need at least 10 to reach first threshold)
test_items = []
for i in range(15):
    test_items.append(Item(f"Food_{i}", 1.0 + i*0.5, 2.0 + i*1.0, "Food & Groceries"))
test_items.extend([
    Item("Laptop", 500.0, 1000.0, "Electronics"),
    Item("Gaming Console", 300.0, 600.0, "Gaming"),
])

# Create item demand
item_demand = {item.name: 10.0 for item in test_items}

print("=" * 60)
print("Test 1: Customer specialization rolling")
print("=" * 60)

# Test roll_specializations
customer = Customer(name="TestCustomer1", customer_type="medium", day=1)
print(f"Before rolling: specializations = {customer.specializations}")
customer.roll_specializations(test_items, item_demand)
print(f"After rolling: specializations = {customer.specializations}")
assert len(customer.specializations) == 2, "Customer should have 2 specializations"
assert all(cat in PRODUCT_CATEGORIES for cat in customer.specializations), "Specializations should be valid categories"
print("✓ Customer can roll specializations\n")

print("=" * 60)
print("Test 2: Customer generate needs with specializations")
print("=" * 60)

# Test that generate_daily_needs respects specializations
customer2 = Customer(name="TestCustomer2", customer_type="medium", day=1)
customer2.specializations = ["Food & Groceries", "Electronics"]
needs = customer2.generate_daily_needs(test_items, {}, item_demand)
print(f"Customer specializations: {customer2.specializations}")
print(f"Generated {len(needs)} items from specialized categories")

# Verify that all items are from the specialized categories
for need in needs:
    for item in test_items:
        if item.name == need.item_name:
            assert item.category in customer2.specializations, f"Item {item.name} not in specialization categories"
            break

print("✓ Customer only buys from specialized categories\n")

print("=" * 60)
print("Test 3: Category specialty threshold detection")
print("=" * 60)

# Create a test player with enough Food & Groceries stock to reach threshold 10
player = Player(name="TestPlayer1")
for i in range(12):
    player.inventory[f"Food_{i}"] = 1

items_by_name = {item.name: item for item in test_items}

threshold = get_category_specialty_threshold(player, "Food & Groceries", items_by_name)
print(f"Food & Groceries threshold reached: {threshold}")
assert threshold is not None, "Player should have a threshold for Food & Groceries"
assert threshold >= 10, "Player with 12 items should reach at least threshold 10"
print("✓ Can detect category specialty thresholds\n")

print("=" * 60)
print("Test 4: Choose best specialized player")
print("=" * 60)

# Create multiple players with different specializations
player1 = Player(name="Player1")
for i in range(12):
    player1.inventory[f"Food_{i}"] = 1

player2 = Player(name="Player2")
for i in range(3):
    player2.inventory[f"Food_{i}"] = 1

players = [player1, player2]

best = choose_best_specialized_player(players, "Food & Groceries", items_by_name)
print(f"Best specialized player for Food & Groceries: {best.name if best else 'None'}")
assert best == player1, "Player1 should be chosen as they have more items (12 vs 3)"
print("✓ Can choose best specialized player\n")

print("=" * 60)
print("All tests passed! ✓")
print("=" * 60)
