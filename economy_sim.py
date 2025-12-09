# econ_sim.py

"""
Economic simulation where players compete to capture customers
by selling items. Each customer has daily item needs that are
randomly generated. A day counter tracks overall progress.

This file is mostly TODOs to be filled in by an AI code assistant.
"""


from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random


# -------------------------------------------------------------------
# Core data models
# -------------------------------------------------------------------

@dataclass
class Item:
    """An item that can be produced and sold."""
    name: str
    base_cost: float  # cost to produce 1 unit
    base_price: float  # default selling price (can be overridden by players)


@dataclass
class Vendor:
    """A vendor that sells items to players at wholesale prices."""
    name: str
    pricing_multiplier: float = 1.0  # Multiplier applied to market price (e.g., 0.7 = 70% of market)
    selection_type: str = "all"  # "random_daily", "price_threshold", "all"
    selection_params: float = 0.0  # For random_daily: count of items. For price_threshold: max price
    items: Dict[str, float] = field(default_factory=dict)  # item_name -> wholesale_price (refreshed daily)

    def get_price(self, item_name: str) -> Optional[float]:
        """Get the wholesale price for an item from this vendor."""
        return self.items.get(item_name)


@dataclass
class Player:
    """Represents a company / player in the economic simulation."""
    name: str
    cash: float = 0.0
    inventory: Dict[str, int] = field(default_factory=dict)  # item_name -> quantity
    prices: Dict[str, float] = field(default_factory=dict)   # item_name -> selling price

    def set_price(self, item_name: str, price: float) -> None:
        """
        Set the selling price for an item in the player's store.
        """
        if price < 0:
            raise ValueError(f"Price cannot be negative: {price}")
        self.prices[item_name] = price

    def produce_item(self, item: Item, quantity: int) -> None:
        """
        Produce items by spending cash to increase inventory.

        Raises ValueError if player doesn't have enough cash.
        """
        if quantity < 0:
            raise ValueError(f"Quantity cannot be negative: {quantity}")

        total_cost = item.base_cost * quantity

        if self.cash < total_cost:
            raise ValueError(
                f"{self.name} cannot afford to produce {quantity} {item.name}. "
                f"Cost: ${total_cost:.2f}, Available: ${self.cash:.2f}"
            )

        self.cash -= total_cost
        self.inventory[item.name] = self.inventory.get(item.name, 0) + quantity

    def sell_to_customer(self, item_name: str, quantity: int, unit_price: float) -> float:
        """
        Attempt to sell 'quantity' units of 'item_name' at 'unit_price'.
        Returns the total revenue actually realized.
        """
        available = self.inventory.get(item_name, 0)
        units_sold = min(quantity, available)

        if units_sold > 0:
            self.inventory[item_name] -= units_sold
            revenue = units_sold * unit_price
            self.cash += revenue
            return revenue

        return 0.0

    def purchase_from_vendor(self, vendor: 'Vendor', item_name: str, quantity: int) -> bool:
        """
        Purchase items from a vendor at their wholesale price.
        Returns True if successful, False if not enough cash.
        """
        if quantity <= 0:
            return False

        vendor_price = vendor.get_price(item_name)
        if vendor_price is None:
            return False

        total_cost = vendor_price * quantity

        if self.cash < total_cost:
            return False

        self.cash -= total_cost
        self.inventory[item_name] = self.inventory.get(item_name, 0) + quantity
        return True


@dataclass
class CustomerNeed:
    """Represents the need of a single item by a customer for a day."""
    item_name: str
    quantity: int


@dataclass
class Customer:
    """Represents a customer with daily needs for items."""
    name: str
    customer_type: str = "medium"  # "low", "medium", or "high"
    budget: float = 0.0

    def __post_init__(self):
        """Set budget based on customer type if not already set."""
        if self.budget == 0.0:
            if self.customer_type == "low":
                self.budget = 20.0
            elif self.customer_type == "medium":
                self.budget = 50.0
            elif self.customer_type == "high":
                self.budget = 100.0

    def generate_daily_needs(self, available_items: List[Item]) -> List[CustomerNeed]:
        """
        Generate a random set of item needs for the day based on budget.

        Randomly selects items and quantities, ensuring total cost doesn't exceed budget.
        """
        if not available_items:
            return []

        needs = []
        remaining_budget = self.budget

        # Decide how many different item types to buy (1 to 3)
        num_item_types = random.randint(1, min(3, len(available_items)))
        selected_items = random.sample(available_items, num_item_types)

        for item in selected_items:
            # Calculate max quantity we can afford
            max_affordable = int(remaining_budget / item.base_price)
            if max_affordable > 0:
                # Buy between 1 and min(5, max_affordable) units
                quantity = random.randint(1, min(5, max_affordable))
                needs.append(CustomerNeed(item_name=item.name, quantity=quantity))
                remaining_budget -= quantity * item.base_price

        return needs

    def choose_supplier(
        self,
        players: List[Player],
        item_name: str,
        quantity: int
    ) -> Optional[Player]:
        """
        Decide which player to buy from for a given item and quantity.

        Chooses the player with the lowest price who has at least some stock.
        Breaks ties randomly.
        """
        candidates = []

        for player in players:
            # Check if player has this item in stock
            if player.inventory.get(item_name, 0) > 0:
                # Check if player has set a price
                if item_name in player.prices:
                    candidates.append((player, player.prices[item_name]))

        if not candidates:
            return None

        # Find the lowest price
        min_price = min(price for _, price in candidates)

        # Get all players with the lowest price
        best_players = [player for player, price in candidates if price == min_price]

        # Return random player from best options
        return random.choice(best_players)


# -------------------------------------------------------------------
# Game / simulation engine
# -------------------------------------------------------------------

@dataclass
class GameConfig:
    """Configuration for the economic simulation."""
    starting_cash: float = 1000.0
    num_days: int = 30
    customers_per_day: int = 10
    # TODO: add more config options if needed (e.g. random seed, max inventory, etc.)


@dataclass
class GameState:
    """Holds the entire current state of the simulation."""
    day: int = 1
    players: List[Player] = field(default_factory=list)
    customers: List[Customer] = field(default_factory=list)
    items: List[Item] = field(default_factory=list)
    vendors: List[Vendor] = field(default_factory=list)
    market_prices: Dict[str, float] = field(default_factory=dict)  # item_name -> current market price
    config: GameConfig = field(default_factory=GameConfig)
    human_player: Optional[Player] = None  # The human-controlled player

    def get_item(self, item_name: str) -> Optional[Item]:
        """
        Look up an item by its name in self.items.
        Returns the Item or None if not found.
        """
        for item in self.items:
            if item.name == item_name:
                return item
        return None

    def get_vendor(self, vendor_name: str) -> Optional[Vendor]:
        """
        Look up a vendor by name.
        Returns the Vendor or None if not found.
        """
        for vendor in self.vendors:
            if vendor.name == vendor_name:
                return vendor
        return None


# -------------------------------------------------------------------
# Initialization helpers
# -------------------------------------------------------------------

def create_default_items() -> List[Item]:
    """
    Create some default items for the simulation.

    TODO:
    - Adjust items, base_cost, and base_price as desired
    """
    return [
        Item(name="Bread", base_cost=2.0, base_price=5.0),
        Item(name="Milk", base_cost=3.0, base_price=6.0),
        Item(name="Fruit", base_cost=1.0, base_price=4.0),
    ]


def create_players(names: List[str], starting_cash: float) -> List[Player]:
    """
    Create players with default inventory and starting cash.

    TODO:
    - Optionally pre-fill inventory
    - Optionally set default prices equal to item.base_price
    """
    players: List[Player] = []
    for name in names:
        players.append(Player(name=name, cash=starting_cash))
    return players


def create_customers(num_customers: int) -> List[Customer]:
    """
    Create a list of customers with random types (low, medium, high spender).
    """
    customers = []
    customer_types = ["low", "medium", "high"]

    for i in range(num_customers):
        customer_type = random.choice(customer_types)
        customers.append(Customer(name=f"Customer_{i+1}", customer_type=customer_type))

    return customers


def create_vendors() -> List[Vendor]:
    """
    Create 5 vendors with different pricing and selection strategies.

    Vendor inventory is refreshed daily based on their selection type.
    """
    vendors = []

    # Vendor 1: 70% of market price, 1 random item per day
    vendors.append(Vendor(
        name="Lucky Deal Trader",
        pricing_multiplier=0.70,
        selection_type="random_daily",
        selection_params=1  # 1 item
    ))

    # Vendor 2: 95% of market price, 5 random items per day
    vendors.append(Vendor(
        name="Discount Wholesale Co.",
        pricing_multiplier=0.95,
        selection_type="random_daily",
        selection_params=5  # 5 items
    ))

    # Vendor 3: Market price, all items under $20 market price
    vendors.append(Vendor(
        name="Budget Goods Ltd.",
        pricing_multiplier=1.0,
        selection_type="price_threshold",
        selection_params=20.0  # $20 threshold
    ))

    # Vendor 4: 105% of market price, all items under $50 market price
    vendors.append(Vendor(
        name="Premium Select Inc.",
        pricing_multiplier=1.05,
        selection_type="price_threshold",
        selection_params=50.0  # $50 threshold
    ))

    # Vendor 5: 110% of market price, all items available
    vendors.append(Vendor(
        name="Universal Supply Corp.",
        pricing_multiplier=1.10,
        selection_type="all",
        selection_params=0  # No limit
    ))

    return vendors


def refresh_vendor_inventory(vendors: List[Vendor], items: List[Item], market_prices: Dict[str, float]) -> None:
    """
    Refresh vendor inventory based on their selection type and current market prices.

    This should be called at the start of each day.
    """
    for vendor in vendors:
        vendor.items.clear()

        if vendor.selection_type == "random_daily":
            # Select N random items
            num_items = int(vendor.selection_params)
            if num_items > 0 and items:
                selected_items = random.sample(items, min(num_items, len(items)))
                for item in selected_items:
                    market_price = market_prices.get(item.name, item.base_price)
                    vendor.items[item.name] = market_price * vendor.pricing_multiplier

        elif vendor.selection_type == "price_threshold":
            # Select all items where market price is under threshold
            price_threshold = vendor.selection_params
            for item in items:
                market_price = market_prices.get(item.name, item.base_price)
                if market_price < price_threshold:
                    vendor.items[item.name] = market_price * vendor.pricing_multiplier

        elif vendor.selection_type == "all":
            # Include all items
            for item in items:
                market_price = market_prices.get(item.name, item.base_price)
                vendor.items[item.name] = market_price * vendor.pricing_multiplier


def initialize_market_prices(items: List[Item]) -> Dict[str, float]:
    """
    Initialize market prices based on item base prices.
    """
    market_prices = {}
    for item in items:
        market_prices[item.name] = item.base_price
    return market_prices


# -------------------------------------------------------------------
# Market dynamics
# -------------------------------------------------------------------

def apply_daily_price_fluctuation(market_prices: Dict[str, float], items: List[Item]) -> None:
    """
    Apply daily price fluctuation to 1-2 random items.
    Prices fluctuate by 5-10% up or down.
    """
    if not items:
        return

    # Choose 1-2 items to fluctuate
    num_items_to_fluctuate = random.randint(1, min(2, len(items)))
    items_to_fluctuate = random.sample(items, num_items_to_fluctuate)

    for item in items_to_fluctuate:
        # 5-10% fluctuation, can be positive or negative
        fluctuation = random.uniform(0.05, 0.10)
        direction = random.choice([-1, 1])

        old_price = market_prices[item.name]
        new_price = old_price * (1 + direction * fluctuation)

        # Keep prices reasonable (not below base cost, not above 2x base price)
        new_price = max(item.base_cost * 1.2, min(new_price, item.base_price * 2.0))

        market_prices[item.name] = new_price


# -------------------------------------------------------------------
# Player strategies
# -------------------------------------------------------------------

def auto_production_strategy(player: Player, items: List[Item], vendors: List[Vendor]) -> None:
    """
    Automatically purchase items for AI players from vendors.

    Each day, player tries to maintain inventory by purchasing from cheapest vendor.
    """
    for item in items:
        current_inventory = player.inventory.get(item.name, 0)

        # Try to maintain inventory of at least 10 units per item
        target_inventory = 10
        if current_inventory < target_inventory:
            quantity_to_purchase = target_inventory - current_inventory

            # Find cheapest vendor for this item
            cheapest_vendor = None
            cheapest_price = float('inf')

            for vendor in vendors:
                vendor_price = vendor.get_price(item.name)
                if vendor_price and vendor_price < cheapest_price:
                    cheapest_price = vendor_price
                    cheapest_vendor = vendor

            # Purchase from cheapest vendor if found
            if cheapest_vendor:
                player.purchase_from_vendor(cheapest_vendor, item.name, quantity_to_purchase)


def auto_pricing_strategy(player: Player, market_prices: Dict[str, float]) -> None:
    """
    Automatically set prices for AI players based on current market prices.

    Uses market price with a small random variation to simulate competition.
    """
    for item_name, market_price in market_prices.items():
        # Set price to market_price with a random variation of +/- 5%
        variation = random.uniform(0.95, 1.05)
        price = market_price * variation
        player.set_price(item_name, price)


# -------------------------------------------------------------------
# Daily simulation logic
# -------------------------------------------------------------------

def run_day(game_state: GameState, show_details: bool = True) -> Dict[str, float]:
    """
    Simulate a single day in the economic game.

    Steps:
    1. Apply daily price fluctuations to market
    2. Refresh vendor inventory based on new market prices
    3. Let AI players purchase items and adjust prices
    4. For each customer, generate needs and make purchases
    5. Track statistics
    6. Advance the day counter

    Returns dictionary of daily sales per player.
    """

    if show_details:
        print(f"\n=== Day {game_state.day} ===")

    # Step 1: Apply price fluctuations
    apply_daily_price_fluctuation(game_state.market_prices, game_state.items)

    # Step 2: Refresh vendor inventory based on new market prices
    refresh_vendor_inventory(game_state.vendors, game_state.items, game_state.market_prices)

    # Step 3: AI player decisions (production / pricing)
    for player in game_state.players:
        if player != game_state.human_player:  # Only automate AI players
            auto_production_strategy(player, game_state.items, game_state.vendors)
            auto_pricing_strategy(player, game_state.market_prices)

    # Track daily statistics
    daily_sales = {player.name: 0.0 for player in game_state.players}
    unmet_demand = 0

    # Step 4: Simulate customers
    for customer in game_state.customers:
        needs = customer.generate_daily_needs(game_state.items)

        for need in needs:
            supplier = customer.choose_supplier(game_state.players, need.item_name, need.quantity)

            if supplier:
                price = supplier.prices.get(need.item_name, 0)
                revenue = supplier.sell_to_customer(need.item_name, need.quantity, price)
                daily_sales[supplier.name] += revenue
            else:
                # Track unmet demand
                unmet_demand += need.quantity

    # Step 5: Print daily summary
    if show_details:
        print(f"\nDaily Sales:")
        for player in game_state.players:
            sales = daily_sales[player.name]
            print(f"  {player.name}: ${sales:.2f} (Cash: ${player.cash:.2f})")

        if unmet_demand > 0:
            print(f"\nUnmet demand: {unmet_demand} items")

    # Step 6: Advance day counter
    game_state.day += 1

    return daily_sales


# -------------------------------------------------------------------
# Interactive menu system
# -------------------------------------------------------------------

def display_market_table(game_state: GameState) -> None:
    """Display the current market prices for all items."""
    print("\n" + "=" * 50)
    print("MARKET PRICE TABLE")
    print("=" * 50)
    print(f"{'Item':<15} {'Market Price':>12}")
    print("-" * 50)
    for item in game_state.items:
        price = game_state.market_prices.get(item.name, 0)
        print(f"{item.name:<15} ${price:>11.2f}")
    print("=" * 50)


def display_vendor_table(game_state: GameState) -> None:
    """Display all vendors and their prices."""
    print("\n" + "=" * 80)
    print("VENDOR INFORMATION")
    print("=" * 80)

    for i, vendor in enumerate(game_state.vendors, 1):
        print(f"\n{i}. {vendor.name}")

        # Display vendor strategy
        if vendor.selection_type == "random_daily":
            print(f"   Strategy: {int(vendor.selection_params)} random item(s) per day")
        elif vendor.selection_type == "price_threshold":
            print(f"   Strategy: All items under ${vendor.selection_params:.2f} market price")
        elif vendor.selection_type == "all":
            print(f"   Strategy: All items available")

        print(f"   Pricing: {vendor.pricing_multiplier*100:.0f}% of market price")

        # Display current inventory
        print(f"   Current stock ({len(vendor.items)} items):")
        if vendor.items:
            for item_name, price in sorted(vendor.items.items()):
                market_price = game_state.market_prices.get(item_name, 0)
                print(f"      - {item_name}: ${price:.2f} (market: ${market_price:.2f})")
        else:
            print(f"      (no items available)")

    print("=" * 80)


def display_player_status(player: Player) -> None:
    """Display the player's current status."""
    print("\n" + "=" * 50)
    print(f"YOUR STORE: {player.name}")
    print("=" * 50)
    print(f"Cash: ${player.cash:.2f}")
    print(f"\nInventory:")
    if player.inventory:
        for item_name, quantity in player.inventory.items():
            print(f"  {item_name}: {quantity} units")
    else:
        print("  (empty)")

    print(f"\nYour Prices:")
    if player.prices:
        for item_name, price in player.prices.items():
            print(f"  {item_name}: ${price:.2f}")
    else:
        print("  (no prices set)")
    print("=" * 50)


def vendor_menu(game_state: GameState, player: Player) -> None:
    """Menu for purchasing items from vendors."""
    while True:
        print("\n" + "=" * 50)
        print("VENDOR MENU - Purchase Items")
        print("=" * 50)

        display_vendor_table(game_state)

        print("\nSelect Vendor:")
        for i, vendor in enumerate(game_state.vendors, 1):
            print(f"  {i}. {vendor.name}")
        print(f"  0. Back to Main Menu")

        try:
            choice = input("\nSelect vendor (0-{}): ".format(len(game_state.vendors)))
            choice_num = int(choice)

            if choice_num == 0:
                break

            if 1 <= choice_num <= len(game_state.vendors):
                vendor = game_state.vendors[choice_num - 1]

                # Show items available from this vendor
                print(f"\n{vendor.name} - Available Items:")
                available_items = []
                for i, item in enumerate(game_state.items, 1):
                    price = vendor.get_price(item.name)
                    if price:
                        print(f"  {i}. {item.name} - ${price:.2f}")
                        available_items.append((i, item.name))

                if not available_items:
                    print("  No items available from this vendor!")
                    continue

                item_choice = input(f"\nSelect item (1-{len(available_items)}) or 0 to cancel: ")
                item_num = int(item_choice)

                if item_num == 0:
                    continue

                # Find the selected item
                selected_item_name = None
                for idx, item_name in available_items:
                    if idx == item_num:
                        selected_item_name = item_name
                        break

                if selected_item_name:
                    quantity_str = input(f"Enter quantity to purchase: ")
                    quantity = int(quantity_str)

                    if quantity > 0:
                        success = player.purchase_from_vendor(vendor, selected_item_name, quantity)
                        if success:
                            total_cost = vendor.get_price(selected_item_name) * quantity
                            print(f"\n✓ Purchased {quantity} {selected_item_name} for ${total_cost:.2f}")
                        else:
                            print(f"\n✗ Failed to purchase. Not enough cash!")
                    else:
                        print("\n✗ Invalid quantity!")
            else:
                print("\n✗ Invalid vendor selection!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def pricing_menu(game_state: GameState, player: Player) -> None:
    """Menu for setting prices."""
    while True:
        print("\n" + "=" * 50)
        print("PRICING MENU - Set Your Prices")
        print("=" * 50)

        # Show current market prices and player's prices
        print(f"\n{'Item':<15} {'Market Price':>12} {'Your Price':>12}")
        print("-" * 50)
        for item in game_state.items:
            market_price = game_state.market_prices.get(item.name, 0)
            your_price = player.prices.get(item.name, 0)
            print(f"{item.name:<15} ${market_price:>11.2f} ${your_price:>11.2f}")

        print("\nSelect item to price:")
        for i, item in enumerate(game_state.items, 1):
            print(f"  {i}. {item.name}")
        print(f"  0. Back to Main Menu")

        try:
            choice = input(f"\nSelect item (0-{len(game_state.items)}): ")
            choice_num = int(choice)

            if choice_num == 0:
                break

            if 1 <= choice_num <= len(game_state.items):
                item = game_state.items[choice_num - 1]
                market_price = game_state.market_prices.get(item.name, 0)

                print(f"\nSetting price for {item.name}")
                print(f"Current market price: ${market_price:.2f}")

                price_str = input(f"Enter your selling price: $")
                price = float(price_str)

                if price >= 0:
                    player.set_price(item.name, price)
                    print(f"\n✓ Price set to ${price:.2f}")
                else:
                    print("\n✗ Price must be positive!")
            else:
                print("\n✗ Invalid item selection!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def main_menu(game_state: GameState) -> bool:
    """
    Display main menu and handle user choice.
    Returns True to continue game, False to quit.
    """
    player = game_state.human_player

    while True:
        print("\n" + "=" * 50)
        print(f"MAIN MENU - Day {game_state.day}")
        print("=" * 50)
        print(f"Your Cash: ${player.cash:.2f}")
        print("\nOptions:")
        print("  1. Pass Day (Simulate)")
        print("  2. View Market Prices")
        print("  3. View Vendors")
        print("  4. Purchase from Vendors")
        print("  5. Set Your Prices")
        print("  6. View Your Store Status")
        print("  7. View Competitor Status")
        print("  0. Quit Game")

        try:
            choice = input("\nSelect option (0-7): ")
            choice_num = int(choice)

            if choice_num == 0:
                print("\nThanks for playing!")
                return False
            elif choice_num == 1:
                # Pass day
                run_day(game_state, show_details=True)
                input("\nPress Enter to continue...")
                return True
            elif choice_num == 2:
                display_market_table(game_state)
                input("\nPress Enter to continue...")
            elif choice_num == 3:
                display_vendor_table(game_state)
                input("\nPress Enter to continue...")
            elif choice_num == 4:
                vendor_menu(game_state, player)
            elif choice_num == 5:
                pricing_menu(game_state, player)
            elif choice_num == 6:
                display_player_status(player)
                input("\nPress Enter to continue...")
            elif choice_num == 7:
                print("\n" + "=" * 50)
                print("COMPETITOR STATUS")
                print("=" * 50)
                for p in game_state.players:
                    if p != player:
                        print(f"\n{p.name}:")
                        print(f"  Cash: ${p.cash:.2f}")
                        print(f"  Inventory: {dict(p.inventory)}")
                        print(f"  Prices: {dict(p.prices)}")
                print("=" * 50)
                input("\nPress Enter to continue...")
            else:
                print("\n✗ Invalid option!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


# -------------------------------------------------------------------
# Main simulation loop
# -------------------------------------------------------------------

def run_game() -> None:
    """
    Top-level function to run the interactive economy simulation game.
    """

    # Create game configuration
    config = GameConfig()
    config.num_days = 365  # Run for a full year

    print("\n" + "=" * 60)
    print("WELCOME TO ECONOMY SIMULATION")
    print("=" * 60)
    print("\nIn this game, you run a store competing against AI players.")
    print("You'll purchase items from vendors and sell them to customers.")
    print("The market prices fluctuate daily, so timing is everything!")
    print("\n" + "=" * 60)

    # Get player name
    player_name = input("\nEnter your store name: ").strip()
    if not player_name:
        player_name = "Your Store"

    print(f"\nStarting cash: ${config.starting_cash:.2f}")
    print(f"Customers per day: {config.customers_per_day}")

    # Initialize items, vendors, customers
    items = create_default_items()
    vendors = create_vendors()
    customers = create_customers(config.customers_per_day)
    market_prices = initialize_market_prices(items)

    # Initialize vendor inventory for day 1
    refresh_vendor_inventory(vendors, items, market_prices)

    # Create human player and AI players
    human_player = Player(name=player_name, cash=config.starting_cash)
    ai_players = create_players(["Alice Corp", "Bob Ltd"], config.starting_cash)
    all_players = [human_player] + ai_players

    # Create GameState
    game_state = GameState(
        day=1,
        players=all_players,
        customers=customers,
        items=items,
        vendors=vendors,
        market_prices=market_prices,
        config=config,
        human_player=human_player,
    )

    # Show initial setup
    print("\n" + "=" * 60)
    print("GAME SETUP COMPLETE")
    print("=" * 60)
    print(f"\nCompetitors:")
    for player in ai_players:
        print(f"  - {player.name}")

    print(f"\nAvailable Items:")
    for item in items:
        print(f"  - {item.name} (Base: ${item.base_cost:.2f})")

    print(f"\nVendors:")
    for vendor in vendors:
        print(f"  - {vendor.name}")

    input("\nPress Enter to start the game...")

    # Main game loop
    game_running = True
    while game_running and game_state.day <= config.num_days:
        game_running = main_menu(game_state)

    # Show final results
    if not game_running:
        print("\n" + "=" * 60)
        print("GAME ENDED")
        print("=" * 60)

    print("\n" + "=" * 60)
    print("FINAL STANDINGS")
    print("=" * 60)
    print(f"Days played: {game_state.day - 1}")

    # Sort players by cash (descending)
    sorted_players = sorted(game_state.players, key=lambda p: p.cash, reverse=True)

    for i, player in enumerate(sorted_players, 1):
        print(f"\n{i}. {player.name}")
        print(f"   Cash: ${player.cash:.2f}")
        print(f"   Inventory value: {sum(player.inventory.values())} units")

    winner = sorted_players[0]
    print("\n" + "=" * 60)
    if winner == human_player:
        print("🎉 CONGRATULATIONS! YOU WON! 🎉")
    else:
        print(f"Winner: {winner.name}")
    print(f"Final cash: ${winner.cash:.2f}")
    print("=" * 60)


if __name__ == "__main__":
    run_game()
