"""Test save/load functionality for category adjacency data."""

import sys
import os
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from economy_sim import (
    Player, Item, GameState, GameConfig, Vendor,
    save_game, load_game,
    create_default_items, create_vendors
)


def test_save_load_category_adjacency_data():
    """Test that category sales history and items stocked today are saved and loaded correctly."""

    # Create a temporary save file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_save_file = f.name

    try:
        # Create a game state
        items = create_default_items()
        vendors = create_vendors()

        player1 = Player(name="TestPlayer1", cash=5000.0)
        player1.is_human = True

        # Add some category sales history
        player1.category_sales_history[1] = {
            "Electronics": 500.0,
            "Gaming": 200.0,
            "Food & Groceries": 100.0
        }
        player1.category_sales_history[2] = {
            "Electronics": 600.0,
            "Gaming": 250.0
        }
        player1.category_sales_history[3] = {
            "Electronics": 550.0,
            "Gaming": 300.0,
            "Fresh Produce": 50.0
        }

        # Add some items stocked today
        player1.items_stocked_today.add("Laptop")
        player1.items_stocked_today.add("Video Game")

        # Add some inventory
        player1.inventory = {"Laptop": 10, "Video Game": 5}
        player1.prices = {"Laptop": 950.0, "Video Game": 55.0}

        game_state = GameState(
            day=3,
            players=[player1],
            items=items,
            vendors=vendors,
            market_prices={item.name: item.base_price for item in items},
            config=GameConfig(),
            human_players=[player1]
        )

        # Save the game
        success = save_game(game_state, temp_save_file)
        assert success, "Save should succeed"
        print("✓ Game saved successfully")

        # Load the game
        loaded_state = load_game(temp_save_file)
        assert loaded_state is not None, "Load should succeed"
        print("✓ Game loaded successfully")

        # Verify the loaded player has the correct data
        loaded_player = loaded_state.players[0]

        # Check category sales history
        assert len(loaded_player.category_sales_history) == 3, f"Expected 3 days of history, got {len(loaded_player.category_sales_history)}"

        assert 1 in loaded_player.category_sales_history, "Day 1 should be in history"
        assert loaded_player.category_sales_history[1] == {
            "Electronics": 500.0,
            "Gaming": 200.0,
            "Food & Groceries": 100.0
        }, "Day 1 sales should match"

        assert 2 in loaded_player.category_sales_history, "Day 2 should be in history"
        assert loaded_player.category_sales_history[2] == {
            "Electronics": 600.0,
            "Gaming": 250.0
        }, "Day 2 sales should match"

        assert 3 in loaded_player.category_sales_history, "Day 3 should be in history"
        assert loaded_player.category_sales_history[3] == {
            "Electronics": 550.0,
            "Gaming": 300.0,
            "Fresh Produce": 50.0
        }, "Day 3 sales should match"

        print("✓ Category sales history preserved correctly")

        # Check items stocked today
        assert "Laptop" in loaded_player.items_stocked_today, "Laptop should be in items stocked today"
        assert "Video Game" in loaded_player.items_stocked_today, "Video Game should be in items stocked today"
        assert len(loaded_player.items_stocked_today) == 2, f"Expected 2 items stocked today, got {len(loaded_player.items_stocked_today)}"

        print("✓ Items stocked today preserved correctly")

        # Verify other data is still correct
        assert loaded_player.name == "TestPlayer1", "Player name should match"
        assert loaded_player.cash == 5000.0, "Cash should match"
        assert loaded_player.inventory == {"Laptop": 10, "Video Game": 5}, "Inventory should match"
        assert loaded_player.prices == {"Laptop": 950.0, "Video Game": 55.0}, "Prices should match"
        assert loaded_state.day == 3, "Day should match"

        print("✓ Other player data preserved correctly")

    finally:
        # Clean up temp file
        if os.path.exists(temp_save_file):
            os.remove(temp_save_file)

    print("\n✅ Save/load test for category adjacency data passed!")


def test_save_load_empty_history():
    """Test that empty category history is handled correctly."""

    # Create a temporary save file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_save_file = f.name

    try:
        # Create a game state with a player that has no history
        items = create_default_items()
        vendors = create_vendors()

        player1 = Player(name="NewPlayer", cash=10000.0)
        player1.is_human = True

        game_state = GameState(
            day=1,
            players=[player1],
            items=items,
            vendors=vendors,
            market_prices={item.name: item.base_price for item in items},
            config=GameConfig(),
            human_players=[player1]
        )

        # Save the game
        success = save_game(game_state, temp_save_file)
        assert success, "Save should succeed"

        # Load the game
        loaded_state = load_game(temp_save_file)
        assert loaded_state is not None, "Load should succeed"

        # Verify the loaded player has empty history
        loaded_player = loaded_state.players[0]
        assert len(loaded_player.category_sales_history) == 0, "History should be empty"
        assert len(loaded_player.items_stocked_today) == 0, "Items stocked today should be empty"

        print("✓ Empty history handled correctly")

    finally:
        # Clean up temp file
        if os.path.exists(temp_save_file):
            os.remove(temp_save_file)

    print("\n✅ Empty history save/load test passed!")


if __name__ == "__main__":
    print("Testing save/load for category adjacency data...\n")
    test_save_load_category_adjacency_data()
    print()
    test_save_load_empty_history()
    print("\n✅ All save/load tests passed!")
