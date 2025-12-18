"""Test warehousing system"""
import sys
sys.path.insert(0, '/home/user/economy-sim')

from economy_sim import (
    GameState, GameConfig, Player, Warehouse,
    create_players, PRODUCT_CATALOG
)

print("=" * 70)
print("Warehousing System Test")
print("=" * 70)

try:
    # Test 1: Create player and check initial warehouse
    print("\n1. Testing initial warehouse setup...")
    player = Player(name="TestPlayer", cash=50000.0, is_human=True)
    print(f"✓ Player created with {len(player.warehouses)} warehouse(s)")
    print(f"  Warehouse 1: Level {player.warehouses[0].level}, {player.warehouses[0].workers} workers")
    print(f"  Max inventory: {player.get_max_inventory()} items")
    assert len(player.warehouses) == 1, "Should start with 1 warehouse"
    assert player.warehouses[0].level == 1, "Initial warehouse should be level 1"
    assert player.get_max_inventory() == 500, "Max inventory should be 500 with 1 level-1 warehouse"

    # Test 2: Hire warehouse worker
    print("\n2. Testing warehouse worker hiring...")
    initial_cash = player.cash
    success = player.hire_warehouse_worker(0)
    print(f"✓ Hired worker: {success}")
    print(f"  Cash: ${initial_cash:.2f} → ${player.cash:.2f}")
    print(f"  Workers in warehouse 1: {player.warehouses[0].workers}/5")
    assert success, "Should be able to hire worker"
    assert player.cash == initial_cash - 500.0, "Cost should be $500"
    assert player.warehouses[0].workers == 1, "Should have 1 worker"
    assert player.get_max_inventory() == 800, "Max inventory should be 500 (warehouse) + 300 (worker)"

    # Test 3: Hire multiple workers (max 5 per warehouse)
    print("\n3. Testing max workers per warehouse (5)...")
    for i in range(4):
        success = player.hire_warehouse_worker(0)
        print(f"  Hired worker {i + 2}: {success}")
    print(f"✓ Workers in warehouse 1: {player.warehouses[0].workers}/5")
    assert player.warehouses[0].workers == 5, "Should have max 5 workers"

    # Try to hire a 6th worker (should fail)
    success = player.hire_warehouse_worker(0)
    print(f"  Tried to hire 6th worker: {success} (should be False)")
    assert not success, "Should not be able to hire more than 5 workers"

    # Test 4: Upgrade warehouse
    print("\n4. Testing warehouse upgrade...")
    player.cash = 50000.0  # Reset cash
    initial_level = player.warehouses[0].level
    total_level_before = player.get_total_warehouse_level()
    upgrade_cost = 5000.0 * total_level_before
    print(f"  Total warehouse level: {total_level_before}")
    print(f"  Upgrade cost: ${upgrade_cost:.2f}")

    initial_cash = player.cash
    success = player.upgrade_warehouse(0)
    print(f"✓ Upgrade successful: {success}")
    print(f"  Warehouse 1 level: {initial_level} → {player.warehouses[0].level}")
    print(f"  Cash: ${initial_cash:.2f} → ${player.cash:.2f}")
    assert success, "Should be able to upgrade warehouse"
    assert player.warehouses[0].level == 2, "Should be level 2 now"
    assert player.cash == initial_cash - upgrade_cost, "Should deduct upgrade cost"

    # Verify capacity increase
    expected_capacity = (500 * 2) + (5 * 300)  # 2 levels * 500 + 5 workers * 300
    print(f"  Max inventory: {player.get_max_inventory()} (expected {expected_capacity})")
    assert player.get_max_inventory() == expected_capacity, "Max inventory should reflect new level and workers"

    # Test 5: Buy new warehouse
    print("\n5. Testing buying new warehouses...")
    player.cash = 300000.0  # Reset cash with enough for all warehouses

    # First warehouse costs 1 * 20000 = 20000
    initial_count = len(player.warehouses)
    cost1 = 20000.0 * initial_count
    print(f"  Current warehouses: {initial_count}")
    print(f"  Cost to buy warehouse: ${cost1:.2f}")

    initial_cash = player.cash
    success = player.buy_warehouse()
    assert success, "Should be able to buy 2nd warehouse"
    print(f"✓ Bought 2nd warehouse")
    print(f"  Warehouses: {initial_count} → {len(player.warehouses)}")
    print(f"  Cash: ${initial_cash:.2f} → ${player.cash:.2f}")
    assert len(player.warehouses) == 2, "Should have 2 warehouses"

    # Buy 3rd and 4th warehouses
    player.buy_warehouse()
    player.buy_warehouse()
    print(f"  Bought 3rd and 4th warehouses")
    print(f"  Total warehouses: {len(player.warehouses)}/4")
    assert len(player.warehouses) == 4, "Should have max 4 warehouses"

    # Try to buy 5th warehouse (should fail)
    success = player.buy_warehouse()
    assert not success, "Should not be able to buy more than 4 warehouses"
    print(f"✓ Tried to buy 5th warehouse: {success} (should be False)")

    # Test 6: Max warehouse level
    print("\n6. Testing max warehouse level (10)...")
    player.cash = 1000000.0  # Lots of cash
    for i in range(9):  # Upgrade from level 2 to level 10
        success = player.upgrade_warehouse(0)
        if not success:
            print(f"  Upgrade failed at level {player.warehouses[0].level}")
            break

    print(f"✓ Warehouse 1 final level: {player.warehouses[0].level}/10")
    assert player.warehouses[0].level == 10, "Should reach max level 10"

    # Try to upgrade beyond level 10 (should fail)
    success = player.upgrade_warehouse(0)
    assert not success, "Should not be able to upgrade beyond level 10"
    print(f"  Tried to upgrade beyond level 10: {success} (should be False)")

    # Test 7: Wage payment
    print("\n7. Testing wage payment...")
    players = create_players(["Alice"], starting_cash=10000.0)
    test_player = players[0]

    # Hire 2 workers and 1 marketing agent
    test_player.cash = 5000.0
    test_player.hire_warehouse_worker(0)
    test_player.hire_warehouse_worker(0)
    test_player.cash = 5000.0
    test_player.store_level = 5
    test_player.hire_employee("marketing_agent")

    print(f"  Workers: {sum(w.workers for w in test_player.warehouses)}")
    print(f"  Marketing agents: {test_player.marketing_agents}")

    # Pay wages on day 30
    wages_paid = test_player.pay_monthly_wages(30)
    print(f"  Wages on day 30: ${wages_paid:.2f}")
    expected_wages = (2 * 500.0) + (1 * 1000.0)  # 2 workers * 500 + 1 agent * 1000
    assert wages_paid == expected_wages, f"Wages should be ${expected_wages:.2f}"
    print(f"✓ Wage calculation correct")

    # Wages should be 0 if called again before day 60
    wages_paid = test_player.pay_monthly_wages(35)
    print(f"  Wages on day 35: ${wages_paid:.2f} (should be 0)")
    assert wages_paid == 0, "Should not pay wages before 30 days have passed"

    print("\n" + "=" * 70)
    print("✓ All warehousing tests passed!")
    print("=" * 70)

except AssertionError as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
