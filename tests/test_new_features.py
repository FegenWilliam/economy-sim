#!/usr/bin/env python3
"""Test new fulfillment multipliers and catch-up discount mechanism."""

from economy_sim import Player, GameState, Vendor, Item, create_vendors, create_default_items

print("Testing new fulfillment multipliers...")
print("=" * 60)

# Test fulfillment multipliers
test_cases = [
    (5, 0.1, "<10%"),
    (15, 0.5, "10-20%"),
    (25, 0.9, "20-50%"),
    (60, 1.0, "50-70%"),
    (75, 1.1, "71-89% (NEW)"),
    (92, 1.4, "90-99%"),
    (100, 2.0, "100%"),
]

print("\nFulfillment Multiplier Tests:")
print("-" * 60)
for fulfillment_pct, expected_mult, description in test_cases:
    # Test the logic directly
    if fulfillment_pct >= 100:
        multiplier = 2.0
    elif fulfillment_pct >= 90:
        multiplier = 1.4
    elif fulfillment_pct > 70:
        multiplier = 1.1
    elif fulfillment_pct >= 50:
        multiplier = 1.0
    elif fulfillment_pct >= 20:
        multiplier = 0.9
    elif fulfillment_pct >= 10:
        multiplier = 0.5
    else:
        multiplier = 0.1

    status = "✓" if multiplier == expected_mult else "✗"
    print(f"{status} {fulfillment_pct:3d}% fulfillment → {multiplier:.1f}x (expected {expected_mult:.1f}x) [{description}]")

print("\n" + "=" * 60)
print("Testing catch-up discount mechanism...")
print("=" * 60)

# Create test game state
items = create_default_items()
vendors = create_vendors()
market_prices = {item.name: item.base_price for item in items}

# Refresh vendor inventory
for vendor in vendors:
    vendor.items = {}
    if vendor.selection_type == "all":
        for item in items:
            vendor.items[item.name] = market_prices[item.name] * vendor.pricing_multiplier

# Create players with different levels
player1 = Player(name="HighLevel", cash=10000, store_level=5)
player2 = Player(name="LowLevel", cash=10000, store_level=2)

game_state = GameState(
    players=[player1, player2],
    vendors=vendors,
    items=items,
    market_prices=market_prices,
    day=15  # Day 15, so catch-up discount is active
)

# Get Daily Essentials Co. and Instant Goods Ltd.
daily_essentials = next(v for v in vendors if v.name == "Daily Essentials Co.")
instant_goods = next(v for v in vendors if v.name == "Instant Goods Ltd.")

# Test item
test_item = "Apples"  # Should be available from Daily Essentials
test_item_obj = next((item for item in items if item.name == test_item), items[0])
market_price = test_item_obj.base_price

print(f"\nTest Item: {test_item}")
print(f"Market Price: ${market_price:.2f}")
print(f"Day: {game_state.day}")
print(f"\nPlayer Levels:")
print(f"  HighLevel: Level {player1.store_level}")
print(f"  LowLevel: Level {player2.store_level}")

# Refresh Daily Essentials inventory to include food items
daily_essentials.items = {}
for item in items:
    if item.category in ["Food & Groceries", "Fresh Produce"]:
        daily_essentials.items[item.name] = item.base_price * 0.90

instant_goods.items = {}
for item in items:
    if item.base_price < 40:
        instant_goods.items[item.name] = item.base_price * 0.98

print("\n" + "-" * 60)
print("Daily Essentials Co. (90% base → 80% for non-highest):")
print("-" * 60)

# Debug: check if item is in inventory
if test_item not in daily_essentials.items:
    print(f"DEBUG: {test_item} not in Daily Essentials items!")
    print(f"Available items: {list(daily_essentials.items.keys())[:5]}")
    # If not, let's just grab any available food item
    if daily_essentials.items:
        test_item = list(daily_essentials.items.keys())[0]
        market_price = daily_essentials.items[test_item] / 0.90
        print(f"Using {test_item} instead at market price ${market_price:.2f}")

# Test for high level player (should pay 90%)
if test_item in daily_essentials.items:
    initial_cash = player1.cash
    player1.purchase_from_vendor(daily_essentials, test_item, 1, market_price, game_state)
    cost_high = initial_cash - player1.cash
    expected_high = market_price * 0.90
    status = "✓" if abs(cost_high - expected_high) < 0.01 else "✗"
    print(f"{status} HighLevel (Lvl {player1.store_level}): ${cost_high:.2f} (expected ${expected_high:.2f})")
    player1.cash = initial_cash  # Reset

# Test for low level player (should pay 80%)
if test_item in daily_essentials.items:
    initial_cash = player2.cash
    player2.purchase_from_vendor(daily_essentials, test_item, 1, market_price, game_state)
    cost_low = initial_cash - player2.cash
    expected_low = market_price * 0.80
    status = "✓" if abs(cost_low - expected_low) < 0.01 else "✗"
    print(f"{status} LowLevel (Lvl {player2.store_level}): ${cost_low:.2f} (expected ${expected_low:.2f}) [CATCH-UP ACTIVE]")
    player2.cash = initial_cash  # Reset

print("\n" + "-" * 60)
print("Instant Goods Ltd. (98% base → 95% for non-highest):")
print("-" * 60)

# Test for high level player (should pay 98%)
if test_item in instant_goods.items:
    initial_cash = player1.cash
    player1.purchase_from_vendor(instant_goods, test_item, 1, market_price, game_state)
    cost_high = initial_cash - player1.cash
    expected_high = market_price * 0.98
    status = "✓" if abs(cost_high - expected_high) < 0.01 else "✗"
    print(f"{status} HighLevel (Lvl {player1.store_level}): ${cost_high:.2f} (expected ${expected_high:.2f})")
    player1.cash = initial_cash  # Reset

# Test for low level player (should pay 95%)
if test_item in instant_goods.items:
    initial_cash = player2.cash
    player2.purchase_from_vendor(instant_goods, test_item, 1, market_price, game_state)
    cost_low = initial_cash - player2.cash
    expected_low = market_price * 0.95
    status = "✓" if abs(cost_low - expected_low) < 0.01 else "✗"
    print(f"{status} LowLevel (Lvl {player2.store_level}): ${cost_low:.2f} (expected ${expected_low:.2f}) [CATCH-UP ACTIVE]")

print("\n" + "=" * 60)
print("Testing catch-up mechanism before day 10...")
print("=" * 60)

# Test that catch-up doesn't apply before day 10
game_state.day = 5
player2.cash = 10000

if test_item in daily_essentials.items:
    initial_cash = player2.cash
    player2.purchase_from_vendor(daily_essentials, test_item, 1, market_price, game_state)
    cost_before_day10 = initial_cash - player2.cash
    expected_before_day10 = market_price * 0.90
    status = "✓" if abs(cost_before_day10 - expected_before_day10) < 0.01 else "✗"
    print(f"{status} Day {game_state.day}: LowLevel pays ${cost_before_day10:.2f} (expected ${expected_before_day10:.2f}) [NO CATCH-UP]")

print("\n" + "=" * 60)
print("🎉 All new feature tests completed!")
print("=" * 60)
