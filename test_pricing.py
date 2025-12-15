#!/usr/bin/env python3
"""
Tests for basic pricing setup and customer price ceiling behavior.
"""

from economy_sim import (
    GameState, GameConfig, Player, Customer, Item, Vendor,
    initialize_market_prices
)


def test_pricing_customer_ceiling():
    """Ensure prices are set above cost and customers respect the 15% ceiling."""

    items = [
        Item("Bread", 2.0, 5.0, "Food & Groceries"),
        Item("Milk", 1.5, 4.0, "Food & Groceries"),
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

    # Initialize player inventories, costs, and set simple prices above cost.
    for player in game_state.players:
        player.inventory = {"Bread": 10, "Milk": 10}
        player.item_costs = {"Bread": 2.5, "Milk": 2.0}
        player.prices = {
            "Bread": market_prices["Bread"] * 1.05,
            "Milk": market_prices["Milk"] * 1.05,
        }

    # Prices should remain profitable relative to cost.
    for player in game_state.players:
        for item_name, price in player.prices.items():
            cost = player.item_costs[item_name]
            assert price > cost, f"Price {price} should be > cost {cost} for {item_name}"

    # Test customer price ceiling behavior (15% above market max).
    customer = Customer("Test Customer", "medium")

    players[0].prices["Bread"] = market_prices["Bread"] * 1.20  # 20% above market
    players[0].inventory["Bread"] = 10

    players[1].prices["Bread"] = market_prices["Bread"] * 1.10  # 10% above market
    players[1].inventory["Bread"] = 10

    supplier = customer.choose_supplier(game_state.players, "Bread", 5, market_prices)

    assert supplier is not None, "A supplier should be chosen when stock is available"
    assert supplier.name == "AI Store 2", "Customer should choose the player within price ceiling"


if __name__ == "__main__":
    test_pricing_customer_ceiling()
