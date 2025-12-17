#!/usr/bin/env python3
"""Test the specialty score system."""

from economy_sim import (
    Item, Player, calculate_specialty_score,
    SPECIALTY_SCORE_THRESHOLDS
)

def test_specialty_score():
    """Test that specialty score calculates correctly."""

    # Create some test items
    items_by_name = {
        "Bread": Item("Bread", 2.0, 5.0, "Food & Groceries"),
        "Milk": Item("Milk", 3.0, 6.0, "Food & Groceries"),
        "Eggs": Item("Eggs", 2.5, 5.5, "Food & Groceries"),
        "Cheese": Item("Cheese", 4.0, 8.0, "Food & Groceries"),
        "Butter": Item("Butter", 3.5, 7.0, "Food & Groceries"),
        "Rice": Item("Rice", 5.0, 10.0, "Food & Groceries"),
        "Coffee": Item("Coffee", 6.0, 12.0, "Food & Groceries"),
        "Tea": Item("Tea", 3.0, 6.5, "Food & Groceries"),
        "Sugar": Item("Sugar", 2.0, 4.5, "Food & Groceries"),
        "Salt": Item("Salt", 1.0, 2.5, "Food & Groceries"),
        "Gaming Console": Item("Gaming Console", 200.0, 400.0, "Gaming"),
        "4K TV": Item("4K TV", 300.0, 600.0, "Luxury"),
        "Bananas": Item("Bananas", 1.5, 3.5, "Fresh Produce"),
    }

    # Test Case 1: Empty inventory - should have 0 multiplier
    print("\nTest Case 1: Empty Inventory")
    player1 = Player("Player1", cash=10000)
    mult, counts, cat_mults = calculate_specialty_score(player1, items_by_name)
    print(f"  Multiplier: {mult} (expected: 0)")
    print(f"  Category counts: {counts}")
    print(f"  Category multipliers: {cat_mults}")
    assert mult == 0, "Empty inventory should have 0 multiplier"
    print("  ✓ PASSED")

    # Test Case 2: 10 Food & Groceries items - should trigger first threshold (1.2x)
    print("\nTest Case 2: 10 Food & Groceries items")
    player2 = Player("Player2", cash=10000)
    for i, item_name in enumerate(list(items_by_name.keys())[:10]):
        if items_by_name[item_name].category == "Food & Groceries":
            player2.inventory[item_name] = 5  # Stock 5 units

    mult, counts, cat_mults = calculate_specialty_score(player2, items_by_name)
    print(f"  Multiplier: {mult} (expected: 1.2)")
    print(f"  Category counts: {counts}")
    print(f"  Category multipliers: {cat_mults}")
    assert mult == 1.2, f"10 Food & Groceries should give 1.2x bonus, got {mult}"
    print("  ✓ PASSED")

    # Test Case 3: 5 Gaming items - should trigger Gaming threshold (1.5x)
    print("\nTest Case 3: 5 Gaming items")
    player3 = Player("Player3", cash=10000)
    # Add Gaming Console 5 times (simulating 5 different gaming items)
    # For this test, we'll just add it once since we only have one gaming item
    player3.inventory["Gaming Console"] = 5

    # Actually, let's create 5 different gaming items
    for i in range(5):
        item_name = f"Game {i+1}"
        items_by_name[item_name] = Item(item_name, 30.0, 60.0, "Gaming")
        player3.inventory[item_name] = 1

    mult, counts, cat_mults = calculate_specialty_score(player3, items_by_name)
    print(f"  Multiplier: {mult} (expected: 1.5)")
    print(f"  Category counts: {counts}")
    print(f"  Category multipliers: {cat_mults}")
    assert mult == 1.5, f"5 Gaming items should give 1.5x bonus, got {mult}"
    print("  ✓ PASSED")

    # Test Case 4: Multiple categories - additive bonuses
    print("\nTest Case 4: Multiple categories (additive)")
    player4 = Player("Player4", cash=10000)

    # Add 10 Food & Groceries (1.2x)
    for i in range(10):
        item_name = f"Food {i+1}"
        items_by_name[item_name] = Item(item_name, 5.0, 10.0, "Food & Groceries")
        player4.inventory[item_name] = 1

    # Add 5 Gaming (1.5x)
    for i in range(5):
        item_name = f"Game {i+1}"
        player4.inventory[item_name] = 1  # Already created above

    mult, counts, cat_mults = calculate_specialty_score(player4, items_by_name)
    print(f"  Multiplier: {mult} (expected: 2.7 = 1.2 + 1.5)")
    print(f"  Category counts: {counts}")
    print(f"  Category multipliers: {cat_mults}")
    assert mult == 2.7, f"10 Food + 5 Gaming should give 2.7x total (1.2 + 1.5), got {mult}"
    print("  ✓ PASSED")

    # Test Case 5: Multiple thresholds in same category
    print("\nTest Case 5: Multiple thresholds in same category")
    player5 = Player("Player5", cash=10000)

    # Add 30 Food & Groceries (should trigger both 10 and 30 thresholds)
    for i in range(30):
        item_name = f"Food Item {i+1}"
        items_by_name[item_name] = Item(item_name, 5.0, 10.0, "Food & Groceries")
        player5.inventory[item_name] = 1

    mult, counts, cat_mults = calculate_specialty_score(player5, items_by_name)
    print(f"  Multiplier: {mult} (expected: 2.7 = 1.2 + 1.5)")
    print(f"  Category counts: {counts}")
    print(f"  Category multipliers: {cat_mults}")
    # Food & Groceries thresholds: [(10, 1.2), (30, 1.5), (60, 2.5)]
    # With 30 items, should get 1.2 + 1.5 = 2.7
    assert mult == 2.7, f"30 Food & Groceries should give 2.7x total (1.2 + 1.5), got {mult}"
    print("  ✓ PASSED")

    print("\n🎉 All specialty score tests PASSED!")

if __name__ == "__main__":
    test_specialty_score()
