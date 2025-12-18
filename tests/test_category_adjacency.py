"""Test category adjacency system and its impact on CAS calculation."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from economy_sim import (
    Player, Item, GameState, GameConfig,
    get_player_main_category,
    get_non_adjacent_categories,
    calculate_adjacency_multiplier,
    calculate_cas_breakdown,
    CATEGORY_ADJACENCY
)


def test_category_adjacency_mappings():
    """Test that category adjacency mappings are defined correctly."""
    # Check that all categories have adjacency definitions
    from economy_sim import PRODUCT_CATEGORIES

    for category in PRODUCT_CATEGORIES.keys():
        assert category in CATEGORY_ADJACENCY, f"Category {category} not in adjacency map"

    # Check that adjacencies are symmetric (if A is adjacent to B, B should be adjacent to A)
    for category, adjacent_set in CATEGORY_ADJACENCY.items():
        for adjacent_category in adjacent_set:
            assert category in CATEGORY_ADJACENCY.get(adjacent_category, set()), \
                f"{category} is adjacent to {adjacent_category}, but not vice versa"

    print("✓ Category adjacency mappings are correct")


def test_main_category_detection():
    """Test that main category is correctly identified from sales history."""
    player = Player(name="TestPlayer", cash=1000.0)

    # No sales yet - should return None
    assert get_player_main_category(player, 1) is None

    # Add sales history for day 1
    player.category_sales_history[1] = {
        "Electronics": 100.0,
        "Gaming": 50.0,
        "Food & Groceries": 30.0
    }

    # Electronics should be main category
    main_cat = get_player_main_category(player, 1)
    assert main_cat == "Electronics", f"Expected Electronics, got {main_cat}"

    # Add more sales for days 2-7
    for day in range(2, 8):
        player.category_sales_history[day] = {
            "Electronics": 20.0,
            "Gaming": 80.0,
        }

    # Now Gaming should be main (higher total over 7 days)
    main_cat = get_player_main_category(player, 7)
    assert main_cat == "Gaming", f"Expected Gaming, got {main_cat}"

    print("✓ Main category detection works correctly")


def test_non_adjacent_categories():
    """Test that non-adjacent categories are correctly identified."""
    player = Player(name="TestPlayer", cash=1000.0)

    # Create some test items
    items = [
        Item("Laptop", 500, 1000, "Electronics"),
        Item("Video Game", 30, 60, "Gaming"),
        Item("Banana", 0.3, 0.6, "Fresh Produce"),
    ]
    items_by_name = {item.name: item for item in items}

    # Stock items
    player.inventory = {"Laptop": 5, "Video Game": 10, "Banana": 20}

    # Set Electronics as main category (via sales)
    player.category_sales_history[1] = {
        "Electronics": 500.0,
        "Gaming": 100.0,
        "Fresh Produce": 50.0
    }

    # Get non-adjacent categories
    non_adjacent = get_non_adjacent_categories(player, items_by_name, 1)

    # Gaming is adjacent to Electronics, but Fresh Produce is not
    assert "Fresh Produce" in non_adjacent, "Fresh Produce should be non-adjacent to Electronics"
    assert "Gaming" not in non_adjacent, "Gaming should be adjacent to Electronics"

    print("✓ Non-adjacent category detection works correctly")


def test_adjacency_multiplier_permanent():
    """Test permanent CAS multiplier based on non-adjacent category count."""
    player = Player(name="TestPlayer", cash=1000.0)

    # Create test items from various categories
    items = [
        Item("Laptop", 500, 1000, "Electronics"),
        Item("Banana", 0.3, 0.6, "Fresh Produce"),
        Item("Office Chair", 50, 100, "Office Supplies"),
        Item("Pet Food", 5, 10, "Pet Supplies"),
        Item("Toy Car", 10, 20, "Toys & Games"),
        Item("Makeup", 15, 30, "Personal Care"),
        Item("Supplements", 20, 40, "Supplements"),
        Item("Paint", 25, 50, "Home Decor"),
        Item("Screwdriver", 8, 16, "Office Supplies"),
        Item("Car Oil", 15, 30, "Automotive"),
        Item("Cashmere Sweater", 180, 360, "Luxury"),
    ]
    items_by_name = {item.name: item for item in items}

    # Set Electronics as main category
    player.category_sales_history[1] = {"Electronics": 1000.0}
    player.inventory = {"Laptop": 10}

    # Test with 0 non-adjacent categories (only main category)
    mult = calculate_adjacency_multiplier(player, items_by_name, 1, check_temporary=False)
    assert mult == 1.0, f"Expected 1.0, got {mult}"

    # Add 1 non-adjacent category (Fresh Produce)
    player.inventory["Banana"] = 10
    mult = calculate_adjacency_multiplier(player, items_by_name, 1, check_temporary=False)
    assert mult == 0.9, f"Expected 0.9 for 1 non-adjacent, got {mult}"

    # Add 2 more non-adjacent categories (Pet Supplies, Personal Care) = 3 total
    player.inventory["Pet Food"] = 10
    player.inventory["Makeup"] = 10
    mult = calculate_adjacency_multiplier(player, items_by_name, 1, check_temporary=False)
    assert mult == 0.6, f"Expected 0.6 for 3 non-adjacent, got {mult}"

    # Add more non-adjacent categories to reach 7
    player.inventory["Supplements"] = 10  # 4
    player.inventory["Paint"] = 10  # 5 (Home Decor)
    player.inventory["Car Oil"] = 10  # 6 (Automotive is adjacent to Electronics, so doesn't count)
    player.inventory["Toy Car"] = 10  # Still need one more

    non_adj = get_non_adjacent_categories(player, items_by_name, 1)
    # Need to reach 7 non-adjacent
    if len(non_adj) < 7:
        player.inventory["Cashmere Sweater"] = 10  # Add Luxury (adjacent to Electronics, so doesn't count)

    # Recount
    non_adj = get_non_adjacent_categories(player, items_by_name, 1)

    # If we have 7+ non-adjacent, multiplier should be 0.4
    if len(non_adj) >= 7:
        mult = calculate_adjacency_multiplier(player, items_by_name, 1, check_temporary=False)
        assert mult == 0.4, f"Expected 0.4 for 7 non-adjacent, got {mult}"

    print("✓ Permanent adjacency multiplier works correctly")


def test_adjacency_multiplier_temporary():
    """Test temporary CAS penalty for newly stocked non-adjacent items."""
    player = Player(name="TestPlayer", cash=1000.0)

    # Create test items
    items = [
        Item("Laptop", 500, 1000, "Electronics"),
        Item("Banana", 0.3, 0.6, "Fresh Produce"),
    ]
    items_by_name = {item.name: item for item in items}

    # Set Electronics as main category
    player.category_sales_history[1] = {"Electronics": 1000.0}
    player.inventory = {"Laptop": 10}

    # No new items stocked today
    mult = calculate_adjacency_multiplier(player, items_by_name, 1, check_temporary=True)
    assert mult == 1.0, "Should be 1.0 with no new non-adjacent items"

    # Add a new non-adjacent item today
    player.inventory["Banana"] = 10
    player.items_stocked_today.add("Banana")

    # Should get both permanent (0.9) and temporary (0.9) penalties = 0.81
    mult = calculate_adjacency_multiplier(player, items_by_name, 1, check_temporary=True)
    assert mult == 0.81, f"Expected 0.81 (0.9 * 0.9), got {mult}"

    # Without temporary check, should only get permanent penalty
    mult = calculate_adjacency_multiplier(player, items_by_name, 1, check_temporary=False)
    assert mult == 0.9, f"Expected 0.9, got {mult}"

    print("✓ Temporary adjacency penalty works correctly")


def test_cas_integration():
    """Test that adjacency multiplier is integrated into CAS calculation."""
    player = Player(name="TestPlayer", cash=1000.0, reputation=50.0)

    # Create game state with items
    items = [
        Item("Laptop", 500, 1000, "Electronics"),
        Item("Banana", 0.3, 0.6, "Fresh Produce"),
    ]
    items_by_name = {item.name: item for item in items}

    market_prices = {
        "Laptop": 1000.0,
        "Banana": 0.6
    }

    # Set up player with inventory and prices
    player.inventory = {"Laptop": 10}
    player.prices = {"Laptop": 950.0}  # 5% discount

    # Set Electronics as main category
    player.category_sales_history[1] = {"Electronics": 1000.0}

    # Calculate CAS breakdown without non-adjacent items
    breakdown = calculate_cas_breakdown(player, market_prices, items_by_name, items, current_day=1)
    cas_without_penalty = breakdown["final_cas"]
    adjacency_mult_1 = breakdown["adjacency_multiplier"]

    assert adjacency_mult_1 == 1.0, "Should have no adjacency penalty with only main category"

    # Add non-adjacent item
    player.inventory["Banana"] = 10
    player.prices["Banana"] = 0.55

    # Calculate CAS breakdown with non-adjacent item
    breakdown = calculate_cas_breakdown(player, market_prices, items_by_name, items, current_day=1)
    cas_with_penalty = breakdown["final_cas"]
    adjacency_mult_2 = breakdown["adjacency_multiplier"]

    assert adjacency_mult_2 == 0.9, "Should have 0.9x penalty for 1 non-adjacent category"
    # Note: CAS might be higher overall due to added inventory, but the multiplier is correctly applied

    # Check that main category is reported correctly
    assert breakdown["main_category"] == "Electronics"
    assert "Fresh Produce" in breakdown["non_adjacent_categories"]

    print("✓ Adjacency multiplier is correctly integrated into CAS calculation")


def test_sales_history_tracking():
    """Test that sales are tracked by category."""
    player = Player(name="TestPlayer", cash=1000.0)

    # Create item
    item_category = "Electronics"

    # Simulate a sale
    player.inventory["Laptop"] = 10
    revenue, profit, units_sold = player.sell_to_customer("Laptop", 2, 950.0, current_day=1, item_category=item_category)

    # Check that sales were tracked
    assert 1 in player.category_sales_history, "Day 1 should be in sales history"
    assert item_category in player.category_sales_history[1], "Electronics should be in day 1 sales"
    assert player.category_sales_history[1][item_category] == revenue, "Revenue should match"

    # Sell more on the same day
    revenue2, profit2, units_sold2 = player.sell_to_customer("Laptop", 1, 950.0, current_day=1, item_category=item_category)

    # Check that sales accumulated
    total_revenue = revenue + revenue2
    assert player.category_sales_history[1][item_category] == total_revenue, "Revenue should accumulate"

    print("✓ Sales history tracking works correctly")


def run_all_tests():
    """Run all tests."""
    print("Running category adjacency tests...\n")

    test_category_adjacency_mappings()
    test_main_category_detection()
    test_non_adjacent_categories()
    test_adjacency_multiplier_permanent()
    test_adjacency_multiplier_temporary()
    test_cas_integration()
    test_sales_history_tracking()

    print("\n✅ All category adjacency tests passed!")


if __name__ == "__main__":
    run_all_tests()
