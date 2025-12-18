#!/usr/bin/env python3
"""
Test purchase_from_vendor directly.
"""

from economy_sim import GameState, Player, Vendor, Item, GameConfig

def main():
    print("Direct Purchase Test")
    print("=" * 60)

    # Create game state
    config = GameConfig()
    game_state = GameState(day=1, config=config)

    # Create a simple item
    item = Item(name="Widget", base_cost=5.0, base_price=10.0, category="Office Supplies", size=1.0)
    game_state.items = [item]
    game_state.market_prices = {"Widget": 10.0}

    # Create vendor
    vendor = Vendor(
        name="Test Vendor",
        items={"Widget": 5.0},
        lead_time=2
    )
    game_state.vendors = [vendor]

    # Create player
    player = Player(name="TestPlayer", cash=10000.0)
    player.inventory["Widget"] = 8

    print(f"Before purchase:")
    print(f"  Cash: ${player.cash}")
    print(f"  Inventory: {player.inventory}")
    print(f"  Pending deliveries: {player.pending_deliveries}")
    print()

    # Try to purchase
    print(f"Attempting to purchase 7 Widgets from {vendor.name}...")
    success = player.purchase_from_vendor(vendor, "Widget", 7, 10.0, game_state)

    print(f"Purchase success: {success}")
    print()

    print(f"After purchase:")
    print(f"  Cash: ${player.cash}")
    print(f"  Inventory: {player.inventory}")
    print(f"  Pending deliveries: {player.pending_deliveries}")

if __name__ == "__main__":
    main()
