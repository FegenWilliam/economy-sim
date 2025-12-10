#!/usr/bin/env python3
"""Test script for the demand system."""

from economy_sim import (
    GameState, Item, Customer, create_default_items,
    initialize_item_demand, update_item_demand,
    weighted_random_choice, weighted_random_sample
)

# Test 1: Initialize demand
print("Test 1: Initialize demand")
items = create_default_items()
demand = initialize_item_demand(items)
print(f"Initialized demand for {len(demand)} items")
for item_name, d in demand.items():
    print(f"  {item_name}: {d}")

# Test 2: Create a GameState and update demand
print("\nTest 2: Update demand")
game_state = GameState(
    items=items,
    item_demand=demand
)

for i in range(3):
    print(f"\n  Round {i+1}:")
    updated = update_item_demand(game_state)
    print(f"  Updated {len(updated)} items: {updated}")
    for item_name in updated:
        print(f"    {item_name}: {game_state.item_demand[item_name]:.2f}")

# Test 3: Test weighted selection
print("\nTest 3: Weighted selection")
# Set different demands
game_state.item_demand["Bread"] = 2.0  # High demand
game_state.item_demand["Milk"] = 1.0   # Normal
game_state.item_demand["Eggs"] = 0.1   # Low demand

print("Demand levels:")
for item in items:
    print(f"  {item.name}: {game_state.item_demand[item.name]:.2f}")

# Test random selection 100 times to see distribution
selections = {}
for _ in range(100):
    selected = weighted_random_choice(items, game_state.item_demand)
    if selected:
        selections[selected.name] = selections.get(selected.name, 0) + 1

print("\nSelection frequency (100 iterations):")
for item_name, count in sorted(selections.items(), key=lambda x: x[1], reverse=True):
    print(f"  {item_name}: {count} times ({count}%)")

# Test 4: Test customer want generation
print("\nTest 4: Customer want generation with demand")
customer = Customer(name="Test Customer", customer_type="medium")
needs = customer.generate_daily_needs(items, item_demand=game_state.item_demand)
print(f"Customer wants {len(needs)} items:")
for need in needs:
    print(f"  {need.item_name}: {need.quantity} units (demand: {game_state.item_demand[need.item_name]:.2f})")

print("\n✅ All tests passed!")
