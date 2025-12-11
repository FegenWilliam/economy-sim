# econ_sim.py

"""
Economic simulation where players compete to capture customers
by selling items. Each customer has daily item needs that are
randomly generated. A day counter tracks overall progress.

This file is mostly TODOs to be filled in by an AI code assistant.
"""


from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
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

    def __post_init__(self):
        """Validate that base_price and base_cost have a reasonable ratio."""
        if self.base_cost <= 0:
            raise ValueError(f"Item {self.name}: base_cost must be positive, got {self.base_cost}")
        if self.base_price <= 0:
            raise ValueError(f"Item {self.name}: base_price must be positive, got {self.base_price}")
        # Ensure base_price is at least 1.2x base_cost to avoid price bound contradictions
        # (Market price fluctuation uses max(base_cost * 1.2, min(price, base_price * 2.0)))
        if self.base_price < self.base_cost * 1.2:
            raise ValueError(
                f"Item {self.name}: base_price ({self.base_price}) must be at least "
                f"1.2x base_cost ({self.base_cost * 1.2:.2f}) to avoid pricing contradictions"
            )


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

    # More Groceries & Food
    Item("Peanut Butter", 4.0, 8.0),
    Item("Jelly", 3.0, 6.0),
    Item("Honey", 5.0, 10.0),
    Item("Maple Syrup", 6.0, 12.0),
    Item("Crackers", 3.0, 6.0),
    Item("Chips", 2.5, 5.0),
    Item("Pretzels", 2.5, 5.0),
    Item("Popcorn", 2.0, 4.0),
    Item("Cookies", 3.5, 7.0),
    Item("Cake Mix", 3.0, 6.0),
    Item("Brownie Mix", 3.0, 6.0),
    Item("Chocolate Bar", 1.5, 3.0),
    Item("Candy", 1.0, 2.5),
    Item("Gum", 1.0, 2.5),
    Item("Mints", 1.5, 3.0),
    Item("Granola Bars", 4.0, 8.0),
    Item("Energy Bars", 5.0, 10.0),
    Item("Protein Powder", 25.0, 50.0),
    Item("Vitamins", 12.0, 24.0),
    Item("Fish Oil", 15.0, 30.0),
    Item("Canned Tuna", 1.5, 3.5),
    Item("Canned Beans", 1.5, 3.5),
    Item("Canned Corn", 1.5, 3.5),
    Item("Canned Tomatoes", 2.0, 4.0),
    Item("Tomato Sauce", 2.0, 4.5),
    Item("Spaghetti Sauce", 3.0, 6.5),
    Item("Hot Sauce", 2.5, 5.5),
    Item("Soy Sauce", 3.0, 6.0),
    Item("Vinegar", 2.0, 4.5),
    Item("Olive Oil", 8.0, 16.0),
    Item("Coconut Oil", 9.0, 18.0),
    Item("Protein Shake", 4.0, 8.0),
    Item("Sports Drink", 2.0, 4.5),
    Item("Energy Drink", 3.0, 6.0),
    Item("Bottled Water", 1.0, 2.5),
    Item("Sparkling Water", 1.5, 3.5),
    Item("Iced Tea", 2.0, 4.5),
    Item("Lemonade", 2.5, 5.5),

    # Pet Supplies
    Item("Dog Food", 15.0, 30.0),
    Item("Cat Food", 12.0, 24.0),
    Item("Dog Treats", 5.0, 10.0),
    Item("Cat Treats", 4.0, 8.0),
    Item("Dog Toy", 6.0, 12.0),
    Item("Cat Toy", 4.0, 8.0),
    Item("Pet Bowl", 8.0, 16.0),
    Item("Pet Collar", 10.0, 20.0),
    Item("Pet Leash", 12.0, 24.0),
    Item("Cat Litter", 10.0, 20.0),
    Item("Fish Tank", 40.0, 80.0),
    Item("Fish Food", 4.0, 8.0),
    Item("Bird Cage", 50.0, 100.0),
    Item("Bird Seed", 6.0, 12.0),

    # Baby Products
    Item("Diapers", 20.0, 40.0),
    Item("Baby Wipes", 5.0, 10.0),
    Item("Baby Formula", 25.0, 50.0),
    Item("Baby Bottle", 8.0, 16.0),
    Item("Pacifier", 4.0, 8.0),
    Item("Baby Lotion", 6.0, 12.0),
    Item("Baby Shampoo", 5.0, 10.0),
    Item("Baby Powder", 4.0, 8.0),
    Item("Diaper Bag", 30.0, 60.0),
    Item("Baby Blanket", 15.0, 30.0),
    Item("Teething Ring", 5.0, 10.0),

    # Pharmacy & Health
    Item("Pain Reliever", 8.0, 16.0),
    Item("Cold Medicine", 10.0, 20.0),
    Item("Allergy Medicine", 12.0, 24.0),
    Item("Band-Aids", 4.0, 8.0),
    Item("First Aid Kit", 20.0, 40.0),
    Item("Thermometer", 15.0, 30.0),
    Item("Cough Drops", 3.0, 6.0),
    Item("Antacid", 6.0, 12.0),
    Item("Eye Drops", 8.0, 16.0),
    Item("Lip Balm", 2.0, 4.5),
    Item("Sunscreen", 10.0, 20.0),
    Item("Bug Spray", 7.0, 14.0),

    # Kitchen & Dining
    Item("Plates Set", 20.0, 40.0),
    Item("Bowls Set", 15.0, 30.0),
    Item("Cups Set", 12.0, 24.0),
    Item("Silverware Set", 25.0, 50.0),
    Item("Cooking Pot", 30.0, 60.0),
    Item("Frying Pan", 25.0, 50.0),
    Item("Baking Sheet", 12.0, 24.0),
    Item("Mixing Bowl", 10.0, 20.0),
    Item("Cutting Board", 15.0, 30.0),
    Item("Kitchen Knife", 20.0, 40.0),
    Item("Can Opener", 8.0, 16.0),
    Item("Bottle Opener", 5.0, 10.0),
    Item("Measuring Cups", 10.0, 20.0),
    Item("Measuring Spoons", 8.0, 16.0),
    Item("Spatula", 7.0, 14.0),
    Item("Whisk", 6.0, 12.0),
    Item("Tongs", 8.0, 16.0),
    Item("Ladle", 7.0, 14.0),
    Item("Colander", 12.0, 24.0),
    Item("Grater", 10.0, 20.0),

    # Home Decor
    Item("Picture Frame", 12.0, 24.0),
    Item("Wall Art", 25.0, 50.0),
    Item("Throw Pillow", 15.0, 30.0),
    Item("Blanket", 25.0, 50.0),
    Item("Curtains", 30.0, 60.0),
    Item("Area Rug", 60.0, 120.0),
    Item("Table Lamp", 35.0, 70.0),
    Item("Floor Lamp", 50.0, 100.0),
    Item("Wall Clock", 20.0, 40.0),
    Item("Vase", 18.0, 36.0),
    Item("Candle Holder", 12.0, 24.0),
    Item("Plant Pot", 10.0, 20.0),
    Item("Fake Plant", 15.0, 30.0),
    Item("Mirror", 40.0, 80.0),

    # Garden & Outdoor
    Item("Garden Hose", 25.0, 50.0),
    Item("Sprinkler", 20.0, 40.0),
    Item("Garden Gloves", 8.0, 16.0),
    Item("Plant Seeds", 3.0, 6.0),
    Item("Fertilizer", 12.0, 24.0),
    Item("Potting Soil", 10.0, 20.0),
    Item("Weed Killer", 15.0, 30.0),
    Item("Lawn Mower", 200.0, 400.0),
    Item("Rake", 18.0, 36.0),
    Item("Shovel", 22.0, 44.0),
    Item("Garden Shears", 15.0, 30.0),
    Item("Watering Can", 12.0, 24.0),
    Item("BBQ Grill", 150.0, 300.0),
    Item("Charcoal", 10.0, 20.0),
    Item("Lighter Fluid", 6.0, 12.0),
    Item("Patio Furniture", 250.0, 500.0),

    # Toys & Games
    Item("Board Game", 20.0, 40.0),
    Item("Puzzle", 15.0, 30.0),
    Item("Playing Cards", 5.0, 10.0),
    Item("Action Figure", 12.0, 24.0),
    Item("Doll", 18.0, 36.0),
    Item("Stuffed Animal", 15.0, 30.0),
    Item("Building Blocks", 25.0, 50.0),
    Item("Art Supplies", 20.0, 40.0),
    Item("Crayons", 4.0, 8.0),
    Item("Coloring Book", 5.0, 10.0),
    Item("Play-Doh", 8.0, 16.0),
    Item("Remote Control Car", 40.0, 80.0),
    Item("Nerf Gun", 25.0, 50.0),
    Item("Water Gun", 10.0, 20.0),
    Item("Frisbee", 8.0, 16.0),
    Item("Soccer Ball", 18.0, 36.0),
    Item("Football", 20.0, 40.0),
    Item("Baseball Glove", 35.0, 70.0),
    Item("Baseball Bat", 30.0, 60.0),

    # Car Accessories
    Item("Car Phone Mount", 15.0, 30.0),
    Item("Car Charger", 12.0, 24.0),
    Item("Jumper Cables", 25.0, 50.0),
    Item("Car Air Freshener", 3.0, 6.0),
    Item("Windshield Wiper", 18.0, 36.0),
    Item("Motor Oil", 20.0, 40.0),
]


@dataclass
class Vendor:
    """A vendor that sells items to players at wholesale prices."""
    name: str
    pricing_multiplier: float = 1.0  # Multiplier applied to market price (e.g., 0.7 = 70% of market)
    selection_type: str = "all"  # "random_daily", "price_threshold", "price_range", "all"
    selection_params: float = 0.0  # For random_daily: count of items. For price_threshold: max price
    items: Dict[str, float] = field(default_factory=dict)  # item_name -> wholesale_price (refreshed daily)
    max_per_item_per_player: Optional[int] = None  # Max quantity per item per player per day (None = unlimited)
    min_purchase: Optional[int] = None  # Minimum quantity per purchase (None = no minimum)
    price_min: Optional[float] = None  # Minimum price threshold (None = no minimum)
    price_max: Optional[float] = None  # Maximum price threshold (None = no maximum)

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
    duration_days: int = 0  # Duration in days (0 = permanent, >0 = temporary)


@dataclass
class Player:
    """Represents a company / player in the economic simulation."""
    name: str
    cash: float = 0.0
    inventory: Dict[str, int] = field(default_factory=dict)  # item_name -> quantity
    prices: Dict[str, float] = field(default_factory=dict)   # item_name -> selling price
    buy_orders: Dict[str, tuple] = field(default_factory=dict)  # item_name -> (quantity, vendor_name)
    cashiers: int = 0  # Each cashier handles 10 customers per day
    restockers: int = 0  # Each restocker handles 20 items per day
    store_level: int = 1  # Limits how many different products can be stocked (starts at 3)
    experience: float = 0.0  # XP gained from profits
    item_costs: Dict[str, float] = field(default_factory=dict)  # Track cost per item for profit calculation
    purchased_upgrades: List['Upgrade'] = field(default_factory=list)  # Upgrades bought by this player
    is_human: bool = False  # Whether this is a human-controlled player
    # Sales tracking for AI pricing strategy (yesterday's results)
    daily_sales_data: Dict[str, Dict[str, any]] = field(default_factory=dict)  # item_name -> {units_sold, revenue, sold_out}
    last_wage_payment_day: int = 0  # Track when wages were last paid (for 30-day wage cycle)
    vendor_partnership_expiration: Dict[str, int] = field(default_factory=dict)  # upgrade_name -> expiration_day (for temporary vendor partnerships)

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
        base = 10 + (self.cashiers * 10)  # Base 10 customers + 10 per cashier
        bonus = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "max_customers")
        return int(base + bonus)

    def get_max_items_per_day(self) -> int:
        """Get max number of items that can be restocked per day."""
        base = 20 + (self.restockers * 20)  # Base 20 items + 20 per restocker
        bonus = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "max_items")
        return int(base + bonus)

    def get_xp_multiplier(self) -> float:
        """Get XP gain multiplier from upgrades."""
        bonus_percent = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "xp_gain")
        return 1.0 + (bonus_percent / 100.0)

    def get_vendor_discount(self, vendor_name: str, current_day: int = 0) -> float:
        """Get discount percentage for a specific vendor, checking expiration for temporary upgrades."""
        discount = 0
        for u in self.purchased_upgrades:
            if u.effect_type == "vendor_discount" and u.vendor_name == vendor_name:
                # Check if upgrade has expired
                if u.duration_days > 0:  # Temporary upgrade
                    expiration_day = self.vendor_partnership_expiration.get(u.name, 0)
                    if current_day > 0 and current_day >= expiration_day:
                        continue  # Expired, skip this upgrade
                discount += u.effect_value
        return discount / 100.0  # Convert percentage to decimal

    def has_production_line(self, item_name: str) -> bool:
        """Check if player owns a production line for a specific item."""
        return any(u.effect_type == "production_line" and u.vendor_name == item_name
                  for u in self.purchased_upgrades)

    def get_production_line_price(self, item_name: str, market_price: float) -> Optional[float]:
        """Get the production line price (50% of market price) if owned."""
        if self.has_production_line(item_name):
            return market_price * 0.5
        return None

    def purchase_upgrade(self, upgrade: 'Upgrade', current_day: int = 0) -> bool:
        """
        Purchase an upgrade if player has enough cash.
        Returns True if successful, False otherwise.
        For vendor partnerships, allows re-purchasing to extend duration.
        For other upgrades, prevents purchasing the same upgrade twice.
        """
        # Check if already purchased (by name for standard upgrades, or by production line item)
        if upgrade.effect_type == "production_line":
            # For production lines, check if we already have one for this vendor
            if self.has_production_line(upgrade.vendor_name):
                return False
        elif upgrade.effect_type == "vendor_discount":
            # For vendor partnerships, allow re-purchasing but check stacking limit (max 15%)
            existing_discount = self.get_vendor_discount(upgrade.vendor_name, current_day)
            if existing_discount >= 0.15:  # Max 15% discount
                return False
        else:
            # For other upgrades, check by name
            already_purchased = any(u.name == upgrade.name for u in self.purchased_upgrades)
            if already_purchased:
                return False

        if self.cash < upgrade.cost:
            return False

        self.cash -= upgrade.cost
        self.purchased_upgrades.append(upgrade)

        # Set expiration date for temporary upgrades
        if upgrade.duration_days > 0 and current_day > 0:
            self.vendor_partnership_expiration[upgrade.name] = current_day + upgrade.duration_days

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

    def pay_monthly_wages(self, current_day: int) -> float:
        """
        Pay monthly wages for all employees ($500 per employee every 30 days).
        Only pays if 30 days have passed since last payment.
        Returns total wages paid (0 if not a payment day).
        """
        # Check if it's time to pay wages (every 30 days)
        if current_day - self.last_wage_payment_day < 30:
            return 0.0

        total_employees = self.cashiers + self.restockers

        # No wages if no employees
        if total_employees == 0:
            return 0.0

        monthly_wage_per_employee = 500.0

        # Apply wage reduction upgrades (still applies to monthly wage)
        wage_reduction = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "wage_reduction")
        actual_wage = max(0, monthly_wage_per_employee - wage_reduction)

        wages = total_employees * actual_wage
        self.cash -= wages
        self.last_wage_payment_day = current_day
        return wages

    def set_price(self, item_name: str, price: float) -> None:
        """
        Set the selling price for an item in the player's store.
        """
        if price <= 0:
            raise ValueError(f"Price must be positive: {price}")
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

        # Update weighted average cost for profit tracking
        current_inventory = self.inventory.get(item.name, 0)
        current_cost = self.item_costs.get(item.name, 0)
        new_total_qty = current_inventory + quantity
        if new_total_qty > 0:
            weighted_cost = ((current_inventory * current_cost) + (quantity * item.base_cost)) / new_total_qty
            self.item_costs[item.name] = weighted_cost

        self.inventory[item.name] = current_inventory + quantity

    def sell_to_customer(self, item_name: str, quantity: int, unit_price: float) -> tuple:
        """
        Attempt to sell 'quantity' units of 'item_name' at 'unit_price'.
        Returns (revenue, profit, units_sold) tuple.
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

            # Award +1 XP for each item sold (helps with leveling regardless of profit)
            self.add_experience(units_sold * 1.0)

            return (revenue, profit, units_sold)

        return (0.0, 0.0, 0)

    def purchase_from_vendor(self, vendor: 'Vendor', item_name: str, quantity: int, market_price: float = 0,
                            game_state: Optional['GameState'] = None) -> bool:
        """
        Purchase items from a vendor at their wholesale price.
        Returns True if successful, False if not enough cash.
        Also tracks the weighted average cost per item for profit calculation.
        Applies vendor discount upgrades and production line pricing.
        Enforces vendor-specific purchase limits (min/max per player).
        """
        if quantity <= 0:
            return False

        # Check minimum purchase requirement
        if vendor.min_purchase is not None and quantity < vendor.min_purchase:
            return False

        # Check maximum per-item-per-player limit
        if vendor.max_per_item_per_player is not None and game_state is not None:
            # Initialize tracking if needed
            if self.name not in game_state.vendor_daily_purchases:
                game_state.vendor_daily_purchases[self.name] = {}
            if vendor.name not in game_state.vendor_daily_purchases[self.name]:
                game_state.vendor_daily_purchases[self.name][vendor.name] = {}

            # Get current purchases for this item today
            current_purchases = game_state.vendor_daily_purchases[self.name][vendor.name].get(item_name, 0)

            # Check if this purchase would exceed the limit
            if current_purchases + quantity > vendor.max_per_item_per_player:
                return False

        # Check if player owns production line for this item (takes priority)
        production_price = self.get_production_line_price(item_name, market_price) if market_price > 0 else None

        if production_price is not None:
            # Use production line pricing (50% of market)
            final_price = production_price
        else:
            # Use vendor pricing
            vendor_price = vendor.get_price(item_name)
            if vendor_price is None:
                return False

            # Apply vendor discount
            current_day = game_state.day if game_state else 0
            discount = self.get_vendor_discount(vendor.name, current_day)
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

        # Track purchase for max-per-player limits
        if vendor.max_per_item_per_player is not None and game_state is not None:
            game_state.vendor_daily_purchases[self.name][vendor.name][item_name] = \
                game_state.vendor_daily_purchases[self.name][vendor.name].get(item_name, 0) + quantity

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
    customer_type: str = "medium"  # "low", "medium", "high", "uncapped", "hoarder", "rich_guy", "poor_man", "kid"
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
            elif self.customer_type == "uncapped":
                self.budget = 10000.0  # Effectively unlimited for 1 expensive item
            elif self.customer_type == "hoarder":
                self.budget = 40.0
            elif self.customer_type == "rich_guy":
                self.budget = 400.0
            elif self.customer_type == "poor_man":
                self.budget = 10.0
            elif self.customer_type == "kid":
                self.budget = 10.0

    def generate_daily_needs(self, available_items: List[Item], market_prices: Dict[str, float] = None, item_demand: Dict[str, float] = None) -> List[CustomerNeed]:
        """
        Generate a random set of item needs for the day based on budget.
        Uses item demand as weights for selection - higher demand items are more likely to be chosen.

        For uncapped customers: only buy 1 expensive item (base_price >= 100).
        For hoarder: buys 3-10 of 1 item only (budget $40).
        For rich_guy: buys only items >$50, normal quantity (budget $400).
        For poor_man: buys exactly 1 item <$10 (budget $10).
        For kid: buys exactly 2 items <$5 (budget $10).
        For other customers: randomly selects items and quantities.
        """
        if not available_items:
            return []

        # Default to equal demand if not provided
        if item_demand is None:
            item_demand = {}

        needs = []

        # Uncapped customers buy exactly 1 expensive item
        if self.customer_type == "uncapped":
            expensive_items = [item for item in available_items if item.base_price >= 100]
            if expensive_items:
                selected_item = weighted_random_choice(expensive_items, item_demand)
                if selected_item:
                    needs.append(CustomerNeed(item_name=selected_item.name, quantity=1))
            return needs

        # Hoarder: buys 3-10 of 1 item only
        if self.customer_type == "hoarder":
            # Filter items that fit within budget for at least 3 units
            affordable_items = [item for item in available_items if item.base_price * 3 <= self.budget]
            if affordable_items:
                selected_item = weighted_random_choice(affordable_items, item_demand)
                if selected_item:
                    max_qty = min(10, int(self.budget / selected_item.base_price))
                    quantity = random.randint(3, max_qty)
                    needs.append(CustomerNeed(item_name=selected_item.name, quantity=quantity))
            return needs

        # Rich Guy: buys only items that cost >$50 (uses market prices if available, else base price)
        if self.customer_type == "rich_guy":
            if market_prices:
                expensive_items = [item for item in available_items
                                 if market_prices.get(item.name, item.base_price) > 50.0]
            else:
                expensive_items = [item for item in available_items if item.base_price > 50.0]

            if expensive_items:
                remaining_budget = self.budget
                # Buy 1-3 different expensive items
                num_item_types = random.randint(1, min(3, len(expensive_items)))
                selected_items = weighted_random_sample(expensive_items, item_demand, num_item_types)

                for item in selected_items:
                    price = market_prices.get(item.name, item.base_price) if market_prices else item.base_price
                    max_affordable = int(remaining_budget / price)
                    if max_affordable > 0:
                        quantity = random.randint(1, min(2, max_affordable))
                        needs.append(CustomerNeed(item_name=item.name, quantity=quantity))
                        remaining_budget -= quantity * price
            return needs

        # Poor Man: buys exactly 1 item that costs <$10
        if self.customer_type == "poor_man":
            if market_prices:
                cheap_items = [item for item in available_items
                             if market_prices.get(item.name, item.base_price) < 10.0]
            else:
                cheap_items = [item for item in available_items if item.base_price < 10.0]

            if cheap_items:
                selected_item = weighted_random_choice(cheap_items, item_demand)
                if selected_item:
                    needs.append(CustomerNeed(item_name=selected_item.name, quantity=1))
            return needs

        # A Kid: buys exactly 2 items that cost <$5
        if self.customer_type == "kid":
            if market_prices:
                kid_items = [item for item in available_items
                           if market_prices.get(item.name, item.base_price) < 5.0]
            else:
                kid_items = [item for item in available_items if item.base_price < 5.0]

            if len(kid_items) >= 2:
                selected_items = weighted_random_sample(kid_items, item_demand, 2)
                for item in selected_items:
                    needs.append(CustomerNeed(item_name=item.name, quantity=1))
            elif len(kid_items) == 1:
                # If only one item available, buy 2 of the same
                needs.append(CustomerNeed(item_name=kid_items[0].name, quantity=2))
            return needs

        # Regular customers (low, medium, high)
        remaining_budget = self.budget

        # Decide how many different item types to buy (1 to 3)
        num_item_types = random.randint(1, min(3, len(available_items)))
        selected_items = weighted_random_sample(available_items, item_demand, num_item_types)

        for item in selected_items:
            # Calculate max quantity we can afford
            if item.base_price <= 0:
                continue  # Skip items with invalid pricing
            max_affordable = int(remaining_budget / item.base_price)
            if max_affordable > 0:
                # Buy between 1 and min(2, max_affordable) units - most customers buy 1-2 of each item
                quantity = random.randint(1, min(2, max_affordable))
                needs.append(CustomerNeed(item_name=item.name, quantity=quantity))
                remaining_budget -= quantity * item.base_price

        return needs

    def choose_supplier(
        self,
        players: List[Player],
        item_name: str,
        quantity: int,
        market_prices: Dict[str, float]
    ) -> Optional[Player]:
        """
        Decide which player to buy from for a given item and quantity.

        Chooses the player with the lowest price who has at least some stock.
        Customers will only buy if the price is within 15% of market price.
        Breaks ties randomly.
        """
        candidates = []
        market_price = market_prices.get(item_name, float('inf'))
        max_acceptable_price = market_price * 1.15  # 15% above market price

        for player in players:
            # Check if player has this item in stock
            if player.inventory.get(item_name, 0) > 0:
                # Check if player has set a price
                if item_name in player.prices:
                    price = player.prices[item_name]
                    # Only consider if price is within 15% of market price
                    if price <= max_acceptable_price:
                        candidates.append((player, price))

        if not candidates:
            return None

        # Find the lowest price
        min_price = min(price for _, price in candidates)

        # Get all players with the lowest price
        best_players = [player for player, price in candidates if price == min_price]

        # Return random player from best options
        return random.choice(best_players)

    def get_all_suppliers_sorted(
        self,
        players: List[Player],
        item_name: str,
        quantity: int,
        market_prices: Dict[str, float]
    ) -> List[Player]:
        """
        Get all valid suppliers for an item, sorted by price (lowest first).

        Returns a list of players who have stock and acceptable prices,
        sorted from cheapest to most expensive.
        """
        candidates = []
        market_price = market_prices.get(item_name, float('inf'))
        max_acceptable_price = market_price * 1.15  # 15% above market price

        for player in players:
            # Check if player has this item in stock
            if player.inventory.get(item_name, 0) > 0:
                # Check if player has set a price
                if item_name in player.prices:
                    price = player.prices[item_name]
                    # Only consider if price is within 15% of market price
                    if price <= max_acceptable_price:
                        candidates.append((player, price))

        if not candidates:
            return []

        # Sort by price (lowest first), with random tiebreaking
        random.shuffle(candidates)  # Shuffle first for random tiebreaking
        candidates.sort(key=lambda x: x[1])

        # Return just the players
        return [player for player, price in candidates]


# -------------------------------------------------------------------
# Game / simulation engine
# -------------------------------------------------------------------

@dataclass
class GameConfig:
    """Configuration for the economic simulation."""
    starting_cash: float = 2500.0
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
    event_price_changes: Dict[str, float] = field(default_factory=dict)  # Tracks items with temporary event prices and their original prices
    item_demand: Dict[str, float] = field(default_factory=dict)  # item_name -> demand multiplier (0.1 to 2.0)
    vendor_daily_purchases: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=dict)  # player_name -> vendor_name -> item_name -> quantity_today
    players_passed: Set[int] = field(default_factory=set)  # Set of player indices who have passed their turn

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
    Price limits by day:
    - Before day 15: only items with base_price <= 10
    - Day 15-29: only items with base_price <= 20
    - Day 30-49: only items with base_price <= 100
    - Day 50+: can unlock any item

    Returns the unlocked Item or None if no valid items available.
    """
    # Get indices of products not yet unlocked
    available_indices = [
        i for i in range(len(PRODUCT_CATALOG))
        if i not in game_state.unlocked_product_indices
    ]

    if not available_indices:
        return None  # All products unlocked

    # Filter by price threshold based on game day
    if game_state.day < 15:
        max_price = 10
    elif game_state.day < 30:
        max_price = 20
    elif game_state.day < 50:
        max_price = 100
    else:
        max_price = float('inf')  # No limit

    if max_price != float('inf'):
        available_indices = [
            i for i in available_indices
            if PRODUCT_CATALOG[i].base_price <= max_price
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
    game_state.item_demand[new_item.name] = 1.0  # Initialize demand at normal level

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
    Create 8 vendors with different pricing and selection strategies.

    Vendor inventory is refreshed daily based on their selection type.
    """
    vendors = []

    # Vendor 1: 50% of market price, 1 random item per day, max 100 per item per player
    vendors.append(Vendor(
        name="Lucky Deal Trader",
        pricing_multiplier=0.50,
        selection_type="random_daily",
        selection_params=1,  # 1 item
        max_per_item_per_player=100
    ))

    # Vendor 2: 80% of market price, 5 random items per day, max 100 per item per player
    vendors.append(Vendor(
        name="Discount Wholesale Co.",
        pricing_multiplier=0.80,
        selection_type="random_daily",
        selection_params=5,  # 5 items
        max_per_item_per_player=100
    ))

    # Vendor 3: 90% of market price, all items under $20 market price
    vendors.append(Vendor(
        name="Budget Goods Ltd.",
        pricing_multiplier=0.90,
        selection_type="price_threshold",
        selection_params=20.0  # $20 threshold
    ))

    # Vendor 4: 95% of market price, all items under $50 market price
    vendors.append(Vendor(
        name="Premium Select Inc.",
        pricing_multiplier=0.95,
        selection_type="price_threshold",
        selection_params=50.0  # $50 threshold
    ))

    # Vendor 5: 102% of market price, all items available
    vendors.append(Vendor(
        name="Universal Supply Corp.",
        pricing_multiplier=1.02,
        selection_type="all",
        selection_params=0  # No limit
    ))

    # Vendor 6: 85% of market price, min 100 per purchase, items $30 or less
    vendors.append(Vendor(
        name="Bulk Goods Co.",
        pricing_multiplier=0.85,
        selection_type="price_range",
        selection_params=0,
        min_purchase=100,
        price_max=30.0
    ))

    # Vendor 7: 80% of market price, min 500 per purchase, items $10 or less
    vendors.append(Vendor(
        name="Cheap Goods Co.",
        pricing_multiplier=0.80,
        selection_type="price_range",
        selection_params=0,
        min_purchase=500,
        price_max=10.0
    ))

    # Vendor 8: 95% of market price, min 10 per purchase, items $200 or more
    vendors.append(Vendor(
        name="VIP Goods Co.",
        pricing_multiplier=0.95,
        selection_type="price_range",
        selection_params=0,
        min_purchase=10,
        price_min=200.0
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
            # Select all items where market price is at or under threshold
            price_threshold = vendor.selection_params
            for item in items:
                market_price = market_prices.get(item.name, item.base_price)
                if market_price <= price_threshold:
                    vendor.items[item.name] = market_price * vendor.pricing_multiplier

        elif vendor.selection_type == "price_range":
            # Select items within a price range (min and/or max)
            for item in items:
                market_price = market_prices.get(item.name, item.base_price)
                # Check if price is within range
                if vendor.price_min is not None and market_price < vendor.price_min:
                    continue
                if vendor.price_max is not None and market_price > vendor.price_max:
                    continue
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


def initialize_item_demand(items: List[Item]) -> Dict[str, float]:
    """
    Initialize demand for all items. Starts at 1.0 (normal demand).
    Demand ranges from 0.1 (lowest) to 2.0 (highest).
    """
    demand = {}
    for item in items:
        demand[item.name] = 1.0
    return demand


def weighted_random_choice(items: List[Item], demand_map: Dict[str, float]) -> Optional[Item]:
    """
    Select a random item from the list using demand as weights.
    Higher demand = higher probability of being selected.

    Returns None if items list is empty.
    """
    if not items:
        return None

    # Get weights for each item (default to 1.0 if not in demand_map)
    weights = [demand_map.get(item.name, 1.0) for item in items]

    # Use random.choices which supports weights
    selected = random.choices(items, weights=weights, k=1)
    return selected[0] if selected else None


def weighted_random_sample(items: List[Item], demand_map: Dict[str, float], k: int) -> List[Item]:
    """
    Select k random items from the list using demand as weights (without replacement).
    Higher demand = higher probability of being selected.

    Returns a list of selected items (may be fewer than k if not enough items available).
    """
    if not items or k <= 0:
        return []

    k = min(k, len(items))  # Can't sample more than available

    # Get weights for each item
    weights = [demand_map.get(item.name, 1.0) for item in items]

    # Sample without replacement
    # We'll use a manual approach since random.sample doesn't support weights
    selected = []
    remaining_items = items.copy()
    remaining_weights = weights.copy()

    for _ in range(k):
        # Choose one item based on weights
        chosen = random.choices(remaining_items, weights=remaining_weights, k=1)[0]
        selected.append(chosen)

        # Remove chosen item and its weight
        idx = remaining_items.index(chosen)
        remaining_items.pop(idx)
        remaining_weights.pop(idx)

    return selected


def update_item_demand(game_state: GameState) -> List[str]:
    """
    Update demand for 1/4 of available products (rounded up).

    First, resets extreme demand values to prevent long hype trains or slumps:
    - Items at 2.0 (max) → reset to 1.0
    - Items at 0.1 (min) → reset to 0.5

    Then, randomly changes demand for 1/4 of items by ±0.2 to 0.4.
    Demand is clamped between 0.1 and 2.0.

    Returns list of item names that had demand changes.
    """
    if not game_state.items:
        return []

    updated_items = []

    # Step 1: Reset extreme demand values (prevents monotone hype trains/slumps)
    for item in game_state.items:
        current_demand = game_state.item_demand.get(item.name, 1.0)

        if current_demand >= 2.0:
            # Max demand → reset to normal
            game_state.item_demand[item.name] = 1.0
            updated_items.append(item.name)
        elif current_demand <= 0.1:
            # Min demand → boost to 0.5
            game_state.item_demand[item.name] = 0.5
            updated_items.append(item.name)

    # Step 2: Apply random changes to 1/4 of items
    num_items_to_update = max(1, (len(game_state.items) + 3) // 4)  # Ceiling division

    # Randomly select items to update (may include items already reset)
    items_to_update = random.sample(game_state.items, min(num_items_to_update, len(game_state.items)))

    for item in items_to_update:
        # Generate random change between -0.4 and +0.4
        change = random.uniform(-0.4, 0.4)

        # Get current demand (may have been reset above)
        current_demand = game_state.item_demand.get(item.name, 1.0)

        # Apply change and clamp between 0.1 and 2.0
        new_demand = max(0.1, min(2.0, current_demand + change))

        game_state.item_demand[item.name] = new_demand

        # Only add to updated_items if not already there
        if item.name not in updated_items:
            updated_items.append(item.name)

    return updated_items


def create_default_upgrades(vendors: List[Vendor]) -> List[Upgrade]:
    """
    Create a list of default upgrades available for purchase.
    Admins can add more upgrades to this list.
    """
    upgrades = [
        # Customer capacity upgrades
        Upgrade(name="Extra Cashier Station", cost=2000, effect_type="max_customers", effect_value=10),
        Upgrade(name="Express Checkout Lane", cost=3500, effect_type="max_customers", effect_value=15),

        # Buyout capacity upgrades
        Upgrade(name="Warehouse Extension", cost=2500, effect_type="max_items", effect_value=20),
        Upgrade(name="Loading Dock", cost=4000, effect_type="max_items", effect_value=30),

        # Max different items upgrades
        Upgrade(name="Additional Shelving", cost=2000, effect_type="max_products", effect_value=2),
        Upgrade(name="Display Cases", cost=3500, effect_type="max_products", effect_value=3),

        # XP gain upgrades
        Upgrade(name="Business Course", cost=2000, effect_type="xp_gain", effect_value=10),
        Upgrade(name="MBA Program", cost=5000, effect_type="xp_gain", effect_value=25),

        # Wage reduction upgrade
        Upgrade(name="Employee Benefits Package", cost=20000, effect_type="wage_reduction", effect_value=100),
    ]

    # Add vendor discount upgrades for each vendor (30-day duration, tier-based pricing)
    # Pricing tiers based on vendor value:
    vendor_pricing = {
        "Lucky Deal Trader": (5000, 10000),  # Limited (1 random item)
        "Discount Wholesale Co.": (6000, 13000),  # Moderate (5 random items)
        "Budget Goods Ltd.": (6000, 13000),  # Moderate (cheap items only)
        "Premium Select Inc.": (8000, 16000),  # High (wide selection, okay pricing)
        "Universal Supply Corp.": (15000, 30000),  # Highest (everything, guaranteed)
        "Bulk Goods Co.": (7000, 14000),  # Moderate-high (good pricing, high minimum)
        "Cheap Goods Co.": (5000, 12000),  # Low (very limited range, very high minimum)
        "VIP Goods Co.": (10000, 20000),  # High (expensive items, late game)
    }

    for vendor in vendors:
        # Get pricing for this vendor (default to 5k/10k if not specified)
        basic_cost, premium_cost = vendor_pricing.get(vendor.name, (5000, 10000))

        upgrades.append(Upgrade(
            name=f"Partnership with {vendor.name}",
            cost=basic_cost,
            effect_type="vendor_discount",
            effect_value=5,
            vendor_name=vendor.name,
            duration_days=30
        ))
        upgrades.append(Upgrade(
            name=f"Premium Contract with {vendor.name}",
            cost=premium_cost,
            effect_type="vendor_discount",
            effect_value=10,
            vendor_name=vendor.name,
            duration_days=30
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

    For vendors with minimum purchase requirements:
    - VIP Goods Co. (high-end items $200+) falls back to Universal Supply Corp.
    - Other vendors fall back to Budget Goods Ltd.

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
            if player.inventory.get(item_name, 0) == 0 and current_products >= max_products:
                continue  # Skip this item, store is full of different products

            # Find the vendor
            vendor = game_state.get_vendor(vendor_name)
            if vendor:
                # Get the price from this vendor (might be None if item not available)
                price = vendor.get_price(item_name)

                # For random vendors, check if item is available, fallback if not
                if vendor.selection_type == "random_daily" and price is None:
                    original_vendor_name = vendor.name
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

                # For vendors with minimum purchase, check if quantity meets minimum
                # If not, fallback to appropriate vendor based on price range
                if vendor.min_purchase is not None and quantity < vendor.min_purchase and price is not None:
                    # VIP Goods Co. (high-end items $200+) should fallback to Universal Supply Corp.
                    # Other vendors fallback to Budget Goods Ltd.
                    if vendor.price_min is not None and vendor.price_min >= 200.0:
                        # VIP vendor - fallback to Universal Supply Corp. (index 4)
                        if len(game_state.vendors) > 4:
                            fallback_vendor = game_state.vendors[4]  # Universal Supply Corp.
                            fallback_price = fallback_vendor.get_price(item_name)
                            if fallback_price is not None:
                                vendor = fallback_vendor
                                price = fallback_price
                    else:
                        # Regular vendor - fallback to Budget Goods Ltd. (index 2)
                        if len(game_state.vendors) > 2:
                            fallback_vendor = game_state.vendors[2]  # Budget Goods Ltd.
                            fallback_price = fallback_vendor.get_price(item_name)
                            if fallback_price is not None:
                                vendor = fallback_vendor
                                price = fallback_price

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

        # Get market price for production line check
        market_price = game_state.market_prices.get(item_name, 0)

        success = player.purchase_from_vendor(vendor, item_name, actual_quantity, market_price, game_state)
        if success:
            purchases[item_name] = actual_quantity
            total_items_bought += actual_quantity
        else:
            # Try to buy as many as possible with remaining cash
            # Recalculate price if production line owned
            actual_price = player.get_production_line_price(item_name, market_price) or price
            max_affordable = int(player.cash / actual_price)
            if max_affordable > 0:
                affordable_quantity = min(max_affordable, remaining_capacity)
                partial_success = player.purchase_from_vendor(vendor, item_name, affordable_quantity, market_price, game_state)
                if partial_success:
                    purchases[item_name] = affordable_quantity
                    total_items_bought += affordable_quantity

    return purchases


# -------------------------------------------------------------------
# Player strategies
# -------------------------------------------------------------------

def auto_setup_buy_orders(player: Player, items: List[Item], vendors: List[Vendor], market_prices: Dict[str, float]) -> None:
    """
    Automatically set up buy orders for AI players.

    AI players will buy to maintain inventory of at least 10 units per item,
    always choosing the cheapest available vendor.
    Only buys items available at or below market price to avoid overpaying.
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

        # Only buy if available at a reasonable price (≤ 110% of market price)
        # Allows some flexibility while preventing overpaying at expensive vendors
        market_price = market_prices.get(item.name, item.base_price)
        max_acceptable_price = market_price * 1.10
        if cheapest_vendor and quantity_to_buy > 0 and cheapest_price <= max_acceptable_price:
            player.set_buy_order(item.name, quantity_to_buy, cheapest_vendor.name)
        else:
            player.set_buy_order(item.name, 0, "")


def auto_pricing_strategy(player: Player, market_prices: Dict[str, float], items: List[Item] = None,
                         all_players: List[Player] = None, vendors: List[Vendor] = None) -> None:
    """
    Intelligent pricing strategy for AI players.

    Strategy:
    - Alice Corp: Volume strategy - aims to be the cheapest and sell maximum units
    - Bob Ltd: Profit margin strategy - maintains higher prices while staying competitive

    Common rules:
    - Never sell at a loss (price must be > cost)
    - Adjust prices based on previous day's sales performance
    - Consider unmet demand signals
    - Consider competitor prices (human and AI)
    - Consider vendor wholesale prices to understand market dynamics
    """
    # Determine AI strategy based on player name
    is_alice = "Alice" in player.name  # Volume strategy - be the cheapest
    is_bob = "Bob" in player.name  # Profit margin strategy - maximize profit per item
    # Build a lookup for item base costs
    item_costs_lookup = {}
    if items:
        for item in items:
            item_costs_lookup[item.name] = item.base_cost

    # Build competitor price lookup (prices set by other players)
    competitor_prices = {}  # item_name -> list of competitor prices
    if all_players:
        for other_player in all_players:
            if other_player.name != player.name:  # Don't include self
                for item_name, price in other_player.prices.items():
                    if item_name not in competitor_prices:
                        competitor_prices[item_name] = []
                    competitor_prices[item_name].append(price)

    # Build vendor price lookup (wholesale prices from vendors)
    vendor_prices = {}  # item_name -> list of vendor wholesale prices
    if vendors:
        for vendor in vendors:
            for item_name, price in vendor.items.items():
                if item_name not in vendor_prices:
                    vendor_prices[item_name] = []
                vendor_prices[item_name].append(price)

    for item_name, market_price in market_prices.items():
        # Get the cost this player paid for the item (or base cost as fallback)
        cost = player.item_costs.get(item_name, item_costs_lookup.get(item_name, 0))

        # Get yesterday's sales data if available
        sales_data = player.daily_sales_data.get(item_name, {})
        units_sold = sales_data.get('units_sold', 0)
        sold_out = sales_data.get('sold_out', False)
        unmet_demand = sales_data.get('unmet_demand', 0)

        # Get current price (if set) for incremental adjustments
        current_price = player.prices.get(item_name, market_price)

        # Analyze competitor prices
        comp_prices = competitor_prices.get(item_name, [])
        min_competitor_price = min(comp_prices) if comp_prices else None
        avg_competitor_price = sum(comp_prices) / len(comp_prices) if comp_prices else None
        max_competitor_price = max(comp_prices) if comp_prices else None

        # Analyze vendor prices (to understand supply costs)
        vend_prices = vendor_prices.get(item_name, [])
        min_vendor_price = min(vend_prices) if vend_prices else None
        avg_vendor_price = sum(vend_prices) / len(vend_prices) if vend_prices else None

        # Determine pricing strategy based on sales performance and competition
        if is_alice:
            # ALICE: Volume strategy - always aim to be the cheapest
            if not sales_data:
                # No sales history - undercut market aggressively
                if min_competitor_price:
                    price = min_competitor_price * random.uniform(0.90, 0.95)
                else:
                    price = market_price * random.uniform(0.93, 0.97)
            elif sold_out:
                # Even if sold out, Alice only raises price slightly (volume over margin)
                if min_competitor_price:
                    price = min_competitor_price * random.uniform(0.95, 0.98)
                else:
                    price = current_price * random.uniform(1.01, 1.03)
            elif units_sold == 0:
                # Aggressively cut prices to move inventory
                if min_competitor_price:
                    price = min_competitor_price * random.uniform(0.88, 0.93)
                else:
                    price = current_price * random.uniform(0.85, 0.90)
            elif unmet_demand > 5:
                # Even with high demand, only moderate increase (want volume)
                if min_competitor_price:
                    price = min_competitor_price * random.uniform(0.96, 0.99)
                else:
                    price = current_price * random.uniform(1.00, 1.03)
            else:
                # Normal sales - stay cheapest
                if min_competitor_price:
                    price = min_competitor_price * random.uniform(0.92, 0.97)
                else:
                    price = market_price * random.uniform(0.95, 0.98)

        elif is_bob:
            # BOB: Profit margin strategy - maximize profit per item while staying competitive
            if not sales_data:
                # No sales history - price at higher end but competitive
                if avg_competitor_price:
                    price = avg_competitor_price * random.uniform(0.98, 1.05)
                else:
                    price = market_price * random.uniform(1.00, 1.08)
            elif sold_out:
                # Sold out - raise prices more aggressively for profit
                if max_competitor_price:
                    price = max_competitor_price * random.uniform(1.00, 1.08)
                else:
                    price = current_price * random.uniform(1.08, 1.15)
            elif units_sold == 0:
                # Didn't sell - reduce price but maintain margin
                if avg_competitor_price:
                    price = avg_competitor_price * random.uniform(0.95, 1.00)
                else:
                    price = current_price * random.uniform(0.93, 0.97)
            elif unmet_demand > 5:
                # High demand - raise prices significantly to maximize profit
                if avg_competitor_price:
                    price = max(current_price * random.uniform(1.05, 1.12),
                               avg_competitor_price * random.uniform(1.00, 1.05))
                else:
                    price = current_price * random.uniform(1.05, 1.12)
            else:
                # Normal sales - maintain healthy margins
                if avg_competitor_price:
                    price = avg_competitor_price * random.uniform(0.98, 1.04)
                else:
                    price = current_price * random.uniform(1.00, 1.05)
        else:
            # Default strategy (for any other AI players)
            if not sales_data:
                # No sales history - price competitively based on competitors
                if min_competitor_price:
                    # Undercut the cheapest competitor slightly
                    price = min_competitor_price * random.uniform(0.95, 0.99)
                else:
                    # No competitors - price near market
                    price = market_price * random.uniform(0.97, 1.03)
            elif sold_out:
                # Item sold out - raise price to increase profit margin
                # But don't go too far above competitors if they exist
                if max_competitor_price:
                    # Try to match the highest competitor, maybe slightly above
                    price = max_competitor_price * random.uniform(0.98, 1.05)
                else:
                    # No competitors - raise significantly
                    price = current_price * random.uniform(1.05, 1.10)
            elif units_sold == 0:
                # Didn't sell any - price is too high
                if min_competitor_price and current_price > min_competitor_price:
                    # We're more expensive than competitors - match or undercut them
                    price = min_competitor_price * random.uniform(0.93, 0.97)
                else:
                    # Lower price generally
                    price = current_price * random.uniform(0.90, 0.95)
            elif unmet_demand > 5:
                # High unmet demand - raise prices to capture more value
                # But be mindful of competitor prices
                if avg_competitor_price:
                    # Try to stay competitive but increase toward competitor average
                    price = min(current_price * random.uniform(1.03, 1.08),
                               avg_competitor_price * random.uniform(0.98, 1.02))
                else:
                    price = current_price * random.uniform(1.03, 1.08)
            else:
                # Selling moderately - stay competitive with market
                if avg_competitor_price:
                    # Target slightly below average competitor price
                    price = avg_competitor_price * random.uniform(0.96, 1.00)
                else:
                    # No competitors - make small adjustments
                    price = current_price * random.uniform(0.98, 1.02)

        # CRITICAL: Never sell below cost
        # Bob needs higher margin to survive (15%), Alice can work with 10%
        if is_bob:
            min_profitable_price = cost * 1.15  # Bob needs 15% margin minimum
        else:
            min_profitable_price = cost * 1.10  # Others need 10% margin

        if price < min_profitable_price:
            price = min_profitable_price

        # Don't price too far above market (customers won't buy >15% above market)
        # Stay within 14% of market to be competitive while maximizing profit
        max_price = market_price * 1.14
        if price > max_price:
            price = max_price

        # Round to nearest $0.05 for natural-looking prices
        price = round(price * 20) / 20

        player.set_price(item_name, price)


def auto_purchase_upgrades(player: Player, game_state: GameState) -> None:
    """
    Automatically purchase upgrades for AI players based on strategic decision-making.

    Strategy:
    1. Maintain a cash reserve (at least $2000 + $1000 per store level)
    2. Prioritize capacity upgrades when hitting limits
    3. Invest in efficiency upgrades (XP, vendor discounts) mid-game
    4. Purchase production lines for high-volume items late-game
    """
    # Calculate minimum cash reserve (increases with store level)
    min_reserve = 2000 + (1000 * player.store_level)
    available_cash = player.cash - min_reserve

    if available_cash <= 0:
        return  # Not enough cash to safely purchase upgrades

    # Get all available upgrades
    all_upgrades = game_state.available_upgrades.copy()

    # Add production line upgrades dynamically
    production_line_upgrades = []
    for item in game_state.items:
        if not player.has_production_line(item.name):
            upgrade_cost = item.base_cost * 20000
            if upgrade_cost <= available_cash:  # Only consider affordable production lines
                production_line_upgrades.append(Upgrade(
                    name=f"Production Line: {item.name}",
                    cost=upgrade_cost,
                    effect_type="production_line",
                    effect_value=0,
                    vendor_name=item.name
                ))

    all_upgrades.extend(production_line_upgrades)

    # Filter out already purchased upgrades (except production lines which are tracked differently)
    available_upgrades = []
    for upgrade in all_upgrades:
        if upgrade.effect_type == "production_line":
            # Already filtered above by has_production_line check
            available_upgrades.append(upgrade)
        elif upgrade not in player.purchased_upgrades:
            available_upgrades.append(upgrade)

    # Filter by affordability
    affordable_upgrades = [u for u in available_upgrades if u.cost <= available_cash]

    if not affordable_upgrades:
        return  # No affordable upgrades

    # Score each upgrade based on current needs and situation
    scored_upgrades = []
    for upgrade in affordable_upgrades:
        # Skip upgrades with invalid cost (prevents division by zero)
        if upgrade.cost <= 0:
            continue

        score = 0

        # Customer capacity upgrades - high priority if approaching limit
        if upgrade.effect_type == "max_customers":
            # Higher priority if we have good cash flow
            if player.cash > 5000:
                score = 80 + (upgrade.effect_value / upgrade.cost * 1000)

        # Inventory capacity upgrades - medium-high priority
        elif upgrade.effect_type == "max_items":
            score = 70 + (upgrade.effect_value / upgrade.cost * 1000)

        # Product variety upgrades - important for growth
        elif upgrade.effect_type == "max_products":
            current_max = player.get_max_products()
            # Higher priority if we're likely to need more product slots
            if player.store_level >= 3:
                score = 75 + (upgrade.effect_value / upgrade.cost * 2000)
            else:
                score = 60 + (upgrade.effect_value / upgrade.cost * 2000)

        # XP gain upgrades - good mid-game investment
        elif upgrade.effect_type == "xp_gain":
            if player.store_level >= 5:
                score = 65 + (upgrade.effect_value / upgrade.cost * 500)
            else:
                score = 85 + (upgrade.effect_value / upgrade.cost * 500)  # Higher priority early

        # Wage reduction - excellent late-game investment
        elif upgrade.effect_type == "wage_reduction":
            total_employees = player.cashiers + player.restockers
            daily_savings = upgrade.effect_value * total_employees
            # ROI-based scoring: higher score if payback period is short
            if daily_savings > 0:
                payback_days = upgrade.cost / daily_savings
                score = max(50, 100 - payback_days)  # Better score for faster payback

        # Vendor discounts - valuable for high-volume purchasing
        elif upgrade.effect_type == "vendor_discount":
            # Estimate value based on typical daily spending
            score = 60 + (upgrade.effect_value / upgrade.cost * 800)

        # Production lines - late-game investment for high-volume items
        elif upgrade.effect_type == "production_line":
            item_name = upgrade.vendor_name
            current_inventory = player.inventory.get(item_name, 0)

            # Only invest in production lines for items we actively stock
            if current_inventory > 0:
                # Higher score for expensive items (more savings)
                market_price = game_state.market_prices.get(item_name, 0)
                daily_savings = market_price * 0.5 * 10  # Assume 10 units sold per day

                if daily_savings > 0:
                    payback_days = upgrade.cost / daily_savings
                    # Only pursue if payback is reasonable (< 100 days)
                    if payback_days < 100:
                        score = max(40, 90 - (payback_days / 2))
                    else:
                        score = 30  # Low priority for poor ROI
            else:
                score = 20  # Very low priority for items we don't stock

        scored_upgrades.append((score, upgrade))

    # Sort by score (highest first)
    scored_upgrades.sort(reverse=True, key=lambda x: x[0])

    # Purchase the highest-scoring affordable upgrade
    if scored_upgrades:
        best_score, best_upgrade = scored_upgrades[0]

        # Only purchase if score is reasonable (above 40)
        if best_score >= 40:
            success = player.purchase_upgrade(best_upgrade, game_state.day)
            if success:
                # AI purchases are silent (no print statements)
                pass


def auto_hire_employees(player: Player, game_state: GameState) -> None:
    """
    Automatically hire employees for AI players based on strategic decision-making.

    Strategy:
    1. Maintain a cash reserve (at least $2000 + $1000 per store level)
    2. Consider ongoing wage costs ($500/month per employee)
    3. Hire cashiers when customer capacity is limiting sales
    4. Hire restockers when inventory capacity is limiting operations
    5. Balance hiring with long-term profitability
    """
    HIRING_COST = 500.0
    MONTHLY_WAGE = 500.0

    # Calculate minimum cash reserve (same as upgrades)
    min_reserve = 2000 + (1000 * player.store_level)

    # For hiring decisions, we want a larger buffer since employees have ongoing costs
    # Reserve enough for at least 3 months of wages for current + potential new employee
    total_employees = player.cashiers + player.restockers
    wage_buffer = (total_employees + 1) * MONTHLY_WAGE * 3 / 30  # 3 months of daily wages

    available_cash = player.cash - min_reserve - wage_buffer

    if available_cash < HIRING_COST:
        return  # Not enough cash to safely hire

    # Analyze current constraints
    current_inventory_count = sum(len(inv.items) for inv in player.inventory.values())
    max_items = player.get_max_items_per_day()
    max_customers = player.get_max_customers()

    # Calculate utilization rates (how close we are to hitting limits)
    # Higher utilization = more need for that employee type
    inventory_utilization = current_inventory_count / max(max_items, 1)

    # Estimate customer demand based on current inventory and pricing
    # This is a rough estimate - AI assumes they could sell to capacity if they had stock
    num_products = len(player.inventory)
    estimated_customer_demand = min(num_products * 5, max_customers * 1.2)  # Rough estimate
    customer_utilization = estimated_customer_demand / max(max_customers, 1)

    # Calculate ROI for each employee type
    # Cashiers: increase customer capacity by 10 customers/day
    # Restockers: increase inventory capacity by 20 items/day
    # Assume average profit per customer is $5, and inventory turnover matters

    cashier_value = 0.0
    restocker_value = 0.0

    # Score cashiers higher if we're hitting customer capacity limits
    if customer_utilization > 0.8:  # Over 80% capacity
        # Expected additional revenue from 10 more customers per day
        cashier_value = 10 * 5 * 30  # 10 customers * $5 profit * 30 days = $1500/month
        cashier_value -= MONTHLY_WAGE  # Subtract monthly cost
        cashier_value *= (customer_utilization - 0.7)  # Scale by how constrained we are

    # Score restockers higher if we're hitting inventory capacity limits
    if inventory_utilization > 0.7:  # Over 70% capacity
        # Expected additional revenue from being able to stock more
        restocker_value = 20 * 2 * 30  # 20 items * $2 profit/item * 30 days = $1200/month
        restocker_value -= MONTHLY_WAGE  # Subtract monthly cost
        restocker_value *= (inventory_utilization - 0.6)  # Scale by how constrained we are

    # Only hire if the expected monthly value is positive and significant
    # Early game: be more aggressive (lower threshold)
    # Late game: be more conservative (higher threshold)
    min_monthly_value = 200 + (player.store_level * 100)

    # Decide what to hire
    hire_type = None
    if cashier_value > max(restocker_value, min_monthly_value):
        hire_type = "cashier"
    elif restocker_value > min_monthly_value:
        hire_type = "restocker"

    # Attempt to hire
    if hire_type:
        success = player.hire_employee(hire_type)
        if success:
            # AI hiring is silent (no print statements)
            pass


# -------------------------------------------------------------------
# Daily simulation logic
# -------------------------------------------------------------------

def run_day(game_state: GameState, show_details: bool = True) -> Dict[str, float]:
    """
    Simulate a single day in the economic game.

    Steps:
    1. Apply daily price fluctuations and special events
    2. Let AI players adjust buy orders and prices
    3. Execute buy orders for all players (from cheapest to most expensive)
    4. For each customer, generate needs and make purchases (limited by cashier capacity)
    5. Pay employee wages
    6. Track statistics
    7. Refresh vendor inventory for next day (at END of day)
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

    # Step 1: Reset any event price changes from previous day
    if game_state.event_price_changes:
        for item_name, original_price in game_state.event_price_changes.items():
            game_state.market_prices[item_name] = original_price
        game_state.event_price_changes.clear()

    # Apply price fluctuations and special events
    apply_daily_price_fluctuation(game_state.market_prices, game_state.items)

    # Check for special events
    if game_state.day % 30 == 0 and show_details:
        # 30-day event: one item -50%, one item +50%
        if len(game_state.items) >= 2:
            selected_items = random.sample(game_state.items, 2)
            # Item 1: -50%
            old_price1 = game_state.market_prices[selected_items[0].name]
            game_state.event_price_changes[selected_items[0].name] = old_price1
            game_state.market_prices[selected_items[0].name] = old_price1 * 0.5
            # Item 2: +50%
            old_price2 = game_state.market_prices[selected_items[1].name]
            game_state.event_price_changes[selected_items[1].name] = old_price2
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

    # Calculate uncapped customers (starts at day 50, +1 every 10 days)
    uncapped_customer_count = 0
    if game_state.day >= 50:
        uncapped_customer_count = ((game_state.day - 40) // 10)

    if show_details:
        print(f"Regular customers today: {base_customer_count}")
        if uncapped_customer_count > 0:
            print(f"💎 Uncapped customers today: {uncapped_customer_count} (looking for expensive items ≥$100)")

    # Step 2: AI player decisions (pricing, buying, upgrades, and hiring)
    # Done BEFORE buy orders so they can purchase inventory on Day 1
    for player in game_state.players:
        if not player.is_human:  # Only automate AI players
            # Update AI buy orders every day based on current inventory
            auto_setup_buy_orders(player, game_state.items, game_state.vendors, game_state.market_prices)
            auto_pricing_strategy(player, game_state.market_prices, game_state.items,
                                game_state.players, game_state.vendors)
            # AI players can now purchase upgrades strategically
            auto_purchase_upgrades(player, game_state)
            # AI players can now hire employees strategically
            auto_hire_employees(player, game_state)

    # Step 4: Execute buy orders for ALL players
    if show_details:
        print("\nExecuting buy orders...")

    # Track daily spending per player for accurate profit calculation
    daily_spending = {player.name: 0.0 for player in game_state.players}

    for player in game_state.players:
        # Track actual cash spent (accounts for vendor fallbacks, discounts, etc.)
        cash_before = player.cash
        purchases = execute_buy_orders(player, game_state)
        cash_after = player.cash
        actual_spent = cash_before - cash_after

        daily_spending[player.name] = actual_spent
        if show_details and purchases:
            print(f"  {player.name}: Purchased {sum(purchases.values())} items (spent ${actual_spent:.2f})")

    # Track daily statistics
    daily_sales = {player.name: 0.0 for player in game_state.players}
    daily_profits = {player.name: 0.0 for player in game_state.players}
    customers_served = {player.name: 0 for player in game_state.players}
    uncapped_customers_served = {player.name: 0 for player in game_state.players}
    unmet_demand = 0
    unmet_uncapped_demand = 0

    # Track customer types for daily summary
    customer_type_stats = {
        'spawned': {'low': 0, 'medium': 0, 'high': 0, 'hoarder': 0, 'rich_guy': 0, 'poor_man': 0, 'kid': 0},
        'bought_something': {'low': 0, 'medium': 0, 'high': 0, 'hoarder': 0, 'rich_guy': 0, 'poor_man': 0, 'kid': 0},
        'found_nothing': {'low': 0, 'medium': 0, 'high': 0, 'hoarder': 0, 'rich_guy': 0, 'poor_man': 0, 'kid': 0}
    }

    # Track per-item sales data for pricing strategy
    # player_name -> item_name -> {units_sold, revenue, starting_inventory}
    per_item_sales = {player.name: {} for player in game_state.players}
    # Track starting inventory before sales for each player/item
    for player in game_state.players:
        for item_name, quantity in player.inventory.items():
            per_item_sales[player.name][item_name] = {
                'units_sold': 0,
                'revenue': 0.0,
                'starting_inventory': quantity
            }

    # Track unmet demand per item (for pricing signals)
    unmet_demand_per_item = {}  # item_name -> quantity

    # Step 5: Simulate customers with cashier limits
    # Generate all regular customers for the day
    all_customers = []
    for i in range(base_customer_count):
        customer_type = random.choice(["low", "medium", "high"])
        customer = Customer(name=f"Customer_{i+1}", customer_type=customer_type)
        all_customers.append(customer)
        customer_type_stats['spawned'][customer_type] += 1

    # Generate special customer types (they count towards cashier limit)
    # Only spawn if suitable items exist based on market prices
    special_customer_counter = 0

    # Check for Hoarder-suitable items (can afford 3+ units)
    hoarder_items = [item for item in game_state.items if item.base_price * 3 <= 40.0]
    if hoarder_items and random.random() < 0.3:  # 30% chance to spawn
        special_customer_counter += 1
        customer = Customer(name=f"Hoarder_{special_customer_counter}", customer_type="hoarder")
        all_customers.append(customer)
        customer_type_stats['spawned']['hoarder'] += 1

    # Check for Rich Guy-suitable items (>$50)
    rich_items = [item for item in game_state.items
                 if game_state.market_prices.get(item.name, item.base_price) > 50.0]
    if rich_items and random.random() < 0.3:  # 30% chance to spawn
        special_customer_counter += 1
        customer = Customer(name=f"RichGuy_{special_customer_counter}", customer_type="rich_guy")
        all_customers.append(customer)
        customer_type_stats['spawned']['rich_guy'] += 1

    # Check for Poor Man-suitable items (<$10)
    poor_items = [item for item in game_state.items
                 if game_state.market_prices.get(item.name, item.base_price) < 10.0]
    if poor_items and random.random() < 0.3:  # 30% chance to spawn
        special_customer_counter += 1
        customer = Customer(name=f"PoorMan_{special_customer_counter}", customer_type="poor_man")
        all_customers.append(customer)
        customer_type_stats['spawned']['poor_man'] += 1

    # Check for Kid-suitable items (<$5)
    kid_items = [item for item in game_state.items
                if game_state.market_prices.get(item.name, item.base_price) < 5.0]
    if kid_items and random.random() < 0.3:  # 30% chance to spawn
        special_customer_counter += 1
        customer = Customer(name=f"Kid_{special_customer_counter}", customer_type="kid")
        all_customers.append(customer)
        customer_type_stats['spawned']['kid'] += 1

    # Track total demand per item (what customers want to buy today)
    daily_demand_per_item = {}  # item_name -> total quantity wanted

    # Process each regular customer (with cashier limits)
    for customer in all_customers:
        needs = customer.generate_daily_needs(game_state.items, game_state.market_prices, game_state.item_demand)

        # Track demand for each item the customer wants
        for need in needs:
            daily_demand_per_item[need.item_name] = daily_demand_per_item.get(need.item_name, 0) + need.quantity

        # Track which stores this customer has been counted at (to count each customer only once per store)
        customer_counted_at_store = {}
        customer_bought_anything = False

        # NEW LOGIC: Sort needs by market price (most expensive first)
        # Customer finds cheapest store for most expensive item, then stays there
        needs_with_prices = []
        for need in needs:
            market_price = game_state.market_prices.get(need.item_name, 0)
            needs_with_prices.append((need, market_price))

        # Sort by price descending (most expensive first)
        needs_with_prices.sort(key=lambda x: x[1], reverse=True)
        remaining_needs = [need for need, _ in needs_with_prices]

        # Current supplier (the store customer is shopping at)
        current_supplier = None

        while remaining_needs:
            # If no current supplier, find cheapest supplier for the most expensive remaining item
            if current_supplier is None:
                most_expensive_need = remaining_needs[0]
                sorted_suppliers = customer.get_all_suppliers_sorted(
                    game_state.players,
                    most_expensive_need.item_name,
                    most_expensive_need.quantity,
                    game_state.market_prices
                )

                # Find a supplier with capacity
                found_supplier = False
                for supplier in sorted_suppliers:
                    if customers_served[supplier.name] < supplier.get_max_customers():
                        current_supplier = supplier
                        found_supplier = True
                        break

                if not found_supplier:
                    # No supplier available, mark as unmet and move to next item
                    unmet_demand += most_expensive_need.quantity
                    unmet_demand_per_item[most_expensive_need.item_name] = (
                        unmet_demand_per_item.get(most_expensive_need.item_name, 0) + most_expensive_need.quantity
                    )
                    remaining_needs.remove(most_expensive_need)
                    continue

            # Try to purchase as many items as possible from current supplier
            purchased_needs = []
            for need in remaining_needs:
                # Check if current supplier has this item
                if (need.item_name in current_supplier.inventory and
                    current_supplier.inventory[need.item_name] > 0 and
                    need.item_name in current_supplier.prices):

                    # Check if price is acceptable
                    market_price = game_state.market_prices.get(need.item_name, float('inf'))
                    max_acceptable_price = market_price * 1.15
                    supplier_price = current_supplier.prices[need.item_name]

                    if supplier_price <= max_acceptable_price:
                        # Purchase from current supplier
                        revenue, profit, actual_units_sold = current_supplier.sell_to_customer(
                            need.item_name, need.quantity, supplier_price
                        )

                        if revenue > 0:
                            # Track sales
                            daily_sales[current_supplier.name] += revenue
                            daily_profits[current_supplier.name] += profit

                            # Count customer at this store (only once)
                            if current_supplier.name not in customer_counted_at_store:
                                customers_served[current_supplier.name] += 1
                                customer_counted_at_store[current_supplier.name] = True

                            # Track per-item sales
                            if need.item_name not in per_item_sales[current_supplier.name]:
                                per_item_sales[current_supplier.name][need.item_name] = {
                                    'units_sold': 0,
                                    'revenue': 0.0,
                                    'starting_inventory': 0
                                }
                            per_item_sales[current_supplier.name][need.item_name]['units_sold'] += actual_units_sold
                            per_item_sales[current_supplier.name][need.item_name]['revenue'] += revenue

                            customer_bought_anything = True
                            purchased_needs.append(need)

            # Remove purchased items from remaining needs
            for need in purchased_needs:
                remaining_needs.remove(need)

            # If there are still remaining needs, reset supplier to force finding cheapest for next item
            if remaining_needs:
                current_supplier = None

        # Track customer type statistics
        if customer.customer_type in customer_type_stats['bought_something']:
            if customer_bought_anything or not needs:
                # If customer bought something OR had no needs (couldn't find matching items)
                if not needs:
                    customer_type_stats['found_nothing'][customer.customer_type] += 1
                else:
                    customer_type_stats['bought_something'][customer.customer_type] += 1
            else:
                customer_type_stats['found_nothing'][customer.customer_type] += 1

    # Step 5.5: Process uncapped customers (no cashier limits)
    if uncapped_customer_count > 0:
        uncapped_customers = []
        for i in range(uncapped_customer_count):
            customer = Customer(name=f"Uncapped_{i+1}", customer_type="uncapped")
            uncapped_customers.append(customer)

        for customer in uncapped_customers:
            needs = customer.generate_daily_needs(game_state.items, game_state.market_prices, game_state.item_demand)

            # Track demand for each item the uncapped customer wants
            for need in needs:
                daily_demand_per_item[need.item_name] = daily_demand_per_item.get(need.item_name, 0) + need.quantity

            for need in needs:
                supplier = customer.choose_supplier(game_state.players, need.item_name, need.quantity, game_state.market_prices)

                if supplier:
                    # Uncapped customers bypass cashier limits
                    price = supplier.prices.get(need.item_name, 0)
                    revenue, profit, actual_units_sold = supplier.sell_to_customer(need.item_name, need.quantity, price)
                    if revenue > 0:
                        daily_sales[supplier.name] += revenue
                        daily_profits[supplier.name] += profit
                        uncapped_customers_served[supplier.name] += 1

                        # Track per-item sales
                        if need.item_name not in per_item_sales[supplier.name]:
                            per_item_sales[supplier.name][need.item_name] = {
                                'units_sold': 0,
                                'revenue': 0.0,
                                'starting_inventory': 0
                            }
                        per_item_sales[supplier.name][need.item_name]['units_sold'] += actual_units_sold
                        per_item_sales[supplier.name][need.item_name]['revenue'] += revenue
                else:
                    # Track unmet uncapped demand
                    unmet_uncapped_demand += need.quantity
                    unmet_demand_per_item[need.item_name] = unmet_demand_per_item.get(need.item_name, 0) + need.quantity

    # Step 5.5: Calculate actual profits (Sales - Daily Spending, before wages)
    for player in game_state.players:
        daily_profits[player.name] = daily_sales[player.name] - daily_spending[player.name]

    # Step 5.6: Award XP based on profit (before wages)
    level_ups = {}
    for player in game_state.players:
        profit = daily_profits[player.name]
        if profit > 0:
            leveled_up = player.add_experience(profit)
            if leveled_up:
                level_ups[player.name] = player.store_level

    # Step 6: Pay employee wages (monthly - every 30 days)
    for player in game_state.players:
        wages = player.pay_monthly_wages(game_state.day)
        if show_details and wages > 0:
            print(f"  {player.name}: ${wages:.2f} MONTHLY WAGE ({player.cashiers} cashiers + {player.restockers} restockers)")
        elif show_details and (player.cashiers > 0 or player.restockers > 0):
            days_until_payment = 30 - (game_state.day - player.last_wage_payment_day)
            print(f"  {player.name}: No payment today ({days_until_payment} days until next wage)")

    # Step 7: Print daily summary
    if show_details:
        print(f"\nDaily Results:")
        for player in game_state.players:
            sales = daily_sales[player.name]
            profit = daily_profits[player.name]
            served = customers_served[player.name]
            uncapped_served = uncapped_customers_served[player.name]
            max_served = player.get_max_customers()
            xp_needed = player.get_xp_for_next_level()

            # Calculate total items sold
            total_items_sold = sum(
                data['units_sold']
                for data in per_item_sales[player.name].values()
            )

            print(f"  {player.name}:")
            print(f"    Sales: ${sales:.2f} | Profit: ${profit:.2f} | XP: {player.experience:.0f}/{xp_needed:.0f}")
            customer_info = f"Regular: {served}/{max_served}"
            if uncapped_customer_count > 0:
                customer_info += f" | 💎 Uncapped: {uncapped_served}"
            print(f"    Customers: {customer_info} | Items Sold: {total_items_sold} | Cash: ${player.cash:.2f}")

            # Show level up if occurred
            if player.name in level_ups:
                print(f"    🎉 LEVEL UP! Now level {level_ups[player.name]} (max {player.get_max_products()} products)")

            # Show inventory (end of day)
            if player.inventory:
                inventory_items = [f"{item}: {qty}" for item, qty in sorted(player.inventory.items())]
                inventory_str = ", ".join(inventory_items)
                print(f"    Inventory: {inventory_str}")
            else:
                print(f"    Inventory: (empty)")

            # Show pricing for sold items only
            sold_items = per_item_sales[player.name].keys()
            if sold_items:
                pricing_items = []
                for item_name in sorted(sold_items):
                    if item_name in player.prices:
                        pricing_items.append(f"{item_name}: ${player.prices[item_name]:.2f}")
                if pricing_items:
                    pricing_str = ", ".join(pricing_items)
                    print(f"    Pricing (sold): {pricing_str}")

        if unmet_demand > 0:
            print(f"\nUnmet regular demand: {unmet_demand} items")
        if unmet_uncapped_demand > 0:
            print(f"Unmet uncapped demand: {unmet_uncapped_demand} items")

        # Display customer type statistics
        print(f"\nCustomer Types Today:")
        for ctype in ['low', 'medium', 'high', 'hoarder', 'rich_guy', 'poor_man', 'kid']:
            spawned = customer_type_stats['spawned'][ctype]
            if spawned > 0:
                bought = customer_type_stats['bought_something'][ctype]
                found_nothing = customer_type_stats['found_nothing'][ctype]
                print(f"  {ctype.replace('_', ' ').title()}: {spawned} spawned | {bought} bought | {found_nothing} found nothing")

        # Display demand per item (what customers wanted today)
        if daily_demand_per_item:
            print(f"\nItem Demand Today (Total Quantity Wanted):")
            # Sort by demand (highest first), then by item name
            sorted_demand = sorted(daily_demand_per_item.items(), key=lambda x: (-x[1], x[0]))
            for item_name, quantity in sorted_demand:
                print(f"  {item_name}: {quantity} units")

    # Update item demand for next day (after everything has sold)
    updated_items = update_item_demand(game_state)
    if show_details and updated_items:
        print(f"\n📊 DEMAND UPDATE: {len(updated_items)} items had demand changes")
        # Show top 3 demand changes if there are any
        demand_changes = [(item_name, game_state.item_demand[item_name]) for item_name in updated_items[:3]]
        for item_name, demand in demand_changes:
            if demand >= 1.5:
                emoji = "📈"
            elif demand <= 0.5:
                emoji = "📉"
            else:
                emoji = "➡️"
            print(f"   {emoji} {item_name}: {demand:.2f}x demand")

    # Step 7.5: Store per-item sales data for AI pricing strategy
    for player in game_state.players:
        player.daily_sales_data = {}
        for item_name, data in per_item_sales[player.name].items():
            # Check if item sold out (inventory reached 0)
            current_inventory = player.inventory.get(item_name, 0)
            sold_out = (data['starting_inventory'] > 0 and current_inventory == 0)

            player.daily_sales_data[item_name] = {
                'units_sold': data['units_sold'],
                'revenue': data['revenue'],
                'sold_out': sold_out,
                'unmet_demand': unmet_demand_per_item.get(item_name, 0)
            }

        # Store customer type statistics for AI competitors
        if not hasattr(player, 'customer_type_stats'):
            player.customer_type_stats = customer_type_stats
        else:
            player.customer_type_stats = customer_type_stats

        # Store daily demand per item for AI competitors (most valuable data!)
        if not hasattr(player, 'daily_demand_per_item'):
            player.daily_demand_per_item = daily_demand_per_item
        else:
            player.daily_demand_per_item = daily_demand_per_item

    # Step 8: Refresh vendor inventory for next day
    # Done at END of day so buy orders are set for current vendor inventory
    refresh_vendor_inventory(game_state.vendors, game_state.items, game_state.market_prices)

    # Step 9: Advance day counter
    game_state.day += 1

    # Step 9.5: Clean up expired vendor partnerships
    for player in game_state.players:
        expired_upgrades = []
        for upgrade in player.purchased_upgrades:
            if upgrade.duration_days > 0:  # Temporary upgrade
                expiration_day = player.vendor_partnership_expiration.get(upgrade.name, 0)
                if game_state.day >= expiration_day:
                    expired_upgrades.append(upgrade)
                    # Remove from expiration tracker
                    if upgrade.name in player.vendor_partnership_expiration:
                        del player.vendor_partnership_expiration[upgrade.name]

        # Remove expired upgrades
        for upgrade in expired_upgrades:
            player.purchased_upgrades.remove(upgrade)
            if player.is_human and show_details:
                print(f"\n⚠️  {player.name}: '{upgrade.name}' has expired!")

    # Step 10: Reset daily vendor purchase tracking
    game_state.vendor_daily_purchases.clear()

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
    base_wage = 20.0
    wage_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "wage_reduction")
    actual_wage = max(0, base_wage - wage_reduction)
    print(f"  Daily wages: ${total_employees * actual_wage:.2f} (${actual_wage:.2f}/employee)")

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
                        market_price = game_state.market_prices.get(selected_item_name, 0)
                        success = player.purchase_from_vendor(vendor, selected_item_name, quantity, market_price, game_state)
                        if success:
                            # Calculate actual cost (may be production line pricing)
                            actual_price = player.get_production_line_price(selected_item_name, market_price)
                            if actual_price is None:
                                actual_price = vendor.get_price(selected_item_name)
                            total_cost = actual_price * quantity
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
                    # Show minimum purchase requirement if it exists
                    min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                    if price:
                        print(f"  {i}. {vendor.name}{min_text} - ${price:.2f}")
                        available_vendors.append((i, vendor))
                    else:
                        status = "(not in stock today)" if vendor.selection_type == "random_daily" else "(not available)"
                        print(f"  {i}. {vendor.name}{min_text} - {status}")
                        available_vendors.append((i, vendor))

                vendor_choice = input(f"\nSelect vendor (1-{len(game_state.vendors)}): ")
                vendor_num = int(vendor_choice)

                if 1 <= vendor_num <= len(game_state.vendors):
                    selected_vendor = game_state.vendors[vendor_num - 1]

                    quantity_str = input(f"Enter quantity to buy (0 to skip): ")
                    quantity = int(quantity_str)

                    if quantity >= 0:
                        # Check minimum purchase requirement
                        if quantity > 0 and selected_vendor.min_purchase is not None and quantity < selected_vendor.min_purchase:
                            print(f"\n✗ {selected_vendor.name} requires a minimum purchase of {selected_vendor.min_purchase} units.")
                            print(f"   You tried to order {quantity} units. Please order at least {selected_vendor.min_purchase} or choose a different vendor.")
                            continue

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
    BASE_MONTHLY_WAGE = 500.0

    while True:
        print("\n" + "=" * 60)
        print("EMPLOYEE MENU - Hire Staff")
        print("=" * 60)
        print(f"\nYour Cash: ${player.cash:.2f}")
        print(f"\nCurrent Employees:")
        print(f"  Cashiers: {player.cashiers} (Max {player.get_max_customers()} customers/day)")
        print(f"  Restockers: {player.restockers} (Max {player.get_max_items_per_day()} items/day)")
        total_employees = player.cashiers + player.restockers

        # Calculate actual wage with upgrades
        wage_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "wage_reduction")
        actual_wage = max(0, BASE_MONTHLY_WAGE - wage_reduction)
        print(f"  Total monthly wages: ${total_employees * actual_wage:.2f}")

        print(f"\nHiring Cost: ${HIRING_COST:.2f} per employee")
        if wage_reduction > 0:
            print(f"Monthly Wage: ${actual_wage:.2f} per employee (reduced from ${BASE_MONTHLY_WAGE:.2f})")
        else:
            print(f"Monthly Wage: ${actual_wage:.2f} per employee")

        # Show days until next wage payment
        days_until_payment = 30 - (game_state.day - player.last_wage_payment_day)
        if total_employees > 0:
            print(f"Next wage payment: Day {player.last_wage_payment_day + 30} ({days_until_payment} days)")
        print(f"Note: Wages paid every 30 days for ALL employees (including newly hired)")

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


def production_line_menu(game_state: GameState, player: Player) -> None:
    """Menu for purchasing production line upgrades (own production for items)."""
    while True:
        print("\n" + "=" * 80)
        print("PRODUCTION LINE UPGRADES - Own Your Supply Chain")
        print("=" * 80)
        print(f"\nYour Cash: ${player.cash:.2f}")
        print("\nOwning a production line gives you:")
        print("  • Automatic 'Own' vendor for that item")
        print("  • Purchase at 50% of market price (incredible savings!)")
        print("  • Perfect for late-game investment")

        # Show owned production lines
        owned_lines = [u for u in player.purchased_upgrades if u.effect_type == "production_line"]
        if owned_lines:
            print("\n✅ Your Production Lines:")
            for upgrade in owned_lines:
                item_name = upgrade.vendor_name
                market_price = game_state.market_prices.get(item_name, 0)
                own_price = market_price * 0.5
                print(f"  • {item_name}: ${own_price:.2f} (50% of ${market_price:.2f} market)")
        else:
            print("\n✅ No production lines owned yet")

        # Show available production lines (only for unlocked products)
        print("\n🏭 Available Production Lines:")
        available = []
        for i, item in enumerate(game_state.items, 1):
            # Check if already owned
            already_owned = player.has_production_line(item.name)
            if not already_owned:
                # Calculate cost: 10,000 times the base cost
                upgrade_cost = item.base_cost * 20000
                market_price = game_state.market_prices.get(item.name, item.base_price)
                own_price = market_price * 0.5

                print(f"  {i}. {item.name}")
                print(f"      Cost: ${upgrade_cost:,.2f} | Current Market: ${market_price:.2f} → Own: ${own_price:.2f}")
                available.append((i, item, upgrade_cost))

        if not available:
            print("  (All production lines owned!)")

        print("\n  0. Back to Upgrades Menu")

        try:
            if not available:
                input("\nPress Enter to continue...")
                break

            choice = input(f"\nSelect production line to purchase (0-{len(game_state.items)}): ")
            choice_num = int(choice)

            if choice_num == 0:
                break

            # Find selected item
            selected_item = None
            selected_cost = 0
            for idx, item, cost in available:
                if idx == choice_num:
                    selected_item = item
                    selected_cost = cost
                    break

            if selected_item:
                if player.cash < selected_cost:
                    print(f"\n✗ Not enough cash! Need ${selected_cost:,.2f}, have ${player.cash:.2f}")
                else:
                    # Create and purchase the production line upgrade
                    production_upgrade = Upgrade(
                        name=f"Production Line: {selected_item.name}",
                        cost=selected_cost,
                        effect_type="production_line",
                        effect_value=0,  # Not used
                        vendor_name=selected_item.name  # Store item name in vendor_name field
                    )

                    success = player.purchase_upgrade(production_upgrade, game_state.day)
                    if success:
                        market_price = game_state.market_prices.get(selected_item.name, selected_item.base_price)
                        own_price = market_price * 0.5
                        print(f"\n✓ Purchased Production Line: {selected_item.name} for ${selected_cost:,.2f}!")
                        print(f"  You can now purchase {selected_item.name} at ${own_price:.2f} (50% of market)")
                        print(f"  This will be used automatically when buying!")
                    else:
                        print("\n✗ Failed to purchase production line")
            else:
                print("\n✗ Invalid selection!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def vendor_partnerships_menu(game_state: GameState, player: Player) -> None:
    """Menu for purchasing vendor partnerships (temporary, 30-day duration, max 15% discount)."""
    while True:
        print("\n" + "=" * 70)
        print("VENDOR PARTNERSHIPS MENU")
        print("=" * 70)
        print(f"\nYour Cash: ${player.cash:.2f}")
        print(f"Current Day: {game_state.day}")
        print("\n⚠️  Partnerships last 30 days and DO NOT stack (max 15% total discount per vendor)")

        # Show active partnerships with expiration
        active_partnerships = [u for u in player.purchased_upgrades if u.effect_type == "vendor_discount"]
        if active_partnerships:
            print("\n📋 Active Partnerships:")
            for upgrade in active_partnerships:
                expiration_day = player.vendor_partnership_expiration.get(upgrade.name, 0)
                days_left = expiration_day - game_state.day
                discount = player.get_vendor_discount(upgrade.vendor_name, game_state.day)
                print(f"  ✓ {upgrade.name} - {upgrade.effect_value}% discount")
                print(f"      Expires: Day {expiration_day} ({days_left} days left)")
                print(f"      Total discount for {upgrade.vendor_name}: {discount * 100:.0f}%")
        else:
            print("\n📋 No active partnerships")

        # Show available partnerships (including those that can be re-purchased)
        print("\n🛒 Available Partnerships:")
        available = []
        vendor_partnerships = [u for u in game_state.available_upgrades if u.effect_type == "vendor_discount"]

        for i, upgrade in enumerate(vendor_partnerships, 1):
            current_discount = player.get_vendor_discount(upgrade.vendor_name, game_state.day)
            can_purchase = current_discount < 0.15  # Max 15%

            if can_purchase:
                status = ""
                if current_discount > 0:
                    status = f" (Current: {current_discount * 100:.0f}%, New total: {(current_discount + upgrade.effect_value / 100) * 100:.0f}%)"
                print(f"  {i}. {upgrade.name} - ${upgrade.cost:,.2f}")
                print(f"      Effect: +{upgrade.effect_value}% discount for 30 days{status}")
                available.append((i, upgrade))

        if not available:
            print("  (All partnerships at maximum discount!)")

        print("\n  0. Back to Upgrades Menu")

        try:
            choice = input(f"\nSelect partnership to purchase (0-{len(vendor_partnerships)}): ").strip()
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
                    print(f"\n✗ Not enough cash! Need ${selected_upgrade.cost:,.2f}, have ${player.cash:.2f}")
                else:
                    success = player.purchase_upgrade(selected_upgrade, game_state.day)
                    if success:
                        expiration_day = game_state.day + selected_upgrade.duration_days
                        print(f"\n✓ Purchased {selected_upgrade.name} for ${selected_upgrade.cost:,.2f}!")
                        print(f"  Effect: +{selected_upgrade.effect_value}% discount on {selected_upgrade.vendor_name}")
                        print(f"  Duration: 30 days (expires on day {expiration_day})")
                        new_discount = player.get_vendor_discount(selected_upgrade.vendor_name, game_state.day)
                        print(f"  Total discount for {selected_upgrade.vendor_name}: {new_discount * 100:.0f}%")
                    else:
                        print("\n✗ Failed to purchase partnership (at maximum discount)")
            else:
                print("\n✗ Invalid partnership selection!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def upgrades_menu(game_state: GameState, player: Player) -> None:
    """Menu for purchasing store upgrades."""
    while True:
        print("\n" + "=" * 70)
        print("STORE UPGRADES MENU")
        print("=" * 70)
        print(f"\nYour Cash: ${player.cash:.2f}")

        # Show purchased permanent upgrades (exclude vendor partnerships)
        permanent_upgrades = [u for u in player.purchased_upgrades if u.effect_type != "vendor_discount"]
        if permanent_upgrades:
            print("\n📦 Your Permanent Upgrades:")
            for upgrade in permanent_upgrades:
                effect_desc = _get_upgrade_effect_description(upgrade)
                print(f"  ✓ {upgrade.name} - {effect_desc}")
        else:
            print("\n📦 No permanent upgrades purchased yet")

        # Show available permanent upgrades (not yet purchased, exclude vendor partnerships)
        print("\n🛒 Available Permanent Upgrades:")
        available = []
        for i, upgrade in enumerate(game_state.available_upgrades, 1):
            # Skip vendor partnerships (shown in separate submenu)
            if upgrade.effect_type == "vendor_discount":
                continue

            # Check if already purchased
            already_purchased = any(u.name == upgrade.name for u in player.purchased_upgrades)
            if not already_purchased:
                effect_desc = _get_upgrade_effect_description(upgrade)
                print(f"  {i}. {upgrade.name} - ${upgrade.cost:,.2f}")
                print(f"      Effect: {effect_desc}")
                available.append((i, upgrade))

        if not available:
            print("  (All permanent upgrades purchased!)")

        print("\n  v. Vendor Partnerships (30-day duration, max 15% discount)")
        print("  p. Production Line Upgrades (Late Game)")
        print("  0. Back to Main Menu")

        try:
            choice = input(f"\nSelect upgrade to purchase (0-{len(game_state.available_upgrades)}, v, p): ").strip().lower()

            # Handle vendor partnerships submenu
            if choice == 'v':
                vendor_partnerships_menu(game_state, player)
                continue

            # Handle production line submenu
            if choice == 'p':
                production_line_menu(game_state, player)
                continue

            if not available and choice != '0':
                input("\nPress Enter to continue...")
                continue

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
                    success = player.purchase_upgrade(selected_upgrade, game_state.day)
                    if success:
                        effect_desc = _get_upgrade_effect_description(selected_upgrade)
                        print(f"\n✓ Purchased {selected_upgrade.name} for ${selected_upgrade.cost:.2f}!")
                        print(f"  Effect: {effect_desc}")
                    else:
                        print("\n✗ Failed to purchase upgrade (already owned)")
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
    elif upgrade.effect_type == "wage_reduction":
        return f"-${int(upgrade.effect_value)} monthly wage per employee (from $500 to $400)"
    elif upgrade.effect_type == "production_line":
        return f"Own production for {upgrade.vendor_name} (50% market price)"
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


def display_customer_forecast(game_state: GameState) -> None:
    """Display expected customer traffic for the day."""
    print("\n" + "=" * 60)
    print("CUSTOMER FORECAST")
    print("=" * 60)
    print(f"\nDay {game_state.day} Expected Customers:")

    # Calculate base customer count
    base_customer_count = len(game_state.players) * 10 + game_state.day

    # Check for 14-day event
    event_bonus = 0
    if game_state.day % 14 == 0:
        occurrence_count = game_state.day // 14
        event_bonus = 20 * occurrence_count
        base_customer_count += event_bonus

    # Calculate uncapped customers
    uncapped_customer_count = 0
    if game_state.day >= 50:
        uncapped_customer_count = ((game_state.day - 40) // 10)

    print(f"\n📊 Regular Customers: {base_customer_count}")
    print(f"   - These customers are limited by your cashier capacity")
    print(f"   - Types: Low ($20), Medium ($50), High ($100) budgets")

    if event_bonus > 0:
        print(f"\n🎊 14-Day Event Bonus: +{event_bonus} customers!")

    if uncapped_customer_count > 0:
        print(f"\n💎 Uncapped Customers: {uncapped_customer_count}")
        print(f"   - These customers BYPASS cashier limits!")
        print(f"   - Each buys exactly 1 expensive item (≥$100)")
        expensive_items = [item for item in game_state.items if item.base_price >= 100]
        print(f"   - Available expensive items: {len(expensive_items)}")
        if len(expensive_items) > 0:
            print(f"   - Price range: ${min(i.base_price for i in expensive_items):.2f} - ${max(i.base_price for i in expensive_items):.2f}")
    elif game_state.day < 50:
        print(f"\n💎 Uncapped Customers: Not yet available")
        print(f"   - Unlock at day 50 (in {50 - game_state.day} days)")

    total = base_customer_count + uncapped_customer_count
    print(f"\n🎯 Total Expected: {total} customers")
    print("=" * 60)


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
        print("  c. Customer Forecast")
        print("  s. Save Game")
        print("  0. Quit Game")

        try:
            choice = input("\nSelect option (0-9, c, s): ").strip().lower()

            # Handle customer forecast
            if choice == 'c':
                display_customer_forecast(game_state)
                input("\nPress Enter to continue...")
                continue

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
                # Pass day - handle multiplayer turn system
                if len(game_state.human_players) > 1:
                    # Mark this player as having passed
                    game_state.players_passed.add(game_state.current_player_index)

                    # Check if all players have passed
                    if len(game_state.players_passed) == len(game_state.human_players):
                        # All players passed - actually pass the day
                        run_day(game_state, show_details=True)
                        # Reset the passed set for next day
                        game_state.players_passed.clear()
                        input("\nPress Enter to continue...")
                        return True
                    else:
                        # Not all players passed yet - continue to next player
                        print(f"\n✓ {player.name} has passed. Waiting for other players...")
                        input("\nPress Enter to continue...")
                        return True
                else:
                    # Single player - pass day immediately
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
                "max_per_item_per_player": vendor.max_per_item_per_player,
                "min_purchase": vendor.min_purchase,
                "price_min": vendor.price_min,
                "price_max": vendor.price_max,
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
                        "duration_days": upgrade.duration_days,
                    }
                    for upgrade in player.purchased_upgrades
                ],
                "is_human": player.is_human,
                "last_wage_payment_day": player.last_wage_payment_day,
                "vendor_partnership_expiration": player.vendor_partnership_expiration,
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
        "vendor_daily_purchases": game_state.vendor_daily_purchases,
        "players_passed": list(game_state.players_passed),
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
            max_per_item_per_player=vendor_data.get("max_per_item_per_player"),
            min_purchase=vendor_data.get("min_purchase"),
            price_min=vendor_data.get("price_min"),
            price_max=vendor_data.get("price_max"),
        )
        for vendor_data in data["vendors"]
    ]

    # Regenerate available upgrades (don't load from save to ensure balance changes are applied)
    available_upgrades = create_default_upgrades(vendors)

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
                duration_days=upgrade_data.get("duration_days", 0),
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
            last_wage_payment_day=player_data.get("last_wage_payment_day", 0),
            vendor_partnership_expiration=player_data.get("vendor_partnership_expiration", {}),
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
        vendor_daily_purchases=data.get("vendor_daily_purchases", {}),
        players_passed=set(data.get("players_passed", [])),
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
        item_demand = initialize_item_demand(items)

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
            item_demand=item_demand,
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

    if sorted_players:
        winner = sorted_players[0]
        print("\n" + "=" * 60)
        if winner.is_human:
            print("🎉 CONGRATULATIONS! YOU WON! 🎉")
        else:
            print(f"Winner: {winner.name}")
        print(f"Final cash: ${winner.cash:.2f}")
        print("=" * 60)
    else:
        print("\nNo players in game.")


if __name__ == "__main__":
    run_game()
