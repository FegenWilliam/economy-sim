#!/usr/bin/env python3
"""
Test auto-restock with lead time - verifies that vendors with lead time
cause auto-restock to order more to account for yesterday's sales.
"""

from economy_sim import (
    GameState, Player, Vendor, Item, GameConfig,
    execute_stock_minimum_restock, execute_category_minimum_restock
)

def test_auto_restock_with_lead_time():
    """Test that auto-restock accounts for lead time by adding yesterday's sales."""
    print("=" * 60)
    print("Testing Auto-Restock with Lead Time")
    print("=" * 60)

    # Create game state
    config = GameConfig()
    game_state = GameState(day=1, config=config)

    # Create a simple item (size >= 5 so it's not packaged)
    item = Item(name="Widget", base_cost=5.0, base_price=10.0, category="Office Supplies", size=5.0)
    game_state.items = [item]
    game_state.market_prices = {"Widget": 10.0}

    # Create two vendors: one instant, one with 2-day lead time
    instant_vendor = Vendor(
        name="Instant Vendor",
        items={"Widget": 5.0},
        lead_time=0
    )

    slow_vendor = Vendor(
        name="Slow Vendor",
        items={"Widget": 5.0},
        lead_time=2
    )

    game_state.vendors = [instant_vendor, slow_vendor]

    # Create player with auto-restock set up
    player = Player(name="TestPlayer", cash=10000.0)

    # Set up auto-restock with minimum of 10 units
    player.stock_minimum_restock["Widget"] = (10, "Instant Vendor")

    # Set yesterday's demand to 5 units
    player.yesterday_demand["Widget"] = 5

    # Set current stock to 8 units (below minimum of 10)
    player.inventory["Widget"] = 8

    print("\nTest 1: Instant vendor (lead_time=0)")
    print(f"  Minimum stock: 10")
    print(f"  Current stock: 8")
    print(f"  Yesterday's demand: 5")
    print(f"  Expected behavior: Order 2 units (10 - 8)")

    purchases, _ = execute_stock_minimum_restock(player, game_state)

    if "Widget" in purchases:
        print(f"  ✓ Ordered {purchases['Widget']} units")
        expected = 2
        if purchases["Widget"] == expected:
            print(f"  ✓ Correct: ordered exactly {expected} units (no lead time adjustment)")
        else:
            print(f"  ✗ ERROR: Expected {expected}, got {purchases['Widget']}")
    else:
        print(f"  ✗ ERROR: No purchase made!")

    # Reset for test 2
    player.inventory["Widget"] = 8
    player.stock_minimum_restock["Widget"] = (10, "Slow Vendor")

    print("\nTest 2: Slow vendor (lead_time=2)")
    print(f"  Minimum stock: 10")
    print(f"  Current stock: 8")
    print(f"  Yesterday's demand: 5")
    print(f"  Expected behavior: Order 12 units (10 + (5 * 2) - 8)")
    print(f"    Because: adjusted_minimum = 10 + (5 * 2) = 20")

    purchases, _ = execute_stock_minimum_restock(player, game_state)

    if "Widget" in purchases:
        print(f"  ✓ Ordered {purchases['Widget']} units")
        expected = 12
        if purchases["Widget"] == expected:
            print(f"  ✓ Correct: ordered {expected} units (with lead time adjustment)")
        else:
            print(f"  ✗ ERROR: Expected {expected}, got {purchases['Widget']}")
    else:
        print(f"  ✗ ERROR: No purchase made!")

    # Test 3: Category auto-restock with lead time
    print("\nTest 3: Category auto-restock with lead time (2 days)")
    player.inventory["Widget"] = 5
    player.stock_minimum_restock = {}  # Clear item-specific restock
    player.category_minimum_restock["Office Supplies"] = (10, "Slow Vendor")
    player.yesterday_demand["Widget"] = 3

    print(f"  Minimum stock per item: 10")
    print(f"  Current stock: 5")
    print(f"  Yesterday's demand: 3")
    print(f"  Expected behavior: Order 11 units (10 + (3 * 2) - 5)")
    print(f"    Because: adjusted_minimum = 10 + (3 * 2) = 16")

    purchases, _ = execute_category_minimum_restock(player, game_state)

    if "Widget" in purchases:
        print(f"  ✓ Ordered {purchases['Widget']} units")
        expected = 11
        if purchases["Widget"] == expected:
            print(f"  ✓ Correct: ordered {expected} units (category with lead time adjustment)")
        else:
            print(f"  ✗ ERROR: Expected {expected}, got {purchases['Widget']}")
    else:
        print(f"  ✗ ERROR: No purchase made!")

    # Test 4: Very slow vendor (lead_time=5) to verify multiplication
    print("\nTest 4: Very slow vendor (lead_time=5)")

    very_slow_vendor = Vendor(
        name="Very Slow Vendor",
        items={"Widget": 5.0},
        lead_time=5
    )
    game_state.vendors.append(very_slow_vendor)

    player.inventory["Widget"] = 10
    player.stock_minimum_restock["Widget"] = (20, "Very Slow Vendor")
    player.category_minimum_restock = {}  # Clear category restock
    player.yesterday_demand["Widget"] = 4

    print(f"  Minimum stock: 20")
    print(f"  Current stock: 10")
    print(f"  Yesterday's demand: 4")
    print(f"  Lead time: 5 days")
    print(f"  Expected behavior: Order 30 units (20 + (4 * 5) - 10)")
    print(f"    Because: adjusted_minimum = 20 + (4 * 5) = 40")

    purchases, _ = execute_stock_minimum_restock(player, game_state)

    if "Widget" in purchases:
        print(f"  ✓ Ordered {purchases['Widget']} units")
        expected = 30
        if purchases["Widget"] == expected:
            print(f"  ✓ Correct: ordered {expected} units (5-day lead time adjustment)")
        else:
            print(f"  ✗ ERROR: Expected {expected}, got {purchases['Widget']}")
    else:
        print(f"  ✗ ERROR: No purchase made!")

    print("\n" + "=" * 60)
    print("✓ All auto-restock lead time tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_auto_restock_with_lead_time()
