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

    # TODO: implement method to set price for an item
    def set_price(self, item_name: str, price: float) -> None:
        """
        TODO:
        - Store the price in self.prices
        - Optionally validate that price >= 0
        """
        pass

    # TODO: implement method to produce items (spend cash to increase inventory)
    def produce_item(self, item: Item, quantity: int) -> None:
        """
        TODO:
        - Compute total production cost (item.base_cost * quantity)
        - Check if player has enough cash
        - Deduct cost from cash
        - Increase inventory[item.name] by quantity
        """
        pass

    # TODO: implement method to sell items to a customer
    def sell_to_customer(self, item_name: str, quantity: int, unit_price: float) -> float:
        """
        Attempt to sell 'quantity' units of 'item_name' at 'unit_price'.
        Returns the total revenue actually realized.

        TODO:
        - Check available inventory for the item
        - Determine how many units can actually be sold (min of requested vs inventory)
        - Decrease inventory accordingly
        - Increase cash by revenue (units_sold * unit_price)
        - Return revenue
        """
        pass


@dataclass
class CustomerNeed:
    """Represents the need of a single item by a customer for a day."""
    item_name: str
    quantity: int


@dataclass
class Customer:
    """Represents a customer with daily needs for items."""
    name: str

    # TODO: daily needs could be regenerated each day
    def generate_daily_needs(self, available_items: List[Item]) -> List[CustomerNeed]:
        """
        Generate a random set of item needs for the day.

        TODO:
        - Decide how many different item types this customer wants today
        - For each chosen item, generate a random quantity (e.g. 1–10)
        - Return as a list of CustomerNeed
        - You can use 'random' module for randomness
        """
        pass

    # TODO: implement logic for choosing which player to buy from
    def choose_supplier(
        self,
        players: List[Player],
        item_name: str,
        quantity: int
    ) -> Optional[Player]:
        """
        Decide which player to buy from for a given item and quantity.

        TODO:
        - Consider each player's price for the item (lowest price wins, for example)
        - Optionally break ties randomly or based on who has enough stock
        - Return the chosen Player or None if nobody can supply
        """
        pass


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

    # TODO: helper to get item by name
    def get_item(self, item_name: str) -> Optional[Item]:
        """
        TODO:
        - Look up an item by its name in self.items
        - Return the Item or None if not found
        """
        pass


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
    Create a list of customers.

    TODO:
    - Give them more interesting names if desired
    """
    return [Customer(name=f"Customer_{i+1}") for i in range(num_customers)]


# -------------------------------------------------------------------
# Daily simulation logic
# -------------------------------------------------------------------

def run_day(game_state: GameState) -> None:
    """
    Simulate a single day in the economic game.

    High-level steps (TODOs):
    1. Let each player produce items / adjust prices for the day.
       - For now this could be automated / AI-driven, or later you can hook
         this to player input or a UI.
    2. For each customer:
       - Generate daily needs (Customer.generate_daily_needs)
       - For each need:
         * Ask the customer to choose a supplier (Customer.choose_supplier)
         * If a supplier exists, perform the sale using Player.sell_to_customer
    3. Track statistics (e.g., total revenue per player, unmet demand).
    4. Advance the day counter.

    TODO:
    - Implement all of the above steps.
    - Optionally print a daily summary.
    """

    # TODO: Step 1 – player decisions (production / pricing)
    # Example idea:
    # for player in game_state.players:
    #     auto_production_strategy(player, game_state.items)
    #     auto_pricing_strategy(player, game_state.items)
    #
    # These strategy functions would also be TODOs elsewhere.

    # TODO: Step 2 – simulate customers
    # for customer in game_state.customers:
    #     needs = customer.generate_daily_needs(game_state.items)
    #     for need in needs:
    #         supplier = customer.choose_supplier(game_state.players, need.item_name, need.quantity)
    #         if supplier:
    #             price = supplier.prices.get(need.item_name, default_price_here)
    #             supplier.sell_to_customer(need.item_name, need.quantity, price)
    #         else:
    #             # Track unmet demand if desired
    #             pass

    # TODO: Step 3 – collect statistics (e.g., total sales per player)

    # TODO: Step 4 – advance day counter
    game_state.day += 1


# -------------------------------------------------------------------
# Main simulation loop
# -------------------------------------------------------------------

def run_game() -> None:
    """
    Top-level function to run the entire simulation for config.num_days.

    TODO:
    - Initialize items, players, and customers
    - Loop from day 1 to num_days
    - Call run_day(...) each iteration
    - At the end, print final standings (who has the most cash, etc.)
    """

    # TODO: create a default config or load from file
    config = GameConfig()

    # TODO: initialize items, players, customers
    items = create_default_items()
    players = create_players(["Alice Corp", "Bob Ltd", "Charlie Inc"], config.starting_cash)
    customers = create_customers(config.customers_per_day)

    # TODO: create GameState
    game_state = GameState(
        day=1,
        players=players,
        customers=customers,
        items=items,
        config=config,
    )

    # TODO: main loop
    # for _ in range(config.num_days):
    #     print(f"=== Day {game_state.day} ===")
    #     run_day(game_state)
    #     # Optionally show per-day summary here

    # TODO: after the loop, show final results / winner


if __name__ == "__main__":
    # TODO: decide if this should actually run the simulation or just be a library
    run_game()
