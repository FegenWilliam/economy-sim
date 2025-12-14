#!/usr/bin/env python3
"""Test script to verify pending deliveries are saved and loaded correctly."""
import json
import tempfile
import os

# Create a save file with pending deliveries
save_data_with_deliveries = {
    "day": 5,
    "current_player_index": 0,
    "unlocked_product_indices": [0, 1, 2, 3, 4, 5],
    "config": {
        "starting_cash": 1000,
        "num_days": 100,
        "customers_per_day": 50
    },
    "items": [
        {"name": "Bread", "base_cost": 2.0, "base_price": 5.0, "category": "Food & Groceries"},
        {"name": "Milk", "base_cost": 3.0, "base_price": 6.0, "category": "Food & Groceries"},
        {"name": "Eggs", "base_cost": 2.5, "base_price": 5.5, "category": "Food & Groceries"}
    ],
    "market_prices": {"Bread": 5.0, "Milk": 6.0, "Eggs": 5.5},
    "vendors": [],
    "players": [
        {
            "name": "Test Player",
            "cash": 1000,
            "inventory": {"Bread": 10},
            "prices": {"Bread": 5.0},
            "buy_orders": {},
            "cashiers": 1,
            "restockers": 0,
            "store_level": 1,
            "experience": 0,
            "item_costs": {"Bread": 2.0},
            "purchased_upgrades": [],
            "is_human": True,
            "last_wage_payment_day": 0,
            "vendor_partnership_expiration": {},
            "reputation": 0.0,
            "average_fulfillment_pct": 70.0,
            "pending_deliveries": [
                ["Milk", 50, 3.0, 8],  # 50 Milk arriving on day 8, cost $3.0 each
                ["Eggs", 100, 2.5, 9],  # 100 Eggs arriving on day 9, cost $2.5 each
                ["Bread", 75, 2.0, 10]  # 75 Bread arriving on day 10, cost $2.0 each
            ]
        }
    ],
    "available_upgrades": [],
    "vendor_daily_purchases": {},
    "players_passed": []
}

# Write to temporary file
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    temp_file = f.name
    json.dump(save_data_with_deliveries, f, indent=2)

print(f"Created test save file: {temp_file}")
print("\nAttempting to load save file with pending deliveries...")

# Import the load function
from economy_sim import load_game, save_game

# Try to load
game_state = load_game(temp_file)

if game_state:
    print("✓ Successfully loaded save file!")

    # Check pending deliveries
    player = game_state.players[0]
    print(f"\n✓ Player has {len(player.pending_deliveries)} pending deliveries:")
    for item_name, quantity, cost, delivery_day in player.pending_deliveries:
        print(f"  - {quantity}x {item_name} @ ${cost:.2f} each, arriving day {delivery_day}")

    # Verify the data matches what we saved
    expected_deliveries = [
        ("Milk", 50, 3.0, 8),
        ("Eggs", 100, 2.5, 9),
        ("Bread", 75, 2.0, 10)
    ]

    if player.pending_deliveries == expected_deliveries:
        print("\n✓ Pending deliveries match expected values!")
    else:
        print("\n✗ Pending deliveries don't match!")
        print(f"Expected: {expected_deliveries}")
        print(f"Got: {player.pending_deliveries}")

    # Now test round-trip save/load
    print("\nTesting round-trip save/load...")
    temp_file2 = temp_file.replace('.json', '_roundtrip.json')
    if save_game(game_state, temp_file2):
        print(f"✓ Saved to {temp_file2}")

        game_state2 = load_game(temp_file2)
        if game_state2:
            player2 = game_state2.players[0]
            if player2.pending_deliveries == expected_deliveries:
                print("✓ Round-trip save/load preserves pending deliveries!")
                print("\n✓✓✓ All tests PASSED! ✓✓✓")
            else:
                print("✗ Round-trip save/load corrupted pending deliveries!")
                print(f"Expected: {expected_deliveries}")
                print(f"Got: {player2.pending_deliveries}")
        else:
            print("✗ Failed to load round-trip save")

        os.unlink(temp_file2)
    else:
        print("✗ Failed to save game state")
else:
    print("✗ Failed to load save file")
    print("✗ Test FAILED!")

# Cleanup
os.unlink(temp_file)
