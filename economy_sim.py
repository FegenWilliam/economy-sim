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
    config: GameConfig = field(default_factory=GameConfig)

    def get_item(self, item_name: str) -> Optional[Item]:
        """
        Look up an item by its name in self.items.
        Returns the Item or None if not found.
        """
        for item in self.items:
            if item.name == item_name:
                return item
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


# -------------------------------------------------------------------
# Player strategies
# -------------------------------------------------------------------

def auto_production_strategy(player: Player, items: List[Item]) -> None:
    """
    Automatically produce items for a player based on simple strategy.

    Each day, player tries to produce some inventory of each item type.
    """
    for item in items:
        current_inventory = player.inventory.get(item.name, 0)

        # Try to maintain inventory of at least 10 units per item
        target_inventory = 10
        if current_inventory < target_inventory:
            quantity_to_produce = target_inventory - current_inventory
            total_cost = item.base_cost * quantity_to_produce

            # Only produce if we have enough cash
            if player.cash >= total_cost:
                try:
                    player.produce_item(item, quantity_to_produce)
                except ValueError:
                    # Not enough cash, skip this item
                    pass


def auto_pricing_strategy(player: Player, items: List[Item]) -> None:
    """
    Automatically set prices for a player based on simple strategy.

    Uses base_price with a small random variation to simulate competition.
    """
    for item in items:
        # Set price to base_price with a random variation of +/- 10%
        variation = random.uniform(0.9, 1.1)
        price = item.base_price * variation
        player.set_price(item.name, price)


# -------------------------------------------------------------------
# Daily simulation logic
# -------------------------------------------------------------------

def run_day(game_state: GameState) -> None:
    """
    Simulate a single day in the economic game.

    Steps:
    1. Let each player produce items / adjust prices for the day.
    2. For each customer:
       - Generate daily needs
       - For each need, choose a supplier and make the purchase
    3. Track statistics
    4. Advance the day counter.
    """

    print(f"\n=== Day {game_state.day} ===")

    # Step 1: Player decisions (production / pricing)
    for player in game_state.players:
        auto_production_strategy(player, game_state.items)
        auto_pricing_strategy(player, game_state.items)

    # Track daily statistics
    daily_sales = {player.name: 0.0 for player in game_state.players}
    unmet_demand = 0

    # Step 2: Simulate customers
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

    # Step 3: Print daily summary
    print(f"\nDaily Sales:")
    for player in game_state.players:
        sales = daily_sales[player.name]
        print(f"  {player.name}: ${sales:.2f} (Cash: ${player.cash:.2f})")

    if unmet_demand > 0:
        print(f"\nUnmet demand: {unmet_demand} items")

    # Step 4: Advance day counter
    game_state.day += 1


# -------------------------------------------------------------------
# Main simulation loop
# -------------------------------------------------------------------

def run_game() -> None:
    """
    Top-level function to run the entire simulation for config.num_days.
    """

    # Create game configuration
    config = GameConfig()

    print("=== ECONOMY SIMULATION ===")
    print(f"Starting cash per player: ${config.starting_cash:.2f}")
    print(f"Number of days: {config.num_days}")
    print(f"Customers per day: {config.customers_per_day}")

    # Initialize items, players, customers
    items = create_default_items()
    players = create_players(["Alice Corp", "Bob Ltd", "Charlie Inc"], config.starting_cash)
    customers = create_customers(config.customers_per_day)

    # Create GameState
    game_state = GameState(
        day=1,
        players=players,
        customers=customers,
        items=items,
        config=config,
    )

    # Main simulation loop
    for _ in range(config.num_days):
        run_day(game_state)

    # Show final results
    print("\n" + "=" * 50)
    print("=== FINAL STANDINGS ===")
    print("=" * 50)

    # Sort players by cash (descending)
    sorted_players = sorted(game_state.players, key=lambda p: p.cash, reverse=True)

    for i, player in enumerate(sorted_players, 1):
        print(f"{i}. {player.name}")
        print(f"   Cash: ${player.cash:.2f}")
        print(f"   Inventory: {dict(player.inventory)}")
        print()

    winner = sorted_players[0]
    print(f"🏆 Winner: {winner.name} with ${winner.cash:.2f}!")


if __name__ == "__main__":
    run_game()
