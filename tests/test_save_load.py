#!/usr/bin/env python3
"""Test script to verify save/load backward compatibility."""
import json
import tempfile
import os

# Create a mock old save file without category field
old_save_data = {
    "day": 5,
    "current_player_index": 0,
    "unlocked_product_indices": [0, 1, 2, 3, 4, 5],
    "config": {
        "starting_cash": 1000,
        "num_days": 100,
        "customers_per_day": 50
    },
    "items": [
        {"name": "Bread", "base_cost": 2.0, "base_price": 5.0},  # Missing category!
        {"name": "Milk", "base_cost": 3.0, "base_price": 6.0},   # Missing category!
        {"name": "Eggs", "base_cost": 2.5, "base_price": 5.5}    # Missing category!
    ],
    "market_prices": {"Bread": 5.0, "Milk": 6.0, "Eggs": 5.5},
    "vendors": [],
    "players": [
        {
            "name": "Test Player",
            "cash": 1000,
            "inventory": {},
            "prices": {},
            "buy_orders": {},
            "cashiers": 1,
            "restockers": 0,
            "store_level": 1,
            "experience": 0,
            "item_costs": {},
            "purchased_upgrades": [],
            "is_human": True,
            "last_wage_payment_day": 0,
            "vendor_partnership_expiration": {},
            "reputation": 0.0,
            "average_fulfillment_pct": 70.0
        }
    ],
    "available_upgrades": [],
    "vendor_daily_purchases": {},
    "players_passed": []
}

# Write to temporary file
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    temp_file = f.name
    json.dump(old_save_data, f, indent=2)

print(f"Created test save file: {temp_file}")
print("\nAttempting to load old save file format (without category field)...")

# Import the load function
from economy_sim import load_game

# Try to load
game_state = load_game(temp_file)

if game_state:
    print("✓ Successfully loaded old save file!")
    print(f"✓ Loaded {len(game_state.items)} items:")
    for item in game_state.items:
        print(f"  - {item.name}: category='{item.category}', importance={item.importance}")
    print("\n✓ Backward compatibility test PASSED!")
else:
    print("✗ Failed to load old save file")
    print("✗ Backward compatibility test FAILED!")

# Cleanup
os.unlink(temp_file)
