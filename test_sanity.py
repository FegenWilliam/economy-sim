"""Sanity test - verify the system compiles and basic functions work"""
import sys
sys.path.insert(0, '/home/user/economy-sim')

from economy_sim import (
    GameState, GameConfig, Player, Customer, 
    create_players, create_customers, PRODUCT_CATALOG
)

print("=" * 60)
print("Sanity Test: Customer Specialization System")
print("=" * 60)

try:
    # Test 1: Create customers and check they can have specializations
    print("\n1. Creating customers...")
    customers = create_customers(5)
    print(f"✓ Created {len(customers)} customers")
    
    # Test 2: Roll specializations
    print("\n2. Rolling specializations...")
    for customer in customers:
        customer.roll_specializations(PRODUCT_CATALOG, {})
    
    spec_count = sum(1 for c in customers if c.specializations)
    print(f"✓ {spec_count}/{len(customers)} customers have specializations")
    
    for i, customer in enumerate(customers[:3]):
        print(f"  - {customer.name}: {customer.specializations}")
    
    # Test 3: Generate needs respecting specializations
    print("\n3. Testing generate_daily_needs with specializations...")
    customer = customers[0]
    needs = customer.generate_daily_needs(PRODUCT_CATALOG, {}, {})
    print(f"✓ Customer {customer.name} generated {len(needs)} needs")
    if needs:
        categories = set()
        for need in needs:
            for item in PRODUCT_CATALOG:
                if item.name == need.item_name:
                    categories.add(item.category)
                    break
        print(f"  Categories: {categories}")
    
    # Test 4: Create players
    print("\n4. Creating players...")
    players = create_players(["Alice", "Bob"], starting_cash=10000.0)
    print(f"✓ Created {len(players)} players: {[p.name for p in players]}")
    
    # Test 5: Create game state
    print("\n5. Creating game state...")
    game_state = GameState(
        day=1,
        players=players,
        customers=customers,
        items=PRODUCT_CATALOG,
        market_prices={item.name: item.base_price for item in PRODUCT_CATALOG},
        item_demand={item.name: 1.0 for item in PRODUCT_CATALOG}
    )
    print(f"✓ Created game state with day {game_state.day}")
    
    print("\n" + "=" * 60)
    print("✓ All sanity tests passed!")
    print("=" * 60)

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
