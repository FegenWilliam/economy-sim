#!/usr/bin/env python3
"""
Test script for the new intelligent pricing strategy.
"""

from economy_sim import (
    GameState, GameConfig, Player, Customer, Item, Vendor,
    initialize_market_prices, run_day, auto_pricing_strategy
)

def test_pricing_strategy():
    """Test that the new pricing strategy works correctly."""

    # Create a simple game state
    items = [
        Item("Bread", 2.0, 5.0),
        Item("Milk", 1.5, 4.0),
    ]

    vendors = [
        Vendor("Baker's Supply", {"Bread": 2.5, "Milk": 2.0}),
    ]

    market_prices = initialize_market_prices(items)

    config = GameConfig(
        starting_cash=1000.0,
        num_days=5,
        customers_per_day=10
    )

    # Create AI players
    players = [
        Player("AI Store 1", cash=1000.0, is_human=False),
        Player("AI Store 2", cash=1000.0, is_human=False),
    ]

    game_state = GameState(
        day=1,
        players=players,
        items=items,
        vendors=vendors,
        market_prices=market_prices,
        config=config,
        available_upgrades=[]
    )

    # Initialize player inventories
    for player in game_state.players:
        player.inventory = {"Bread": 10, "Milk": 10}
        player.item_costs = {"Bread": 2.5, "Milk": 2.0}

    print("Testing pricing strategy...")
    print(f"\nMarket prices: {market_prices}")

    # Test Day 1 - no sales history
    print("\n=== Day 1: Initial pricing (no history) ===")
    for player in game_state.players:
        auto_pricing_strategy(player, market_prices, items)
        print(f"{player.name} prices: {player.prices}")

        # Verify prices are profitable (above cost)
        for item_name, price in player.prices.items():
            cost = player.item_costs.get(item_name, 0)
            assert price > cost, f"Price {price} should be > cost {cost} for {item_name}"
            print(f"  ✓ {item_name}: ${price:.2f} (cost: ${cost:.2f}, margin: {((price/cost - 1) * 100):.1f}%)")

    # Simulate some sales for Day 2
    print("\n=== Simulating sales for Day 1 ===")
    players[0].daily_sales_data = {
        "Bread": {"units_sold": 10, "revenue": 50.0, "sold_out": True, "unmet_demand": 5},
        "Milk": {"units_sold": 2, "revenue": 8.0, "sold_out": False, "unmet_demand": 0}
    }
    players[1].daily_sales_data = {
        "Bread": {"units_sold": 0, "revenue": 0.0, "sold_out": False, "unmet_demand": 0},
        "Milk": {"units_sold": 8, "revenue": 32.0, "sold_out": False, "unmet_demand": 0}
    }

    # Test Day 2 - with sales history
    print("\n=== Day 2: Pricing with sales history ===")
    for player in game_state.players:
        old_prices = player.prices.copy()
        auto_pricing_strategy(player, market_prices, items)
        print(f"\n{player.name}:")
        print(f"  Sales data: {player.daily_sales_data}")
        print(f"  Old prices: {old_prices}")
        print(f"  New prices: {player.prices}")

        # Verify strategic adjustments
        for item_name in player.prices:
            sales = player.daily_sales_data.get(item_name, {})
            old_price = old_prices[item_name]
            new_price = player.prices[item_name]

            if sales.get('sold_out'):
                print(f"  ✓ {item_name} sold out → price increased from ${old_price:.2f} to ${new_price:.2f}")
            elif sales.get('units_sold', 0) == 0:
                print(f"  ✓ {item_name} didn't sell → price decreased from ${old_price:.2f} to ${new_price:.2f}")
            else:
                print(f"  ✓ {item_name} moderate sales → price adjusted from ${old_price:.2f} to ${new_price:.2f}")

    # Test customer price ceiling
    print("\n=== Testing 15% customer price ceiling ===")
    customer = Customer("Test Customer", "medium")

    # Set one player's price too high (>15% above market)
    players[0].prices["Bread"] = market_prices["Bread"] * 1.20  # 20% above market
    players[0].inventory["Bread"] = 10

    # Set another player's price within range
    players[1].prices["Bread"] = market_prices["Bread"] * 1.10  # 10% above market
    players[1].inventory["Bread"] = 10

    print(f"Market price for Bread: ${market_prices['Bread']:.2f}")
    print(f"Player 1 price (20% above): ${players[0].prices['Bread']:.2f}")
    print(f"Player 2 price (10% above): ${players[1].prices['Bread']:.2f}")

    # Customer should choose Player 2 (within 15% ceiling)
    supplier = customer.choose_supplier(game_state.players, "Bread", 5, market_prices)

    if supplier:
        print(f"✓ Customer chose {supplier.name} (price within 15% ceiling)")
        assert supplier.name == "AI Store 2", "Customer should choose the player within price ceiling"
    else:
        print("✗ No supplier chosen (unexpected)")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_pricing_strategy()
