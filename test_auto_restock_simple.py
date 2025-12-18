#!/usr/bin/env python3
"""
Simple test to debug auto-restock with lead time.
"""

from economy_sim import (
    GameState, Player, Vendor, Item, GameConfig,
    execute_stock_minimum_restock
)

def main():
    print("Simple Auto-Restock Debug Test")
    print("=" * 60)

    # Create game state
    config = GameConfig()
    game_state = GameState(day=1, config=config)

    # Create a simple item (size >= 5 so it's not packaged)
    item = Item(name="Widget", base_cost=5.0, base_price=10.0, category="Office Supplies", size=5.0)
    game_state.items = [item]
    game_state.market_prices = {"Widget": 10.0}

    # Create vendor with lead time
    vendor = Vendor(
        name="Test Vendor",
        items={"Widget": 5.0},
        lead_time=2
    )
    game_state.vendors = [vendor]

    # Create player
    player = Player(name="TestPlayer", cash=10000.0)

    # Set inventory and yesterday's demand
    player.inventory["Widget"] = 8
    player.yesterday_demand["Widget"] = 5

    # Set auto-restock
    player.stock_minimum_restock["Widget"] = (10, "Test Vendor")

    print(f"Player cash: ${player.cash}")
    print(f"Current stock: {player.inventory.get('Widget', 0)}")
    print(f"Yesterday demand: {player.yesterday_demand.get('Widget', 0)}")
    print(f"Minimum stock: 10")
    print(f"Vendor lead time: {vendor.lead_time}")
    print(f"Vendor has Widget: {'Widget' in vendor.items}")
    print(f"Vendor price: ${vendor.items.get('Widget', 'N/A')}")
    print()

    # Calculate what should happen
    lead_time_reduction = 0  # No upgrades
    effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
    adjusted_minimum = 10
    if effective_lead_time > 0:
        adjusted_minimum = 10 + 5

    print(f"Effective lead time: {effective_lead_time}")
    print(f"Adjusted minimum: {adjusted_minimum}")
    print(f"Should order: {adjusted_minimum - 8} units")
    print()

    # Test vendor.get_price
    print(f"Testing vendor.get_price('Widget', 7): {vendor.get_price('Widget', 7)}")
    print()

    # Check if Widget is packaged (size < 5, not Luxury)
    print(f"Item size: {item.size}")
    print(f"Item category: {item.category}")
    print(f"Is packaged: {item.size < 5.0 and item.category != 'Luxury'}")
    print()

    # Execute restock
    print("Executing auto-restock...")
    cash_before = player.cash
    purchases, size_used = execute_stock_minimum_restock(player, game_state)

    print(f"Purchases: {purchases}")
    print(f"Size used: {size_used}")
    print(f"Final inventory: {player.inventory.get('Widget', 0)}")
    print(f"Final cash: ${player.cash}")
    print(f"Cash spent: ${cash_before - player.cash}")
    print(f"Pending deliveries: {player.pending_deliveries}")

if __name__ == "__main__":
    main()
