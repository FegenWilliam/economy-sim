"""Test that CAS allocation is honored when player has matching category"""
import random
from economy_sim import (
    Customer, Item, Player, assign_customers_by_cas_with_specialization,
    get_category_specialty_threshold
)

# Set seed for reproducibility
random.seed(42)

# Create test items
test_items = []
for i in range(20):
    test_items.append(Item(f"Food_{i}", 1.0 + i*0.5, 2.0 + i*1.0, "Food & Groceries"))
for i in range(20):
    test_items.append(Item(f"Electronic_{i}", 50.0 + i*5.0, 100.0 + i*10.0, "Electronics"))
for i in range(20):
    test_items.append(Item(f"Game_{i}", 20.0 + i*2.0, 40.0 + i*4.0, "Gaming"))

items_by_name = {item.name: item for item in test_items}
market_prices = {item.name: item.base_cost * 1.5 for item in test_items}

print("=" * 80)
print("Test: CAS allocation is honored when player has at least 1 matching category")
print("=" * 80)

# Create 3 players with different specializations
# Player1: Has Food & Groceries specialty (15 items)
player1 = Player(name="Player1")
player1.cash = 1000.0
for i in range(15):
    player1.inventory[f"Food_{i}"] = 1

# Player2: Has BOTH Food & Groceries (30 items) AND Electronics (30 items) - best specialist
player2 = Player(name="Player2")
player2.cash = 1000.0
for i in range(30):
    player2.inventory[f"Food_{i}"] = 1
for i in range(30):
    player2.inventory[f"Electronic_{i}"] = 1

# Player3: Has Gaming specialty (15 items) - no matching category
player3 = Player(name="Player3")
player3.cash = 1000.0
for i in range(15):
    player3.inventory[f"Game_{i}"] = 1

players = [player1, player2, player3]

# Verify specialty thresholds
print("\nPlayer Specializations:")
print(f"  Player1 - Food & Groceries threshold: {get_category_specialty_threshold(player1, 'Food & Groceries', items_by_name)}")
print(f"  Player2 - Food & Groceries threshold: {get_category_specialty_threshold(player2, 'Food & Groceries', items_by_name)}")
print(f"  Player2 - Electronics threshold: {get_category_specialty_threshold(player2, 'Electronics', items_by_name)}")
print(f"  Player3 - Gaming threshold: {get_category_specialty_threshold(player3, 'Gaming', items_by_name)}")

# Create a customer with Food & Groceries and Electronics specializations
customer = Customer(name="TestCustomer", customer_type="medium", day=1)
customer.specializations = ["Food & Groceries", "Electronics"]

print(f"\nCustomer specializations: {customer.specializations}")

# Test Case 1: Customer gets allocated to Player1 (has 1 matching category)
print("\n" + "=" * 80)
print("Test Case 1: Customer allocated to Player1 (has Food & Groceries)")
print("=" * 80)
print("Expected: Customer stays with Player1 (CAS honored)")
print("Reason: Player1 has Food & Groceries specialty, so CAS is respected")

assignments, _ = assign_customers_by_cas_with_specialization(
    [customer],
    [player1, player2, player3],  # Order matters for CAS allocation
    market_prices,
    items_by_name,
    test_items
)

assigned_to = None
for player_name, customers in assignments.items():
    if customer in customers:
        assigned_to = player_name
        break

print(f"Result: Customer assigned to {assigned_to}")
assert assigned_to == "Player1", "Customer should stay with Player1 (CAS honored)"
print("✓ Test Case 1 PASSED\n")

# Test Case 2: Customer gets allocated to Player3 (no matching category)
print("=" * 80)
print("Test Case 2: Customer allocated to Player3 (no matching categories)")
print("=" * 80)
print("Expected: Customer goes to Player2 (overflow to best specialist)")
print("Reason: Player3 has NO matching categories, so customer becomes overflow")

assignments, _ = assign_customers_by_cas_with_specialization(
    [customer],
    [player3, player1, player2],  # Player3 will get customer via CAS
    market_prices,
    items_by_name,
    test_items
)

assigned_to = None
for player_name, customers in assignments.items():
    if customer in customers:
        assigned_to = player_name
        break

print(f"Result: Customer assigned to {assigned_to}")
assert assigned_to == "Player2", "Customer should go to Player2 (best specialist)"
print("✓ Test Case 2 PASSED\n")

# Test Case 3: Customer with no specializations stays with CAS assignment
print("=" * 80)
print("Test Case 3: Customer with no specializations")
print("=" * 80)
print("Expected: Customer stays with CAS assignment (Player3)")

customer_no_spec = Customer(name="NoSpecCustomer", customer_type="medium", day=1)
customer_no_spec.specializations = []

assignments, _ = assign_customers_by_cas_with_specialization(
    [customer_no_spec],
    [player3, player1, player2],
    market_prices,
    items_by_name,
    test_items
)

assigned_to = None
for player_name, customers in assignments.items():
    if customer_no_spec in customers:
        assigned_to = player_name
        break

print(f"Result: Customer assigned to {assigned_to}")
assert assigned_to == "Player3", "Customer with no specializations should stay with CAS assignment"
print("✓ Test Case 3 PASSED\n")

print("=" * 80)
print("All CAS priority tests PASSED! ✓")
print("=" * 80)
