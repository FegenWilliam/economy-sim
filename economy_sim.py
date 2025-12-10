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
import json
import signal
import sys
import os


# -------------------------------------------------------------------
# Core data models
# -------------------------------------------------------------------

@dataclass
class Item:
    """An item that can be produced and sold."""
    name: str
    base_cost: float  # cost to produce 1 unit
    base_price: float  # default selling price (can be overridden by players)


# Product catalog - items that can be unlocked over time
PRODUCT_CATALOG = [
    # Groceries & Food (cheap items)
    Item("Bread", 2.0, 5.0),
    Item("Milk", 3.0, 6.0),
    Item("Eggs", 2.5, 5.5),
    Item("Cheese", 4.0, 8.0),
    Item("Butter", 3.5, 7.0),
    Item("Yogurt", 2.0, 4.5),
    Item("Cereal", 3.0, 6.5),
    Item("Rice", 5.0, 10.0),
    Item("Pasta", 2.0, 4.0),
    Item("Canned Soup", 1.5, 3.5),
    Item("Frozen Pizza", 4.0, 8.5),
    Item("Ice Cream", 3.5, 7.5),
    Item("Soda", 1.5, 3.0),
    Item("Orange Juice", 3.0, 6.0),
    Item("Coffee", 6.0, 12.0),
    Item("Tea Bags", 3.0, 6.5),
    Item("Sugar", 2.0, 4.5),
    Item("Flour", 3.0, 6.0),
    Item("Cooking Oil", 4.0, 8.0),
    Item("Salt", 1.0, 2.5),
    Item("Pepper", 2.0, 4.5),
    Item("Ketchup", 2.5, 5.0),
    Item("Mustard", 2.0, 4.5),
    Item("Mayo", 3.0, 6.0),
    Item("BBQ Sauce", 3.5, 7.0),

    # Fresh Produce
    Item("Apples", 2.5, 5.5),
    Item("Bananas", 1.5, 3.5),
    Item("Oranges", 3.0, 6.0),
    Item("Grapes", 4.0, 8.5),
    Item("Strawberries", 4.5, 9.0),
    Item("Tomatoes", 2.5, 5.5),
    Item("Lettuce", 2.0, 4.5),
    Item("Carrots", 1.5, 3.5),
    Item("Potatoes", 2.0, 4.0),
    Item("Onions", 1.5, 3.5),

    # Household Items
    Item("Paper Towels", 5.0, 10.0),
    Item("Toilet Paper", 8.0, 15.0),
    Item("Dish Soap", 3.0, 6.5),
    Item("Laundry Detergent", 8.0, 16.0),
    Item("Trash Bags", 5.0, 10.5),
    Item("Sponges", 2.5, 5.5),
    Item("Aluminum Foil", 4.0, 8.5),
    Item("Plastic Wrap", 3.5, 7.5),
    Item("Light Bulbs", 6.0, 12.0),
    Item("Batteries", 5.0, 10.0),
    Item("Candles", 4.0, 8.5),
    Item("Air Freshener", 3.5, 7.5),

    # Personal Care
    Item("Shampoo", 5.0, 10.0),
    Item("Conditioner", 5.0, 10.0),
    Item("Body Wash", 4.5, 9.0),
    Item("Toothpaste", 3.0, 6.5),
    Item("Toothbrush", 2.5, 5.5),
    Item("Deodorant", 4.0, 8.5),
    Item("Razor Blades", 8.0, 16.0),
    Item("Shaving Cream", 4.5, 9.0),
    Item("Hand Soap", 3.0, 6.5),
    Item("Hand Sanitizer", 3.5, 7.5),
    Item("Tissues", 2.5, 5.5),
    Item("Cotton Swabs", 2.0, 4.5),

    # Electronics (cheap to mid-range)
    Item("Phone Charger", 8.0, 16.0),
    Item("USB Cable", 5.0, 10.0),
    Item("Earbuds", 12.0, 25.0),
    Item("Phone Case", 10.0, 20.0),
    Item("Screen Protector", 6.0, 12.0),
    Item("Mouse Pad", 7.0, 15.0),
    Item("Keyboard", 25.0, 50.0),
    Item("Computer Mouse", 15.0, 30.0),
    Item("Webcam", 35.0, 70.0),
    Item("Microphone", 40.0, 80.0),
    Item("USB Flash Drive", 10.0, 20.0),
    Item("SD Card", 12.0, 25.0),
    Item("HDMI Cable", 8.0, 16.0),
    Item("Power Strip", 15.0, 30.0),
    Item("Desk Lamp", 20.0, 40.0),
    Item("Alarm Clock", 12.0, 25.0),
    Item("Calculator", 10.0, 20.0),
    Item("Portable Speaker", 30.0, 60.0),
    Item("Bluetooth Headphones", 45.0, 90.0),

    # Office Supplies
    Item("Pens", 3.0, 6.5),
    Item("Pencils", 2.5, 5.5),
    Item("Notebooks", 4.0, 8.5),
    Item("Sticky Notes", 3.5, 7.5),
    Item("Stapler", 8.0, 16.0),
    Item("Tape Dispenser", 6.0, 12.0),
    Item("Scissors", 5.0, 10.0),
    Item("Ruler", 2.0, 4.5),
    Item("Binder", 4.5, 9.0),
    Item("File Folders", 6.0, 12.5),
    Item("Printer Paper", 15.0, 30.0),

    # Mid-range Electronics
    Item("Tablet", 150.0, 300.0),
    Item("E-Reader", 80.0, 160.0),
    Item("Smart Watch", 120.0, 240.0),
    Item("Fitness Tracker", 60.0, 120.0),
    Item("Wireless Earbuds", 70.0, 140.0),
    Item("Gaming Mouse", 45.0, 90.0),
    Item("Gaming Keyboard", 60.0, 120.0),
    Item("Monitor", 150.0, 300.0),
    Item("External Hard Drive", 55.0, 110.0),
    Item("Wireless Router", 50.0, 100.0),
    Item("Smart Plug", 15.0, 30.0),
    Item("Security Camera", 40.0, 80.0),
    Item("Video Doorbell", 80.0, 160.0),

    # Appliances & Home Electronics (higher priced)
    Item("Coffee Maker", 40.0, 80.0),
    Item("Toaster", 25.0, 50.0),
    Item("Blender", 35.0, 70.0),
    Item("Microwave", 80.0, 160.0),
    Item("Air Fryer", 70.0, 140.0),
    Item("Slow Cooker", 35.0, 70.0),
    Item("Electric Kettle", 30.0, 60.0),
    Item("Hair Dryer", 25.0, 50.0),
    Item("Iron", 20.0, 40.0),
    Item("Vacuum Cleaner", 120.0, 240.0),
    Item("Fan", 35.0, 70.0),
    Item("Space Heater", 45.0, 90.0),
    Item("Humidifier", 40.0, 80.0),
    Item("Air Purifier", 90.0, 180.0),

    # Expensive Electronics
    Item("Laptop", 400.0, 800.0),
    Item("Gaming Console", 300.0, 600.0),
    Item("4K TV", 350.0, 700.0),
    Item("Soundbar", 150.0, 300.0),
    Item("Noise-Cancelling Headphones", 180.0, 360.0),
    Item("Drone", 250.0, 500.0),
    Item("VR Headset", 300.0, 600.0),
    Item("Digital Camera", 400.0, 800.0),
    Item("Projector", 300.0, 600.0),
    Item("Smart Thermostat", 120.0, 240.0),
    Item("Robot Vacuum", 200.0, 400.0),
    Item("Electric Scooter", 350.0, 700.0),

    # Luxury Items (expensive)
    Item("Designer Handbag", 600.0, 1200.0),
    Item("Leather Wallet", 100.0, 200.0),
    Item("Sunglasses", 150.0, 300.0),
    Item("Perfume", 80.0, 160.0),
    Item("Cologne", 70.0, 140.0),
    Item("Watch", 200.0, 400.0),
    Item("Jewelry Box", 60.0, 120.0),
    Item("Gold Necklace", 500.0, 1000.0),
    Item("Silver Bracelet", 150.0, 300.0),
    Item("Diamond Earrings", 800.0, 1600.0),
    Item("Designer Shoes", 300.0, 600.0),
    Item("Leather Jacket", 250.0, 500.0),
    Item("Cashmere Sweater", 180.0, 360.0),
    Item("Silk Scarf", 80.0, 160.0),
    Item("Designer Jeans", 120.0, 240.0),

    # Additional Items (Sports & Outdoor)
    Item("Yoga Mat", 20.0, 40.0),
    Item("Dumbbells", 30.0, 60.0),
    Item("Tennis Racket", 60.0, 120.0),
    Item("Basketball", 15.0, 30.0),
    Item("Camping Tent", 100.0, 200.0),
    Item("Sleeping Bag", 50.0, 100.0),
    Item("Hiking Boots", 80.0, 160.0),
]


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
class Upgrade:
    """An upgrade that players can purchase once."""
    name: str
    cost: float
    effect_type: str  # "max_customers", "max_items", "max_products", "xp_gain", "vendor_discount"
    effect_value: float  # Amount of the effect
    vendor_name: str = ""  # Only used for vendor_discount type


@dataclass
class Player:
    """Represents a company / player in the economic simulation."""
    name: str
    cash: float = 0.0
    inventory: Dict[str, int] = field(default_factory=dict)  # item_name -> quantity
    prices: Dict[str, float] = field(default_factory=dict)   # item_name -> selling price
    buy_orders: Dict[str, tuple] = field(default_factory=dict)  # item_name -> (quantity, vendor_name)
    cashiers: int = 1  # Each cashier handles 10 customers per day
    restockers: int = 1  # Each restocker handles 20 items per day
    store_level: int = 1  # Limits how many different products can be stocked (starts at 3)
    experience: float = 0.0  # XP gained from profits
    item_costs: Dict[str, float] = field(default_factory=dict)  # Track cost per item for profit calculation
    purchased_upgrades: List['Upgrade'] = field(default_factory=list)  # Upgrades bought by this player
    is_human: bool = False  # Whether this is a human-controlled player

    def set_buy_order(self, item_name: str, quantity: int, vendor_name: str) -> None:
        """
        Set a buy order for an item: how many to buy and from which vendor.
        If quantity is 0, the item will be skipped during buying.
        """
        self.buy_orders[item_name] = (quantity, vendor_name)

    def get_buy_order(self, item_name: str) -> tuple:
        """
        Get the buy order for an item.
        Returns (quantity, vendor_name) or (0, "") if not set.
        """
        return self.buy_orders.get(item_name, (0, ""))

    def get_max_products(self) -> int:
        """Get max number of different products based on store level and upgrades."""
        base = 3 + (self.store_level - 1)  # Level 1 = 3, Level 2 = 4, etc.
        bonus = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "max_products")
        return int(base + bonus)

    def get_max_customers(self) -> int:
        """Get max number of customers that can be served per day."""
        base = self.cashiers * 10
        bonus = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "max_customers")
        return int(base + bonus)

    def get_max_items_per_day(self) -> int:
        """Get max number of items that can be restocked per day."""
        base = self.restockers * 20
        bonus = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "max_items")
        return int(base + bonus)

    def get_xp_multiplier(self) -> float:
        """Get XP gain multiplier from upgrades."""
        bonus_percent = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "xp_gain")
        return 1.0 + (bonus_percent / 100.0)

    def get_vendor_discount(self, vendor_name: str) -> float:
        """Get discount percentage for a specific vendor."""
        discount = sum(u.effect_value for u in self.purchased_upgrades
                      if u.effect_type == "vendor_discount" and u.vendor_name == vendor_name)
        return discount / 100.0  # Convert percentage to decimal

    def purchase_upgrade(self, upgrade: 'Upgrade') -> bool:
        """
        Purchase an upgrade if player has enough cash.
        Returns True if successful, False otherwise.
        """
        if self.cash < upgrade.cost:
            return False

        self.cash -= upgrade.cost
        self.purchased_upgrades.append(upgrade)
        return True

    def get_xp_for_next_level(self) -> float:
        """
        Calculate XP needed for next level.
        Formula: 500 * current_level + (10000 * (current_level // 10))
        """
        return 500 * self.store_level + (10000 * (self.store_level // 10))

    def add_experience(self, xp: float) -> bool:
        """
        Add experience points and check for level up.
        Applies XP multiplier from upgrades.
        Returns True if leveled up, False otherwise.
        """
        actual_xp = xp * self.get_xp_multiplier()
        self.experience += actual_xp
        xp_needed = self.get_xp_for_next_level()

        if self.experience >= xp_needed:
            self.experience -= xp_needed
            self.store_level += 1
            return True
        return False

    def hire_employee(self, employee_type: str) -> bool:
        """
        Hire an employee (cashier or restocker).
        Costs $500. Returns True if successful, False if not enough cash.
        """
        HIRING_COST = 500.0

        if self.cash < HIRING_COST:
            return False

        self.cash -= HIRING_COST
        if employee_type == "cashier":
            self.cashiers += 1
        elif employee_type == "restocker":
            self.restockers += 1
        else:
            return False

        return True

    def pay_daily_wages(self) -> float:
        """
        Pay daily wages for all employees ($20 per employee).
        Returns total wages paid.
        """
        total_employees = self.cashiers + self.restockers
        wages = total_employees * 20.0
        self.cash -= wages
        return wages

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

    def sell_to_customer(self, item_name: str, quantity: int, unit_price: float) -> tuple:
        """
        Attempt to sell 'quantity' units of 'item_name' at 'unit_price'.
        Returns (revenue, profit) tuple.
        Profit = revenue - cost
        """
        available = self.inventory.get(item_name, 0)
        units_sold = min(quantity, available)

        if units_sold > 0:
            self.inventory[item_name] -= units_sold
            revenue = units_sold * unit_price
            self.cash += revenue

            # Calculate profit (revenue - cost)
            cost_per_unit = self.item_costs.get(item_name, 0)
            profit = revenue - (cost_per_unit * units_sold)

            return (revenue, profit)

        return (0.0, 0.0)

    def purchase_from_vendor(self, vendor: 'Vendor', item_name: str, quantity: int) -> bool:
        """
        Purchase items from a vendor at their wholesale price.
        Returns True if successful, False if not enough cash.
        Also tracks the weighted average cost per item for profit calculation.
        Applies vendor discount upgrades.
        """
        if quantity <= 0:
            return False

        vendor_price = vendor.get_price(item_name)
        if vendor_price is None:
            return False

        # Apply vendor discount
        discount = self.get_vendor_discount(vendor.name)
        final_price = vendor_price * (1.0 - discount)
        total_cost = final_price * quantity

        if self.cash < total_cost:
            return False

        self.cash -= total_cost

        # Update weighted average cost
        current_inventory = self.inventory.get(item_name, 0)
        current_cost = self.item_costs.get(item_name, 0)

        # Weighted average: (old_qty * old_cost + new_qty * new_cost) / total_qty
        new_total_qty = current_inventory + quantity
        if new_total_qty > 0:
            weighted_cost = ((current_inventory * current_cost) + (quantity * final_price)) / new_total_qty
            self.item_costs[item_name] = weighted_cost

        self.inventory[item_name] = new_total_qty
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
    human_players: List[Player] = field(default_factory=list)  # All human-controlled players
    available_upgrades: List[Upgrade] = field(default_factory=list)  # Upgrades that can be purchased
    current_player_index: int = 0  # For multiplayer turn management
    unlocked_product_indices: List[int] = field(default_factory=list)  # Indices of products from catalog that have been unlocked

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
    Create the starting items for the simulation.
    Returns first 3 items from product catalog.
    """
    # Start with first 3 items (Bread, Milk, Eggs)
    return [PRODUCT_CATALOG[0], PRODUCT_CATALOG[1], PRODUCT_CATALOG[2]]


def unlock_new_product(game_state: GameState) -> Optional[Item]:
    """
    Unlock a new product from the catalog.
    Before day 50: only unlock items with base_price <= 100
    After day 50: can unlock any item

    Returns the unlocked Item or None if no valid items available.
    """
    # Get indices of products not yet unlocked
    available_indices = [
        i for i in range(len(PRODUCT_CATALOG))
        if i not in game_state.unlocked_product_indices
    ]

    if not available_indices:
        return None  # All products unlocked

    # Filter by price threshold before day 50
    if game_state.day < 50:
        available_indices = [
            i for i in available_indices
            if PRODUCT_CATALOG[i].base_price <= 100
        ]

    if not available_indices:
        return None  # No valid products available

    # Randomly select one
    selected_index = random.choice(available_indices)
    new_item = PRODUCT_CATALOG[selected_index]

    # Add to game state
    game_state.items.append(new_item)
    game_state.unlocked_product_indices.append(selected_index)
    game_state.market_prices[new_item.name] = new_item.base_price

    return new_item


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


def create_default_upgrades(vendors: List[Vendor]) -> List[Upgrade]:
    """
    Create a list of default upgrades available for purchase.
    Admins can add more upgrades to this list.
    """
    upgrades = [
        # Customer capacity upgrades
        Upgrade(name="Extra Cashier Station", cost=1000, effect_type="max_customers", effect_value=10),
        Upgrade(name="Express Checkout Lane", cost=1500, effect_type="max_customers", effect_value=15),

        # Buyout capacity upgrades
        Upgrade(name="Warehouse Extension", cost=1200, effect_type="max_items", effect_value=20),
        Upgrade(name="Loading Dock", cost=1800, effect_type="max_items", effect_value=30),

        # Max different items upgrades
        Upgrade(name="Additional Shelving", cost=800, effect_type="max_products", effect_value=2),
        Upgrade(name="Display Cases", cost=1500, effect_type="max_products", effect_value=3),

        # XP gain upgrades
        Upgrade(name="Business Course", cost=2000, effect_type="xp_gain", effect_value=10),
        Upgrade(name="MBA Program", cost=5000, effect_type="xp_gain", effect_value=25),
    ]

    # Add vendor discount upgrades for each vendor
    for vendor in vendors:
        upgrades.append(Upgrade(
            name=f"Partnership with {vendor.name}",
            cost=2500,
            effect_type="vendor_discount",
            effect_value=5,
            vendor_name=vendor.name
        ))
        upgrades.append(Upgrade(
            name=f"Premium Contract with {vendor.name}",
            cost=5000,
            effect_type="vendor_discount",
            effect_value=10,
            vendor_name=vendor.name
        ))

    return upgrades


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
# Buy order execution
# -------------------------------------------------------------------

def execute_buy_orders(player: Player, game_state: GameState) -> Dict[str, int]:
    """
    Execute a player's buy orders, purchasing from cheapest to most expensive items.

    For vendors with random daily selection (vendors 1 & 2), fallback to cheapest
    available vendor if the selected vendor doesn't have the item.

    Respects restocker limits (restockers * 20 items per day) and store level
    (max different products).

    Returns a dictionary of items purchased: {item_name: quantity_bought}
    """
    purchases = {}
    total_items_bought = 0
    max_items = player.get_max_items_per_day()
    max_products = player.get_max_products()

    # Get all non-zero buy orders
    active_orders = []
    for item_name, (quantity, vendor_name) in player.buy_orders.items():
        if quantity > 0:
            # Check if player already has too many different products
            current_products = len([item for item, qty in player.inventory.items() if qty > 0])
            if item_name not in player.inventory and current_products >= max_products:
                continue  # Skip this item, store is full of different products

            # Find the vendor
            vendor = game_state.get_vendor(vendor_name)
            if vendor:
                # Get the price from this vendor (might be None if item not available)
                price = vendor.get_price(item_name)

                # For random vendors, check if item is available, fallback if not
                if vendor.selection_type == "random_daily" and price is None:
                    # Find cheapest vendor that has this item
                    cheapest_vendor = None
                    cheapest_price = float('inf')

                    for v in game_state.vendors:
                        v_price = v.get_price(item_name)
                        if v_price and v_price < cheapest_price:
                            cheapest_price = v_price
                            cheapest_vendor = v

                    if cheapest_vendor:
                        vendor = cheapest_vendor
                        price = cheapest_price

                if price is not None:
                    active_orders.append((item_name, quantity, vendor, price))

    # Sort by price (cheapest first)
    active_orders.sort(key=lambda x: x[3])

    # Execute orders in order, respecting item limit
    for item_name, quantity, vendor, price in active_orders:
        if total_items_bought >= max_items:
            break  # Reached restocker limit

        # Limit quantity by remaining items restockers can handle
        remaining_capacity = max_items - total_items_bought
        actual_quantity = min(quantity, remaining_capacity)

        success = player.purchase_from_vendor(vendor, item_name, actual_quantity)
        if success:
            purchases[item_name] = actual_quantity
            total_items_bought += actual_quantity
        else:
            # Try to buy as many as possible with remaining cash
            max_affordable = int(player.cash / price)
            if max_affordable > 0:
                affordable_quantity = min(max_affordable, remaining_capacity)
                partial_success = player.purchase_from_vendor(vendor, item_name, affordable_quantity)
                if partial_success:
                    purchases[item_name] = affordable_quantity
                    total_items_bought += affordable_quantity

    return purchases


# -------------------------------------------------------------------
# Player strategies
# -------------------------------------------------------------------

def auto_setup_buy_orders(player: Player, items: List[Item], vendors: List[Vendor]) -> None:
    """
    Automatically set up buy orders for AI players.

    AI players will buy to maintain inventory of at least 10 units per item,
    always choosing the cheapest available vendor.
    """
    for item in items:
        current_inventory = player.inventory.get(item.name, 0)

        # Try to maintain inventory of at least 10 units per item
        target_inventory = 10
        quantity_to_buy = max(0, target_inventory - current_inventory)

        # Find cheapest vendor for this item
        cheapest_vendor = None
        cheapest_price = float('inf')

        for vendor in vendors:
            vendor_price = vendor.get_price(item.name)
            if vendor_price and vendor_price < cheapest_price:
                cheapest_price = vendor_price
                cheapest_vendor = vendor

        # Set buy order
        if cheapest_vendor and quantity_to_buy > 0:
            player.set_buy_order(item.name, quantity_to_buy, cheapest_vendor.name)
        else:
            player.set_buy_order(item.name, 0, "")


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
    1. Apply daily price fluctuations and special events
    2. Refresh vendor inventory based on new market prices
    3. Execute buy orders for all players (from cheapest to most expensive)
    4. Let AI players adjust prices
    5. For each customer, generate needs and make purchases (limited by cashier capacity)
    6. Pay employee wages
    7. Track statistics
    8. Advance the day counter

    Returns dictionary of daily sales per player.
    """

    if show_details:
        print(f"\n=== Day {game_state.day} ===")

    # Step 0: Unlock new product every 5 days
    if game_state.day % 5 == 0 and game_state.day > 0:
        new_product = unlock_new_product(game_state)
        if new_product and show_details:
            print(f"\n🎁 NEW PRODUCT UNLOCKED: {new_product.name} (${new_product.base_price:.2f})")
            print(f"   Total products available: {len(game_state.items)}")

    # Step 1: Apply price fluctuations and special events
    apply_daily_price_fluctuation(game_state.market_prices, game_state.items)

    # Check for special events
    if game_state.day % 30 == 0 and show_details:
        # 30-day event: one item -50%, one item +50%
        if len(game_state.items) >= 2:
            selected_items = random.sample(game_state.items, 2)
            # Item 1: -50%
            old_price1 = game_state.market_prices[selected_items[0].name]
            game_state.market_prices[selected_items[0].name] = old_price1 * 0.5
            # Item 2: +50%
            old_price2 = game_state.market_prices[selected_items[1].name]
            game_state.market_prices[selected_items[1].name] = old_price2 * 1.5
            print(f"\n🎉 SPECIAL EVENT! {selected_items[0].name} -50%, {selected_items[1].name} +50% today only!")

    # Calculate base customer count: num_players * 10 + day
    base_customer_count = len(game_state.players) * 10 + game_state.day

    # Check for 14-day event
    if game_state.day % 14 == 0:
        occurrence_count = game_state.day // 14
        bonus_customers = 20 * occurrence_count
        base_customer_count += bonus_customers
        if show_details:
            print(f"🎊 14-DAY EVENT! +{bonus_customers} customers today!")

    if show_details:
        print(f"Total customers today: {base_customer_count}")

    # Step 2: Refresh vendor inventory based on new market prices
    refresh_vendor_inventory(game_state.vendors, game_state.items, game_state.market_prices)

    # Step 3: Execute buy orders for ALL players
    if show_details:
        print("\nExecuting buy orders...")

    for player in game_state.players:
        purchases = execute_buy_orders(player, game_state)
        if show_details and purchases:
            total_spent = sum(
                game_state.get_vendor(player.get_buy_order(item)[1]).get_price(item) * qty
                if game_state.get_vendor(player.get_buy_order(item)[1])
                else 0
                for item, qty in purchases.items()
            )
            print(f"  {player.name}: Purchased {sum(purchases.values())} items")

    # Step 4: AI player decisions (pricing only, buying is handled by orders)
    for player in game_state.players:
        if not player.is_human:  # Only automate AI players
            # Set up AI buy orders if not already set
            if not player.buy_orders:
                auto_setup_buy_orders(player, game_state.items, game_state.vendors)
            auto_pricing_strategy(player, game_state.market_prices)

    # Track daily statistics
    daily_sales = {player.name: 0.0 for player in game_state.players}
    daily_profits = {player.name: 0.0 for player in game_state.players}
    customers_served = {player.name: 0 for player in game_state.players}
    unmet_demand = 0

    # Step 5: Simulate customers with cashier limits
    # Generate all customers for the day
    all_customers = []
    for i in range(base_customer_count):
        customer_type = random.choice(["low", "medium", "high"])
        customer = Customer(name=f"Customer_{i+1}", customer_type=customer_type)
        all_customers.append(customer)

    # Process each customer
    for customer in all_customers:
        needs = customer.generate_daily_needs(game_state.items)

        for need in needs:
            supplier = customer.choose_supplier(game_state.players, need.item_name, need.quantity)

            if supplier:
                # Check if supplier can serve this customer (cashier limit)
                if customers_served[supplier.name] < supplier.get_max_customers():
                    price = supplier.prices.get(need.item_name, 0)
                    revenue, profit = supplier.sell_to_customer(need.item_name, need.quantity, price)
                    if revenue > 0:
                        daily_sales[supplier.name] += revenue
                        daily_profits[supplier.name] += profit
                        customers_served[supplier.name] += 1
                else:
                    # Supplier at cashier capacity, track unmet demand
                    unmet_demand += need.quantity
            else:
                # Track unmet demand
                unmet_demand += need.quantity

    # Step 5.5: Award XP based on profit (before wages)
    level_ups = {}
    for player in game_state.players:
        profit = daily_profits[player.name]
        if profit > 0:
            leveled_up = player.add_experience(profit)
            if leveled_up:
                level_ups[player.name] = player.store_level

    # Step 6: Pay employee wages
    if show_details:
        print(f"\nPaying employee wages...")

    for player in game_state.players:
        wages = player.pay_daily_wages()
        if show_details:
            print(f"  {player.name}: ${wages:.2f} ({player.cashiers} cashiers + {player.restockers} restockers)")

    # Step 7: Print daily summary
    if show_details:
        print(f"\nDaily Results:")
        for player in game_state.players:
            sales = daily_sales[player.name]
            profit = daily_profits[player.name]
            served = customers_served[player.name]
            max_served = player.get_max_customers()
            xp_needed = player.get_xp_for_next_level()
            print(f"  {player.name}:")
            print(f"    Sales: ${sales:.2f} | Profit: ${profit:.2f} | XP: {player.experience:.0f}/{xp_needed:.0f}")
            print(f"    Customers: {served}/{max_served} | Cash: ${player.cash:.2f}")

            # Show level up if occurred
            if player.name in level_ups:
                print(f"    🎉 LEVEL UP! Now level {level_ups[player.name]} (max {player.get_max_products()} products)")

        if unmet_demand > 0:
            print(f"\nUnmet demand: {unmet_demand} items")

    # Step 8: Advance day counter
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
    print("\n" + "=" * 60)
    print(f"YOUR STORE: {player.name}")
    print("=" * 60)
    print(f"Cash: ${player.cash:.2f}")

    xp_needed = player.get_xp_for_next_level()
    print(f"\nStore Level: {player.store_level} (Max {player.get_max_products()} different products)")
    print(f"Experience: {player.experience:.0f}/{xp_needed:.0f} XP")

    print(f"\nEmployees:")
    print(f"  Cashiers: {player.cashiers} (Max {player.get_max_customers()} customers/day)")
    print(f"  Restockers: {player.restockers} (Max {player.get_max_items_per_day()} items/day)")
    total_employees = player.cashiers + player.restockers
    print(f"  Daily wages: ${total_employees * 20:.2f}")

    print(f"\nInventory ({len([i for i, q in player.inventory.items() if q > 0])}/{player.get_max_products()} products):")
    if player.inventory:
        for item_name, quantity in player.inventory.items():
            if quantity > 0:
                print(f"  {item_name}: {quantity} units")
    else:
        print("  (empty)")

    print(f"\nYour Prices:")
    if player.prices:
        for item_name, price in player.prices.items():
            print(f"  {item_name}: ${price:.2f}")
    else:
        print("  (no prices set)")
    print("=" * 60)


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


def buy_order_menu(game_state: GameState, player: Player) -> None:
    """Menu for setting buy orders (quantity and vendor selection per item)."""
    while True:
        print("\n" + "=" * 80)
        print("BUY ORDER MENU - Configure Automatic Purchasing")
        print("=" * 80)
        print("\nCurrent Buy Orders:")
        print(f"{'Item':<15} {'Quantity':>10} {'Vendor':<30}")
        print("-" * 80)

        for item in game_state.items:
            quantity, vendor_name = player.get_buy_order(item.name)
            vendor_display = vendor_name if vendor_name else "(none)"
            print(f"{item.name:<15} {quantity:>10} {vendor_display:<30}")

        print("\nSelect item to configure:")
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

                # Show vendor options
                print(f"\n=== Configuring Buy Order for {item.name} ===")
                print("\nAvailable Vendors:")
                available_vendors = []
                for i, vendor in enumerate(game_state.vendors, 1):
                    price = vendor.get_price(item.name)
                    if price:
                        print(f"  {i}. {vendor.name} - ${price:.2f}")
                        available_vendors.append((i, vendor))
                    else:
                        status = "(not in stock today)" if vendor.selection_type == "random_daily" else "(not available)"
                        print(f"  {i}. {vendor.name} - {status}")
                        available_vendors.append((i, vendor))

                vendor_choice = input(f"\nSelect vendor (1-{len(game_state.vendors)}): ")
                vendor_num = int(vendor_choice)

                if 1 <= vendor_num <= len(game_state.vendors):
                    selected_vendor = game_state.vendors[vendor_num - 1]

                    quantity_str = input(f"Enter quantity to buy (0 to skip): ")
                    quantity = int(quantity_str)

                    if quantity >= 0:
                        # Check product limit BEFORE setting buy order
                        if quantity > 0:
                            # Count how many different products will have quantity > 0
                            products_with_orders = 0
                            for check_item in game_state.items:
                                check_qty, _ = player.get_buy_order(check_item.name)
                                # Count this item if it will have quantity > 0
                                if check_item.name == item.name:
                                    if quantity > 0:
                                        products_with_orders += 1
                                else:
                                    if check_qty > 0:
                                        products_with_orders += 1

                            max_products = player.get_max_products()
                            if products_with_orders > max_products:
                                print(f"\n✗ Exceeded product limit! Your store can only stock {max_products} different products.")
                                print(f"   Please increase store level or reduce other buy orders.")
                                continue

                        player.set_buy_order(item.name, quantity, selected_vendor.name)
                        print(f"\n✓ Buy order set: {quantity} {item.name} from {selected_vendor.name}")
                    else:
                        print("\n✗ Quantity must be non-negative!")
                else:
                    print("\n✗ Invalid vendor selection!")
            else:
                print("\n✗ Invalid item selection!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def employee_menu(game_state: GameState, player: Player) -> None:
    """Menu for hiring employees."""
    HIRING_COST = 500.0
    DAILY_WAGE = 20.0

    while True:
        print("\n" + "=" * 60)
        print("EMPLOYEE MENU - Hire Staff")
        print("=" * 60)
        print(f"\nYour Cash: ${player.cash:.2f}")
        print(f"\nCurrent Employees:")
        print(f"  Cashiers: {player.cashiers} (Max {player.get_max_customers()} customers/day)")
        print(f"  Restockers: {player.restockers} (Max {player.get_max_items_per_day()} items/day)")
        total_employees = player.cashiers + player.restockers
        print(f"  Total daily wages: ${total_employees * DAILY_WAGE:.2f}")

        print(f"\nHiring Cost: ${HIRING_COST:.2f} per employee")
        print(f"Daily Wage: ${DAILY_WAGE:.2f} per employee")

        print("\nOptions:")
        print("  1. Hire Cashier (+10 customers/day capacity)")
        print("  2. Hire Restocker (+20 items/day capacity)")
        print("  0. Back to Main Menu")

        try:
            choice = input("\nSelect option (0-2): ")
            choice_num = int(choice)

            if choice_num == 0:
                break
            elif choice_num == 1:
                if player.cash < HIRING_COST:
                    print(f"\n✗ Not enough cash! Need ${HIRING_COST:.2f}, have ${player.cash:.2f}")
                else:
                    success = player.hire_employee("cashier")
                    if success:
                        print(f"\n✓ Hired 1 cashier for ${HIRING_COST:.2f}")
                        print(f"  New capacity: {player.get_max_customers()} customers/day")
                    else:
                        print("\n✗ Failed to hire cashier")
            elif choice_num == 2:
                if player.cash < HIRING_COST:
                    print(f"\n✗ Not enough cash! Need ${HIRING_COST:.2f}, have ${player.cash:.2f}")
                else:
                    success = player.hire_employee("restocker")
                    if success:
                        print(f"\n✓ Hired 1 restocker for ${HIRING_COST:.2f}")
                        print(f"  New capacity: {player.get_max_items_per_day()} items/day")
                    else:
                        print("\n✗ Failed to hire restocker")
            else:
                print("\n✗ Invalid option!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def upgrades_menu(game_state: GameState, player: Player) -> None:
    """Menu for purchasing store upgrades."""
    while True:
        print("\n" + "=" * 70)
        print("STORE UPGRADES MENU")
        print("=" * 70)
        print(f"\nYour Cash: ${player.cash:.2f}")

        # Show purchased upgrades
        if player.purchased_upgrades:
            print("\n📦 Your Upgrades:")
            for upgrade in player.purchased_upgrades:
                effect_desc = _get_upgrade_effect_description(upgrade)
                print(f"  ✓ {upgrade.name} - {effect_desc}")
        else:
            print("\n📦 No upgrades purchased yet")

        # Show available upgrades (not yet purchased)
        print("\n🛒 Available Upgrades:")
        available = []
        for i, upgrade in enumerate(game_state.available_upgrades, 1):
            # Check if already purchased
            already_purchased = any(u.name == upgrade.name for u in player.purchased_upgrades)
            if not already_purchased:
                effect_desc = _get_upgrade_effect_description(upgrade)
                print(f"  {i}. {upgrade.name} - ${upgrade.cost:.2f}")
                print(f"      Effect: {effect_desc}")
                available.append((i, upgrade))

        if not available:
            print("  (All upgrades purchased!)")

        print("\n  0. Back to Main Menu")

        try:
            if not available:
                input("\nPress Enter to continue...")
                break

            choice = input(f"\nSelect upgrade to purchase (0-{len(game_state.available_upgrades)}): ")
            choice_num = int(choice)

            if choice_num == 0:
                break

            # Find selected upgrade
            selected_upgrade = None
            for idx, upgrade in available:
                if idx == choice_num:
                    selected_upgrade = upgrade
                    break

            if selected_upgrade:
                if player.cash < selected_upgrade.cost:
                    print(f"\n✗ Not enough cash! Need ${selected_upgrade.cost:.2f}, have ${player.cash:.2f}")
                else:
                    success = player.purchase_upgrade(selected_upgrade)
                    if success:
                        effect_desc = _get_upgrade_effect_description(selected_upgrade)
                        print(f"\n✓ Purchased {selected_upgrade.name} for ${selected_upgrade.cost:.2f}!")
                        print(f"  Effect: {effect_desc}")
                    else:
                        print("\n✗ Failed to purchase upgrade")
            else:
                print("\n✗ Invalid upgrade selection!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def _get_upgrade_effect_description(upgrade: Upgrade) -> str:
    """Get a human-readable description of an upgrade's effect."""
    if upgrade.effect_type == "max_customers":
        return f"+{int(upgrade.effect_value)} max customers/day"
    elif upgrade.effect_type == "max_items":
        return f"+{int(upgrade.effect_value)} max items/day"
    elif upgrade.effect_type == "max_products":
        return f"+{int(upgrade.effect_value)} max product types"
    elif upgrade.effect_type == "xp_gain":
        return f"+{int(upgrade.effect_value)}% XP gain"
    elif upgrade.effect_type == "vendor_discount":
        return f"+{int(upgrade.effect_value)}% discount at {upgrade.vendor_name}"
    return "Unknown effect"


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
    player = game_state.human_players[game_state.current_player_index]

    while True:
        print("\n" + "=" * 50)
        print(f"MAIN MENU - Day {game_state.day}")
        print("=" * 50)
        print(f"Your Cash: ${player.cash:.2f}")
        print(f"Employees: {player.cashiers} cashiers, {player.restockers} restockers")
        print("\nOptions:")
        print("  1. Pass Day (Simulate)")
        print("  2. View Market Prices")
        print("  3. View Vendors")
        print("  4. Configure Buy Orders")
        print("  5. Set Your Prices")
        print("  6. Hire Employees")
        print("  7. View Your Store Status")
        print("  8. View Competitor Status")
        print("  9. Store Upgrades")
        print("  s. Save Game")
        print("  0. Quit Game")

        try:
            choice = input("\nSelect option (0-9, s): ").strip().lower()

            # Handle save command
            if choice == 's':
                if save_game(game_state):
                    print(f"\n✓ Game saved successfully to {SAVE_FILE}")
                else:
                    print("\n✗ Failed to save game")
                input("\nPress Enter to continue...")
                continue

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
                buy_order_menu(game_state, player)
            elif choice_num == 5:
                pricing_menu(game_state, player)
            elif choice_num == 6:
                employee_menu(game_state, player)
            elif choice_num == 7:
                display_player_status(player)
                input("\nPress Enter to continue...")
            elif choice_num == 8:
                print("\n" + "=" * 50)
                print("COMPETITOR STATUS")
                print("=" * 50)
                for p in game_state.players:
                    if p != player:
                        print(f"\n{p.name}:")
                        print(f"  Cash: ${p.cash:.2f}")
                        print(f"  Employees: {p.cashiers} cashiers, {p.restockers} restockers")
                        print(f"  Inventory: {dict(p.inventory)}")
                        print(f"  Prices: {dict(p.prices)}")
                print("=" * 50)
                input("\nPress Enter to continue...")
            elif choice_num == 9:
                upgrades_menu(game_state, player)
            else:
                print("\n✗ Invalid option!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


# -------------------------------------------------------------------
# Save/Load System
# -------------------------------------------------------------------

SAVE_FILE = "economy_sim_save.json"

def serialize_game_state(game_state: GameState) -> dict:
    """Convert GameState to a JSON-serializable dictionary."""
    return {
        "day": game_state.day,
        "current_player_index": game_state.current_player_index,
        "unlocked_product_indices": game_state.unlocked_product_indices,
        "config": {
            "starting_cash": game_state.config.starting_cash,
            "num_days": game_state.config.num_days,
            "customers_per_day": game_state.config.customers_per_day,
        },
        "items": [
            {"name": item.name, "base_cost": item.base_cost, "base_price": item.base_price}
            for item in game_state.items
        ],
        "market_prices": game_state.market_prices,
        "vendors": [
            {
                "name": vendor.name,
                "pricing_multiplier": vendor.pricing_multiplier,
                "selection_type": vendor.selection_type,
                "selection_params": vendor.selection_params,
                "items": vendor.items,
            }
            for vendor in game_state.vendors
        ],
        "players": [
            {
                "name": player.name,
                "cash": player.cash,
                "inventory": player.inventory,
                "prices": player.prices,
                "buy_orders": {k: list(v) for k, v in player.buy_orders.items()},
                "cashiers": player.cashiers,
                "restockers": player.restockers,
                "store_level": player.store_level,
                "experience": player.experience,
                "item_costs": player.item_costs,
                "purchased_upgrades": [
                    {
                        "name": upgrade.name,
                        "cost": upgrade.cost,
                        "effect_type": upgrade.effect_type,
                        "effect_value": upgrade.effect_value,
                        "vendor_name": upgrade.vendor_name,
                    }
                    for upgrade in player.purchased_upgrades
                ],
                "is_human": player.is_human,
            }
            for player in game_state.players
        ],
        "available_upgrades": [
            {
                "name": upgrade.name,
                "cost": upgrade.cost,
                "effect_type": upgrade.effect_type,
                "effect_value": upgrade.effect_value,
                "vendor_name": upgrade.vendor_name,
            }
            for upgrade in game_state.available_upgrades
        ],
    }


def deserialize_game_state(data: dict) -> GameState:
    """Load GameState from a JSON dictionary."""
    # Recreate config
    config = GameConfig(
        starting_cash=data["config"]["starting_cash"],
        num_days=data["config"]["num_days"],
        customers_per_day=data["config"]["customers_per_day"],
    )

    # Recreate items
    items = [
        Item(name=item_data["name"], base_cost=item_data["base_cost"], base_price=item_data["base_price"])
        for item_data in data["items"]
    ]

    # Recreate vendors
    vendors = [
        Vendor(
            name=vendor_data["name"],
            pricing_multiplier=vendor_data["pricing_multiplier"],
            selection_type=vendor_data["selection_type"],
            selection_params=vendor_data["selection_params"],
            items=vendor_data["items"],
        )
        for vendor_data in data["vendors"]
    ]

    # Recreate available upgrades
    available_upgrades = [
        Upgrade(
            name=upgrade_data["name"],
            cost=upgrade_data["cost"],
            effect_type=upgrade_data["effect_type"],
            effect_value=upgrade_data["effect_value"],
            vendor_name=upgrade_data.get("vendor_name", ""),
        )
        for upgrade_data in data["available_upgrades"]
    ]

    # Recreate players
    players = []
    for player_data in data["players"]:
        # Recreate purchased upgrades
        purchased_upgrades = [
            Upgrade(
                name=upgrade_data["name"],
                cost=upgrade_data["cost"],
                effect_type=upgrade_data["effect_type"],
                effect_value=upgrade_data["effect_value"],
                vendor_name=upgrade_data.get("vendor_name", ""),
            )
            for upgrade_data in player_data["purchased_upgrades"]
        ]

        # Convert buy_orders back to tuples
        buy_orders = {k: tuple(v) for k, v in player_data["buy_orders"].items()}

        player = Player(
            name=player_data["name"],
            cash=player_data["cash"],
            inventory=player_data["inventory"],
            prices=player_data["prices"],
            buy_orders=buy_orders,
            cashiers=player_data["cashiers"],
            restockers=player_data["restockers"],
            store_level=player_data["store_level"],
            experience=player_data["experience"],
            item_costs=player_data["item_costs"],
            purchased_upgrades=purchased_upgrades,
            is_human=player_data["is_human"],
        )
        players.append(player)

    # Separate human and AI players
    human_players = [p for p in players if p.is_human]

    # Create GameState
    game_state = GameState(
        day=data["day"],
        players=players,
        customers=[],  # Customers are generated dynamically
        items=items,
        vendors=vendors,
        market_prices=data["market_prices"],
        config=config,
        human_players=human_players,
        available_upgrades=available_upgrades,
        current_player_index=data["current_player_index"],
        unlocked_product_indices=data.get("unlocked_product_indices", []),
    )

    return game_state


def save_game(game_state: GameState, filename: str = SAVE_FILE) -> bool:
    """
    Save the current game state to a JSON file.
    Returns True if successful, False otherwise.
    """
    try:
        data = serialize_game_state(game_state)
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"\n✗ Error saving game: {e}")
        return False


def load_game(filename: str = SAVE_FILE) -> Optional[GameState]:
    """
    Load game state from a JSON file.
    Returns GameState if successful, None otherwise.
    """
    try:
        if not os.path.exists(filename):
            return None

        with open(filename, 'r') as f:
            data = json.load(f)

        game_state = deserialize_game_state(data)
        return game_state
    except Exception as e:
        print(f"\n✗ Error loading game: {e}")
        return None


# Global variable to store game state for signal handler
_current_game_state: Optional[GameState] = None


def signal_handler(sig, frame):
    """Handle Ctrl+C by auto-saving the game."""
    global _current_game_state
    print("\n\n🛑 Ctrl+C detected! Auto-saving game...")

    if _current_game_state is not None:
        if save_game(_current_game_state):
            print(f"✓ Game saved successfully to {SAVE_FILE}")
        else:
            print("✗ Failed to save game")
    else:
        print("No game state to save")

    print("\nExiting game. Thanks for playing!")
    sys.exit(0)


# -------------------------------------------------------------------
# Main simulation loop
# -------------------------------------------------------------------

def run_game() -> None:
    """
    Top-level function to run the interactive economy simulation game.
    """
    global _current_game_state

    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("\n" + "=" * 60)
    print("WELCOME TO ECONOMY SIMULATION")
    print("=" * 60)
    print("\nIn this game, you run a store competing against AI players.")
    print("You'll purchase items from vendors and sell them to customers.")
    print("The market prices fluctuate daily, so timing is everything!")
    print("\n" + "=" * 60)

    # Check if save file exists
    game_state = None
    if os.path.exists(SAVE_FILE):
        print(f"\n💾 Found existing save file: {SAVE_FILE}")
        load_choice = input("Would you like to load it? (y/n): ").strip().lower()
        if load_choice == 'y':
            game_state = load_game()
            if game_state:
                print("✓ Game loaded successfully!")
                _current_game_state = game_state
            else:
                print("✗ Failed to load game. Starting new game...")
                game_state = None

    # If no save loaded, start new game
    if game_state is None:
        # Create game configuration
        config = GameConfig()
        config.num_days = 365  # Run for a full year

        # Get number of human players
        while True:
            try:
                num_humans_str = input("\nHow many human players? (1-4): ").strip()
                num_humans = int(num_humans_str)
                if 1 <= num_humans <= 4:
                    break
                else:
                    print("Please enter a number between 1 and 4")
            except ValueError:
                print("Invalid input. Please enter a number.")

        # Get names for human players
        human_players = []
        for i in range(num_humans):
            player_name = input(f"\nEnter name for Player {i+1}: ").strip()
            if not player_name:
                player_name = f"Player {i+1}"
            human_player = Player(name=player_name, cash=config.starting_cash, is_human=True)
            human_players.append(human_player)

        print(f"\nStarting cash: ${config.starting_cash:.2f}")
        print(f"Customers formula: (num_players × 10) + day_number")

        # Initialize items, vendors
        items = create_default_items()
        vendors = create_vendors()
        market_prices = initialize_market_prices(items)

        # Initialize vendor inventory for day 1
        refresh_vendor_inventory(vendors, items, market_prices)

        # Create AI players
        ai_players = create_players(["Alice Corp", "Bob Ltd"], config.starting_cash)
        all_players = human_players + ai_players

        # Create available upgrades
        available_upgrades = create_default_upgrades(vendors)

        # Create GameState (customers generated dynamically each day)
        game_state = GameState(
            day=1,
            players=all_players,
            customers=[],  # Customers generated dynamically in run_day()
            items=items,
            vendors=vendors,
            market_prices=market_prices,
            config=config,
            human_players=human_players,
            available_upgrades=available_upgrades,
            current_player_index=0,
            unlocked_product_indices=[0, 1, 2],  # Start with first 3 products unlocked
        )

        # Set global game state for signal handler
        _current_game_state = game_state

        # Show initial setup
        print("\n" + "=" * 60)
        print("GAME SETUP COMPLETE")
        print("=" * 60)
        print(f"\nHuman Players:")
        for player in human_players:
            print(f"  - {player.name}")

        print(f"\nAI Competitors:")
        for player in ai_players:
            print(f"  - {player.name}")

        print(f"\nAvailable Items:")
        for item in items:
            print(f"  - {item.name} (Base: ${item.base_cost:.2f})")

        print(f"\nVendors:")
        for vendor in vendors:
            print(f"  - {vendor.name}")

        input("\nPress Enter to start the game...")
    else:
        # Game loaded from save, show current status
        print("\n" + "=" * 60)
        print("LOADED GAME STATUS")
        print("=" * 60)
        print(f"\nCurrent Day: {game_state.day}")
        print(f"\nPlayers:")
        for player in game_state.players:
            status = " (YOU)" if player.is_human else " (AI)"
            print(f"  - {player.name}{status}: ${player.cash:.2f}")
        input("\nPress Enter to continue...")

    # Main game loop
    game_running = True
    while game_running and game_state.day <= game_state.config.num_days:
        # Let each human player take their turn
        for i, player in enumerate(game_state.human_players):
            game_state.current_player_index = i
            if not game_running:
                break

            if len(game_state.human_players) > 1:
                print(f"\n{'='*60}")
                print(f"  {player.name}'s Turn")
                print(f"{'='*60}")

            game_running = main_menu(game_state)

            # If player chose "Pass Day", break the turn loop so we don't have
            # multiple players acting on the same day
            if not game_running:
                break

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
    if winner.is_human:
        print("🎉 CONGRATULATIONS! YOU WON! 🎉")
    else:
        print(f"Winner: {winner.name}")
    print(f"Final cash: ${winner.cash:.2f}")
    print("=" * 60)


if __name__ == "__main__":
    run_game()
