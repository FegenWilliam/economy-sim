# econ_sim.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import random
import json
import signal
import sys
import os


# -------------------------------------------------------------------
# Product Categories
# -------------------------------------------------------------------

# Category definitions with importance levels
# Importance: 3=essentials, 2=non-essentials, 1=luxury
PRODUCT_CATEGORIES = {
    "Food & Groceries": 3,
    "Fresh Produce": 3,
    "Household Essentials": 3,
    "Personal Care": 3,
    "Health & Pharmacy": 3,
    "Baby Products": 3,
    "Supplements": 2,
    "Pet Supplies": 2,
    "Kitchen & Dining": 2,
    "Office Supplies": 2,
    "Electronics": 2,
    "Appliances": 2,
    "Sports & Outdoor": 2,
    "Home Decor": 2,
    "Automotive": 2,
    "Gaming": 1,
    "Toys & Games": 1,
    "Luxury": 1,
}

# Specialty Score Configuration
# Rewards players for stocking a certain number of items from each category
# Format: category -> [(threshold, multiplier), ...] sorted by threshold ascending
# Bonuses are ADDITIVE: 1.2x (20% bonus) + 1.8x (80% bonus) = 2.0x total (100% bonus)
SPECIALTY_SCORE_THRESHOLDS = {
    # Essential categories (importance 3) - smaller bonuses
    "Food & Groceries": [(10, 1.2), (30, 1.5), (60, 2.5)],
    "Fresh Produce": [(6, 1.1)],
    "Household Essentials": [(8, 1.2)],
    "Personal Care": [(8, 1.2)],
    "Health & Pharmacy": [(6, 1.2)],
    "Baby Products": [(5, 1.3)],

    # Non-essential categories (importance 2) - medium bonuses
    "Supplements": [(5, 1.2)],
    "Pet Supplies": [(6, 1.2)],
    "Kitchen & Dining": [(8, 1.2), (15, 1.5)],
    "Office Supplies": [(8, 1.2)],
    "Electronics": [(10, 1.2), (20, 1.8)],
    "Appliances": [(10, 1.3)],
    "Sports & Outdoor": [(6, 1.2), (12, 1.5)],
    "Home Decor": [(8, 1.3)],
    "Automotive": [(5, 1.4), (10, 2.0)],

    # Luxury categories (importance 1) - highest bonuses
    "Gaming": [(5, 1.5)],
    "Toys & Games": [(6, 1.4), (12, 1.8)],
    "Luxury": [(5, 1.5), (10, 2.0), (15, 2.5), (18, 3.0)],
}

# Category Adjacency Mappings
# Defines which categories are "adjacent" (make sense to be sold together in the same store)
# Example: Electronics and Gaming are adjacent, but Electronics and Fresh Produce are not
CATEGORY_ADJACENCY = {
    "Food & Groceries": {"Fresh Produce", "Household Essentials", "Personal Care", "Health & Pharmacy", "Baby Products", "Pet Supplies"},
    "Fresh Produce": {"Food & Groceries", "Household Essentials", "Health & Pharmacy"},
    "Household Essentials": {"Food & Groceries", "Fresh Produce", "Personal Care", "Baby Products", "Kitchen & Dining", "Pet Supplies"},
    "Personal Care": {"Food & Groceries", "Household Essentials", "Health & Pharmacy", "Baby Products"},
    "Health & Pharmacy": {"Food & Groceries", "Fresh Produce", "Personal Care", "Baby Products", "Supplements"},
    "Baby Products": {"Food & Groceries", "Household Essentials", "Personal Care", "Health & Pharmacy", "Toys & Games"},
    "Supplements": {"Health & Pharmacy", "Sports & Outdoor", "Pet Supplies"},
    "Pet Supplies": {"Food & Groceries", "Household Essentials", "Supplements"},
    "Kitchen & Dining": {"Household Essentials", "Appliances", "Home Decor"},
    "Office Supplies": {"Electronics"},  # Minimal adjacency
    "Electronics": {"Gaming", "Appliances", "Automotive", "Luxury", "Office Supplies"},
    "Appliances": {"Electronics", "Kitchen & Dining", "Home Decor"},
    "Sports & Outdoor": {"Supplements", "Toys & Games", "Automotive"},
    "Home Decor": {"Kitchen & Dining", "Appliances", "Luxury"},
    "Automotive": {"Electronics", "Sports & Outdoor"},
    "Gaming": {"Electronics", "Toys & Games", "Luxury"},
    "Toys & Games": {"Baby Products", "Gaming", "Sports & Outdoor"},
    "Luxury": {"Electronics", "Gaming", "Home Decor"},
}


# -------------------------------------------------------------------
# Core data models
# -------------------------------------------------------------------

@dataclass
class Item:
    """An item that can be produced and sold."""
    name: str
    base_cost: float  # cost to produce 1 unit
    base_price: float  # default selling price (can be overridden by players)
    category: str  # product category (determines importance level)
    size: float = 1.0  # item size (affects inventory space; 0.1 = 10 items per slot, 10 = takes 10 slots)

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
        if self.category not in PRODUCT_CATEGORIES:
            raise ValueError(f"Item {self.name}: category '{self.category}' not found in PRODUCT_CATEGORIES")

    @property
    def importance(self) -> int:
        """Get importance level from category."""
        return PRODUCT_CATEGORIES[self.category]


# -------------------------------------------------------------------
# Product Packaging System
# -------------------------------------------------------------------

def get_package_info(item: Item, package_type: str = "standard") -> tuple:
    """
    Get packaging information for an item.

    Args:
        item: The item to package
        package_type: Either "standard" (5 size) or "bulk" (20 size)

    Returns:
        Tuple of (package_name, quantity_in_package, package_size)

    For items with size >= 5, returns the item as-is (no packaging).
    For luxury items, returns the item as-is (no packaging).
    For items with size < 5:
    - Standard package: 5 size total
    - Bulk package: 20 size total (only available at Bulk Master Co.)
    """
    # Items >= 5 size are not packaged
    if item.size >= 5.0:
        return (item.name, 1, item.size)

    # Luxury items are not packaged (nobody buys 50x diamond earrings)
    if item.category == "Luxury":
        return (item.name, 1, item.size)

    # Determine target package size
    target_size = 5.0 if package_type == "standard" else 20.0

    # Calculate how many items fit in the package
    quantity_in_package = int(target_size / item.size)

    # Determine package name based on item category and type
    package_prefix = _get_package_prefix(item, package_type)
    package_name = f"{package_prefix} of {item.name}"

    return (package_name, quantity_in_package, target_size)


def _get_package_prefix(item: Item, package_type: str) -> str:
    """
    Get the appropriate package prefix based on item category and package type.

    Standard packages (5 size): Box, Pack, Tray, Set, Bundle
    Bulk packages (20 size): Case, Carton, Crate, Pallet
    """
    if package_type == "bulk":
        # Bulk package prefixes
        if item.category in ["Food & Groceries", "Fresh Produce"]:
            return "Case"
        elif item.category in ["Personal Care", "Health & Pharmacy"]:
            return "Carton"
        elif item.category in ["Electronics", "Gaming"]:
            return "Crate"
        else:
            return "Case"
    else:
        # Standard package prefixes
        if item.category in ["Food & Groceries", "Fresh Produce"]:
            return "Tray"
        elif item.category in ["Office Supplies"]:
            return "Box"
        elif item.category in ["Personal Care", "Health & Pharmacy", "Baby Products"]:
            return "Pack"
        elif item.category in ["Electronics", "Gaming"]:
            return "Set"
        elif item.category in ["Household Essentials", "Pet Supplies"]:
            return "Bundle"
        else:
            return "Pack"


def parse_package_name(package_name: str) -> Optional[str]:
    """
    Parse a package name to extract the base item name.

    Args:
        package_name: Name like "Box of Pens" or "Case of Batteries"

    Returns:
        Base item name (e.g., "Pens", "Batteries"), or None if not a package
    """
    # List of known package prefixes
    prefixes = ["Box", "Pack", "Tray", "Set", "Bundle", "Case", "Carton", "Crate", "Pallet"]

    for prefix in prefixes:
        pattern = f"{prefix} of "
        if package_name.startswith(pattern):
            return package_name[len(pattern):]

    # Not a package name, return None
    return None


def is_package(name: str) -> bool:
    """Check if a name is a package name."""
    return parse_package_name(name) is not None


# Product catalog - items that can be unlocked over time
PRODUCT_CATALOG = [
    # Groceries & Food
    Item("Bread", 2.0, 5.0, "Food & Groceries", 1.0),
    Item("Milk", 3.0, 6.0, "Food & Groceries", 1.0),
    Item("Eggs", 2.5, 5.5, "Food & Groceries", 1.0),
    Item("Bananas", 1.5, 3.5, "Fresh Produce", 0.8),
    Item("Batteries", 5.0, 10.0, "Household Essentials", 0.3),
    Item("Rice", 5.0, 10.0, "Food & Groceries", 1.5),
    Item("Coffee", 6.0, 12.0, "Food & Groceries", 0.8),
    Item("Toilet Paper", 8.0, 15.0, "Household Essentials", 2.0),
    Item("Vitamins", 12.0, 24.0, "Supplements", 0.3),
    Item("Cheese", 4.0, 8.0, "Food & Groceries", 0.8),
    Item("Butter", 3.5, 7.0, "Food & Groceries", 0.5),
    Item("Yogurt", 2.0, 4.5, "Food & Groceries", 0.6),
    Item("Cereal", 3.0, 6.5, "Food & Groceries", 1.5),
    Item("Pasta", 2.0, 4.0, "Food & Groceries", 0.8),
    Item("Canned Soup", 1.5, 3.5, "Food & Groceries", 0.5),
    Item("Frozen Pizza", 4.0, 8.5, "Food & Groceries", 1.2),
    Item("Ice Cream", 3.5, 7.5, "Food & Groceries", 1.0),
    Item("Soda", 1.5, 3.0, "Food & Groceries", 0.8),
    Item("Orange Juice", 3.0, 6.0, "Food & Groceries", 1.0),
    Item("Tea Bags", 3.0, 6.5, "Food & Groceries", 0.6),
    Item("Sugar", 2.0, 4.5, "Food & Groceries", 1.2),
    Item("Flour", 3.0, 6.0, "Food & Groceries", 1.5),
    Item("Cooking Oil", 4.0, 8.0, "Food & Groceries", 1.0),
    Item("Salt", 1.0, 2.5, "Food & Groceries", 0.4),
    Item("Pepper", 2.0, 4.5, "Food & Groceries", 0.3),
    Item("Ketchup", 2.5, 5.0, "Food & Groceries", 0.7),
    Item("Mustard", 2.0, 4.5, "Food & Groceries", 0.6),
    Item("Mayo", 3.0, 6.0, "Food & Groceries", 0.8),
    Item("BBQ Sauce", 3.5, 7.0, "Food & Groceries", 0.7),

    # Fresh Produce
    Item("Apples", 2.5, 5.5, "Fresh Produce", 0.7),
    Item("Oranges", 3.0, 6.0, "Fresh Produce", 0.7),
    Item("Grapes", 4.0, 8.5, "Fresh Produce", 0.6),
    Item("Strawberries", 4.5, 9.0, "Fresh Produce", 0.5),
    Item("Tomatoes", 2.5, 5.5, "Fresh Produce", 0.6),
    Item("Lettuce", 2.0, 4.5, "Fresh Produce", 0.8),
    Item("Carrots", 1.5, 3.5, "Fresh Produce", 0.6),
    Item("Potatoes", 2.0, 4.0, "Fresh Produce", 1.0),
    Item("Onions", 1.5, 3.5, "Fresh Produce", 0.6),

    # Household Items
    Item("Paper Towels", 5.0, 10.0, "Household Essentials", 1.5),
    Item("Dish Soap", 3.0, 6.5, "Household Essentials", 0.7),
    Item("Laundry Detergent", 8.0, 16.0, "Household Essentials", 2.0),
    Item("Trash Bags", 5.0, 10.5, "Household Essentials", 1.0),
    Item("Sponges", 2.5, 5.5, "Household Essentials", 0.3),
    Item("Aluminum Foil", 4.0, 8.5, "Household Essentials", 0.8),
    Item("Plastic Wrap", 3.5, 7.5, "Household Essentials", 0.7),
    Item("Light Bulbs", 6.0, 12.0, "Household Essentials", 0.4),
    Item("Candles", 4.0, 8.5, "Household Essentials", 0.5),
    Item("Air Freshener", 3.5, 7.5, "Household Essentials", 0.6),

    # Personal Care
    Item("Shampoo", 5.0, 10.0, "Personal Care", 0.8),
    Item("Conditioner", 5.0, 10.0, "Personal Care", 0.8),
    Item("Body Wash", 4.5, 9.0, "Personal Care", 0.8),
    Item("Toothpaste", 3.0, 6.5, "Personal Care", 0.4),
    Item("Toothbrush", 2.5, 5.5, "Personal Care", 0.1),
    Item("Deodorant", 4.0, 8.5, "Personal Care", 0.5),
    Item("Razor Blades", 8.0, 16.0, "Personal Care", 0.2),
    Item("Shaving Cream", 4.5, 9.0, "Personal Care", 0.6),
    Item("Hand Soap", 3.0, 6.5, "Personal Care", 0.6),
    Item("Hand Sanitizer", 3.5, 7.5, "Personal Care", 0.5),
    Item("Tissues", 2.5, 5.5, "Personal Care", 0.7),
    Item("Cotton Swabs", 2.0, 4.5, "Personal Care", 0.2),

    # Electronics
    Item("Phone Charger", 8.0, 16.0, "Electronics", 0.3),
    Item("USB Cable", 5.0, 10.0, "Electronics", 0.2),
    Item("Earbuds", 12.0, 25.0, "Electronics", 0.3),
    Item("Phone Case", 10.0, 20.0, "Electronics", 0.2),
    Item("Screen Protector", 6.0, 12.0, "Electronics", 0.1),
    Item("Mouse Pad", 7.0, 15.0, "Electronics", 0.3),
    Item("Keyboard", 25.0, 50.0, "Electronics", 1.2),
    Item("Computer Mouse", 15.0, 30.0, "Electronics", 0.4),
    Item("Webcam", 35.0, 70.0, "Electronics", 0.6),
    Item("Microphone", 40.0, 80.0, "Electronics", 0.8),
    Item("USB Flash Drive", 10.0, 20.0, "Electronics", 0.05),
    Item("SD Card", 12.0, 25.0, "Electronics", 0.05),
    Item("HDMI Cable", 8.0, 16.0, "Electronics", 0.2),
    Item("Power Strip", 15.0, 30.0, "Electronics", 0.8),
    Item("Desk Lamp", 20.0, 40.0, "Electronics", 1.5),
    Item("Alarm Clock", 12.0, 25.0, "Electronics", 0.5),
    Item("Calculator", 10.0, 20.0, "Electronics", 0.3),
    Item("Portable Speaker", 30.0, 60.0, "Electronics", 1.0),
    Item("Bluetooth Headphones", 45.0, 90.0, "Electronics", 0.8),

    # Office Supplies
    Item("Pens", 3.0, 6.5, "Office Supplies", 0.1),
    Item("Pencils", 2.5, 5.5, "Office Supplies", 0.1),
    Item("Notebooks", 4.0, 8.5, "Office Supplies", 0.6),
    Item("Sticky Notes", 3.5, 7.5, "Office Supplies", 0.2),
    Item("Stapler", 8.0, 16.0, "Office Supplies", 0.4),
    Item("Tape Dispenser", 6.0, 12.0, "Office Supplies", 0.4),
    Item("Scissors", 5.0, 10.0, "Office Supplies", 0.3),
    Item("Ruler", 2.0, 4.5, "Office Supplies", 0.2),
    Item("Binder", 4.5, 9.0, "Office Supplies", 0.6),
    Item("File Folders", 6.0, 12.5, "Office Supplies", 0.4),
    Item("Printer Paper", 15.0, 30.0, "Office Supplies", 2.0),

    # Mid-range Electronics & Gaming
    Item("Tablet", 150.0, 300.0, "Electronics", 0.8),
    Item("E-Reader", 80.0, 160.0, "Electronics", 0.5),
    Item("Smart Watch", 120.0, 240.0, "Luxury", 0.3),
    Item("Fitness Tracker", 60.0, 120.0, "Electronics", 0.2),
    Item("Wireless Earbuds", 70.0, 140.0, "Electronics", 0.3),
    Item("Gaming Mouse", 45.0, 90.0, "Gaming", 0.4),
    Item("Gaming Keyboard", 60.0, 120.0, "Gaming", 1.2),
    Item("Monitor", 150.0, 300.0, "Electronics", 4.0),
    Item("External Hard Drive", 55.0, 110.0, "Electronics", 0.5),
    Item("Wireless Router", 50.0, 100.0, "Electronics", 0.8),
    Item("Smart Plug", 15.0, 30.0, "Electronics", 0.3),
    Item("Security Camera", 40.0, 80.0, "Electronics", 0.6),
    Item("Video Doorbell", 80.0, 160.0, "Electronics", 0.8),

    # Appliances & Home Electronics
    Item("Coffee Maker", 40.0, 80.0, "Appliances", 2.5),
    Item("Toaster", 25.0, 50.0, "Appliances", 1.5),
    Item("Blender", 35.0, 70.0, "Appliances", 2.0),
    Item("Microwave", 80.0, 160.0, "Appliances", 3.5),
    Item("Air Fryer", 70.0, 140.0, "Appliances", 3.0),
    Item("Slow Cooker", 35.0, 70.0, "Appliances", 2.5),
    Item("Electric Kettle", 30.0, 60.0, "Appliances", 1.5),
    Item("Hair Dryer", 25.0, 50.0, "Appliances", 0.8),
    Item("Iron", 20.0, 40.0, "Appliances", 1.2),
    Item("Vacuum Cleaner", 120.0, 240.0, "Appliances", 5.0),
    Item("Fan", 35.0, 70.0, "Appliances", 2.5),
    Item("Space Heater", 45.0, 90.0, "Appliances", 2.5),
    Item("Humidifier", 40.0, 80.0, "Appliances", 2.0),
    Item("Air Purifier", 90.0, 180.0, "Appliances", 3.5),

    # Expensive Electronics & Gaming
    Item("Laptop", 400.0, 800.0, "Gaming", 2.5),
    Item("Gaming Console", 300.0, 600.0, "Gaming", 2.0),
    Item("4K TV", 350.0, 700.0, "Gaming", 6.0),
    Item("Soundbar", 150.0, 300.0, "Electronics", 2.5),
    Item("Noise-Cancelling Headphones", 180.0, 360.0, "Gaming", 0.8),
    Item("Drone", 250.0, 500.0, "Luxury", 2.0),
    Item("VR Headset", 300.0, 600.0, "Gaming", 2.0),
    Item("Digital Camera", 400.0, 800.0, "Luxury", 1.5),
    Item("Projector", 300.0, 600.0, "Electronics", 3.5),
    Item("Smart Thermostat", 120.0, 240.0, "Electronics", 0.8),
    Item("Robot Vacuum", 200.0, 400.0, "Appliances", 3.5),
    Item("Electric Scooter", 350.0, 700.0, "Luxury", 8.0),

    # Luxury Items
    Item("Designer Handbag", 600.0, 1200.0, "Luxury", 2.0),
    Item("Leather Wallet", 100.0, 200.0, "Luxury", 0.2),
    Item("Sunglasses", 150.0, 300.0, "Luxury", 0.3),
    Item("Perfume", 80.0, 160.0, "Luxury", 0.4),
    Item("Cologne", 70.0, 140.0, "Luxury", 0.4),
    Item("Watch", 200.0, 400.0, "Luxury", 0.3),
    Item("Jewelry Box", 60.0, 120.0, "Luxury", 1.0),
    Item("Gold Necklace", 500.0, 1000.0, "Luxury", 0.2),
    Item("Silver Bracelet", 150.0, 300.0, "Luxury", 0.2),
    Item("Diamond Earrings", 800.0, 1600.0, "Luxury", 0.1),
    Item("Designer Shoes", 300.0, 600.0, "Luxury", 1.5),
    Item("Leather Jacket", 250.0, 500.0, "Luxury", 2.0),
    Item("Cashmere Sweater", 180.0, 360.0, "Luxury", 1.0),
    Item("Silk Scarf", 80.0, 160.0, "Luxury", 0.3),
    Item("Designer Jeans", 120.0, 240.0, "Luxury", 0.8),

    # Sports & Outdoor
    Item("Yoga Mat", 20.0, 40.0, "Sports & Outdoor", 1.5),
    Item("Dumbbells", 30.0, 60.0, "Sports & Outdoor", 1.5),
    Item("Tennis Racket", 60.0, 120.0, "Sports & Outdoor", 1.2),
    Item("Basketball", 15.0, 30.0, "Sports & Outdoor", 1.0),
    Item("Camping Tent", 100.0, 200.0, "Sports & Outdoor", 4.0),
    Item("Sleeping Bag", 50.0, 100.0, "Sports & Outdoor", 2.5),
    Item("Hiking Boots", 80.0, 160.0, "Sports & Outdoor", 1.5),

    # More Groceries & Food
    Item("Peanut Butter", 4.0, 8.0, "Food & Groceries", 0.9),
    Item("Jelly", 3.0, 6.0, "Food & Groceries", 0.7),
    Item("Honey", 5.0, 10.0, "Food & Groceries", 0.8),
    Item("Maple Syrup", 6.0, 12.0, "Food & Groceries", 0.9),
    Item("Crackers", 3.0, 6.0, "Food & Groceries", 0.8),
    Item("Chips", 2.5, 5.0, "Food & Groceries", 0.9),
    Item("Pretzels", 2.5, 5.0, "Food & Groceries", 0.8),
    Item("Popcorn", 2.0, 4.0, "Food & Groceries", 0.7),
    Item("Cookies", 3.5, 7.0, "Food & Groceries", 0.8),
    Item("Cake Mix", 3.0, 6.0, "Food & Groceries", 1.0),
    Item("Brownie Mix", 3.0, 6.0, "Food & Groceries", 0.9),
    Item("Chocolate Bar", 1.5, 3.0, "Food & Groceries", 0.2),
    Item("Candy", 1.0, 2.5, "Food & Groceries", 0.1),
    Item("Gum", 1.0, 2.5, "Food & Groceries", 0.05),
    Item("Mints", 1.5, 3.0, "Food & Groceries", 0.05),
    Item("Granola Bars", 4.0, 8.0, "Food & Groceries", 0.6),
    Item("Energy Bars", 5.0, 10.0, "Food & Groceries", 0.6),
    Item("Protein Powder", 25.0, 50.0, "Supplements", 1.5),
    Item("Fish Oil", 15.0, 30.0, "Supplements", 0.4),
    Item("Canned Tuna", 1.5, 3.5, "Food & Groceries", 0.4),
    Item("Canned Beans", 1.5, 3.5, "Food & Groceries", 0.5),
    Item("Canned Corn", 1.5, 3.5, "Food & Groceries", 0.5),
    Item("Canned Tomatoes", 2.0, 4.0, "Food & Groceries", 0.6),
    Item("Tomato Sauce", 2.0, 4.5, "Food & Groceries", 0.7),
    Item("Spaghetti Sauce", 3.0, 6.5, "Food & Groceries", 0.9),
    Item("Hot Sauce", 2.5, 5.5, "Food & Groceries", 0.5),
    Item("Soy Sauce", 3.0, 6.0, "Food & Groceries", 0.6),
    Item("Vinegar", 2.0, 4.5, "Food & Groceries", 0.9),
    Item("Olive Oil", 8.0, 16.0, "Food & Groceries", 1.2),
    Item("Coconut Oil", 9.0, 18.0, "Food & Groceries", 1.0),
    Item("Protein Shake", 4.0, 8.0, "Supplements", 0.7),
    Item("Sports Drink", 2.0, 4.5, "Food & Groceries", 0.8),
    Item("Energy Drink", 3.0, 6.0, "Food & Groceries", 0.6),
    Item("Bottled Water", 1.0, 2.5, "Food & Groceries", 0.8),
    Item("Sparkling Water", 1.5, 3.5, "Food & Groceries", 0.8),
    Item("Iced Tea", 2.0, 4.5, "Food & Groceries", 0.8),
    Item("Lemonade", 2.5, 5.5, "Food & Groceries", 0.9),

    # Pet Supplies
    Item("Dog Food", 15.0, 30.0, "Pet Supplies", 2.5),
    Item("Cat Food", 12.0, 24.0, "Pet Supplies", 1.5),
    Item("Dog Treats", 5.0, 10.0, "Pet Supplies", 0.6),
    Item("Cat Treats", 4.0, 8.0, "Pet Supplies", 0.4),
    Item("Dog Toy", 6.0, 12.0, "Pet Supplies", 0.5),
    Item("Cat Toy", 4.0, 8.0, "Pet Supplies", 0.3),
    Item("Pet Bowl", 8.0, 16.0, "Pet Supplies", 0.8),
    Item("Pet Collar", 10.0, 20.0, "Pet Supplies", 0.2),
    Item("Pet Leash", 12.0, 24.0, "Pet Supplies", 0.4),
    Item("Cat Litter", 10.0, 20.0, "Pet Supplies", 2.5),
    Item("Fish Tank", 40.0, 80.0, "Pet Supplies", 5.0),
    Item("Fish Food", 4.0, 8.0, "Pet Supplies", 0.3),
    Item("Bird Cage", 50.0, 100.0, "Pet Supplies", 6.0),
    Item("Bird Seed", 6.0, 12.0, "Pet Supplies", 1.0),

    # Baby Products
    Item("Diapers", 20.0, 40.0, "Baby Products", 2.5),
    Item("Baby Wipes", 5.0, 10.0, "Baby Products", 0.8),
    Item("Baby Formula", 25.0, 50.0, "Baby Products", 2.0),
    Item("Baby Bottle", 8.0, 16.0, "Baby Products", 0.4),
    Item("Pacifier", 4.0, 8.0, "Baby Products", 0.1),
    Item("Baby Lotion", 6.0, 12.0, "Baby Products", 0.6),
    Item("Baby Shampoo", 5.0, 10.0, "Baby Products", 0.6),
    Item("Baby Powder", 4.0, 8.0, "Baby Products", 0.5),
    Item("Diaper Bag", 30.0, 60.0, "Baby Products", 2.0),
    Item("Baby Blanket", 15.0, 30.0, "Baby Products", 1.0),
    Item("Teething Ring", 5.0, 10.0, "Baby Products", 0.2),

    # Pharmacy & Health
    Item("Pain Reliever", 8.0, 16.0, "Health & Pharmacy", 0.3),
    Item("Cold Medicine", 10.0, 20.0, "Health & Pharmacy", 0.4),
    Item("Allergy Medicine", 12.0, 24.0, "Health & Pharmacy", 0.3),
    Item("Band-Aids", 4.0, 8.0, "Health & Pharmacy", 0.2),
    Item("First Aid Kit", 20.0, 40.0, "Health & Pharmacy", 1.5),
    Item("Thermometer", 15.0, 30.0, "Health & Pharmacy", 0.3),
    Item("Cough Drops", 3.0, 6.0, "Health & Pharmacy", 0.2),
    Item("Antacid", 6.0, 12.0, "Health & Pharmacy", 0.3),
    Item("Eye Drops", 8.0, 16.0, "Health & Pharmacy", 0.2),
    Item("Lip Balm", 2.0, 4.5, "Health & Pharmacy", 0.05),
    Item("Sunscreen", 10.0, 20.0, "Health & Pharmacy", 0.6),
    Item("Bug Spray", 7.0, 14.0, "Health & Pharmacy", 0.6),

    # Kitchen & Dining
    Item("Plates Set", 20.0, 40.0, "Kitchen & Dining", 2.5),
    Item("Bowls Set", 15.0, 30.0, "Kitchen & Dining", 2.0),
    Item("Cups Set", 12.0, 24.0, "Kitchen & Dining", 1.5),
    Item("Silverware Set", 25.0, 50.0, "Kitchen & Dining", 1.5),
    Item("Cooking Pot", 30.0, 60.0, "Kitchen & Dining", 2.5),
    Item("Frying Pan", 25.0, 50.0, "Kitchen & Dining", 2.0),
    Item("Baking Sheet", 12.0, 24.0, "Kitchen & Dining", 1.0),
    Item("Mixing Bowl", 10.0, 20.0, "Kitchen & Dining", 1.0),
    Item("Cutting Board", 15.0, 30.0, "Kitchen & Dining", 0.8),
    Item("Kitchen Knife", 20.0, 40.0, "Kitchen & Dining", 0.5),
    Item("Can Opener", 8.0, 16.0, "Kitchen & Dining", 0.3),
    Item("Bottle Opener", 5.0, 10.0, "Kitchen & Dining", 0.1),
    Item("Measuring Cups", 10.0, 20.0, "Kitchen & Dining", 0.6),
    Item("Measuring Spoons", 8.0, 16.0, "Kitchen & Dining", 0.3),
    Item("Spatula", 7.0, 14.0, "Kitchen & Dining", 0.4),
    Item("Whisk", 6.0, 12.0, "Kitchen & Dining", 0.4),
    Item("Tongs", 8.0, 16.0, "Kitchen & Dining", 0.4),
    Item("Ladle", 7.0, 14.0, "Kitchen & Dining", 0.4),
    Item("Colander", 12.0, 24.0, "Kitchen & Dining", 1.5),
    Item("Grater", 10.0, 20.0, "Kitchen & Dining", 0.5),

    # Home Decor
    Item("Picture Frame", 12.0, 24.0, "Home Decor", 0.8),
    Item("Wall Art", 25.0, 50.0, "Home Decor", 1.5),
    Item("Throw Pillow", 15.0, 30.0, "Home Decor", 1.0),
    Item("Blanket", 25.0, 50.0, "Household Essentials", 1.5),
    Item("Curtains", 30.0, 60.0, "Home Decor", 1.5),
    Item("Area Rug", 60.0, 120.0, "Home Decor", 4.0),
    Item("Table Lamp", 35.0, 70.0, "Home Decor", 1.5),
    Item("Floor Lamp", 50.0, 100.0, "Home Decor", 2.5),
    Item("Wall Clock", 20.0, 40.0, "Home Decor", 1.0),
    Item("Vase", 18.0, 36.0, "Home Decor", 0.8),
    Item("Candle Holder", 12.0, 24.0, "Home Decor", 0.5),
    Item("Plant Pot", 10.0, 20.0, "Home Decor", 1.0),
    Item("Fake Plant", 15.0, 30.0, "Home Decor", 1.2),
    Item("Mirror", 40.0, 80.0, "Home Decor", 3.0),

    # Garden & Outdoor
    Item("Garden Hose", 25.0, 50.0, "Sports & Outdoor", 2.5),
    Item("Sprinkler", 20.0, 40.0, "Sports & Outdoor", 1.5),
    Item("Garden Gloves", 8.0, 16.0, "Sports & Outdoor", 0.3),
    Item("Plant Seeds", 3.0, 6.0, "Sports & Outdoor", 0.1),
    Item("Fertilizer", 12.0, 24.0, "Sports & Outdoor", 3.0),
    Item("Potting Soil", 10.0, 20.0, "Sports & Outdoor", 4.0),
    Item("Weed Killer", 15.0, 30.0, "Sports & Outdoor", 1.5),
    Item("Lawn Mower", 200.0, 400.0, "Sports & Outdoor", 15.0),
    Item("Rake", 18.0, 36.0, "Sports & Outdoor", 1.5),
    Item("Shovel", 22.0, 44.0, "Sports & Outdoor", 1.8),
    Item("Garden Shears", 15.0, 30.0, "Sports & Outdoor", 0.6),
    Item("Watering Can", 12.0, 24.0, "Sports & Outdoor", 1.5),
    Item("BBQ Grill", 150.0, 300.0, "Sports & Outdoor", 8.0),
    Item("Charcoal", 10.0, 20.0, "Sports & Outdoor", 2.5),
    Item("Lighter Fluid", 6.0, 12.0, "Sports & Outdoor", 0.8),
    Item("Patio Furniture", 250.0, 500.0, "Luxury", 20.0),

    # Toys & Games
    Item("Board Game", 20.0, 40.0, "Toys & Games", 1.5),
    Item("Puzzle", 15.0, 30.0, "Toys & Games", 1.0),
    Item("Playing Cards", 5.0, 10.0, "Toys & Games", 0.1),
    Item("Action Figure", 12.0, 24.0, "Toys & Games", 0.3),
    Item("Doll", 18.0, 36.0, "Toys & Games", 0.6),
    Item("Stuffed Animal", 15.0, 30.0, "Toys & Games", 0.8),
    Item("Building Blocks", 25.0, 50.0, "Toys & Games", 1.5),
    Item("Art Supplies", 20.0, 40.0, "Toys & Games", 1.2),
    Item("Crayons", 4.0, 8.0, "Toys & Games", 0.2),
    Item("Coloring Book", 5.0, 10.0, "Toys & Games", 0.3),
    Item("Play-Doh", 8.0, 16.0, "Toys & Games", 0.5),
    Item("Remote Control Car", 40.0, 80.0, "Toys & Games", 1.5),
    Item("Nerf Gun", 25.0, 50.0, "Toys & Games", 1.0),
    Item("Water Gun", 10.0, 20.0, "Toys & Games", 0.6),
    Item("Frisbee", 8.0, 16.0, "Sports & Outdoor", 0.4),
    Item("Soccer Ball", 18.0, 36.0, "Sports & Outdoor", 1.0),
    Item("Football", 20.0, 40.0, "Sports & Outdoor", 1.0),
    Item("Baseball Glove", 35.0, 70.0, "Sports & Outdoor", 1.0),
    Item("Baseball Bat", 30.0, 60.0, "Sports & Outdoor", 1.2),

    # Automotive
    Item("Car Phone Mount", 15.0, 30.0, "Automotive", 0.4),
    Item("Car Charger", 12.0, 24.0, "Automotive", 0.2),
    Item("Jumper Cables", 25.0, 50.0, "Automotive", 1.5),
    Item("Car Air Freshener", 3.0, 6.0, "Automotive", 0.1),
    Item("Windshield Wiper", 18.0, 36.0, "Automotive", 0.8),
    Item("Motor Oil", 20.0, 40.0, "Automotive", 1.5),
]


@dataclass
class Vendor:
    """A vendor that sells items to players at wholesale prices."""
    name: str
    pricing_multiplier: float = 1.0  # Multiplier applied to market price (e.g., 0.7 = 70% of market)
    selection_type: str = "all"  # "random_daily", "price_threshold", "price_range", "all", "category"
    selection_params: float = 0.0  # For random_daily: count of items. For price_threshold: max price
    items: Dict[str, float] = field(default_factory=dict)  # item_name -> wholesale_price (refreshed daily)
    max_per_item_per_player: Optional[int] = None  # Max quantity per item per player per day (None = unlimited)
    min_purchase: Optional[int] = None  # Minimum quantity per purchase (None = no minimum)
    price_min: Optional[float] = None  # Minimum price threshold (None = no minimum)
    price_max: Optional[float] = None  # Maximum price threshold (None = no maximum)
    lead_time: int = 0  # Number of days for delivery (0 = instant delivery)
    volume_pricing_tiers: Optional[List[tuple]] = None  # List of (quantity_threshold, pricing_multiplier) sorted by quantity
    required_reputation: Optional[float] = None  # Minimum reputation required to use this vendor
    required_level: Optional[int] = None  # Minimum player level required to use this vendor
    allowed_categories: Optional[List[str]] = None  # If set, only items from these categories are available

    def get_price(self, item_name: str, quantity: int = 1) -> Optional[float]:
        """
        Get the wholesale price for an item from this vendor.
        If quantity is provided and volume_pricing_tiers is set, returns price with volume discount.
        """
        base_price = self.items.get(item_name)
        if base_price is None:
            return None

        # Apply volume pricing if available
        if self.volume_pricing_tiers and quantity > 0:
            # Find the appropriate tier (tiers are sorted by quantity descending)
            applicable_multiplier = self.pricing_multiplier
            for threshold, multiplier in self.volume_pricing_tiers:
                if quantity >= threshold:
                    applicable_multiplier = multiplier
                    break
            # Recalculate price with volume discount multiplier
            # base_price was calculated with pricing_multiplier, so we need to adjust
            market_price = base_price / self.pricing_multiplier
            return market_price * applicable_multiplier

        return base_price


@dataclass
class Upgrade:
    """An upgrade that players can purchase once."""
    name: str
    cost: float
    effect_type: str  # "xp_gain", "vendor_discount", "lead_time_reduction", "wage_reduction", "production_line"
    effect_value: float  # Amount of the effect
    vendor_name: str = ""  # Only used for vendor_discount type
    duration_days: int = 0  # Duration in days (0 = permanent, >0 = temporary)


@dataclass
class Warehouse:
    """Represents a warehouse owned by a player."""
    level: int = 1  # Warehouse level (1-10), each level adds 500 capacity
    workers: int = 0  # Number of workers in this warehouse (max 5)


@dataclass
class Loan:
    """Represents a loan taken by a player."""
    lender_name: str  # Name of the lending institution
    principal: float  # Original loan amount
    remaining_balance: float  # Current amount owed (principal + interest)
    interest_rate: float  # Interest rate (as decimal, e.g., 0.10 for 10%)
    early_interest_rate: float  # Reduced interest rate for early payoff (as decimal)
    due_day: int  # Game day when loan must be paid
    taken_day: int  # Game day when loan was taken


@dataclass
class RecurringBuyOrder:
    """Represents a recurring buy order that executes every N days."""
    item_name: str
    vendor_name: str
    quantity: int
    interval_days: int  # Execute every N days
    last_executed_day: int = 0  # Last day this order was executed


@dataclass
class Player:
    """Represents a company / player in the economic simulation."""
    name: str
    cash: float = 0.0
    inventory: Dict[str, int] = field(default_factory=dict)  # item_name -> quantity
    prices: Dict[str, float] = field(default_factory=dict)   # item_name -> selling price
    buy_orders: Dict[str, List[tuple]] = field(default_factory=dict)  # item_name -> [(quantity, vendor_name), ...] (up to 3 vendors)
    restockers: int = 0  # Warehouse Workers: Each adds +300 max inventory capacity
    marketing_agents: int = 0  # Marketing agents boost customer attraction
    cashiers: int = 0  # Cashiers: Each handles 200 customers/day (owner handles 100 base)
    store_level: int = 1  # Store level (affects inventory capacity)
    experience: float = 0.0  # XP gained from profits
    item_costs: Dict[str, float] = field(default_factory=dict)  # Track cost per item for profit calculation
    purchased_upgrades: List['Upgrade'] = field(default_factory=list)  # Upgrades bought by this player
    is_human: bool = False  # Whether this is a human-controlled player
    reputation: float = 0.0  # Store reputation from -100 to 100, affects customer choice
    average_fulfillment_pct: float = 70.0  # Average % of customer needs fulfilled (used for scoring)
    allocated_average_fulfillment_pct: float = 70.0  # Avg fulfillment for initially assigned customers
    overflow_average_fulfillment_pct: float = 70.0  # Avg fulfillment for overflow customers
    last_wage_payment_day: int = 0  # Track when wages were last paid (for 30-day wage cycle)
    vendor_partnership_expiration: Dict[str, int] = field(default_factory=dict)  # upgrade_name -> expiration_day (for temporary vendor partnerships)
    price_history: Dict[str, float] = field(default_factory=dict)  # item_name -> previous_price (for consistency tracking)
    pending_deliveries: List[tuple] = field(default_factory=list)  # List of (item_name, quantity, cost_per_item, delivery_day) for orders with lead time
    loans: List['Loan'] = field(default_factory=list)  # Active loans taken by the player
    warehouses: List['Warehouse'] = field(default_factory=lambda: [Warehouse()])  # List of warehouses (starts with 1)
    recurring_buy_orders: List[RecurringBuyOrder] = field(default_factory=list)  # Recurring buy orders (scheduled)
    stock_minimum_restock: Dict[str, tuple] = field(default_factory=dict)  # item_name -> (minimum_stock, vendor_name) for auto-restock
    category_minimum_restock: Dict[str, tuple] = field(default_factory=dict)  # category_name -> (minimum_stock_per_item, vendor_name) for category auto-restock
    category_pricing: Dict[str, float] = field(default_factory=dict)  # category -> percentage below market (e.g., 5.0 = 5% below market)
    yesterday_demand: Dict[str, int] = field(default_factory=dict)  # item_name -> total quantity wanted yesterday (for lead time calculation)
    category_sales_history: Dict[int, Dict[str, float]] = field(default_factory=dict)  # day -> category -> total_sales_value (for main category detection)
    items_stocked_today: Set[str] = field(default_factory=set)  # Track items that were stocked for the first time today (resets each day)

    def set_buy_order(self, item_name: str, quantity: int, vendor_name: str) -> None:
        """
        Legacy method: Set a single buy order for an item.
        Clears any existing orders and sets one vendor.
        """
        if quantity > 0:
            self.buy_orders[item_name] = [(quantity, vendor_name)]
        else:
            self.buy_orders.pop(item_name, None)

    def get_buy_order(self, item_name: str) -> List[tuple]:
        """
        Get the buy order list for an item.
        Returns list of (quantity, vendor_name) tuples, or empty list if not set.
        """
        return self.buy_orders.get(item_name, [])

    def add_vendor_to_buy_order(self, item_name: str, quantity: int, vendor_name: str) -> bool:
        """
        Add a vendor to the buy order for an item (up to 3 vendors).
        Returns True if added successfully, False if limit reached.
        """
        if item_name not in self.buy_orders:
            self.buy_orders[item_name] = []

        # Check if vendor already exists for this item
        for i, (q, v) in enumerate(self.buy_orders[item_name]):
            if v == vendor_name:
                # Update quantity for existing vendor
                self.buy_orders[item_name][i] = (quantity, vendor_name)
                return True

        # Check vendor limit (max 3)
        if len(self.buy_orders[item_name]) >= 3:
            return False

        # Add new vendor
        if quantity > 0:
            self.buy_orders[item_name].append((quantity, vendor_name))

        return True

    def remove_vendor_from_buy_order(self, item_name: str, vendor_name: str) -> None:
        """Remove a specific vendor from the buy order for an item."""
        if item_name not in self.buy_orders:
            return

        self.buy_orders[item_name] = [(q, v) for q, v in self.buy_orders[item_name] if v != vendor_name]

        # Clean up empty lists
        if not self.buy_orders[item_name]:
            self.buy_orders.pop(item_name, None)

    def clear_buy_order(self, item_name: str) -> None:
        """Clear all vendors for an item's buy order."""
        self.buy_orders.pop(item_name, None)

    def get_total_buy_order_quantity(self, item_name: str) -> int:
        """Get total quantity across all vendors for an item."""
        return sum(q for q, v in self.get_buy_order(item_name))

    def get_max_inventory(self) -> int:
        """Get max inventory capacity (total items that can be stored)."""
        # Warehouse capacity: each warehouse level 1 = 500, +500 per upgrade (level 10 = 5000)
        warehouse_capacity = sum(warehouse.level * 500 for warehouse in self.warehouses)

        # Warehouse workers add capacity
        total_workers = sum(warehouse.workers for warehouse in self.warehouses)
        worker_bonus = total_workers * 300

        return int(warehouse_capacity + worker_bonus)

    def get_inventory_size_used(self, items_by_name: Dict[str, 'Item']) -> float:
        """Calculate total inventory space used based on item sizes."""
        total_size = 0.0
        for item_name, quantity in self.inventory.items():
            if item_name in items_by_name:
                item_size = items_by_name[item_name].size
                total_size += item_size * quantity
        return total_size

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
        Formula: 500 * (1 + current_level // 5) * current_level
                 + (10000 * (current_level // 10))
        """
        level = self.store_level
        return 500 * (1 + level // 5) * level + (10000 * (level // 10))

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

    def hire_warehouse_worker(self, warehouse_index: int) -> bool:
        """
        Hire a warehouse worker for a specific warehouse.
        - Cost: $500 upfront, $500/month
        - Each warehouse can have at most 5 workers
        - Adds +300 max inventory per worker
        Returns True if successful, False if not enough cash or warehouse is full.
        """
        if warehouse_index < 0 or warehouse_index >= len(self.warehouses):
            return False

        warehouse = self.warehouses[warehouse_index]
        if warehouse.workers >= 5:
            return False

        HIRING_COST = 500.0
        if self.cash < HIRING_COST:
            return False

        self.cash -= HIRING_COST
        warehouse.workers += 1
        return True

    def hire_employee(self, employee_type: str) -> bool:
        """
        Hire an employee.
        - Cashier: $500 upfront, $500/month, handles 200 customers/day
        - Marketing Agent: 5x scaling cost (1k, 5k, 25k...), $1000/month, requires level 5+
        Returns True if successful, False if not enough cash or requirements not met.
        """
        if employee_type == "cashier":
            HIRING_COST = 500.0
            if self.cash < HIRING_COST:
                return False
            self.cash -= HIRING_COST
            self.cashiers += 1
            return True
        elif employee_type == "marketing_agent":
            # Level 5+ required
            if self.store_level < 5:
                return False
            # Scaling cost: 1k * (5 ^ current_count)
            HIRING_COST = 1000.0 * (5 ** self.marketing_agents)
            if self.cash < HIRING_COST:
                return False
            self.cash -= HIRING_COST
            self.marketing_agents += 1
            return True
        else:
            return False

    def pay_monthly_wages(self, current_day: int) -> float:
        """
        Pay monthly wages for all employees every 30 days.
        - Warehouse workers: $500/month each
        - Cashiers: $500/month each
        - Marketing agents: $1000/month each
        Only pays if 30 days have passed since last payment.
        Returns total wages paid (0 if not a payment day).
        """
        # Check if it's time to pay wages (every 30 days)
        if current_day - self.last_wage_payment_day < 30:
            return 0.0

        # Calculate total warehouse workers
        total_warehouse_workers = sum(warehouse.workers for warehouse in self.warehouses)

        # Total employees
        total_employees = total_warehouse_workers + self.cashiers + self.marketing_agents

        # No wages if no employees
        if total_employees == 0:
            return 0.0

        # Warehouse workers: $500/month
        warehouse_worker_wage = 500.0
        # Cashiers: $500/month
        cashier_wage = 500.0
        # Marketing agents: $1000/month
        marketing_agent_wage = 1000.0

        # Apply wage reduction upgrades (applies to all wages)
        wage_reduction = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "wage_reduction")

        actual_worker_wage = max(0, warehouse_worker_wage - wage_reduction)
        actual_cashier_wage = max(0, cashier_wage - wage_reduction)
        actual_agent_wage = max(0, marketing_agent_wage - wage_reduction)

        wages = (total_warehouse_workers * actual_worker_wage) + (self.cashiers * actual_cashier_wage) + (self.marketing_agents * actual_agent_wage)
        self.cash -= wages
        self.last_wage_payment_day = current_day
        return wages

    def get_total_warehouse_level(self) -> int:
        """Get total warehouse level across all warehouses."""
        return sum(warehouse.level for warehouse in self.warehouses)

    def buy_warehouse(self) -> bool:
        """
        Buy a new warehouse.
        - Cost: $20000 * number of warehouses already owned
        - Max 4 warehouses per player
        Returns True if successful, False otherwise.
        """
        if len(self.warehouses) >= 4:
            return False

        cost = 20000.0 * len(self.warehouses)
        if self.cash < cost:
            return False

        self.cash -= cost
        self.warehouses.append(Warehouse())
        return True

    def upgrade_warehouse(self, warehouse_index: int) -> bool:
        """
        Upgrade a warehouse by one level.
        - Cost: $5000 * current total warehouse level
        - Max level per warehouse: 10
        Returns True if successful, False otherwise.
        """
        if warehouse_index < 0 or warehouse_index >= len(self.warehouses):
            return False

        warehouse = self.warehouses[warehouse_index]
        if warehouse.level >= 10:
            return False

        total_level = self.get_total_warehouse_level()
        cost = 5000.0 * total_level

        if self.cash < cost:
            return False

        self.cash -= cost
        warehouse.level += 1
        return True

    def set_category_pricing(self, category: str, percent_below_market: float, market_prices: Dict[str, float], items_by_name: Dict[str, 'Item']) -> None:
        """
        Set pricing for an entire category as a percentage below market price.
        Updates all item prices in that category immediately.

        Args:
            category: Category name (e.g., "Food & Groceries")
            percent_below_market: Percentage below market (e.g., 5.0 = 5% below market, -5.0 = 5% above market)
            market_prices: Current market prices
            items_by_name: Dictionary mapping item names to Item objects
        """
        if category not in PRODUCT_CATEGORIES:
            raise ValueError(f"Invalid category: {category}")

        # Store the category pricing rule
        self.category_pricing[category] = percent_below_market

        # Update all prices for items in this category
        for item_name, item in items_by_name.items():
            if item.category == category:
                if item_name in market_prices:
                    new_price = market_prices[item_name] * (1 - percent_below_market / 100.0)
                    if new_price > 0:
                        # Track price history for consistency bonus
                        if item_name in self.prices:
                            self.price_history[item_name] = self.prices[item_name]
                        self.prices[item_name] = new_price

    def update_prices_from_market(self, market_prices: Dict[str, float], items_by_name: Dict[str, 'Item']) -> None:
        """
        Update all item prices based on current market prices and category pricing rules.
        Called when market prices change to keep player prices synchronized.

        Args:
            market_prices: Current market prices
            items_by_name: Dictionary mapping item names to Item objects
        """
        for category, percent_below in self.category_pricing.items():
            for item_name, item in items_by_name.items():
                if item.category == category and item_name in market_prices:
                    new_price = market_prices[item_name] * (1 - percent_below / 100.0)
                    if new_price > 0:
                        # Track price history for consistency bonus
                        if item_name in self.prices:
                            self.price_history[item_name] = self.prices[item_name]
                        self.prices[item_name] = new_price

    def get_category_pricing_percent(self, category: str) -> Optional[float]:
        """Get the pricing percentage for a category, or None if not set."""
        return self.category_pricing.get(category)

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

        # Track if this is the first time stocking this item today
        if current_inventory == 0 and quantity > 0:
            self.items_stocked_today.add(item.name)

        self.inventory[item.name] = current_inventory + quantity

    def sell_to_customer(self, item_name: str, quantity: int, unit_price: float, current_day: int = 1, item_category: Optional[str] = None) -> tuple:
        """
        Attempt to sell 'quantity' units of 'item_name' at 'unit_price'.
        Returns (revenue, profit, units_sold) tuple.
        Profit = revenue - cost
        Tracks sales by category for adjacency calculations.
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

            # Track sales by category for adjacency calculations
            if item_category is not None:
                if current_day not in self.category_sales_history:
                    self.category_sales_history[current_day] = {}
                self.category_sales_history[current_day][item_category] = \
                    self.category_sales_history[current_day].get(item_category, 0.0) + revenue

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
        Checks reputation requirements.

        Handles packaged items: If item_name is a package (e.g., "Box of Pens"),
        the purchase adds individual items to inventory, not the package itself.
        """
        if quantity <= 0:
            return False

        # Check if this is a packaged item
        base_item_name = parse_package_name(item_name)
        items_per_package = 1
        actual_item_name = item_name

        if base_item_name is not None:
            # This is a package, so we need to convert to individual items
            actual_item_name = base_item_name

            # Find the item in the catalog to get package info
            item_obj = next((i for i in PRODUCT_CATALOG if i.name == base_item_name), None)
            if item_obj:
                # Determine package type based on package name prefix
                if item_name.startswith("Case") or item_name.startswith("Carton") or item_name.startswith("Crate"):
                    _, items_per_package, _ = get_package_info(item_obj, "bulk")
                else:
                    _, items_per_package, _ = get_package_info(item_obj, "standard")

        # Check reputation requirement
        if vendor.required_reputation is not None and self.reputation < vendor.required_reputation:
            return False

        # Check level requirement
        if vendor.required_level is not None and self.store_level < vendor.required_level:
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

            # Get current purchases for this item today (track by package name)
            current_purchases = game_state.vendor_daily_purchases[self.name][vendor.name].get(item_name, 0)

            # Check if this purchase would exceed the limit
            if current_purchases + quantity > vendor.max_per_item_per_player:
                return False

        # Check if player owns production line for this item (takes priority)
        # Production lines work on the base item, not packages
        production_price = self.get_production_line_price(actual_item_name, market_price) if market_price > 0 else None

        if production_price is not None:
            # Use production line pricing (50% of market)
            # For packages, this is the price per individual item
            final_price_per_unit = production_price
        else:
            # Use vendor pricing with volume discounts
            vendor_price = vendor.get_price(item_name, quantity)
            if vendor_price is None:
                return False

            # Apply vendor discount
            current_day = game_state.day if game_state else 0
            discount = self.get_vendor_discount(vendor.name, current_day)
            final_price_package = vendor_price * (1.0 - discount)

            # Apply catch-up discount for non-dominating players (starts day 10)
            if game_state and game_state.day >= 10:
                # Find the highest level player
                highest_level = max(p.store_level for p in game_state.players)

                # If this player is not the highest level, apply catch-up discount
                if self.store_level < highest_level:
                    if vendor.name == "Daily Essentials Co.":
                        # 10% additional discount: 90% → 80% market price
                        final_price_package *= (0.80 / 0.90)
                    elif vendor.name == "Instant Goods Ltd.":
                        # 3% additional discount: 98% → 95% market price
                        final_price_package *= (0.95 / 0.98)

            # Calculate price per individual item (for packages, this divides by items_per_package)
            final_price_per_unit = final_price_package / items_per_package

        # Total cost is for buying 'quantity' packages
        total_cost = final_price_per_unit * items_per_package * quantity

        if self.cash < total_cost:
            return False

        self.cash -= total_cost

        # Calculate total individual items to add to inventory
        total_items = quantity * items_per_package

        # Check if vendor has lead time
        if vendor.lead_time > 0 and game_state is not None:
            # Calculate effective lead time with any reductions from upgrades
            lead_time_reduction = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "lead_time_reduction")
            effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))

            # Add to pending deliveries instead of inventory (or immediate if lead time reduced to 0)
            if effective_lead_time > 0:
                delivery_day = game_state.day + effective_lead_time
                # Store as individual items, not packages
                self.pending_deliveries.append((actual_item_name, total_items, final_price_per_unit, delivery_day))
            else:
                # Lead time reduced to 0, deliver immediately
                current_inventory = self.inventory.get(actual_item_name, 0)
                current_cost = self.item_costs.get(actual_item_name, 0)

                # Weighted average: (old_qty * old_cost + new_qty * new_cost) / total_qty
                new_total_qty = current_inventory + total_items
                if new_total_qty > 0:
                    weighted_cost = ((current_inventory * current_cost) + (total_items * final_price_per_unit)) / new_total_qty
                    self.item_costs[actual_item_name] = weighted_cost

                # Track if this is the first time stocking this item today
                if current_inventory == 0 and total_items > 0:
                    self.items_stocked_today.add(actual_item_name)

                self.inventory[actual_item_name] = new_total_qty
        else:
            # Immediate delivery - update inventory and weighted average cost
            current_inventory = self.inventory.get(actual_item_name, 0)
            current_cost = self.item_costs.get(actual_item_name, 0)

            # Weighted average: (old_qty * old_cost + new_qty * new_cost) / total_qty
            new_total_qty = current_inventory + total_items
            if new_total_qty > 0:
                weighted_cost = ((current_inventory * current_cost) + (total_items * final_price_per_unit)) / new_total_qty
                self.item_costs[actual_item_name] = weighted_cost

            # Track if this is the first time stocking this item today
            if current_inventory == 0 and total_items > 0:
                self.items_stocked_today.add(actual_item_name)

            self.inventory[actual_item_name] = new_total_qty

        # Track purchase for max-per-player limits (track by package name)
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
    customer_type: str = "medium"  # "low", "medium", "high", "uncapped", or special types
    budget: float = 0.0
    day: int = 0  # Current game day for budget scaling
    specializations: List[str] = field(default_factory=list)  # 2 rolled categories for specialization

    def __post_init__(self):
        """Set budget based on customer type if not already set."""
        if self.budget == 0.0:
            if self.customer_type == "low":
                self.budget = 20.0
            elif self.customer_type == "medium":
                self.budget = 50.0
            elif self.customer_type == "high":
                # High spender budget increases by $100 every 30 days
                base_budget = 100.0
                additional_budget = (self.day // 30) * 100.0
                self.budget = base_budget + additional_budget
            elif self.customer_type == "uncapped":
                self.budget = 10000.0  # Effectively unlimited for 1 expensive item
            # Special customer types
            elif self.customer_type == "hoarder":
                self.budget = 500.0
            elif self.customer_type == "shoplifter":
                self.budget = 0.0  # Shoplifters steal, don't buy
            elif self.customer_type == "party_prep_mom":
                self.budget = 200.0
            elif self.customer_type == "gamer":
                self.budget = 600.0
            elif self.customer_type == "christmas_dad":
                self.budget = 1400.0  # Enough for Gaming Console + 4K TV
            elif self.customer_type == "lottery_winner":
                self.budget = 3000.0
            elif self.customer_type == "youtuber":
                self.budget = 10000.0

    def roll_specializations(self, available_items: List[Item], item_demand: Dict[str, float] = None) -> None:
        """
        Roll 2 different categories for customer specialization.
        Only considers categories that exist in the current market.
        Categories are weighted by total demand of items in each category.

        If there's only 1 category in the market, rolls that category twice.
        Otherwise rolls 2 different categories.
        """
        if item_demand is None:
            item_demand = {}

        # Get unique categories that have items in the market
        market_categories = set(item.category for item in available_items)

        if not market_categories:
            # No items available, default to all categories
            market_categories = set(PRODUCT_CATEGORIES.keys())

        # Calculate total demand for each market category
        category_demands = {}
        for category in market_categories:
            category_items = [item for item in available_items if item.category == category]
            total_demand = sum(item_demand.get(item.name, 1.0) for item in category_items)
            if total_demand > 0:
                category_demands[category] = total_demand

        # If no categories have demand, distribute evenly
        if not category_demands:
            category_demands = {category: 1.0 for category in market_categories}

        categories = list(category_demands.keys())
        weights = [category_demands[cat] for cat in categories]

        # Roll 2 categories
        if len(categories) == 1:
            # Only 1 category available, roll it twice
            self.specializations = [categories[0], categories[0]]
        else:
            # Roll 2 different categories using weighted selection without replacement
            # Use manual sampling without replacement
            selected = []
            remaining_categories = categories.copy()
            remaining_weights = weights.copy()

            for _ in range(2):
                chosen = random.choices(remaining_categories, weights=remaining_weights, k=1)[0]
                selected.append(chosen)
                # Remove the chosen category so we don't pick it again
                idx = remaining_categories.index(chosen)
                remaining_categories.pop(idx)
                remaining_weights.pop(idx)

            self.specializations = selected

    def generate_daily_needs(self, available_items: List[Item], market_prices: Dict[str, float] = None, item_demand: Dict[str, float] = None) -> List[CustomerNeed]:
        """
        Generate a random set of item needs for the day based on budget.
        Uses item demand as weights for selection - higher demand items are more likely to be chosen.

        For uncapped customers: only buy 1 expensive item (base_price >= 100).
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

        # Special customer types have unique need generation
        if self.customer_type == "hoarder":
            # Hoarder: buys 20-30 units of ONE random item type (not affected by demand)
            if available_items:
                selected_item = random.choice(available_items)
                # Calculate how many they can afford
                item_price = market_prices.get(selected_item.name, selected_item.base_price) if market_prices else selected_item.base_price
                max_affordable = int(self.budget / item_price) if item_price > 0 else 0
                quantity = min(random.randint(20, 30), max_affordable)
                if quantity > 0:
                    needs.append(CustomerNeed(item_name=selected_item.name, quantity=quantity))
            return needs

        if self.customer_type == "shoplifter":
            # Shoplifter: doesn't generate needs normally, stealing is handled in selection logic
            return []

        if self.customer_type == "party_prep_mom":
            # Party Prep Mom: buys 20-30 items with importance 3
            importance_3_items = [item for item in available_items if item.importance == 3]
            if importance_3_items:
                remaining_budget = self.budget
                target_items = random.randint(20, 30)
                total_items = 0

                while total_items < target_items and remaining_budget > 0 and importance_3_items:
                    affordable_items = [
                        item for item in importance_3_items
                        if (market_prices.get(item.name, item.base_price) if market_prices else item.base_price) <= remaining_budget
                    ]
                    if not affordable_items:
                        break

                    selected_item = random.choice(affordable_items)
                    item_price = market_prices.get(selected_item.name, selected_item.base_price) if market_prices else selected_item.base_price
                    needs.append(CustomerNeed(item_name=selected_item.name, quantity=1))
                    remaining_budget -= item_price
                    total_items += 1
            return needs

        if self.customer_type == "gamer":
            # Gamer: buys 1-3 gaming-related items from Gaming category
            available_gamer_items = [item for item in available_items if item.category == "Gaming"]
            if available_gamer_items:
                remaining_budget = self.budget
                target_items = random.randint(1, 3)
                selected_items = []

                for _ in range(target_items):
                    affordable_items = [
                        item for item in available_gamer_items
                        if item not in selected_items  # Don't buy duplicates
                        and (market_prices.get(item.name, item.base_price) if market_prices else item.base_price) <= remaining_budget
                    ]
                    if not affordable_items:
                        break

                    selected_item = random.choice(affordable_items)
                    item_price = market_prices.get(selected_item.name, selected_item.base_price) if market_prices else selected_item.base_price
                    needs.append(CustomerNeed(item_name=selected_item.name, quantity=1))
                    remaining_budget -= item_price
                    selected_items.append(selected_item)
            return needs

        if self.customer_type == "christmas_dad":
            # Christmas Dad: buys exactly Gaming Console and 4K TV
            target_items = ["Gaming Console", "4K TV"]
            for item_name in target_items:
                needs.append(CustomerNeed(item_name=item_name, quantity=1))
            return needs

        if self.customer_type == "lottery_winner":
            # Lottery Winner: buys up to 10 importance 1 (luxury) items
            luxury_items = [item for item in available_items if item.importance == 1]
            if luxury_items:
                remaining_budget = self.budget
                target_items = 10
                total_items = 0
                selected_items = []

                while total_items < target_items and remaining_budget > 0 and luxury_items:
                    affordable_items = [
                        item for item in luxury_items
                        if item not in selected_items  # Don't buy duplicates
                        and (market_prices.get(item.name, item.base_price) if market_prices else item.base_price) <= remaining_budget
                    ]
                    if not affordable_items:
                        break

                    selected_item = random.choice(affordable_items)
                    item_price = market_prices.get(selected_item.name, selected_item.base_price) if market_prices else selected_item.base_price
                    needs.append(CustomerNeed(item_name=selected_item.name, quantity=1))
                    remaining_budget -= item_price
                    total_items += 1
                    selected_items.append(selected_item)
            return needs

        if self.customer_type == "youtuber":
            # Youtuber: wants to buy everything, actual purchase handled in selection logic
            # Generate needs for all available items
            for item in available_items:
                needs.append(CustomerNeed(item_name=item.name, quantity=100))  # Request large quantity
            return needs

        # Regular customers (low, medium, high)
        remaining_budget = self.budget

        # Set guaranteed item count based on customer type (hard cap)
        if self.customer_type == "low":
            max_items = 5
        elif self.customer_type == "medium":
            max_items = 15
        elif self.customer_type == "high":
            max_items = 30
        else:
            max_items = 5  # Default fallback

        # Keep buying items until we hit the item limit or run out of budget
        total_items = 0

        # Filter to specialization categories if customer has rolled specializations
        items_to_shop = available_items
        if self.specializations:
            items_to_shop = [item for item in available_items if item.category in self.specializations]

        while total_items < max_items and remaining_budget > 0 and items_to_shop:
            # Filter to only affordable items with valid pricing
            affordable_items = [
                item for item in items_to_shop
                if (market_prices.get(item.name, item.base_price) if market_prices else item.base_price) > 0
                and (market_prices.get(item.name, item.base_price) if market_prices else item.base_price) <= remaining_budget
            ]

            # If no affordable items left, stop shopping
            if not affordable_items:
                break

            # Select one affordable item based on demand
            selected_item = weighted_random_sample(affordable_items, item_demand, 1)[0]

            # Get current market price for this item
            item_price = market_prices.get(selected_item.name, selected_item.base_price) if market_prices else selected_item.base_price

            # Buy 1 unit of this item
            needs.append(CustomerNeed(item_name=selected_item.name, quantity=1))
            remaining_budget -= item_price
            total_items += 1

        return needs

    def choose_supplier(
        self,
        players: List[Player],
        item_name: str,
        quantity: int,
        market_prices: Dict[str, float],
        customer_visits_per_store: Dict[str, int] = None
    ) -> Optional[Player]:
        """
        Decide which player to buy from for a given item and quantity.

        Chooses the player with the lowest price who has at least some stock.
        Customers will only buy if the price is within 15% of market price.

        NEW: Considers customer capacity - prefers stores that aren't overcrowded.

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

        # If no capacity tracking, use original behavior
        if customer_visits_per_store is None:
            return random.choice(best_players)

        # Prefer stores that are under capacity
        under_capacity = []
        over_capacity = []

        for player in best_players:
            capacity = get_player_customer_capacity(player)
            current_visits = customer_visits_per_store.get(player.name, 0)

            if current_visits < capacity:
                under_capacity.append(player)
            else:
                over_capacity.append((player, current_visits))

        # Prefer stores under capacity
        if under_capacity:
            return random.choice(under_capacity)

        # If all are over capacity, choose the least crowded
        if over_capacity:
            # Sort by visit count (ascending) and pick the least crowded
            over_capacity.sort(key=lambda x: x[1])
            least_crowded = [p for p, visits in over_capacity if visits == over_capacity[0][1]]
            return random.choice(least_crowded)

        # Fallback (shouldn't happen)
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

    def choose_supplier_by_reputation(
        self,
        players: List[Player],
        needs: List[CustomerNeed],
        market_prices: Dict[str, float],
        items_by_name: Dict[str, Item],
        all_available_items: List[Item]
    ) -> Optional[Player]:
        """
        Choose a supplier based on reputation, discount scores, specialty score, and fulfillment.

        Formula:
        - reputation_multiplier = 10 ** (reputation / 100)
        - For each item in needs, calculate discount % weighted by importance (only for stocked items)
        - discount_score = sum((market_price - player_price) / market_price * 100 * importance)
        - item_stability = sum of (proximity_score + consistency_bonus) * importance for all stocked items
          * proximity_score: 10 if within 5% of market, -1 per 1% beyond 5%
          * consistency_bonus: +2 if price change <= 5% from previous
        - specialty_multiplier based on category item counts (additive bonuses)
        - fulfillment_multiplier based on average % customer needs fulfilled (from past performance):
          * <10%: ×0.1
          * 10-20%: ×0.5
          * 20-50%: ×0.9
          * 50-70%: ×1.0
          * 71-89%: ×1.1
          * 90-99%: ×1.4
          * 100%: ×2.0
        - final_score = (discount_score + item_stability) * reputation_multiplier * specialty_multiplier * fulfillment_multiplier

        Returns the player with the highest score who has capacity to serve customers.
        Only considers players with stock and acceptable prices.
        """
        if not players or not needs:
            return None

        player_scores = []
        max_acceptable_price_multiplier = 1.15  # 15% above market price
        total_catalog_items = len(all_available_items)

        for player in players:
            # Calculate discount score for this player
            discount_score = 0.0
            has_any_stock = False

            for need in needs:
                item_name = need.item_name
                market_price = market_prices.get(item_name, 0)

                # Skip if no market price
                if market_price <= 0:
                    continue

                # Check if player has stock and price
                player_stock = player.inventory.get(item_name, 0)
                if player_stock > 0 and item_name in player.prices:
                    player_price = player.prices[item_name]
                    max_acceptable_price = market_price * max_acceptable_price_multiplier

                    # Only consider if price is acceptable
                    if player_price <= max_acceptable_price:
                        has_any_stock = True

                        # Calculate discount percentage
                        if player_price < market_price:
                            discount_pct = ((market_price - player_price) / market_price) * 100
                        else:
                            discount_pct = 0  # No discount if at or above market

                        # Get item importance
                        item = items_by_name.get(item_name)
                        importance = item.importance if item else 2

                        # Add weighted discount to score
                        discount_score += discount_pct * importance

            # Skip players with no relevant stock
            if not has_any_stock:
                continue

            # Calculate specialty score (category-based bonuses for item variety)
            specialty_multiplier_effective, _, _ = calculate_specialty_score(player, items_by_name)

            # Calculate fulfillment multiplier based on historical performance
            fulfillment_pct = player.average_fulfillment_pct
            if fulfillment_pct >= 100:
                fulfillment_multiplier = 2.0
            elif fulfillment_pct >= 90:
                fulfillment_multiplier = 1.4
            elif fulfillment_pct > 70:
                fulfillment_multiplier = 1.1
            elif fulfillment_pct >= 50:
                fulfillment_multiplier = 1.0
            elif fulfillment_pct >= 20:
                fulfillment_multiplier = 0.9
            elif fulfillment_pct >= 10:
                fulfillment_multiplier = 0.5
            else:
                fulfillment_multiplier = 0.1

            # Calculate reputation multiplier
            reputation = player.reputation
            reputation_multiplier = 10 ** (reputation / 100)

            # Calculate item stability score
            item_stability = calculate_item_stability(player, market_prices, items_by_name)

            # Calculate marketing effect (adds to both discount and stability)
            marketing_effect = calculate_marketing_effect(player, market_prices)

            # Calculate final score (marketing effect boosts both components)
            final_score = (discount_score + marketing_effect + item_stability + marketing_effect) * reputation_multiplier * specialty_multiplier_effective * fulfillment_multiplier

            player_scores.append((player, final_score))

        if not player_scores:
            return None

        # Sort by score descending (highest first)
        player_scores.sort(key=lambda x: x[1], reverse=True)

        # Return the player with the highest score
        return player_scores[0][0]

    def choose_supplier_for_special_customer(
        self,
        players: List[Player],
        needs: List[CustomerNeed],
        market_prices: Dict[str, float],
        items_by_name: Dict[str, Item],
        all_available_items: List[Item]
    ) -> Optional[Player]:
        """
        Choose supplier for special customers based on their unique selection criteria.
        Different logic for each special customer type.
        """
        if self.customer_type == "hoarder":
            # Hoarder: picks player with highest total stock
            player_stock_counts = []
            for player in players:
                total_stock = sum(player.inventory.values())
                if total_stock > 0:
                    player_stock_counts.append((player, total_stock))

            if not player_stock_counts:
                return None

            # Sort by total stock (highest first)
            player_stock_counts.sort(key=lambda x: x[1], reverse=True)
            return player_stock_counts[0][0]

        elif self.customer_type == "shoplifter":
            # Shoplifter: targets highest reputation player
            # If tied, check stock amount
            max_reputation = max((p.reputation for p in players), default=0)
            high_rep_players = [p for p in players if p.reputation == max_reputation]

            if not high_rep_players:
                return None

            # If multiple players with max reputation, pick one with most stock
            if len(high_rep_players) > 1:
                player_stock = [(p, sum(p.inventory.values())) for p in high_rep_players]
                player_stock.sort(key=lambda x: x[1], reverse=True)
                return player_stock[0][0]
            else:
                return high_rep_players[0]

        elif self.customer_type == "party_prep_mom":
            # Party Prep Mom: picks based on global availability of importance 3 items and lowest avg price
            player_scores = []
            for player in players:
                importance_3_stock = sum(
                    player.inventory.get(item.name, 0)
                    for item in all_available_items
                    if item.importance == 3
                )

                if importance_3_stock == 0:
                    continue

                # Calculate average price for importance 3 items
                total_price = 0
                count = 0
                for item in all_available_items:
                    if item.importance == 3 and player.inventory.get(item.name, 0) > 0 and item.name in player.prices:
                        total_price += player.prices[item.name]
                        count += 1

                avg_price = total_price / count if count > 0 else float('inf')
                player_scores.append((player, importance_3_stock, avg_price))

            if not player_scores:
                return None

            # Sort by stock (descending), then by price (ascending)
            player_scores.sort(key=lambda x: (-x[1], x[2]))
            return player_scores[0][0]

        elif self.customer_type == "gamer":
            # Gamer: picks store with most types of gaming items, ties broken by lowest price
            gaming_items = [item for item in all_available_items if item.category == "Gaming"]
            player_scores = []

            for player in players:
                available_types = sum(
                    1 for item in gaming_items
                    if player.inventory.get(item.name, 0) > 0 and item.name in player.prices
                )

                if available_types == 0:
                    continue

                # Calculate average price for available gaming items
                total_price = 0
                count = 0
                for item in gaming_items:
                    if player.inventory.get(item.name, 0) > 0 and item.name in player.prices:
                        total_price += player.prices[item.name]
                        count += 1

                avg_price = total_price / count if count > 0 else float('inf')
                player_scores.append((player, available_types, avg_price))

            if not player_scores:
                return None

            # Sort by number of types (descending), then by average price (ascending)
            player_scores.sort(key=lambda x: (-x[1], x[2]))
            return player_scores[0][0]

        elif self.customer_type == "christmas_dad":
            # Christmas Dad: checks lowest price and reputation for Gaming Console and 4K TV
            target_items = ["Gaming Console", "4K TV"]
            player_scores = []

            for player in players:
                # Check if player has both items
                has_both = all(
                    player.inventory.get(item_name, 0) > 0 and item_name in player.prices
                    for item_name in target_items
                )

                if not has_both:
                    continue

                # Calculate total price for both items
                total_price = sum(player.prices[item_name] for item_name in target_items)
                player_scores.append((player, total_price, player.reputation))

            if not player_scores:
                return None

            # Sort by total price (ascending), then by reputation (descending)
            player_scores.sort(key=lambda x: (x[1], -x[2]))
            return player_scores[0][0]

        elif self.customer_type == "lottery_winner":
            # Lottery Winner: picks store with most available expensive items (>$100)
            player_scores = []

            for player in players:
                expensive_count = sum(
                    1 for item in all_available_items
                    if item.base_price > 100
                    and player.inventory.get(item.name, 0) > 0
                    and item.name in player.prices
                )

                if expensive_count > 0:
                    player_scores.append((player, expensive_count))

            if not player_scores:
                return None

            # Sort by count (descending), random tiebreaker
            random.shuffle(player_scores)
            player_scores.sort(key=lambda x: x[1], reverse=True)
            return player_scores[0][0]

        elif self.customer_type == "youtuber":
            # Youtuber: picks player with lowest cash (near bankruptcy, <$1000)
            low_cash_players = [p for p in players if p.cash < 1000]

            if not low_cash_players:
                return None

            # Pick the one with lowest cash
            low_cash_players.sort(key=lambda p: p.cash)
            return low_cash_players[0]

        else:
            # Default to reputation-based selection
            return self.choose_supplier_by_reputation(players, needs, market_prices, items_by_name, all_available_items)


# -------------------------------------------------------------------
# Game / simulation engine
# -------------------------------------------------------------------

@dataclass
class GameConfig:
    """Configuration for the economic simulation."""
    starting_cash: float = 10000.0
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

    @property
    def items_by_name(self) -> Dict[str, Item]:
        """
        Returns a dictionary mapping item names to Item objects.
        """
        return {item.name: item for item in self.items}


# -------------------------------------------------------------------
# Initialization helpers
# -------------------------------------------------------------------

def create_default_items() -> List[Item]:
    """
    Create the starting items for the simulation.
    Returns first 60 items from product catalog (all $20 or below with varied categories).
    """
    # Start with first 60 items - includes Food & Groceries, Fresh Produce,
    # Household Essentials, Personal Care items (all $20 or below)
    return [PRODUCT_CATALOG[i] for i in range(60)]


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

    # Vendor 1: Bulk Goods Co. - 85% of market price, items $30 or less, 1 day lead time, big bulk only (20 size)
    vendors.append(Vendor(
        name="Bulk Goods Co.",
        pricing_multiplier=0.85,
        selection_type="price_range",
        selection_params=0,
        price_max=30.0,
        lead_time=1
    ))

    # Vendor 2: Instant Goods Ltd. - 98% of market price, all items under $40, instant delivery (no lead time)
    vendors.append(Vendor(
        name="Instant Goods Ltd.",
        pricing_multiplier=0.98,
        selection_type="price_threshold",
        selection_params=40.0,  # $40 threshold
        lead_time=0
    ))

    # Vendor 3: Universal Supply Corp. - 102% of market price, all items available, instant delivery (no lead time)
    vendors.append(Vendor(
        name="Universal Supply Corp.",
        pricing_multiplier=1.02,
        selection_type="all",
        selection_params=0,  # No limit
        lead_time=0
    ))

    # Vendor 4: Bulk Master Co. - Volume-based pricing, items under $100, 1 day lead time
    # Base: 110% market, scales down with volume
    # Tiers (sorted descending): 10000->70%, 5000->75%, 2500->80%, 1000->85%, 500->90%, 300->95%, 100->100%
    vendors.append(Vendor(
        name="Bulk Master Co.",
        pricing_multiplier=1.10,  # Base pricing
        selection_type="price_threshold",
        selection_params=100.0,  # Items under $100
        lead_time=1,
        volume_pricing_tiers=[
            (10000, 0.70),
            (5000, 0.75),
            (2500, 0.80),
            (1000, 0.85),
            (500, 0.90),
            (300, 0.95),
            (100, 1.00)
        ]
    ))

    # Vendor 5: Stock Masters Ltd - 80% market price, requires 100 reputation, level 10, max 500 per item, 2 day lead time, all items
    vendors.append(Vendor(
        name="Stock Masters Ltd",
        pricing_multiplier=0.80,
        selection_type="all",
        selection_params=0,
        max_per_item_per_player=500,
        lead_time=2,
        required_reputation=100.0,
        required_level=10
    ))

    # Vendor 6: Luxury House Co. - Only Gaming and Luxury categories
    # Base: 98% market, 90% at 50+ items
    vendors.append(Vendor(
        name="Luxury House Co.",
        pricing_multiplier=0.98,
        selection_type="category",
        selection_params=0,
        allowed_categories=["Gaming", "Luxury"],
        lead_time=1,
        volume_pricing_tiers=[
            (50, 0.90)
        ]
    ))

    # Vendor 7: Daily Essentials Co. - Only Food & Groceries and Fresh Produce categories
    # Base: 90% market, 80% at 1000+ items
    vendors.append(Vendor(
        name="Daily Essentials Co.",
        pricing_multiplier=0.90,
        selection_type="category",
        selection_params=0,
        allowed_categories=["Food & Groceries", "Fresh Produce"],
        lead_time=1,
        volume_pricing_tiers=[
            (1000, 0.80)
        ]
    ))

    # Vendor 8: Restocking Essentials Co. - Everything EXCEPT Food & Groceries and Fresh Produce
    # Base: 90% market, 80% at 1000+ items (reverse of vendor 7)
    vendors.append(Vendor(
        name="Restocking Essentials Co.",
        pricing_multiplier=0.90,
        selection_type="category",
        selection_params=0,
        allowed_categories=[
            "Household Essentials", "Personal Care", "Health & Pharmacy", "Baby Products",
            "Supplements", "Pet Supplies", "Kitchen & Dining", "Office Supplies",
            "Electronics", "Appliances", "Sports & Outdoor", "Home Decor",
            "Automotive", "Gaming", "Toys & Games", "Luxury"
        ],
        lead_time=1,
        volume_pricing_tiers=[
            (1000, 0.80)
        ]
    ))

    return vendors


def _add_item_to_vendor(vendor: Vendor, item: Item, market_price: float) -> None:
    """
    Add an item to a vendor's inventory, using packaging if the item size < 5.

    For items with size < 5:
    - Bulk Master Co. and Bulk Goods Co.: Only add bulk package (20 size)
    - All other vendors: Add standard package (5 size)

    For items with size >= 5:
    - Add as-is without packaging
    """
    # For items >= 5 size, no packaging
    if item.size >= 5.0:
        vendor.items[item.name] = market_price * vendor.pricing_multiplier
        return

    # For items < 5 size, use packaging
    # Bulk package (20 size) - only Bulk Master Co. and Bulk Goods Co.
    if vendor.name in ["Bulk Master Co.", "Bulk Goods Co."]:
        bulk_package_name, bulk_quantity, _ = get_package_info(item, "bulk")
        bulk_package_price = market_price * bulk_quantity
        vendor.items[bulk_package_name] = bulk_package_price * vendor.pricing_multiplier
    else:
        # Standard package (5 size) - all other vendors
        package_name, quantity, _ = get_package_info(item, "standard")
        package_price = market_price * quantity  # Total price for the package
        vendor.items[package_name] = package_price * vendor.pricing_multiplier


def refresh_vendor_inventory(vendors: List[Vendor], items: List[Item], market_prices: Dict[str, float]) -> None:
    """
    Refresh vendor inventory based on their selection type and current market prices.

    This should be called at the start of each day.

    Items with size < 5 will be sold as packages:
    - Standard packages (5 size): Available at all vendors
    - Bulk packages (20 size): Only available at Bulk Master Co.
    """
    for vendor in vendors:
        vendor.items.clear()

        # Filter items by allowed categories if specified
        available_items = items
        if vendor.allowed_categories is not None:
            available_items = [item for item in items if item.category in vendor.allowed_categories]

        if vendor.selection_type == "random_daily":
            # Select N random items
            num_items = int(vendor.selection_params)
            if num_items > 0 and available_items:
                selected_items = random.sample(available_items, min(num_items, len(available_items)))
                for item in selected_items:
                    market_price = market_prices.get(item.name, item.base_price)
                    _add_item_to_vendor(vendor, item, market_price)

        elif vendor.selection_type == "price_threshold":
            # Select all items where market price is at or under threshold
            price_threshold = vendor.selection_params
            for item in available_items:
                market_price = market_prices.get(item.name, item.base_price)
                if market_price <= price_threshold:
                    _add_item_to_vendor(vendor, item, market_price)

        elif vendor.selection_type == "price_range":
            # Select items within a price range (min and/or max)
            for item in available_items:
                market_price = market_prices.get(item.name, item.base_price)
                # Check if price is within range
                if vendor.price_min is not None and market_price < vendor.price_min:
                    continue
                if vendor.price_max is not None and market_price > vendor.price_max:
                    continue
                _add_item_to_vendor(vendor, item, market_price)

        elif vendor.selection_type == "all":
            # Include all items
            for item in available_items:
                market_price = market_prices.get(item.name, item.base_price)
                _add_item_to_vendor(vendor, item, market_price)

        elif vendor.selection_type == "category":
            # Select items from allowed categories only (already filtered above)
            for item in available_items:
                market_price = market_prices.get(item.name, item.base_price)
                _add_item_to_vendor(vendor, item, market_price)


def vendor_would_sell_item(vendor: Vendor, item: Item, market_price: float) -> bool:
    """
    Check if a vendor would sell an item based on their selection criteria.
    This is used for recurring orders and auto-restock to determine availability
    independent of current inventory state.
    """
    # Check category restrictions first
    if vendor.allowed_categories is not None:
        if item.category not in vendor.allowed_categories:
            return False

    # Check selection type criteria
    if vendor.selection_type == "random_daily":
        # Random vendors might have it, but it's unpredictable
        return True
    elif vendor.selection_type == "price_threshold":
        return market_price <= vendor.selection_params
    elif vendor.selection_type == "price_range":
        if vendor.price_min is not None and market_price < vendor.price_min:
            return False
        if vendor.price_max is not None and market_price > vendor.price_max:
            return False
        return True
    elif vendor.selection_type == "all":
        return True
    elif vendor.selection_type == "category":
        # Already checked category above
        return True

    return False


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

    Then, randomly changes demand for 1/4 of items based on importance:
    - Importance 3 (essentials): ±0.2 (more stable)
    - Importance 2 (medium): ±0.4 (baseline)
    - Importance 1 (luxury): ±0.6 (more volatile)
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

    # Step 2: Apply random changes to 5 items
    num_items_to_update = min(5, len(game_state.items))  # Flat 5 items (or all if less than 5)

    # Randomly select items to update (may include items already reset)
    items_to_update = random.sample(game_state.items, min(num_items_to_update, len(game_state.items)))

    for item in items_to_update:
        # Generate random change based on importance
        # Importance 3 (essentials): -0.2 to +0.2 (more stable)
        # Importance 2 (medium): -0.4 to +0.4 (baseline)
        # Importance 1 (luxury): -0.6 to +0.6 (more volatile)
        if item.importance == 3:  # Essentials - more stable
            change = random.uniform(-0.2, 0.2)
        elif item.importance == 1:  # Luxury - more volatile
            change = random.uniform(-0.6, 0.6)
        else:  # importance == 2 - baseline
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
        # XP gain upgrades
        Upgrade(name="Business Course", cost=2000, effect_type="xp_gain", effect_value=10),
        Upgrade(name="MBA Program", cost=5000, effect_type="xp_gain", effect_value=25),

        # Wage reduction upgrade
        Upgrade(name="Employee Benefits Package", cost=20000, effect_type="wage_reduction", effect_value=100),

        # Lead time reduction upgrade
        Upgrade(name="Distribution Network", cost=150000, effect_type="lead_time_reduction", effect_value=1),
    ]

    # Add vendor discount upgrades for each vendor (30-day duration, tier-based pricing)
    # Pricing tiers based on vendor value:
    vendor_pricing = {
        "Bulk Goods Co.": (9000, 18000),  # Good pricing, high minimum, limited price ceiling
        "Instant Goods Ltd.": (11000, 22000),  # Fast delivery for budget items
        "Universal Supply Corp.": (18000, 36000),  # Everything available instantly
        "Bulk Master Co.": (30000, 60000),  # Extreme volume value → very high cost
        "Stock Masters Ltd": (28000, 56000),  # Premium access, strong discounts
        "Luxury House Co.": (14000, 28000),  # Luxury and gaming focus with discounts
        "Daily Essentials Co.": (10000, 20000),  # Essentials specialist
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

def apply_daily_price_fluctuation(market_prices: Dict[str, float], items: List[Item]) -> List[tuple]:
    """
    Apply daily price fluctuation to 1-2 random items.
    Fluctuation ranges based on item importance:
    - Importance 3 (essentials): 3-6% (more stable)
    - Importance 2 (medium): 5-10% (baseline)
    - Importance 1 (luxury): 7-14% (more volatile)

    Returns list of (item_name, old_price, new_price, change_percent) tuples for changed items.
    """
    if not items:
        return []

    price_changes = []

    # Choose 1-2 items to fluctuate
    num_items_to_fluctuate = random.randint(1, min(2, len(items)))
    items_to_fluctuate = random.sample(items, num_items_to_fluctuate)

    for item in items_to_fluctuate:
        # Fluctuation range based on importance
        if item.importance == 3:  # Essentials - more stable
            fluctuation = random.uniform(0.03, 0.06)
        elif item.importance == 1:  # Luxury - more volatile
            fluctuation = random.uniform(0.07, 0.14)
        else:  # importance == 2 - baseline
            fluctuation = random.uniform(0.05, 0.10)

        direction = random.choice([-1, 1])

        old_price = market_prices[item.name]
        new_price = old_price * (1 + direction * fluctuation)

        # Keep prices reasonable (not below base cost, not above 2x base price)
        new_price = max(item.base_cost * 1.2, min(new_price, item.base_price * 2.0))

        market_prices[item.name] = new_price

        # Calculate actual change percent
        change_percent = ((new_price - old_price) / old_price) * 100
        price_changes.append((item.name, old_price, new_price, change_percent))

    return price_changes


# -------------------------------------------------------------------
# Buy order execution
# -------------------------------------------------------------------

def execute_buy_orders(player: Player, game_state: GameState) -> Tuple[Dict[str, int], float]:
    """
    Execute a player's buy orders, purchasing from cheapest to most expensive items.

    For vendors with random daily selection (vendors 1 & 2), fallback to cheapest
    available vendor if the selected vendor doesn't have the item.

    For vendors with minimum purchase requirements:
    - VIP Goods Co. (high-end items $200+) falls back to Universal Supply Corp.
    - Other vendors fall back to Budget Goods Ltd.

    Respects max inventory capacity. Buy orders have no per-day limit,
    but purchases stop when inventory would exceed capacity or money runs out.

    NEW: Manual buy orders only execute if total warehouse space required >= 1000.
    If below 1000, the entire manual buy order is cancelled for the day.

    Returns a tuple of (items purchased: {item_name: quantity_bought}, inventory_size_used: float)
    """
    purchases = {}

    # Calculate total warehouse space required for all manual buy orders
    total_space_required = 0.0
    for item_name, vendor_list in player.buy_orders.items():
        item = game_state.items_by_name.get(item_name)
        if item:
            for quantity, vendor_name in vendor_list:
                total_space_required += quantity * item.size

    # Check if total space required meets minimum threshold
    if total_space_required < 1000:
        # Cancel entire manual buy order
        return purchases, 0.0

    total_size_bought = 0.0
    max_inventory = player.get_max_inventory()
    current_inventory_size = player.get_inventory_size_used(game_state.items_by_name)

    # Get all non-zero buy orders (now supporting multiple vendors per item)
    active_orders = []
    for item_name, vendor_list in player.buy_orders.items():
        # Iterate through all vendors for this item (up to 3)
        for quantity, vendor_name in vendor_list:
            if quantity > 0:
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

    # Execute orders in order, respecting inventory capacity
    for item_name, quantity, vendor, price in active_orders:
        if current_inventory_size + total_size_bought >= max_inventory:
            break  # Reached inventory capacity

        # Get item size to calculate how much space this order needs
        item = game_state.items_by_name.get(item_name)
        if not item:
            continue
        item_size = item.size

        # Limit quantity by remaining warehouse capacity (based on size)
        remaining_capacity_size = max_inventory - current_inventory_size - total_size_bought
        max_quantity_by_size = int(remaining_capacity_size / item_size) if item_size > 0 else quantity
        actual_quantity = min(quantity, max_quantity_by_size)

        # Get market price for production line check
        market_price = game_state.market_prices.get(item_name, 0)

        success = player.purchase_from_vendor(vendor, item_name, actual_quantity, market_price, game_state)
        if success:
            purchases[item_name] = actual_quantity
            total_size_bought += actual_quantity * item_size
        else:
            # Try to buy as many as possible with remaining cash
            # Recalculate price if production line owned
            actual_price = player.get_production_line_price(item_name, market_price) or price
            max_affordable = int(player.cash / actual_price)
            if max_affordable > 0:
                affordable_quantity = min(max_affordable, max_quantity_by_size)
                partial_success = player.purchase_from_vendor(vendor, item_name, affordable_quantity, market_price, game_state)
                if partial_success:
                    purchases[item_name] = affordable_quantity
                    total_size_bought += affordable_quantity * item_size

    return purchases, total_size_bought


def execute_recurring_buy_orders(player: Player, game_state: GameState) -> Tuple[Dict[str, int], float]:
    """
    Execute recurring buy orders that are due (based on interval_days).
    Respects inventory capacity - stops buying when player reaches max inventory.

    Returns a tuple of (items purchased: {item_name: quantity_bought}, inventory_size_used: float)
    """
    purchases = {}
    total_size_used = 0.0
    current_day = game_state.day

    # Get current inventory size and max capacity
    current_inventory_size = player.get_inventory_size_used(game_state.items_by_name)
    max_inventory = player.get_max_inventory()

    for order in player.recurring_buy_orders:
        # Check if this order is due (current_day - last_executed >= interval)
        days_since_last = current_day - order.last_executed_day

        if days_since_last >= order.interval_days:
            # Find the vendor
            vendor = game_state.get_vendor(order.vendor_name)
            if not vendor:
                continue

            # Get item object first
            item = game_state.items_by_name.get(order.item_name)
            if not item:
                continue

            # Determine the package name to use when querying the vendor
            # For small items (size < 5, excluding luxury), vendors sell packages
            purchase_item_name = order.item_name
            packages_to_buy = order.quantity
            items_per_package = 1

            if item.size < 5.0 and item.category != "Luxury":
                # Item is packaged - determine package type based on vendor
                package_type = "bulk" if vendor.name in ["Bulk Master Co.", "Bulk Goods Co."] else "standard"
                package_name, items_per_package, _ = get_package_info(item, package_type)
                purchase_item_name = package_name

                # Convert quantity from items to packages (round up)
                packages_to_buy = (order.quantity + items_per_package - 1) // items_per_package

            # Get the price from this vendor using the package name
            price = vendor.get_price(purchase_item_name, packages_to_buy)
            if price is None:
                # Vendor doesn't have this item, skip
                continue

            # Get market price for production line check
            market_price = game_state.market_prices.get(order.item_name, 0)

            # Check if we have enough inventory space before buying
            items_added = packages_to_buy * items_per_package
            size_needed = items_added * item.size

            if current_inventory_size + total_size_used + size_needed > max_inventory:
                # Not enough space, skip this purchase
                continue

            # Try to purchase (purchase_from_vendor handles package conversion)
            success = player.purchase_from_vendor(vendor, purchase_item_name, packages_to_buy, market_price, game_state)
            if success:
                # Track actual items added to inventory (not packages)
                purchases[order.item_name] = purchases.get(order.item_name, 0) + items_added
                order.last_executed_day = current_day
                # Track inventory size used
                total_size_used += size_needed

    return purchases, total_size_used


def execute_stock_minimum_restock(player: Player, game_state: GameState) -> Tuple[Dict[str, int], float]:
    """
    Execute stock minimum restock orders for items below their minimum threshold.
    Respects packaging system - buys at least 1 package if the item is packaged.
    Respects inventory capacity - stops buying when player reaches max inventory.

    Returns a tuple of (items purchased: {item_name: quantity_bought}, inventory_size_used: float)
    """
    purchases = {}
    total_size_used = 0.0

    # Get current inventory size and max capacity
    current_inventory_size = player.get_inventory_size_used(game_state.items_by_name)
    max_inventory = player.get_max_inventory()

    for item_name, (minimum_stock, vendor_name) in player.stock_minimum_restock.items():
        # Check current inventory
        current_stock = player.inventory.get(item_name, 0)

        # Find the vendor
        vendor = game_state.get_vendor(vendor_name)
        if not vendor:
            continue

        # Calculate effective lead time with any reductions from upgrades
        lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
        effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))

        # Adjust minimum stock for vendors with lead time
        # If vendor has lead time, add yesterday's demand to account for expected demand during delivery period
        adjusted_minimum = minimum_stock
        if effective_lead_time > 0:
            yesterday_item_demand = player.yesterday_demand.get(item_name, 0)
            adjusted_minimum = minimum_stock + yesterday_item_demand

        if current_stock >= adjusted_minimum:
            # Stock is sufficient, skip
            continue

        # Get item object first
        item = game_state.items_by_name.get(item_name)
        if not item:
            continue

        # Determine the package name to use when querying the vendor
        # For small items (size < 5, excluding luxury), vendors sell packages
        purchase_item_name = item_name
        packages_to_buy = 1
        items_per_package = 1

        if item.size < 5.0 and item.category != "Luxury":
            # Item is packaged - determine package type based on vendor
            package_type = "bulk" if vendor.name in ["Bulk Master Co.", "Bulk Goods Co."] else "standard"
            package_name, items_per_package, _ = get_package_info(item, package_type)
            purchase_item_name = package_name

            # Calculate how many packages to buy
            needed = adjusted_minimum - current_stock
            packages_to_buy = (needed + items_per_package - 1) // items_per_package
        else:
            # Item is not packaged - buy exactly what's needed
            packages_to_buy = adjusted_minimum - current_stock

        # Get the price from this vendor using the package name
        price = vendor.get_price(purchase_item_name, packages_to_buy)
        if price is None:
            # Vendor doesn't have this item, skip
            continue

        # Get market price for production line check
        market_price = game_state.market_prices.get(item_name, 0)

        # Check if we have enough inventory space before buying
        items_added = packages_to_buy * items_per_package
        size_needed = items_added * item.size

        if current_inventory_size + total_size_used + size_needed > max_inventory:
            # Not enough space, skip this purchase
            continue

        # Try to purchase (purchase_from_vendor handles package conversion)
        success = player.purchase_from_vendor(vendor, purchase_item_name, packages_to_buy, market_price, game_state)
        if success:
            # Track actual items added to inventory (not packages)
            purchases[item_name] = purchases.get(item_name, 0) + items_added
            # Track inventory size used
            total_size_used += size_needed

    return purchases, total_size_used


def execute_category_minimum_restock(player: Player, game_state: GameState) -> Tuple[Dict[str, int], float]:
    """
    Execute category minimum restock orders for all items in a category below their minimum threshold.
    For each category with auto-restock enabled, ensures all items in that category have at least
    the specified minimum stock.

    Respects packaging system - buys at least 1 package if the item is packaged.
    Respects inventory capacity - stops buying when player reaches max inventory.

    Returns a tuple of (items purchased: {item_name: quantity_bought}, inventory_size_used: float)
    """
    purchases = {}
    total_size_used = 0.0

    # Get current inventory size and max capacity
    current_inventory_size = player.get_inventory_size_used(game_state.items_by_name)
    max_inventory = player.get_max_inventory()

    for category_name, (minimum_stock, vendor_name) in player.category_minimum_restock.items():
        # Find the vendor
        vendor = game_state.get_vendor(vendor_name)
        if not vendor:
            continue

        # Calculate effective lead time with any reductions from upgrades
        lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
        effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))

        # Get all items in this category
        category_items = [item for item in game_state.items if item.category == category_name]

        for item in category_items:
            item_name = item.name

            # Check current inventory
            current_stock = player.inventory.get(item_name, 0)

            # Adjust minimum stock for vendors with lead time
            # If vendor has lead time, add yesterday's demand to account for expected demand during delivery period
            adjusted_minimum = minimum_stock
            if effective_lead_time > 0:
                yesterday_item_demand = player.yesterday_demand.get(item_name, 0)
                adjusted_minimum = minimum_stock + yesterday_item_demand

            if current_stock >= adjusted_minimum:
                # Stock is sufficient, skip
                continue

            # Determine the package name to use when querying the vendor
            # For small items (size < 5, excluding luxury), vendors sell packages
            purchase_item_name = item_name
            packages_to_buy = 1
            items_per_package = 1

            if item.size < 5.0 and item.category != "Luxury":
                # Item is packaged - determine package type based on vendor
                package_type = "bulk" if vendor.name in ["Bulk Master Co.", "Bulk Goods Co."] else "standard"
                package_name, items_per_package, _ = get_package_info(item, package_type)
                purchase_item_name = package_name

                # Calculate how many packages to buy
                needed = adjusted_minimum - current_stock
                packages_to_buy = (needed + items_per_package - 1) // items_per_package
            else:
                # Item is not packaged - buy exactly what's needed
                packages_to_buy = adjusted_minimum - current_stock

            # Get the price from this vendor using the package name
            price = vendor.get_price(purchase_item_name, packages_to_buy)
            if price is None:
                # Vendor doesn't have this item, skip
                continue

            # Get market price for production line check
            market_price = game_state.market_prices.get(item_name, 0)

            # Check if we have enough inventory space before buying
            items_added = packages_to_buy * items_per_package
            size_needed = items_added * item.size

            if current_inventory_size + total_size_used + size_needed > max_inventory:
                # Not enough space, skip this purchase
                continue

            # Try to purchase (purchase_from_vendor handles package conversion)
            success = player.purchase_from_vendor(vendor, purchase_item_name, packages_to_buy, market_price, game_state)
            if success:
                # Track actual items added to inventory (not packages)
                purchases[item_name] = purchases.get(item_name, 0) + items_added
                # Track inventory size used
                total_size_used += size_needed

    return purchases, total_size_used


# -------------------------------------------------------------------
# Daily simulation logic
# -------------------------------------------------------------------

def get_weighted_customer_type(day: int) -> str:
    """
    Returns a weighted random customer type based on the current day.

    Day ranges:
    - Below Day 30: Low=40%, Medium=50%, High=10%
    - Day 30-99: Low=10%, Medium=60%, High=30%
    - Day 100+: Low=5%, Medium=25%, High=70%
    """
    if day < 30:
        weights = {"low": 0.40, "medium": 0.50, "high": 0.10}
    elif day < 100:
        weights = {"low": 0.10, "medium": 0.60, "high": 0.30}
    else:
        weights = {"low": 0.05, "medium": 0.25, "high": 0.70}

    rand = random.random()
    cumulative = 0.0

    for customer_type, weight in weights.items():
        cumulative += weight
        if rand < cumulative:
            return customer_type

    return "medium"  # Fallback


def get_special_customer_count(day: int) -> int:
    """
    Calculate how many special customers should spawn today.

    - Available from day 10+
    - Starts with 1 special customer
    - Adds +1 at day 30
    - Then +1 every 30 days after that (day 60, 90, 120, etc.)
    """
    if day < 10:
        return 0
    elif day < 30:
        return 1
    else:
        # day 30: 2, day 60: 3, day 90: 4, etc.
        return 2 + ((day - 30) // 30)


def can_special_customer_type_spawn(customer_type: str, items: List[Item]) -> bool:
    """
    Check if a special customer type can spawn based on available items.

    Some customer types require specific items/categories to exist:
    - Gamer: requires at least one Gaming category item
    - Christmas Dad: requires both "Gaming Console" and "4K TV"
    """
    if customer_type == "gamer":
        # Check if any Gaming category items exist
        return any(item.category == "Gaming" for item in items)

    elif customer_type == "christmas_dad":
        # Check if both required items exist
        item_names = {item.name for item in items}
        return "Gaming Console" in item_names and "4K TV" in item_names

    # All other customer types can always spawn
    return True


def get_weighted_special_customer_type() -> str:
    """
    Returns a weighted random special customer type.

    These are relative weights, not spawn probabilities. Special customers
    spawn every day (based on get_special_customer_count), and these weights
    determine which types are selected.

    Selection weights:
    - Hoarder: 30 (most common)
    - Shoplifter: 15
    - Party Prep Mom: 30 (most common)
    - Gamer: 10
    - Christmas Dad: 10
    - Lottery Winner: 4 (rare)
    - Youtuber: 1 (very rare)
    """
    weights = {
        "hoarder": 0.30,
        "shoplifter": 0.15,
        "party_prep_mom": 0.30,
        "gamer": 0.10,
        "christmas_dad": 0.10,
        "lottery_winner": 0.04,
        "youtuber": 0.01
    }

    rand = random.random()
    cumulative = 0.0

    for customer_type, weight in weights.items():
        cumulative += weight
        if rand < cumulative:
            return customer_type

    return "hoarder"  # Fallback


def get_player_main_category(player: Player, current_day: int) -> Optional[str]:
    """
    Determine the player's main category based on sales history from the last 14 days.

    Returns the category with the highest total sales value over the last 14 days.
    If less than 14 days of data exists, uses all available data.
    Returns None if no sales history exists.
    """
    # Get the range of days to consider (last 14 days, or all available if less than 14)
    start_day = max(1, current_day - 13)  # Look back 14 days including today

    # Aggregate sales by category across the time period
    category_totals: Dict[str, float] = {}

    for day in range(start_day, current_day + 1):
        if day in player.category_sales_history:
            for category, sales in player.category_sales_history[day].items():
                category_totals[category] = category_totals.get(category, 0.0) + sales

    if not category_totals:
        return None

    # Return the category with the highest total sales
    return max(category_totals.items(), key=lambda x: x[1])[0]


def get_non_adjacent_categories(player: Player, items_by_name: Dict[str, Item], current_day: int) -> Set[str]:
    """
    Get all categories that are non-adjacent to the player's main category.

    Returns a set of category names that are stocked but not adjacent to the main category.
    """
    main_category = get_player_main_category(player, current_day)

    # If no main category (no sales yet), treat all stocked categories as adjacent
    if main_category is None:
        return set()

    # Get all categories the player currently stocks
    stocked_categories = set()
    for item_name, quantity in player.inventory.items():
        if quantity > 0 and item_name in items_by_name:
            stocked_categories.add(items_by_name[item_name].category)

    # Remove the main category itself
    stocked_categories.discard(main_category)

    # Get adjacent categories for the main category
    adjacent_categories = CATEGORY_ADJACENCY.get(main_category, set())

    # Return categories that are stocked but not adjacent
    non_adjacent = stocked_categories - adjacent_categories
    return non_adjacent


def calculate_adjacency_multiplier(
    player: Player,
    items_by_name: Dict[str, Item],
    current_day: int,
    check_temporary: bool = False
) -> float:
    """
    Calculate the CAS multiplier based on non-adjacent categories.

    Permanent effect based on number of non-adjacent categories:
    - 1 non-adjacent: 0.9x
    - 3 non-adjacent: 0.6x
    - 7 non-adjacent: 0.4x
    - 10+ non-adjacent: 0.1x

    Temporary effect (today only): 0.9x if a new non-adjacent item was stocked today.

    Args:
        player: The player to calculate for
        items_by_name: Dictionary mapping item names to Item objects
        current_day: Current game day
        check_temporary: If True, also apply temporary penalty for new items today

    Returns:
        The multiplier to apply to CAS (e.g., 0.9 for 10% penalty)
    """
    multiplier = 1.0

    # Calculate permanent penalty based on non-adjacent category count
    non_adjacent = get_non_adjacent_categories(player, items_by_name, current_day)
    non_adjacent_count = len(non_adjacent)

    if non_adjacent_count >= 10:
        multiplier *= 0.1
    elif non_adjacent_count >= 7:
        multiplier *= 0.4
    elif non_adjacent_count >= 3:
        multiplier *= 0.6
    elif non_adjacent_count >= 1:
        multiplier *= 0.9

    # Check for temporary penalty (new non-adjacent items stocked today)
    if check_temporary and player.items_stocked_today:
        main_category = get_player_main_category(player, current_day)
        if main_category is not None:
            adjacent_categories = CATEGORY_ADJACENCY.get(main_category, set())

            # Check if any newly stocked item today is from a non-adjacent category
            for item_name in player.items_stocked_today:
                if item_name in items_by_name:
                    item_category = items_by_name[item_name].category
                    if item_category != main_category and item_category not in adjacent_categories:
                        # Found a new non-adjacent item, apply temporary 0.9x penalty
                        multiplier *= 0.9
                        break  # Only apply once, even if multiple new non-adjacent items

    return multiplier


def calculate_player_cas(
    player: Player,
    market_prices: Dict[str, float],
    items_by_name: Dict[str, Item],
    all_available_items: List[Item],
    current_day: int = 1
) -> float:
    """
    Calculate Customer Attraction Score (CAS) for a player based on their overall store.
    This is used for weighted customer distribution.

    Formula:
    - reputation_multiplier = 10 ** (reputation / 100)
    - discount_score = sum of discount % for all stocked items
    - item_stability = sum of proximity and consistency scores
    - specialty_multiplier based on category item counts (additive bonuses)
    - fulfillment_multiplier based on average fulfillment %
    - adjacency_multiplier based on non-adjacent categories (0.1x to 1.0x)
    - CAS = (discount_score + item_stability) * reputation_multiplier * specialty_multiplier * fulfillment_multiplier * adjacency_multiplier

    Returns 0 if player has no stock or no acceptable prices.
    """
    discount_score = 0.0
    has_any_stock = False
    max_acceptable_price_multiplier = 1.15
    total_catalog_items = len(all_available_items)

    # Calculate discount score for all stocked items
    for item_name, quantity in player.inventory.items():
        if quantity <= 0 or item_name not in player.prices:
            continue

        market_price = market_prices.get(item_name, 0)
        if market_price <= 0:
            continue

        player_price = player.prices[item_name]
        max_acceptable_price = market_price * max_acceptable_price_multiplier

        # Only consider if price is acceptable
        if player_price <= max_acceptable_price:
            has_any_stock = True

            # Calculate discount percentage
            if player_price < market_price:
                discount_pct = ((market_price - player_price) / market_price) * 100
            else:
                discount_pct = 0

            # Get item importance
            item = items_by_name.get(item_name)
            importance = item.importance if item else 2

            # Add weighted discount to score
            discount_score += discount_pct * importance

    # Return 0 if no stock
    if not has_any_stock:
        return 0.0

    # Calculate specialty score (category-based bonuses for item variety)
    specialty_multiplier_effective, _, _ = calculate_specialty_score(player, items_by_name)

    # Calculate fulfillment multiplier
    fulfillment_pct = player.average_fulfillment_pct
    if fulfillment_pct >= 100:
        fulfillment_multiplier = 2.0
    elif fulfillment_pct >= 90:
        fulfillment_multiplier = 1.4
    elif fulfillment_pct > 70:
        fulfillment_multiplier = 1.1
    elif fulfillment_pct >= 50:
        fulfillment_multiplier = 1.0
    elif fulfillment_pct >= 20:
        fulfillment_multiplier = 0.9
    elif fulfillment_pct >= 10:
        fulfillment_multiplier = 0.5
    else:
        fulfillment_multiplier = 0.1

    # Calculate reputation multiplier
    reputation_multiplier = 10 ** (player.reputation / 100)

    # Calculate item stability
    item_stability = calculate_item_stability(player, market_prices, items_by_name)

    # Calculate marketing effect (adds to both discount and stability)
    marketing_effect = calculate_marketing_effect(player, market_prices)

    # Calculate adjacency multiplier (penalty for non-adjacent categories)
    adjacency_multiplier = calculate_adjacency_multiplier(player, items_by_name, current_day, check_temporary=True)

    # Calculate final CAS (marketing effect boosts both components)
    cas = (discount_score + marketing_effect + item_stability + marketing_effect) * reputation_multiplier * specialty_multiplier_effective * fulfillment_multiplier * adjacency_multiplier

    return cas


def get_category_specialty_threshold(player: Player, category: str, items_by_name: Dict[str, Item]) -> Optional[int]:
    """
    Get the highest threshold a player has reached for a specific category specialization.
    Returns the threshold number, or None if the category has no specialization bonus.
    """
    # Count items in this category that the player has in stock
    category_count = 0
    for item_name, qty in player.inventory.items():
        if qty > 0:
            item = items_by_name.get(item_name)
            if item and item.category == category:
                category_count += 1

    # Get the thresholds for this category
    thresholds = SPECIALTY_SCORE_THRESHOLDS.get(category, [])
    if not thresholds:
        return None

    # Find the highest threshold the player has reached
    highest_threshold = None
    for threshold, multiplier in thresholds:
        if category_count >= threshold:
            highest_threshold = threshold

    return highest_threshold


def player_has_both_specializations(
    player: Player,
    categories: List[str],
    items_by_name: Dict[str, Item]
) -> bool:
    """
    Check if a player has specialization bonuses for both of a customer's categories.
    Returns True if player has thresholds for both categories, False otherwise.
    """
    for category in categories:
        threshold = get_category_specialty_threshold(player, category, items_by_name)
        if threshold is None:
            return False
    return True


def choose_best_specialized_player(
    players: List[Player],
    categories: List[str],
    items_by_name: Dict[str, Item]
) -> Optional[Player]:
    """
    Choose the best player for a customer with category specializations.
    Implements priority logic:
    1. Players with BOTH specialization bonuses get highest priority (higher combined threshold wins)
    2. If no player has both, choose based on any matching category (higher threshold wins)
    3. If same threshold: player with most products in that category wins
    4. If tied: pick randomly
    """
    # First, try to find players with BOTH specializations
    both_spec_candidates = []
    for player in players:
        if player_has_both_specializations(player, categories, items_by_name):
            # Calculate combined threshold
            threshold1 = get_category_specialty_threshold(player, categories[0], items_by_name) or 0
            threshold2 = get_category_specialty_threshold(player, categories[1], items_by_name) or 0
            combined_threshold = threshold1 + threshold2

            # Count total items in both categories
            total_count = 0
            for item_name, qty in player.inventory.items():
                if qty > 0:
                    item = items_by_name.get(item_name)
                    if item and item.category in categories:
                        total_count += 1

            both_spec_candidates.append((player, combined_threshold, total_count))

    if both_spec_candidates:
        # Sort by combined threshold (descending), then by total count (descending)
        both_spec_candidates.sort(key=lambda x: (-x[1], -x[2]))
        best = both_spec_candidates[0]
        best_threshold = best[1]
        best_count = best[2]

        # Find all players with the same best score
        tied_players = [
            p for p in both_spec_candidates
            if p[1] == best_threshold and p[2] == best_count
        ]
        return random.choice(tied_players)[0]

    # If no player has both, find players with at least one category
    single_spec_candidates = []
    for player in players:
        for category in categories:
            threshold = get_category_specialty_threshold(player, category, items_by_name)
            if threshold is not None:
                # Count items in this category
                category_count = 0
                for item_name, qty in player.inventory.items():
                    if qty > 0:
                        item = items_by_name.get(item_name)
                        if item and item.category == category:
                            category_count += 1
                single_spec_candidates.append((player, threshold, category_count, category))
                break  # Only consider first matching category

    if not single_spec_candidates:
        return None

    # Sort by threshold (descending), then by category_count (descending)
    single_spec_candidates.sort(key=lambda x: (-x[1], -x[2]))

    best = single_spec_candidates[0]
    best_threshold = best[1]
    best_count = best[2]

    # Find all players with the same best score
    tied_players = [
        p for p in single_spec_candidates
        if p[1] == best_threshold and p[2] == best_count
    ]

    # If there's a tie, pick randomly
    return random.choice(tied_players)[0]


def get_player_customer_capacity(player: Player) -> int:
    """
    Calculate the maximum customer capacity for a player.
    - Base (owner only): 100 customers/day
    - Each cashier: +200 customers/day
    """
    return 100 + (player.cashiers * 200)


def calculate_capacity_penalty(customers_allocated: int, capacity: int) -> float:
    """
    Calculate the CAS penalty multiplier based on overcapacity.

    This is a soft limit - going over capacity reduces CAS effectiveness with a smooth linear scale.

    Penalty Scale (smooth linear degradation):
    - At or below capacity (ratio ≤ 1.0): 1.0x multiplier (no penalty)
    - At 2.0x capacity (ratio = 2.0): 0.1x multiplier (90% penalty)
    - Smooth linear interpolation between 1.0x and 2.0x capacity
    - Clamped at minimum 0.1x for extreme overcapacity (>2.0x)

    Formula: penalty = max(0.1, 1.0 - 0.9 * (ratio - 1.0))

    Examples:
    - ratio 1.0 (at capacity): 1.00x multiplier
    - ratio 1.1 (10% over): 0.91x multiplier
    - ratio 1.5 (50% over): 0.55x multiplier
    - ratio 2.0 (100% over): 0.10x multiplier

    This creates a fair, gradual degradation that simulates customers
    avoiding overcrowded stores and choosing less busy competitors.

    Returns:
        A multiplier between 0.1 and 1.0 to apply to CAS
    """
    if capacity == 0:
        # No capacity means severe penalty
        return 0.1

    ratio = customers_allocated / capacity

    # If under or at capacity, no penalty
    if ratio <= 1.0:
        return 1.0

    # Smooth linear scale from 1.0 (at capacity) to 0.1 (at 2x capacity)
    # Linearly decreases by 0.9 over the range [1.0, 2.0]
    penalty = max(0.1, 1.0 - 0.9 * (ratio - 1.0))
    return penalty


def assign_customers_by_cas_with_specialization(
    customers: List[Customer],
    players: List[Player],
    market_prices: Dict[str, float],
    items_by_name: Dict[str, Item],
    all_available_items: List[Item],
    current_day: int = 1
) -> Tuple[Dict[str, List[Customer]], Dict[str, Dict[str, Any]]]:
    """
    Assign customers to players with CAS-first, then specialization overflow.

    Process:
    1. Assign customers normally by CAS
    2. For customers with specializations:
       - Check if the CAS-assigned player has at least ONE of the customer's categories
       - If YES: customer stays with that player (CAS honored)
       - If NO: customer becomes overflow, reassign to best specialized player if one exists
       - If no specialized player exists: keep original CAS assignment

    NEW: Iterative capacity-based reallocation
    3. Check if any player is over their customer capacity
    4. If yes, apply capacity penalty to their CAS and reallocate
    5. Repeat until stable or max iterations reached
    """
    # Create a player lookup by name for easier access
    players_by_name = {player.name: player for player in players}

    # Track capacity penalties for each player (starts at 1.0 = no penalty)
    capacity_penalties = {player.name: 1.0 for player in players}

    # Iterative reallocation with capacity checks
    MAX_ITERATIONS = 2
    for iteration in range(MAX_ITERATIONS):
        # Do CAS assignment with current capacity penalties
        assignments, cas_breakdowns = assign_customers_by_cas(
            customers, players, market_prices, items_by_name, all_available_items,
            current_day, capacity_penalties
        )

        # Handle specialization-based overflow allocation
        specialized_assignments = {player.name: [] for player in players}

        # Process each player's assigned customers
        for player_name, assigned_customers in assignments.items():
            assigned_player = players_by_name[player_name]

            for customer in assigned_customers:
                # Check if customer has specializations
                if customer.specializations:
                    # Check if the assigned player has at least ONE of the customer's categories
                    has_matching_category = False
                    for category in customer.specializations:
                        threshold = get_category_specialty_threshold(assigned_player, category, items_by_name)
                        if threshold is not None:
                            has_matching_category = True
                            break

                    if has_matching_category:
                        # CAS assignment honored - player has a matching category
                        specialized_assignments[player_name].append(customer)
                    else:
                        # Player doesn't have any matching categories - try to find a specialized player
                        best_specialized_player = choose_best_specialized_player(players, customer.specializations, items_by_name)

                        if best_specialized_player:
                            # Found a specialized player, reassign to them
                            specialized_assignments[best_specialized_player.name].append(customer)
                        else:
                            # No specialized player found, keep original CAS assignment
                            specialized_assignments[player_name].append(customer)
                else:
                    # No specialization, keep original assignment
                    specialized_assignments[player_name].append(customer)

        # Check if any player is over capacity and needs penalty
        needs_reallocation = False
        new_capacity_penalties = {}

        for player in players:
            allocated_count = len(specialized_assignments[player.name])
            capacity = get_player_customer_capacity(player)
            penalty = calculate_capacity_penalty(allocated_count, capacity)

            new_capacity_penalties[player.name] = penalty

            # If penalty changed, we need to reallocate
            if abs(penalty - capacity_penalties[player.name]) > 0.001:
                needs_reallocation = True

        # Update penalties
        capacity_penalties = new_capacity_penalties

        # If no reallocation needed, we've reached a stable state
        if not needs_reallocation:
            break

    # Store capacity penalties in CAS breakdowns for visibility
    for player_name in cas_breakdowns:
        cas_breakdowns[player_name]["capacity_penalty"] = capacity_penalties[player_name]
        cas_breakdowns[player_name]["customer_capacity"] = get_player_customer_capacity(players_by_name[player_name])
        cas_breakdowns[player_name]["allocated_customers"] = len(specialized_assignments[player_name])

    return specialized_assignments, cas_breakdowns


def assign_customers_by_cas(
    customers: List[Customer],
    players: List[Player],
    market_prices: Dict[str, float],
    items_by_name: Dict[str, Item],
    all_available_items: List[Item],
    current_day: int = 1,
    capacity_penalties: Dict[str, float] = None
) -> Tuple[Dict[str, List[Customer]], Dict[str, Dict[str, Any]]]:
    """
    Assign customers to players based on proportional CAS distribution.

    If a player has 30% of total CAS, they receive exactly 30% of customers.
    This is deterministic and proportional, not random.

    Capacity penalties (if provided) are applied to CAS to simulate customers
    avoiding overcrowded stores.

    Returns:
        - A dictionary mapping player name to list of assigned customers.
        - A dictionary mapping player name to their CAS breakdown data.
    """
    # Initialize capacity penalties if not provided
    if capacity_penalties is None:
        capacity_penalties = {player.name: 1.0 for player in players}

    # Calculate CAS for each player and store breakdown
    player_cas = {}
    cas_breakdowns = {}
    for player in players:
        breakdown = calculate_cas_breakdown(player, market_prices, items_by_name, all_available_items, current_day)
        base_cas = breakdown["final_cas"]

        # Apply capacity penalty
        penalty = capacity_penalties.get(player.name, 1.0)
        penalized_cas = base_cas * penalty

        player_cas[player.name] = penalized_cas
        cas_breakdowns[player.name] = breakdown
        cas_breakdowns[player.name]["capacity_penalty_applied"] = penalty

    # Calculate total CAS
    total_cas = sum(player_cas.values())

    # If no players have any CAS, distribute evenly
    if total_cas == 0:
        # Equal distribution
        assignments = {player.name: [] for player in players}
        for i, customer in enumerate(customers):
            player = players[i % len(players)]
            assignments[player.name].append(customer)
        return assignments, cas_breakdowns

    # Distribute customers based on CAS proportions (not random weights)
    # If a player has 30% of total CAS, they get exactly 30% of customers
    assignments = {player.name: [] for player in players}

    # Calculate each player's allocation based on their CAS proportion
    allocations = {}  # player_name -> number of customers
    remainders = {}   # player_name -> fractional remainder

    total_customers = len(customers)
    for player in players:
        proportion = player_cas[player.name] / total_cas
        exact_allocation = proportion * total_customers
        allocations[player.name] = int(exact_allocation)  # whole number
        remainders[player.name] = exact_allocation - allocations[player.name]  # fractional part

    # Distribute any remaining customers due to rounding
    # Give them to players with highest fractional remainders
    total_allocated = sum(allocations.values())
    customers_remaining = total_customers - total_allocated

    if customers_remaining > 0:
        # Sort players by remainder (highest first)
        sorted_by_remainder = sorted(players, key=lambda p: remainders[p.name], reverse=True)
        for i in range(customers_remaining):
            allocations[sorted_by_remainder[i].name] += 1

    # Assign customers to players based on allocations
    customer_index = 0
    for player in players:
        num_to_assign = allocations[player.name]
        for _ in range(num_to_assign):
            if customer_index < len(customers):
                assignments[player.name].append(customers[customer_index])
                customer_index += 1

    return assignments, cas_breakdowns


def update_player_fulfillment_averages(player: Player, fulfillment_data: Dict[str, List[float]]) -> None:
    """Update a player's overall, allocated, and overflow fulfillment averages."""
    allocated_data = fulfillment_data.get("allocated", [])
    overflow_data = fulfillment_data.get("overflow", [])
    combined_data = allocated_data + overflow_data

    if combined_data:
        player.average_fulfillment_pct = sum(combined_data) / len(combined_data)

    if allocated_data:
        player.allocated_average_fulfillment_pct = sum(allocated_data) / len(allocated_data)

    if overflow_data:
        player.overflow_average_fulfillment_pct = sum(overflow_data) / len(overflow_data)


def record_store_visit_metrics(
    store_visit_data: List[Dict[str, Any]],
    daily_fulfillment_data: Dict[str, Dict[str, List[float]]],
    fulfillment_visit_counts: Dict[str, Dict[str, int]],
    daily_reputation_changes: Dict[str, int],
    routed_no_need_counts: Optional[Dict[str, Dict[str, int]]] = None,
) -> None:
    """Track fulfillment and reputation for every store visit.

    Zero-need visits are ignored for fulfillment and reputation but can be counted
    separately through ``routed_no_need_counts`` if provided.
    """

    for visit in store_visit_data:
        record_single_store_visit(
            visit,
            daily_fulfillment_data,
            fulfillment_visit_counts,
            daily_reputation_changes,
            routed_no_need_counts,
        )


def record_single_store_visit(
    visit: Dict[str, Any],
    daily_fulfillment_data: Dict[str, Dict[str, List[float]]],
    fulfillment_visit_counts: Dict[str, Dict[str, int]],
    daily_reputation_changes: Dict[str, int],
    routed_no_need_counts: Optional[Dict[str, Dict[str, int]]] = None,
) -> None:
    """Record fulfillment stats and reputation impact for a single store visit."""

    store_name = visit.get("store_name")
    visit_type = visit.get("visit_type") or "allocated"
    starting_needs = visit.get("starting_needs", 0)

    if (not store_name or store_name not in daily_fulfillment_data
            or store_name not in fulfillment_visit_counts
            or store_name not in daily_reputation_changes):
        return

    if visit_type not in daily_fulfillment_data[store_name]:
        visit_type = "allocated"

    if starting_needs <= 0:
        if routed_no_need_counts is not None:
            routed_no_need_counts[store_name][visit_type] += 1
        return

    fulfillment_percentage = (visit["fulfilled"] / starting_needs) * 100

    # Track fulfillment percentage for this customer visit
    daily_fulfillment_data[store_name][visit_type].append(fulfillment_percentage)

    if visit_type == "overflow":
        fulfillment_visit_counts[store_name]["overflow"] += 1
    else:
        fulfillment_visit_counts[store_name]["allocated"] += 1

    # Mark visit as successfully recorded
    visit['recorded'] = True

    # Track reputation changes based on fulfillment for this store visit
    if fulfillment_percentage <= 30:
        # 30% or less: -1 reputation
        daily_reputation_changes[store_name] -= 1
    elif fulfillment_percentage >= 80:
        # 80% or more: +1 reputation
        daily_reputation_changes[store_name] += 1

        # If 100% fulfilled at exactly one store, +2 total (so +1 additional)
        if fulfillment_percentage >= 99.9 and visit.get("only_store", False):
            daily_reputation_changes[store_name] += 1


def format_fulfillment_summary(player: Player, visit_counts: Dict[str, int]) -> str:
    """Generate a formatted fulfillment summary for display."""
    allocated_visits = visit_counts.get("allocated", 0)
    overflow_visits = visit_counts.get("overflow", 0)
    total_visits = allocated_visits + overflow_visits

    return (
        f"   Average Fulfillment: {player.average_fulfillment_pct:.1f}% "
        f"(from {total_visits} customers"
        f" | Allocated Avg: {player.allocated_average_fulfillment_pct:.1f}% ({allocated_visits})"
        f" | Overflow Avg: {player.overflow_average_fulfillment_pct:.1f}% ({overflow_visits}))"
    )


def run_day(game_state: GameState, show_details: bool = True) -> Dict[str, float]:
    """
    Simulate a single day in the economic game.

    Steps:
    1. Reset special event prices from previous day
    2. Apply special events for today (if any)
    3. Let AI players adjust buy orders and prices
    4. Execute buy orders for all players (from cheapest to most expensive)
    5. For each customer, generate needs and make purchases (limited by cashier capacity)
    6. Pay employee wages
    7. Track statistics
    8. Refresh vendor inventory for next day (at END of day)
    9. Advance the day counter
    10. Apply daily price fluctuations for next day (at END of day)

    Returns dictionary of daily sales per player.
    """

    if show_details:
        print(f"\n=== Day {game_state.day} ===")

    # Step 1: Reset any event price changes from previous day
    if game_state.event_price_changes:
        for item_name, original_price in game_state.event_price_changes.items():
            game_state.market_prices[item_name] = original_price
        game_state.event_price_changes.clear()

    # Reset items stocked today for all players (new day starts)
    for player in game_state.players:
        player.items_stocked_today.clear()

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

    # Calculate base customer count: num_players * 50 + 5 per day
    base_customer_count = len(game_state.players) * 50 + (game_state.day * 5)

    # Add permanent customer increase for every 14-day period that has passed
    fourteen_day_periods = game_state.day // 14
    if fourteen_day_periods > 0:
        permanent_bonus = 20 * fourteen_day_periods
        base_customer_count += permanent_bonus

        # Show event message only on the actual milestone days
        if game_state.day % 14 == 0 and show_details:
            print(f"🎊 14-DAY EVENT! +20 permanent customers! (Total permanent bonus: +{permanent_bonus})")

    # Calculate uncapped customers (starts at day 50, +1 every 10 days)
    uncapped_customer_count = 0
    if game_state.day >= 50:
        uncapped_customer_count = ((game_state.day - 40) // 10)

    if show_details:
        print(f"Regular customers today: {base_customer_count}")
        if uncapped_customer_count > 0:
            print(f"💎 Uncapped customers today: {uncapped_customer_count} (looking for expensive items ≥$100)")


    # Step 4: Execute buy orders for ALL players
    if show_details:
        print("\nExecuting buy orders...")

    # Track daily spending per player for accurate profit calculation
    daily_spending = {player.name: 0.0 for player in game_state.players}

    # Track inventory space used per player (for buy orders)
    daily_inventory_used = {player.name: 0.0 for player in game_state.players}

    for player in game_state.players:
        # Track actual cash spent (accounts for vendor fallbacks, discounts, etc.)
        cash_before = player.cash

        # Execute recurring buy orders first
        recurring_purchases, recurring_size = execute_recurring_buy_orders(player, game_state)

        # Execute stock minimum restock
        restock_purchases, restock_size = execute_stock_minimum_restock(player, game_state)

        # Execute category minimum restock
        category_restock_purchases, category_restock_size = execute_category_minimum_restock(player, game_state)

        # Execute manual buy orders
        manual_purchases, manual_size = execute_buy_orders(player, game_state)

        # Track total inventory space used
        daily_inventory_used[player.name] = recurring_size + restock_size + category_restock_size + manual_size

        # Combine all purchases
        all_purchases = {}
        for item, qty in recurring_purchases.items():
            all_purchases[item] = all_purchases.get(item, 0) + qty
        for item, qty in restock_purchases.items():
            all_purchases[item] = all_purchases.get(item, 0) + qty
        for item, qty in category_restock_purchases.items():
            all_purchases[item] = all_purchases.get(item, 0) + qty
        for item, qty in manual_purchases.items():
            all_purchases[item] = all_purchases.get(item, 0) + qty

        cash_after = player.cash
        actual_spent = cash_before - cash_after

        daily_spending[player.name] = actual_spent
        if show_details and all_purchases:
            print(f"  {player.name}: Purchased {sum(all_purchases.values())} items (bought: {daily_inventory_used[player.name]:.1f} space)(spent ${actual_spent:.2f})")
            if recurring_purchases:
                print(f"    - Recurring orders: {sum(recurring_purchases.values())} items")
            if restock_purchases:
                print(f"    - Auto-restock: {sum(restock_purchases.values())} items")
            if category_restock_purchases:
                print(f"    - Category auto-restock: {sum(category_restock_purchases.values())} items")

    # Track daily statistics
    daily_sales = {player.name: 0.0 for player in game_state.players}
    daily_profits = {player.name: 0.0 for player in game_state.players}
    customers_served = {player.name: 0 for player in game_state.players}
    allocated_customers_served = {player.name: 0 for player in game_state.players}
    allocated_customers_assigned = {player.name: 0 for player in game_state.players}
    overflow_customers_served = {player.name: 0 for player in game_state.players}
    uncapped_customers_served = {player.name: 0 for player in game_state.players}
    unmet_demand = 0
    unmet_uncapped_demand = 0

    # Track reputation changes per player (to be applied at end of day with limits)
    daily_reputation_changes = {player.name: 0 for player in game_state.players}

    # Track fulfillment percentages per player (to calculate average at end of day)
    daily_fulfillment_data = {
        player.name: {"allocated": [], "overflow": []}
        for player in game_state.players
    }
    fulfillment_visit_counts = {player.name: {"allocated": 0, "overflow": 0} for player in game_state.players}
    routed_no_need_counts = {player.name: {"allocated": 0, "overflow": 0} for player in game_state.players}

    # Track customer types for daily summary
    customer_type_stats = {
        'spawned': {'low': 0, 'medium': 0, 'high': 0},
        'bought_something': {'low': 0, 'medium': 0, 'high': 0},
        'found_nothing': {'low': 0, 'medium': 0, 'high': 0}
    }
    customers_counted_in_stats: Set[str] = set()

    # Track special customers for daily summary
    special_customer_events = []  # List of (customer_type, target_player_name, items_taken/bought)

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
        customer_type = get_weighted_customer_type(game_state.day)
        customer = Customer(name=f"Customer_{i+1}", customer_type=customer_type, day=game_state.day)
        # Roll specializations for regular customers (low, medium, high)
        if customer_type in ["low", "medium", "high"]:
            customer.roll_specializations(game_state.items, game_state.item_demand)
        all_customers.append(customer)
        customer_type_stats['spawned'][customer_type] += 1


    # Track total demand per item (what customers want to buy today)
    daily_demand_per_item = {}  # item_name -> total quantity wanted

    # Build items dictionary for quick lookup (needed for CAS calculation)
    items_by_name = {item.name: item for item in game_state.items}

    # Assign customers to players based on weighted CAS distribution with specialization priority
    customer_assignments, cas_breakdowns_pre_shopping = assign_customers_by_cas_with_specialization(
        all_customers,
        game_state.players,
        game_state.market_prices,
        items_by_name,
        game_state.items,
        game_state.day
    )

    # Track how many customers have visited each store (for capacity-aware overflow)
    customer_visits_per_store = {player.name: 0 for player in game_state.players}

    # Process customers for each player
    for player in game_state.players:
        allocated_customers_assigned[player.name] = len(customer_assignments.get(player.name, []))

    for player in game_state.players:
        assigned_customers = customer_assignments.get(player.name, [])

        for customer in assigned_customers:
            needs = customer.generate_daily_needs(game_state.items, game_state.market_prices, game_state.item_demand)

            # Track demand for each item the customer wants
            for need in needs:
                daily_demand_per_item[need.item_name] = daily_demand_per_item.get(need.item_name, 0) + need.quantity

            # Skip customers with no needs
            if not needs:
                continue

            # Track customer spending against their budget
            customer_spending = 0.0
            customer_budget = customer.budget
            customer_bought_anything = False

            # Track which stores this customer made purchases at (for customer counting)
            stores_purchased_from = {}  # store_name -> visit_type

            # Track whether this customer has already been counted in daily stats
            customer_stat_recorded = False
            had_needs = True

            # Customer starts at their assigned player's store
            current_supplier = player

            # Track all store visits with basket size when entering
            store_visits = []

            # Copy needs to track what remains
            remaining_needs = list(needs)

            # Track visited stores to avoid loops
            visited_stores: Set[str] = set()

            # Helper to check if customer still has items in basket
            def has_remaining_items(needs_list):
                return any(need.quantity > 0 for need in needs_list)

            # Main shopping loop
            while has_remaining_items(remaining_needs) and customer_spending < customer_budget:
                # Check if we've already visited this store
                if current_supplier.name in visited_stores:
                    break

                visited_stores.add(current_supplier.name)

                # Track customer visit to this store
                customer_visits_per_store[current_supplier.name] += 1

                # Determine visit type
                visit_type = "allocated" if current_supplier == player else "overflow"

                # Record basket size when entering this store
                basket_size_on_entry = sum(need.quantity for need in remaining_needs)

                # Try to purchase items from current supplier
                items_purchased_at_store = 0
                purchased_needs = []

                for need in list(remaining_needs):
                    # Check if current supplier has this item
                    if (need.item_name in current_supplier.inventory and
                        current_supplier.inventory[need.item_name] > 0 and
                        need.item_name in current_supplier.prices):

                        # Check if price is acceptable
                        market_price = game_state.market_prices.get(need.item_name, float('inf'))
                        max_acceptable_price = market_price * 1.15
                        supplier_price = current_supplier.prices[need.item_name]

                        if supplier_price <= max_acceptable_price:
                            remaining_budget = customer_budget - customer_spending

                            # Check if customer can afford this item (at least 1 unit)
                            if supplier_price <= remaining_budget:
                                # Adjust quantity based on remaining budget
                                affordable_quantity = min(need.quantity, int(remaining_budget / supplier_price))

                                if affordable_quantity > 0:
                                    # Purchase from current supplier
                                    item_category = items_by_name.get(need.item_name).category if need.item_name in items_by_name else None
                                    revenue, profit, actual_units_sold = current_supplier.sell_to_customer(
                                        need.item_name, affordable_quantity, supplier_price, game_state.day, item_category
                                    )

                                    if revenue > 0 and actual_units_sold > 0:
                                        # Track customer spending
                                        customer_spending += revenue

                                        # Track items purchased at this store
                                        items_purchased_at_store += actual_units_sold

                                        # Track sales
                                        daily_sales[current_supplier.name] += revenue
                                        daily_profits[current_supplier.name] += profit

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

                                        # Mark customer as having bought something for daily stats (only once)
                                        if (customer.customer_type in customer_type_stats['bought_something']
                                                and not customer_stat_recorded):
                                            customer_type_stats['bought_something'][customer.customer_type] += 1
                                            customers_counted_in_stats.add(customer.name)
                                            customer_stat_recorded = True

                                        # Update need quantity
                                        need.quantity -= actual_units_sold
                                        if need.quantity <= 0:
                                            purchased_needs.append(need)

                                        # Check if customer has hit their budget limit
                                        if customer_spending >= customer_budget:
                                            break

                # Remove fully purchased items
                for need in purchased_needs:
                    if need in remaining_needs:
                        remaining_needs.remove(need)

                # Only record this visit if customer made purchases
                if items_purchased_at_store > 0:
                    # Calculate fulfillment for this visit
                    fulfillment_pct = (items_purchased_at_store / basket_size_on_entry) * 100

                    # Record the visit
                    store_visits.append({
                        'store_name': current_supplier.name,
                        'visit_type': visit_type,
                        'basket_on_entry': basket_size_on_entry,
                        'items_purchased': items_purchased_at_store,
                        'fulfillment_pct': fulfillment_pct,
                    })

                    # Track that customer made purchase at this store
                    if current_supplier.name not in stores_purchased_from:
                        stores_purchased_from[current_supplier.name] = visit_type

                # Check if done shopping
                if not has_remaining_items(remaining_needs) or customer_spending >= customer_budget:
                    break

                # Try to find next store for overflow
                next_supplier = None
                for need in remaining_needs:
                    if need.quantity > 0:
                        alternative_supplier = customer.choose_supplier(
                            [p for p in game_state.players if p.name not in visited_stores],
                            need.item_name,
                            need.quantity,
                            game_state.market_prices,
                            customer_visits_per_store
                        )
                        if alternative_supplier:
                            next_supplier = alternative_supplier
                            break

                if next_supplier:
                    current_supplier = next_supplier
                else:
                    # No more stores available, mark remaining as unmet
                    for need in remaining_needs:
                        if need.quantity > 0:
                            unmet_demand += need.quantity
                            unmet_demand_per_item[need.item_name] = (
                                unmet_demand_per_item.get(need.item_name, 0) + need.quantity
                            )
                    break

            # Now record all visits and update counters
            customer_visited_only_one_store = len(store_visits) == 1

            for visit in store_visits:
                store_name = visit['store_name']
                visit_type = visit['visit_type']
                fulfillment_pct = visit['fulfillment_pct']

                # Record fulfillment data
                daily_fulfillment_data[store_name][visit_type].append(fulfillment_pct)
                fulfillment_visit_counts[store_name][visit_type] += 1

                # Update reputation based on fulfillment
                if fulfillment_pct <= 30:
                    daily_reputation_changes[store_name] -= 1
                elif fulfillment_pct >= 80:
                    daily_reputation_changes[store_name] += 1
                    # Bonus for 100% fulfillment at only store
                    if fulfillment_pct >= 99.9 and customer_visited_only_one_store:
                        daily_reputation_changes[store_name] += 1

            # Update customer counters (only count each store once)
            for store_name, visit_type in stores_purchased_from.items():
                customers_served[store_name] += 1
                if visit_type == "allocated":
                    allocated_customers_served[store_name] += 1
                else:
                    overflow_customers_served[store_name] += 1

            # Track customer type statistics for customers who never bought anything
            if (customer.customer_type in customer_type_stats['bought_something']
                    and not customer_stat_recorded):
                if customer_bought_anything:
                    customer_type_stats['bought_something'][customer.customer_type] += 1
                elif had_needs:
                    # Only count as found nothing if they actually had needs
                    customer_type_stats['found_nothing'][customer.customer_type] += 1
                customers_counted_in_stats.add(customer.name)

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
                    item_category = items_by_name.get(need.item_name).category if need.item_name in items_by_name else None
                    revenue, profit, actual_units_sold = supplier.sell_to_customer(need.item_name, need.quantity, price, game_state.day, item_category)
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

    # Step 5.6: Process special customers (no cashier limits, unique selection logic)
    special_customer_count = get_special_customer_count(game_state.day)
    if special_customer_count > 0:
        special_customers = []
        lottery_winner_spawned = False
        youtuber_spawned = False

        for i in range(special_customer_count):
            # Get weighted special customer type, with validation for item requirements
            max_attempts = 20  # Prevent infinite loop
            special_type = None

            for _ in range(max_attempts):
                candidate_type = get_weighted_special_customer_type()

                # Check if this customer type can spawn (has required items)
                if not can_special_customer_type_spawn(candidate_type, game_state.items):
                    continue  # Try again with different type

                # Enforce max 1 lottery winner and 1 youtuber per day
                if candidate_type == "lottery_winner":
                    if lottery_winner_spawned:
                        continue  # Try again
                    else:
                        lottery_winner_spawned = True
                        special_type = candidate_type
                        break
                elif candidate_type == "youtuber":
                    if youtuber_spawned:
                        continue  # Try again
                    else:
                        youtuber_spawned = True
                        special_type = candidate_type
                        break
                else:
                    # Valid type that can spawn
                    special_type = candidate_type
                    break

            # If we couldn't find a valid type after max_attempts, skip this spawn
            if special_type is None:
                continue

            customer = Customer(name=f"Special_{i+1}", customer_type=special_type, day=game_state.day)
            special_customers.append(customer)

        # Process each special customer
        for customer in special_customers:
            # Build items dictionary for quick lookup
            items_by_name = {item.name: item for item in game_state.items}

            # Format customer type for display
            customer_type_display = customer.customer_type.replace("_", " ").title()

            # Shoplifter has special handling (steals items)
            if customer.customer_type == "shoplifter":
                # Choose target (highest reputation player)
                target = customer.choose_supplier_for_special_customer(
                    game_state.players, [], game_state.market_prices, items_by_name, game_state.items
                )

                if target:
                    # Find 1-2 most expensive items in target's inventory
                    available_items = [
                        (item_name, target.prices.get(item_name, 0))
                        for item_name in target.inventory.keys()
                        if target.inventory[item_name] > 0 and item_name in target.prices
                    ]

                    if available_items:
                        # Sort by price descending
                        available_items.sort(key=lambda x: x[1], reverse=True)
                        steal_count = random.randint(1, 2)
                        stolen_items = []

                        for item_name, price in available_items[:steal_count]:
                            # Steal 1 unit
                            if target.inventory[item_name] > 0:
                                target.inventory[item_name] -= 1
                                stolen_items.append(item_name)

                        if stolen_items:
                            special_customer_events.append((
                                customer_type_display,
                                target.name,
                                f"Stole: {', '.join(stolen_items)}"
                            ))
                            # Apply reputation penalty for theft
                            daily_reputation_changes[target.name] -= 5
                        else:
                            special_customer_events.append((
                                customer_type_display,
                                target.name,
                                "Visited but found nothing to steal"
                            ))
                    else:
                        special_customer_events.append((
                            customer_type_display,
                            target.name,
                            "Visited but found nothing to steal"
                        ))
                else:
                    special_customer_events.append((
                        customer_type_display,
                        "No store",
                        "Could not find a target"
                    ))
                continue

            # For other special customers, generate needs
            needs = customer.generate_daily_needs(game_state.items, game_state.market_prices, game_state.item_demand)

            if not needs:
                special_customer_events.append((
                    customer_type_display,
                    "No store",
                    "Could not generate shopping needs"
                ))
                continue

            # Choose supplier using special customer logic
            supplier = customer.choose_supplier_for_special_customer(
                game_state.players, needs, game_state.market_prices, items_by_name, game_state.items
            )

            if not supplier:
                special_customer_events.append((
                    customer_type_display,
                    "No store",
                    "Could not find a suitable store"
                ))
                continue

            # Track purchases
            items_bought = []
            total_spent = 0.0

            for need in needs:
                if need.item_name in supplier.inventory and supplier.inventory[need.item_name] > 0:
                    if need.item_name in supplier.prices:
                        price = supplier.prices[need.item_name]
                        # Special customers bypass the 15% market price rule
                        item_category = items_by_name.get(need.item_name).category if need.item_name in items_by_name else None
                        revenue, profit, actual_units_sold = supplier.sell_to_customer(need.item_name, need.quantity, price, game_state.day, item_category)

                        if revenue > 0:
                            daily_sales[supplier.name] += revenue
                            daily_profits[supplier.name] += profit
                            total_spent += revenue

                            # Track per-item sales
                            if need.item_name not in per_item_sales[supplier.name]:
                                per_item_sales[supplier.name][need.item_name] = {
                                    'units_sold': 0,
                                    'revenue': 0.0,
                                    'starting_inventory': 0
                                }
                            per_item_sales[supplier.name][need.item_name]['units_sold'] += actual_units_sold
                            per_item_sales[supplier.name][need.item_name]['revenue'] += revenue

                            items_bought.append(f"{actual_units_sold}x {need.item_name}")

            if items_bought:
                special_customer_events.append((
                    customer_type_display,
                    supplier.name,
                    f"Bought: {', '.join(items_bought[:3])}{'...' if len(items_bought) > 3 else ''} (${total_spent:.2f})"
                ))
            else:
                special_customer_events.append((
                    customer_type_display,
                    supplier.name,
                    "Visited but couldn't find desired items"
                ))

    # Step 5.7: Calculate actual profits (Sales - Daily Spending, before wages)
    for player in game_state.players:
        daily_profits[player.name] = daily_sales[player.name] - daily_spending[player.name]

    # Step 5.6: Award XP based on sales (every $5 of sales = 1 XP)
    level_ups = {}
    for player in game_state.players:
        sales = daily_sales[player.name]
        if sales > 0:
            # Every $5 of sales = 1 XP
            sales_xp = sales / 5.0
            leveled_up = player.add_experience(sales_xp)
            if leveled_up:
                level_ups[player.name] = player.store_level

    # Step 6: Pay employee wages (monthly - every 30 days)
    for player in game_state.players:
        wages = player.pay_monthly_wages(game_state.day)
        total_employees = player.restockers + player.marketing_agents
        if show_details and wages > 0:
            print(f"  {player.name}: ${wages:.2f} MONTHLY WAGE ({player.restockers} warehouse workers, {player.marketing_agents} marketing agents)")
        elif show_details and total_employees > 0:
            days_until_payment = 30 - (game_state.day - player.last_wage_payment_day)
            print(f"  {player.name}: No payment today ({days_until_payment} days until next wage)")

    # Step 7: Print daily summary
    if show_details:
        print(f"\nDaily Results:")
        for player in game_state.players:
            sales = daily_sales[player.name]
            profit = daily_profits[player.name]
            served = customers_served[player.name]
            allocated_served = allocated_customers_served[player.name]
            allocated_assigned = allocated_customers_assigned[player.name]
            overflow_served = overflow_customers_served[player.name]
            uncapped_served = uncapped_customers_served[player.name]
            xp_needed = player.get_xp_for_next_level()

            # Calculate total items sold
            total_items_sold = sum(
                data['units_sold']
                for data in per_item_sales[player.name].values()
            )

            # Main stats line
            uncapped_text = f", 💎{uncapped_served}" if uncapped_customer_count > 0 and uncapped_served > 0 else ""
            level_up_text = f" 🎉LVL{level_ups[player.name]}!" if player.name in level_ups else ""
            print(f"  {player.name}: Sales ${sales:.2f}, Profit ${profit:.2f}, Lvl {player.store_level} ({player.experience:.0f}/{xp_needed:.0f}XP){level_up_text}, Cust {served} (A:{allocated_served}/{allocated_assigned}, O:{overflow_served}{uncapped_text}), Items {total_items_sold}, Cash ${player.cash:.2f}")

            # Show per-category sales breakdown
            if per_item_sales[player.name]:
                # Create item name to category mapping
                item_to_category = {item.name: item.category for item in game_state.items}

                # Aggregate sales by category
                category_sales = {}
                for item_name, data in per_item_sales[player.name].items():
                    if data['units_sold'] > 0:
                        category = item_to_category.get(item_name, "Unknown")
                        category_sales[category] = category_sales.get(category, 0) + data['units_sold']

                if category_sales:
                    categories_breakdown = [f"{cat}: {qty}" for cat, qty in sorted(category_sales.items())]
                    print(f"    Sales: {', '.join(categories_breakdown)}")

            # Show inventory by category (end of day)
            if player.inventory:
                # Create item name to category mapping (reuse if already created above)
                if 'item_to_category' not in locals():
                    item_to_category = {item.name: item.category for item in game_state.items}

                # Aggregate inventory by category
                category_inventory = {}
                for item_name, qty in player.inventory.items():
                    category = item_to_category.get(item_name, "Unknown")
                    category_inventory[category] = category_inventory.get(category, 0) + qty

                inventory_items = [f"{cat}: {qty}" for cat, qty in sorted(category_inventory.items())]
                # Add inventory space used from buy orders
                inv_used = daily_inventory_used[player.name]
                if inv_used > 0:
                    print(f"    Inv: {', '.join(inventory_items)} (bought: {inv_used:.1f} space)")
                else:
                    print(f"    Inv: {', '.join(inventory_items)}")

            # Show pricing by category (% below market)
            if player.category_pricing:
                pricing_items = [f"{cat}: {pct:.0f}%" for cat, pct in sorted(player.category_pricing.items())]
                print(f"    Price: {', '.join(pricing_items)}")

        if unmet_demand > 0:
            print(f"\nUnmet regular demand: {unmet_demand} items")
        if unmet_uncapped_demand > 0:
            print(f"Unmet uncapped demand: {unmet_uncapped_demand} items")

        # Display customer type statistics
        print(f"\nCustomer Types Today:")
        for ctype in ['low', 'medium', 'high']:
            spawned = customer_type_stats['spawned'][ctype]
            if spawned > 0:
                bought = customer_type_stats['bought_something'][ctype]
                found_nothing = customer_type_stats['found_nothing'][ctype]
                print(f"  {ctype.replace('_', ' ').title()}: {spawned} spawned | {bought} bought | {found_nothing} found nothing")

        # Display special customer events
        if special_customer_events:
            print(f"\n🌟 Special Customers Today ({len(special_customer_events)} spawned):")
            for customer_type, target_name, details in special_customer_events:
                print(f"  {customer_type} → {target_name}: {details}")

        # Display demand per item (what customers wanted today)
        if daily_demand_per_item:
            print(f"\nItem Demand Today (Total Quantity Wanted):")
            # Sort by demand (highest first), then by item name
            sorted_demand = sorted(daily_demand_per_item.items(), key=lambda x: (-x[1], x[0]))
            # Show 7 items per line
            items_per_line = 7
            for i in range(0, len(sorted_demand), items_per_line):
                line_items = sorted_demand[i:i+items_per_line]
                formatted_items = [f"{item_name}: {quantity}" for item_name, quantity in line_items]
                print(f"  {', '.join(formatted_items)}")

    # Update item demand for next day (after everything has sold)
    updated_items = update_item_demand(game_state)
    if show_details and updated_items:
        print(f"\n📊 DEMAND UPDATE: {len(updated_items)} items had demand changes")
        # Show demand changes in compact format (5 items per line)
        demand_changes = [(item_name, game_state.item_demand[item_name]) for item_name in updated_items]
        items_per_line = 5
        for i in range(0, len(demand_changes), items_per_line):
            line_items = demand_changes[i:i+items_per_line]
            formatted_items = []
            for item_name, demand in line_items:
                if demand >= 1.5:
                    emoji = "📈"
                elif demand <= 0.5:
                    emoji = "📉"
                else:
                    emoji = "➡️"
                formatted_items.append(f"{emoji}{item_name}:{demand:.2f}x")
            print(f"   {' | '.join(formatted_items)}")

    # Apply price fluctuations for next day (before other end-of-day processing)
    # Done here so we can display it near demand changes
    price_changes = apply_daily_price_fluctuation(game_state.market_prices, game_state.items)

    # Update all player prices based on their category pricing rules
    items_by_name = {item.name: item for item in game_state.items}
    for player in game_state.players:
        player.update_prices_from_market(game_state.market_prices, items_by_name)

    if show_details and price_changes:
        print(f"\n💰 MARKET PRICE UPDATE: {len(price_changes)} items had price changes")
        for item_name, old_price, new_price, change_percent in price_changes:
            if change_percent > 0:
                emoji = "📈"
            elif change_percent < 0:
                emoji = "📉"
            else:
                emoji = "➡️"
            print(f"   {emoji} {item_name}: ${old_price:.2f} → ${new_price:.2f} ({change_percent:+.1f}%)")

    # Unlock new products every 10 days (at end of day, so players can buy them next day)
    if game_state.day % 10 == 0 and game_state.day > 0:
        new_products = []
        for _ in range(5):
            new_product = unlock_new_product(game_state)
            if new_product:
                new_products.append(new_product)

        if new_products and show_details:
            print(f"\n🎁 NEW PRODUCTS UNLOCKED ({len(new_products)} items):")
            for product in new_products:
                print(f"   - {product.name} (${product.base_price:.2f})")
            print(f"   Total products available: {len(game_state.items)}")

    # Step 7.8: Apply daily reputation changes with limits and decay
    import math

    # Collect data for table displays
    reputation_data = []
    cas_data = []

    for player in game_state.players:
        # Apply daily reputation changes from customer interactions
        rep_change = daily_reputation_changes[player.name]

        # Limit negative changes to -5 max per day
        if rep_change < -5:
            rep_change = -5
        # Limit positive changes to +25 max per day
        if rep_change > 25:
            rep_change = 25

        # Additional penalties (applied separately from customer interaction cap)
        # Penalty: -5 reputation if stock is completely empty
        total_stock = sum(player.inventory.values())
        if total_stock == 0:
            rep_change -= 5

        # Penalty: -5 reputation if average fulfillment is below 30%
        if player.average_fulfillment_pct < 30.0:
            rep_change -= 5

        # Apply the total change
        player.reputation += rep_change

        # Apply 5% decay (rounded up) for positive reputation only
        decay_amount = 0
        if player.reputation > 0:
            decay_amount = math.ceil(player.reputation * 0.05)
            player.reputation -= decay_amount
            # Ensure we don't go below 0 from decay
            if player.reputation < 0:
                player.reputation = 0

        # Ensure reputation stays within bounds [-100, 100]
        player.reputation = max(-100, min(100, player.reputation))

        fulfillment_data = daily_fulfillment_data[player.name]
        visit_counts = {
            "allocated": len(fulfillment_data.get("allocated", [])),
            "overflow": len(fulfillment_data.get("overflow", [])),
        }

        # Update fulfillment averages based on today's data
        update_player_fulfillment_averages(player, fulfillment_data)
        has_fulfillment_data = bool(
            fulfillment_data["allocated"] or fulfillment_data["overflow"]
        )

        # Collect reputation/fulfillment data for table display
        if show_details:
            reputation_data.append({
                'name': player.name,
                'reputation': player.reputation,
                'rep_change': rep_change,
                'decay': decay_amount,
                'avg_fulfillment': player.average_fulfillment_pct,
                'allocated_avg': player.allocated_average_fulfillment_pct,
                'allocated_count': visit_counts["allocated"],
                'overflow_avg': player.overflow_average_fulfillment_pct,
                'overflow_count': visit_counts["overflow"],
                'total_customers': visit_counts["allocated"] + visit_counts["overflow"],
                'has_fulfillment': has_fulfillment_data
            })

            # Collect CAS data (using pre-shopping data)
            breakdown = cas_breakdowns_pre_shopping.get(player.name)
            if breakdown:
                cas_data.append({
                    'name': player.name,
                    'reputation': breakdown["reputation"],
                    'discount_pct': breakdown["total_discount_pct"],
                    'discount_score': breakdown["discount_score"],
                    'items_counted': breakdown["items_counted"],
                    'stability': breakdown["item_stability"],
                    'marketing': breakdown["marketing_effect"],
                    'marketing_agents': breakdown["marketing_agents"],
                    'specialty_mult': breakdown["specialty_multiplier"],
                    'specialty_mult_raw': breakdown["specialty_multiplier_raw"],
                    'fulfill_mult': breakdown["fulfillment_multiplier"],
                    'fulfill_pct': breakdown["fulfillment_pct"],
                    'final_cas': breakdown["final_cas"]
                })

    # Display reputation and fulfillment table
    if show_details and reputation_data:
        print("\n📊 Reputation & Fulfillment:")
        for data in reputation_data:
            decay_text = f" (decay: -{data['decay']})" if data['decay'] > 0 else ""
            change_text = f" ({data['rep_change']:+d}{decay_text})" if (data['rep_change'] != 0 or data['decay'] > 0) else ""
            fulfillment_text = ""
            if data['has_fulfillment']:
                fulfillment_text = f" | Avg: {data['avg_fulfillment']:.1f}% ({data['total_customers']} cust: Alloc {data['allocated_avg']:.1f}%/{data['allocated_count']}, Ovrf {data['overflow_avg']:.1f}%/{data['overflow_count']})"
            print(f"  {data['name']}: Rep {data['reputation']:.0f}{change_text}{fulfillment_text}")

    # Display CAS table
    if show_details and cas_data:
        print("\n🎯 Customer Attraction Score (CAS):")
        for data in cas_data:
            marketing_text = f", Mkt: {data['marketing']:.1f}" if data['marketing'] > 0 else ""
            specialty_text = f"{data['specialty_mult']:.2f}x"
            if data['specialty_mult_raw'] > 0:
                specialty_text += f" (+{data['specialty_mult_raw']:.2f})"
            print(f"  {data['name']}: CAS={data['final_cas']:.1f} | Rep: {data['reputation']:.0f}, Disc: {data['discount_pct']:.1f}%, Stab: {data['stability']:.1f}{marketing_text}, Spec: {specialty_text}, Fulfill: {data['fulfill_mult']:.2f}x ({data['fulfill_pct']:.0f}%)")

    # Step 8: Refresh vendor inventory for next day
    # Done at END of day so buy orders are set for current vendor inventory
    refresh_vendor_inventory(game_state.vendors, game_state.items, game_state.market_prices)

    # Step 9: Advance day counter
    game_state.day += 1

    # Step 9.25: Process pending deliveries for all players
    delivery_summary = {}  # Track deliveries per player for consolidated output

    for player in game_state.players:
        deliveries_to_process = []
        remaining_deliveries = []

        for delivery in player.pending_deliveries:
            item_name, quantity, cost_per_item, delivery_day = delivery
            if delivery_day <= game_state.day:
                # Delivery has arrived
                deliveries_to_process.append(delivery)
            else:
                # Still in transit
                remaining_deliveries.append(delivery)

        # Process deliveries that have arrived
        player_deliveries = []
        for delivery in deliveries_to_process:
            item_name, quantity, cost_per_item, delivery_day = delivery

            # Update weighted average cost
            current_inventory = player.inventory.get(item_name, 0)
            current_cost = player.item_costs.get(item_name, 0)

            # Weighted average: (old_qty * old_cost + new_qty * new_cost) / total_qty
            new_total_qty = current_inventory + quantity
            if new_total_qty > 0:
                weighted_cost = ((current_inventory * current_cost) + (quantity * cost_per_item)) / new_total_qty
                player.item_costs[item_name] = weighted_cost

            # Track if this is the first time stocking this item today
            if current_inventory == 0 and quantity > 0:
                player.items_stocked_today.add(item_name)

            player.inventory[item_name] = new_total_qty

            if player.is_human:
                player_deliveries.append(f"{quantity}x {item_name}")

        # Track deliveries for this player
        if player.is_human and player_deliveries:
            delivery_summary[player.name] = player_deliveries

        # Update pending deliveries list
        player.pending_deliveries = remaining_deliveries

    # Print consolidated delivery notifications
    if show_details and delivery_summary:
        for player_name, deliveries in delivery_summary.items():
            print(f"\n📦 Deliveries for {player_name}: {', '.join(deliveries)}")

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

    # Display loan warnings for human players
    for player in game_state.players:
        if player.is_human and player.loans and show_details:
            for loan in player.loans:
                days_remaining = loan.due_day - game_state.day
                if days_remaining <= 0:
                    print(f"\n💸 WARNING: {player.name}'s loan from {loan.lender_name} is OVERDUE!")
                    print(f"    Amount due: ${loan.remaining_balance:,.2f}")
                elif days_remaining <= 5:
                    print(f"\n⏰ REMINDER: {player.name}'s loan from {loan.lender_name} is due in {days_remaining} days")
                    print(f"    Amount due: ${loan.remaining_balance:,.2f}")

    # Step 10: Save yesterday's demand per item for each player (used for lead time calculations)
    # Use global demand (what all customers wanted) rather than individual sales (which may be limited by stock)
    for player in game_state.players:
        player.yesterday_demand = dict(daily_demand_per_item)  # Copy the global demand data

    # Step 11: Reset daily vendor purchase tracking
    game_state.vendor_daily_purchases.clear()

    return daily_sales


# -------------------------------------------------------------------
# Interactive menu system
# -------------------------------------------------------------------

def calculate_item_stability(player: Player, market_prices: Dict[str, float], items_by_name: Dict[str, Item]) -> float:
    """
    Calculate item stability score to reward pricing close to market price and consistent pricing.

    Formula:
    For each item with stock:
    1. Price proximity score:
       - Starts at 5 if at exact market price (0% difference)
       - Decreases by 1 for each 1% difference from market price
       - Minimum of 0
    2. Consistency bonus:
       - +2 if price hasn't changed more than ±5% from previous price
    3. Multiply by item importance (1, 2, or 3)
    4. Sum all items

    Returns: Total item stability score
    """
    total_stability = 0.0

    for item_name, qty in player.inventory.items():
        # Only consider items with stock and set prices
        if qty <= 0 or item_name not in player.prices:
            continue

        player_price = player.prices[item_name]
        market_price = market_prices.get(item_name, 0)

        # Skip if no market price
        if market_price <= 0:
            continue

        # Get item importance
        item = items_by_name.get(item_name)
        importance = item.importance if item else 2

        # Calculate price difference percentage
        price_diff_pct = abs((player_price - market_price) / market_price) * 100

        # Calculate proximity score: 5 at market price, -1 per 1% difference
        proximity_score = max(0, 5 - price_diff_pct)

        # Calculate consistency bonus
        consistency_bonus = 0.0
        if item_name in player.price_history:
            prev_price = player.price_history[item_name]
            if prev_price > 0:
                price_change_pct = abs((player_price - prev_price) / prev_price) * 100
                if price_change_pct <= 5:
                    consistency_bonus = 2.0

        # Combine and weight by importance
        item_stability = (proximity_score + consistency_bonus) * importance
        total_stability += item_stability

    return total_stability


def calculate_marketing_effect(player: Player, market_prices: Dict[str, float]) -> float:
    """
    Calculate marketing effect from Marketing Agents.

    Formula:
    - Base effect: +1 for every 2 reputation (max +50 at reputation 100)
    - Item price scaling: + (highest_market_price_in_stock / 10), rounded down

    Marketing effect is only active if player has marketing agents.
    Returns: Marketing effect bonus (0 if no marketing agents)
    """
    if player.marketing_agents <= 0:
        return 0.0

    # Reputation bonus: +1 per 2 reputation, max 50
    reputation_bonus = min(50, player.reputation / 2)

    # Find highest market price among items in stock
    highest_price = 0.0
    for item_name, qty in player.inventory.items():
        if qty > 0:
            market_price = market_prices.get(item_name, 0)
            if market_price > highest_price:
                highest_price = market_price

    # Price scaling bonus: highest_price / 10, rounded down
    price_bonus = int(highest_price / 10)

    return reputation_bonus + price_bonus


def calculate_specialty_score(player: Player, items_by_name: Dict[str, Item]) -> Tuple[float, Dict[str, int], Dict[str, float]]:
    """
    Calculate specialty score multiplier based on category item counts.

    Rewards players for stocking a certain number of items from specific categories.
    Bonuses are ADDITIVE: 1.2x (20% bonus) + 1.8x (80% bonus) = 2.0x total (100% bonus).

    Returns:
        - Total specialty multiplier (1.0 + sum of all bonus percentages)
        - Dictionary of category -> count of items in stock
        - Dictionary of category -> total bonus multiplier for that category
    """
    # Count items in stock per category
    category_counts: Dict[str, int] = {}

    for item_name, qty in player.inventory.items():
        if qty <= 0:
            continue

        item = items_by_name.get(item_name)
        if not item:
            continue

        category = item.category
        category_counts[category] = category_counts.get(category, 0) + 1

    # Calculate specialty bonuses for each category
    category_multipliers: Dict[str, float] = {}
    total_bonus = 0.0  # Sum of bonus percentages (not full multipliers)

    for category, count in category_counts.items():
        thresholds = SPECIALTY_SCORE_THRESHOLDS.get(category, [])
        category_bonus = 0.0

        # Sum all BONUSES for thresholds met (bonus = multiplier - 1.0)
        for threshold, multiplier in thresholds:
            if count >= threshold:
                bonus = multiplier - 1.0  # Extract the bonus percentage
                category_bonus += bonus

        if category_bonus > 0:
            category_total_mult = 1.0 + category_bonus  # Convert back to multiplier for display
            category_multipliers[category] = category_total_mult
            total_bonus += category_bonus

    total_multiplier = 1.0 + total_bonus
    return total_multiplier, category_counts, category_multipliers


def calculate_cas_breakdown(player: Player, market_prices: Dict[str, float], items_by_name: Dict[str, Item], all_available_items: List[Item], current_day: int = 1) -> Dict[str, Any]:
    """
    Calculate Customer Attraction Score (CAS) breakdown for a player.
    Returns a dictionary with all CAS components.
    """
    # Calculate reputation multiplier
    reputation_multiplier = 10 ** (player.reputation / 100)

    # Calculate discount score (sum across all stocked items)
    discount_score = 0.0
    total_discount_pct = 0.0
    items_counted = 0
    if player.inventory and player.prices:
        for item_name, qty in player.inventory.items():
            if qty > 0 and item_name in player.prices:
                market_price = market_prices.get(item_name, 0)
                if market_price > 0:
                    player_price = player.prices[item_name]
                    # Get item importance
                    item = next((i for i in all_available_items if i.name == item_name), None)
                    importance = item.importance if item else 2

                    # Calculate discount percentage
                    if player_price < market_price:
                        discount_pct = ((market_price - player_price) / market_price) * 100
                    else:
                        discount_pct = 0

                    total_discount_pct += discount_pct
                    discount_score += discount_pct * importance
                    items_counted += 1

    # Calculate item stability score
    item_stability = calculate_item_stability(player, market_prices, items_by_name)

    # Calculate specialty score (category-based bonuses for item variety)
    specialty_multiplier_effective, category_counts, category_multipliers = calculate_specialty_score(player, items_by_name)

    # Calculate fulfillment multiplier
    fulfillment_pct = player.average_fulfillment_pct
    if fulfillment_pct >= 100:
        fulfillment_multiplier = 2.0
    elif fulfillment_pct >= 90:
        fulfillment_multiplier = 1.4
    elif fulfillment_pct > 70:
        fulfillment_multiplier = 1.1
    elif fulfillment_pct >= 50:
        fulfillment_multiplier = 1.0
    elif fulfillment_pct >= 20:
        fulfillment_multiplier = 0.9
    elif fulfillment_pct >= 10:
        fulfillment_multiplier = 0.5
    else:
        fulfillment_multiplier = 0.1

    # Calculate marketing effect
    marketing_effect = calculate_marketing_effect(player, market_prices)

    # Calculate adjacency multiplier (penalty for non-adjacent categories)
    adjacency_multiplier = calculate_adjacency_multiplier(player, items_by_name, current_day, check_temporary=True)

    # Get non-adjacent categories for display
    non_adjacent_categories = get_non_adjacent_categories(player, items_by_name, current_day)
    main_category = get_player_main_category(player, current_day)

    # Calculate final CAS
    final_cas = (discount_score + marketing_effect + item_stability + marketing_effect) * reputation_multiplier * specialty_multiplier_effective * fulfillment_multiplier * adjacency_multiplier

    # Return all components as a dictionary
    return {
        "reputation": player.reputation,
        "discount_score": discount_score,
        "total_discount_pct": total_discount_pct,
        "items_counted": items_counted,
        "item_stability": item_stability,
        "marketing_effect": marketing_effect,
        "marketing_agents": player.marketing_agents,
        "specialty_multiplier": specialty_multiplier_effective,
        "specialty_multiplier_raw": specialty_multiplier_effective - 1.0,  # Just the bonus amount
        "category_counts": category_counts,
        "category_multipliers": category_multipliers,
        "fulfillment_multiplier": fulfillment_multiplier,
        "fulfillment_pct": fulfillment_pct,
        "adjacency_multiplier": adjacency_multiplier,
        "non_adjacent_categories": non_adjacent_categories,
        "main_category": main_category,
        "final_cas": final_cas
    }


def display_cas_breakdown(player: Player, game_state: GameState, breakdown: Dict[str, Any] = None) -> None:
    """Display Customer Attraction Score (CAS) breakdown for a player."""
    print(f"\n🎯 {player.name} - Customer Attraction Score (CAS):")

    # Use pre-calculated breakdown if provided, otherwise calculate it
    if breakdown is None:
        # Build items_by_name dict for item_stability calculation
        items_by_name = {item.name: item for item in game_state.items}
        breakdown = calculate_cas_breakdown(player, game_state.market_prices, items_by_name, game_state.items, game_state.day)

    # Extract values from breakdown
    discount_score = breakdown["discount_score"]
    total_discount_pct = breakdown["total_discount_pct"]
    items_counted = breakdown["items_counted"]
    item_stability = breakdown["item_stability"]
    marketing_effect = breakdown["marketing_effect"]
    marketing_agents = breakdown["marketing_agents"]
    specialty_multiplier = breakdown["specialty_multiplier"]
    specialty_multiplier_raw = breakdown["specialty_multiplier_raw"]
    category_counts = breakdown["category_counts"]
    category_multipliers = breakdown["category_multipliers"]
    fulfillment_multiplier = breakdown["fulfillment_multiplier"]
    fulfillment_pct = breakdown["fulfillment_pct"]
    adjacency_multiplier = breakdown.get("adjacency_multiplier", 1.0)
    non_adjacent_categories = breakdown.get("non_adjacent_categories", set())
    main_category = breakdown.get("main_category", None)
    final_cas = breakdown["final_cas"]
    reputation = breakdown["reputation"]

    # Display compact breakdown
    print(f"   Reputation:              {reputation:.0f}")
    print(f"   Discount Score:          {total_discount_pct:.1f}% total across {items_counted} items (importance: {discount_score:.2f})")
    print(f"   Item Stability:          {item_stability:.2f}")
    if marketing_effect > 0:
        print(f"   Marketing Effect:        {marketing_effect:.2f} ({marketing_agents} agents)")

    # Display specialty score with category breakdown
    print(f"   Specialty Multiplier:    {specialty_multiplier:6.2f}x  (base 1.0 + {specialty_multiplier_raw:.2f} bonus)")
    if category_multipliers:
        print(f"      Category Bonuses:")
        for category, multiplier in sorted(category_multipliers.items(), key=lambda x: x[1], reverse=True):
            count = category_counts.get(category, 0)
            bonus = multiplier - 1.0  # Convert full multiplier to bonus for display
            print(f"        • {category}: {count} items → +{bonus:.2f}x")

    print(f"   Fulfillment Multiplier:  {fulfillment_multiplier:6.2f}x  ({fulfillment_pct:.0f}% avg)")

    # Display adjacency multiplier information
    print(f"   Adjacency Multiplier:    {adjacency_multiplier:6.2f}x", end="")
    if main_category:
        print(f"  (main: {main_category})")
        if non_adjacent_categories:
            print(f"      Non-adjacent categories: {', '.join(sorted(non_adjacent_categories))}")
    else:
        print("  (no main category yet)")

    print(f"   ─────────────────────────────────────────")
    print(f"   📈 FINAL CAS = {final_cas:.2f}")


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

        # Display lead time
        if vendor.lead_time > 0:
            print(f"   Lead Time: {vendor.lead_time} day(s)")
        else:
            print(f"   Lead Time: Instant delivery")

        # Display minimum purchase requirement if it exists
        if vendor.min_purchase is not None:
            print(f"   MINIMUM BUY: {vendor.min_purchase} units per purchase")

    print("=" * 80)


def display_player_status(player: Player, game_state: GameState = None) -> None:
    """Display the player's current status."""
    print("\n" + "=" * 60)
    print(f"YOUR STORE: {player.name}")
    print("=" * 60)
    print(f"Cash: ${player.cash:.2f}")

    xp_needed = player.get_xp_for_next_level()
    print(f"\nStore Level: {player.store_level}")
    print(f"Experience: {player.experience:.0f}/{xp_needed:.0f} XP")

    print(f"\nEmployees:")
    print(f"  Warehouse Workers: {player.restockers} (Max inventory: {player.get_max_inventory()} items)")
    print(f"  Marketing Agents: {player.marketing_agents} (Boost customer attraction)")
    total_employees = player.restockers + player.marketing_agents
    monthly_wage = 1000.0
    wage_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "wage_reduction")
    actual_wage = max(0, monthly_wage - wage_reduction)
    print(f"  Monthly wages: ${total_employees * actual_wage:.2f} (${actual_wage:.2f}/employee)")

    if game_state:
        inventory_size_used = player.get_inventory_size_used(game_state.items_by_name)
        total_items = sum(player.inventory.values())
        num_products = len([i for i, q in player.inventory.items() if q > 0])
        print(f"\nInventory ({inventory_size_used:.1f}/{player.get_max_inventory()} space, {total_items} items, {num_products} products):")
    else:
        total_items = sum(player.inventory.values())
        num_products = len([i for i, q in player.inventory.items() if q > 0])
        print(f"\nInventory ({total_items} items, {num_products} different products):")
    if player.inventory:
        for item_name, quantity in player.inventory.items():
            if quantity > 0:
                print(f"  {item_name}: {quantity} units")
    else:
        print("  (empty)")

    # Display pending deliveries if any
    if player.pending_deliveries:
        print(f"\n📦 Pending Deliveries:")
        # Group deliveries by item for cleaner display
        delivery_summary = {}
        for item_name, quantity, cost, delivery_day in player.pending_deliveries:
            if item_name not in delivery_summary:
                delivery_summary[item_name] = []
            delivery_summary[item_name].append((quantity, delivery_day))

        for item_name, deliveries in sorted(delivery_summary.items()):
            for quantity, delivery_day in sorted(deliveries, key=lambda x: x[1]):
                days_remaining = delivery_day - (game_state.day if game_state else 0)
                print(f"  {item_name}: {quantity} units (arrives in {days_remaining} day(s))")

    print(f"\nYour Prices:")
    if player.prices:
        for item_name, price in player.prices.items():
            print(f"  {item_name}: ${price:.2f}")
    else:
        print("  (no prices set)")

    # Add reputation display
    print(f"\n📊 Reputation: {player.reputation:.0f}/100")
    print(f"   Average Fulfillment: {player.average_fulfillment_pct:.1f}%")

    # Add CAS display if game_state is provided
    if game_state:
        display_cas_breakdown(player, game_state)

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
            requirements = []
            if vendor.required_reputation:
                requirements.append(f"{vendor.required_reputation:.0f} reputation")
            if vendor.required_level:
                requirements.append(f"level {vendor.required_level}")

            req_info = f" (Requires {', '.join(requirements)})" if requirements else ""

            # Check if vendor is locked
            rep_locked = vendor.required_reputation and player.reputation < vendor.required_reputation
            level_locked = vendor.required_level and player.store_level < vendor.required_level
            locked = " [LOCKED]" if (rep_locked or level_locked) else ""

            print(f"  {i}. {vendor.name}{req_info}{locked}")
        print(f"  0. Back to Main Menu")

        try:
            choice = input("\nSelect vendor (0-{}): ".format(len(game_state.vendors)))
            choice_num = int(choice)

            if choice_num == 0:
                break

            if 1 <= choice_num <= len(game_state.vendors):
                vendor = game_state.vendors[choice_num - 1]

                # Check reputation requirement
                if vendor.required_reputation and player.reputation < vendor.required_reputation:
                    print(f"\n✗ You need {vendor.required_reputation:.0f} reputation to use this vendor. Your reputation: {player.reputation:.0f}")
                    continue

                # Check level requirement
                if vendor.required_level and player.store_level < vendor.required_level:
                    print(f"\n✗ You need level {vendor.required_level} to use this vendor. Your level: {player.store_level}")
                    continue

                # Show volume pricing info if applicable
                if vendor.volume_pricing_tiers:
                    print(f"\n{vendor.name} - Volume Pricing Tiers:")
                    print(f"  Base: {vendor.pricing_multiplier*100:.0f}% of market price")
                    for threshold, multiplier in sorted(vendor.volume_pricing_tiers, key=lambda x: x[0]):
                        print(f"  {threshold}+ items: {multiplier*100:.0f}% of market price")

                # Show items available from this vendor
                print(f"\n{vendor.name} - Available Items (showing base prices):")
                available_items = []
                for i, item in enumerate(game_state.items, 1):
                    price = vendor.get_price(item.name, 1)  # Show base price (quantity=1)
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

                        # Calculate and show the actual price with volume discount
                        actual_price_per_unit = player.get_production_line_price(selected_item_name, market_price)
                        if actual_price_per_unit is None:
                            actual_price_per_unit = vendor.get_price(selected_item_name, quantity)
                        total_cost = actual_price_per_unit * quantity

                        print(f"\nTotal cost: ${total_cost:.2f} (${actual_price_per_unit:.2f} per unit)")

                        success = player.purchase_from_vendor(vendor, selected_item_name, quantity, market_price, game_state)
                        if success:
                            print(f"\n✓ Purchased {quantity} {selected_item_name} for ${total_cost:.2f}")
                        else:
                            # More detailed error message
                            if vendor.min_purchase and quantity < vendor.min_purchase:
                                print(f"\n✗ Failed to purchase. Minimum purchase: {vendor.min_purchase} units")
                            elif player.cash < total_cost:
                                print(f"\n✗ Failed to purchase. Not enough cash! Need ${total_cost:.2f}, have ${player.cash:.2f}")
                            else:
                                print(f"\n✗ Failed to purchase. Check requirements!")
                    else:
                        print("\n✗ Invalid quantity!")
            else:
                print("\n✗ Invalid vendor selection!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def configure_orders_and_prices_menu(game_state: GameState, player: Player) -> None:
    """Combined menu for configuring buy orders and sell prices."""
    while True:
        print("\n" + "=" * 120)
        print("CONFIGURE BUY ORDERS AND SALE PRICES")
        print("=" * 120)

        # Build table data
        print(f"\n{'Item':<15} {'Qty':>6} {'Market':>8} {'Buy Qty':>8} {'Vendors (qty each)':>40} {'Vend $':>8} {'Sell $':>8}")
        print("-" * 140)

        for item in game_state.items:
            # Get current inventory quantity
            inv_qty = player.inventory.get(item.name, 0)
            qty_str = str(inv_qty) if inv_qty > 0 else ""

            # Get market price
            market_price = game_state.market_prices.get(item.name, 0)

            # Get buy order info (now supports multiple vendors)
            vendor_orders = player.get_buy_order(item.name)
            order_qty = sum(q for q, v in vendor_orders)

            # Display vendor info with quantities
            if len(vendor_orders) == 0:
                vendor_display = "-"
            elif len(vendor_orders) == 1:
                qty, vendor_name = vendor_orders[0]
                vendor_display = f"{vendor_name[:20]} ({qty})"
            else:
                # Multiple vendors: show abbreviated names with quantities
                vendor_parts = []
                for qty, vendor_name in vendor_orders:
                    # Abbreviate vendor name to fit multiple
                    abbrev = vendor_name[:12] if len(vendor_name) > 12 else vendor_name
                    vendor_parts.append(f"{abbrev}({qty})")
                vendor_display = ", ".join(vendor_parts)

            # Get cheapest vendor buy price for reference
            vendor_buy_price = 0.0
            own_price = player.get_production_line_price(item.name, market_price)
            if own_price is not None:
                vendor_buy_price = own_price
            elif vendor_orders:
                # Find cheapest vendor price among all orders (using their ordered quantities)
                cheapest_price = float('inf')
                for qty, vendor_name in vendor_orders:
                    for vendor in game_state.vendors:
                        if vendor.name == vendor_name:
                            price = vendor.get_price(item.name, qty)  # Pass quantity for volume pricing
                            if price:
                                discount = player.get_vendor_discount(vendor_name, game_state.day)
                                actual_price = price * (1 - discount)
                                if actual_price < cheapest_price:
                                    cheapest_price = actual_price
                            break
                if cheapest_price < float('inf'):
                    vendor_buy_price = cheapest_price

            vendor_price_str = f"${vendor_buy_price:.2f}" if vendor_buy_price > 0 else "-"

            # Get sell price
            sell_price = player.prices.get(item.name, 0)
            sell_price_str = f"${sell_price:.2f}" if sell_price > 0 else "-"

            # Show ordered quantity in parentheses if no inventory
            if inv_qty == 0 and order_qty > 0:
                qty_str = f"({order_qty})"

            print(f"{item.name:<15} {qty_str:>6} ${market_price:>7.2f} {order_qty:>8} {vendor_display:>40} {vendor_price_str:>8} {sell_price_str:>8}")

        print("\nOptions:")
        print("  b. Configure Buy Order (select item)")
        print("  0. Back to Main Menu")
        print("\nNote: Set prices by category in the Pricing Menu (option 6 from main menu)")

        try:
            choice = input("\nSelect option (b/0): ").strip().lower()

            if choice == '0':
                break
            elif choice == 'b':
                # Configure buy order (multi-vendor support)
                # Wrap in a loop so user can configure multiple items without going back to main menu
                while True:
                    print("\nSelect item to configure buy order:")
                    for i, item in enumerate(game_state.items, 1):
                        print(f"  {i}. {item.name}")
                    print("  0. Back to main menu")

                    item_choice = input(f"\nSelect item (0-{len(game_state.items)}): ")
                    try:
                        item_num = int(item_choice)
                    except ValueError:
                        print("\n✗ Invalid input!")
                        continue

                    if item_num == 0:
                        break

                    if 1 <= item_num <= len(game_state.items):
                        item = game_state.items[item_num - 1]

                        # Item configuration submenu (supports up to 3 vendors)
                        while True:
                            print(f"\n{'='*80}")
                            print(f"Configuring Buy Orders for: {item.name}")
                            print(f"{'='*80}")

                            vendor_orders = player.get_buy_order(item.name)
                            print(f"\nCurrent orders ({len(vendor_orders)}/3 vendors):")
                            if vendor_orders:
                                for i, (qty, vendor_name) in enumerate(vendor_orders, 1):
                                    # Get vendor price and lead time
                                    vendor = next((v for v in game_state.vendors if v.name == vendor_name), None)
                                    if vendor:
                                        price = vendor.get_price(item.name, qty)  # Pass quantity for volume pricing
                                        # Calculate effective lead time with player's upgrades
                                        lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                                        effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                                        lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                                        price_str = f"${price:.2f}" if price else "N/A"
                                        print(f"  {i}. {vendor_name}: {qty} units @ {price_str} (lead: {lead_time_str})")
                            else:
                                print("  (no vendors configured)")

                            print(f"\nOptions:")
                            print(f"  1. Add/update vendor (max 3)")
                            if vendor_orders:
                                print(f"  2. Remove vendor")
                                print(f"  3. Clear all vendors")
                            if len(vendor_orders) < 3:
                                print(f"  4. Add multiple vendors at once")
                            print(f"  0. Back to item list")

                            sub_choice = input(f"\nSelect option: ").strip()

                            if sub_choice == "0":
                                break
                            elif sub_choice == "1":
                                # Add/update vendor
                                if len(vendor_orders) >= 3:
                                    print(f"\n⚠ Already have 3 vendors. Select a vendor to update:")
                                    for i, (qty, vendor_name) in enumerate(vendor_orders, 1):
                                        print(f"  {i}. {vendor_name}")
                                    print(f"  0. Cancel")

                                    update_choice = input(f"\nSelect vendor to update (0-{len(vendor_orders)}): ").strip()
                                    try:
                                        update_num = int(update_choice)
                                        if update_num == 0:
                                            continue
                                        elif 1 <= update_num <= len(vendor_orders):
                                            # User wants to update this vendor
                                            qty_to_update, vendor_to_update = vendor_orders[update_num - 1]
                                            print(f"\nUpdating: {vendor_to_update} (currently {qty_to_update} units)")

                                            # Show vendor list
                                            print("\nAvailable Vendors:")
                                            for i, vendor in enumerate(game_state.vendors, 1):
                                                price = vendor.get_price(item.name, 1)  # Show base price
                                                min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                                                vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                                                req_parts = []
                                                if vendor.required_reputation:
                                                    req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                                                if vendor.required_level:
                                                    req_parts.append(f"lvl: {vendor.required_level}")
                                                rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                                                # Calculate effective lead time with player's upgrades
                                                lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                                                effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                                                lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                                                if price:
                                                    discount = player.get_vendor_discount(vendor.name, game_state.day)
                                                    final_price = price * (1 - discount)
                                                    discount_text = f" (-{discount*100:.0f}%)" if discount > 0 else ""
                                                    print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ${final_price:.2f}{discount_text} (lead: {lead_time_str})")
                                                else:
                                                    status = "(not in stock today)" if vendor.selection_type == "random_daily" else "(not available)"
                                                    print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - {status}")

                                            vendor_choice = input(f"\nSelect new vendor (1-{len(game_state.vendors)}, 0 to cancel): ").strip()
                                            vendor_num = int(vendor_choice)
                                            if vendor_num == 0:
                                                continue
                                            elif 1 <= vendor_num <= len(game_state.vendors):
                                                selected_vendor = game_state.vendors[vendor_num - 1]

                                                quantity_str = input(f"Enter new quantity (0 to remove): ").strip()
                                                quantity = int(quantity_str)

                                                if quantity == 0:
                                                    # Remove this vendor
                                                    player.remove_vendor_from_buy_order(item.name, vendor_to_update)
                                                    print(f"\n✓ Removed {vendor_to_update} from buy order")
                                                elif quantity > 0:
                                                    # Check minimum purchase
                                                    if selected_vendor.min_purchase is not None and quantity < selected_vendor.min_purchase:
                                                        print(f"\n✗ {selected_vendor.name} requires minimum {selected_vendor.min_purchase} units")
                                                        input("Press Enter to continue...")
                                                        continue

                                                    # Remove old vendor and add new one
                                                    player.remove_vendor_from_buy_order(item.name, vendor_to_update)
                                                    player.add_vendor_to_buy_order(item.name, quantity, selected_vendor.name)
                                                    print(f"\n✓ Updated: {quantity} {item.name} from {selected_vendor.name}")
                                                else:
                                                    print("\n✗ Quantity must be non-negative!")
                                                    input("Press Enter to continue...")
                                        else:
                                            print("\n✗ Invalid selection!")
                                            input("Press Enter to continue...")
                                    except ValueError:
                                        print("\n✗ Invalid input!")
                                        input("Press Enter to continue...")
                                else:
                                    # Add new vendor
                                    print("\nAvailable Vendors:")
                                    for i, vendor in enumerate(game_state.vendors, 1):
                                        price = vendor.get_price(item.name, 1)  # Show base price
                                        min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                                        vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                                        req_parts = []
                                        if vendor.required_reputation:
                                            req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                                        if vendor.required_level:
                                            req_parts.append(f"lvl: {vendor.required_level}")
                                        rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                                        # Calculate effective lead time with player's upgrades
                                        lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                                        effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                                        lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                                        if price:
                                            discount = player.get_vendor_discount(vendor.name, game_state.day)
                                            final_price = price * (1 - discount)
                                            discount_text = f" (-{discount*100:.0f}%)" if discount > 0 else ""
                                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ${final_price:.2f}{discount_text} (lead: {lead_time_str})")
                                        else:
                                            status = "(not in stock today)" if vendor.selection_type == "random_daily" else "(not available)"
                                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - {status}")

                                    vendor_choice = input(f"\nEnter vendor number and quantity (e.g., '2 100'), or just vendor number (0 to cancel): ").strip()
                                    try:
                                        # Parse input - support both "vendor_num quantity" and just "vendor_num"
                                        parts = vendor_choice.split()
                                        vendor_num = int(parts[0])

                                        if vendor_num == 0:
                                            continue
                                        elif 1 <= vendor_num <= len(game_state.vendors):
                                            selected_vendor = game_state.vendors[vendor_num - 1]

                                            # Get quantity - either from second part or prompt
                                            if len(parts) >= 2:
                                                quantity = int(parts[1])
                                            else:
                                                quantity_str = input(f"Enter quantity to buy: ").strip()
                                                quantity = int(quantity_str)

                                            if quantity > 0:
                                                # Check minimum purchase
                                                if selected_vendor.min_purchase is not None and quantity < selected_vendor.min_purchase:
                                                    print(f"\n✗ {selected_vendor.name} requires minimum {selected_vendor.min_purchase} units")
                                                    input("Press Enter to continue...")
                                                    continue

                                                success = player.add_vendor_to_buy_order(item.name, quantity, selected_vendor.name)
                                                if success:
                                                    print(f"\n✓ Added: {quantity} {item.name} from {selected_vendor.name}")
                                                else:
                                                    print(f"\n✗ Failed to add vendor (limit reached or duplicate)")
                                                    input("Press Enter to continue...")
                                            else:
                                                print("\n✗ Quantity must be positive!")
                                                input("Press Enter to continue...")
                                        else:
                                            print("\n✗ Invalid vendor selection!")
                                            input("Press Enter to continue...")
                                    except ValueError:
                                        print("\n✗ Invalid input!")
                                        input("Press Enter to continue...")

                            elif sub_choice == "2" and vendor_orders:
                                # Remove vendor
                                print("\nSelect vendor to remove:")
                                for i, (qty, vendor_name) in enumerate(vendor_orders, 1):
                                    print(f"  {i}. {vendor_name} ({qty} units)")
                                print(f"  0. Cancel")

                                remove_choice = input(f"\nSelect vendor (0-{len(vendor_orders)}): ").strip()
                                try:
                                    remove_num = int(remove_choice)
                                    if remove_num == 0:
                                        continue
                                    elif 1 <= remove_num <= len(vendor_orders):
                                        qty, vendor_name = vendor_orders[remove_num - 1]
                                        player.remove_vendor_from_buy_order(item.name, vendor_name)
                                        print(f"\n✓ Removed {vendor_name} from buy order")
                                    else:
                                        print("\n✗ Invalid selection!")
                                        input("Press Enter to continue...")
                                except ValueError:
                                    print("\n✗ Invalid input!")
                                    input("Press Enter to continue...")

                            elif sub_choice == "3" and vendor_orders:
                                # Clear all vendors
                                player.clear_buy_order(item.name)
                                print(f"\n✓ Cleared all buy orders for {item.name}")

                            elif sub_choice == "4" and len(vendor_orders) < 3:
                                # Add multiple vendors at once
                                print("\nAvailable Vendors:")
                                for i, vendor in enumerate(game_state.vendors, 1):
                                    price = vendor.get_price(item.name, 1)  # Show base price
                                    min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                                    vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                                    req_parts = []
                                    if vendor.required_reputation:
                                        req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                                    if vendor.required_level:
                                        req_parts.append(f"lvl: {vendor.required_level}")
                                    rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                                    # Calculate effective lead time with player's upgrades
                                    lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                                    effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                                    lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                                    if price:
                                        discount = player.get_vendor_discount(vendor.name, game_state.day)
                                        final_price = price * (1 - discount)
                                        discount_text = f" (-{discount*100:.0f}%)" if discount > 0 else ""
                                        print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ${final_price:.2f}{discount_text} (lead: {lead_time_str})")
                                    else:
                                        status = "(not in stock today)" if vendor.selection_type == "random_daily" else "(not available)"
                                        print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - {status}")

                                slots_available = 3 - len(vendor_orders)
                                print(f"\nEnter up to {slots_available} vendor(s) in format: vendor_number quantity")
                                print(f"One per line, or press Enter to finish")

                                vendors_added = 0
                                while vendors_added < slots_available:
                                    try:
                                        vendor_input = input(f"\nVendor {vendors_added + 1} (or Enter to finish): ").strip()
                                        if not vendor_input:
                                            break

                                        parts = vendor_input.split()
                                        if len(parts) != 2:
                                            print("\n✗ Invalid format! Use: vendor_number quantity (e.g., '2 100')")
                                            continue

                                        vendor_num = int(parts[0])
                                        quantity = int(parts[1])

                                        if vendor_num < 1 or vendor_num > len(game_state.vendors):
                                            print(f"\n✗ Invalid vendor number! Must be 1-{len(game_state.vendors)}")
                                            continue

                                        selected_vendor = game_state.vendors[vendor_num - 1]

                                        if quantity <= 0:
                                            print("\n✗ Quantity must be positive!")
                                            continue

                                        # Check minimum purchase
                                        if selected_vendor.min_purchase is not None and quantity < selected_vendor.min_purchase:
                                            print(f"\n✗ {selected_vendor.name} requires minimum {selected_vendor.min_purchase} units")
                                            continue

                                        success = player.add_vendor_to_buy_order(item.name, quantity, selected_vendor.name)
                                        if success:
                                            print(f"✓ Added: {quantity} {item.name} from {selected_vendor.name}")
                                            vendors_added += 1
                                            # Update vendor_orders for current display
                                            vendor_orders = player.get_buy_order(item.name)
                                        else:
                                            print(f"\n✗ Failed to add vendor (limit reached or duplicate)")

                                    except ValueError:
                                        print("\n✗ Invalid input! Use numbers only (e.g., '2 100')")
                                    except Exception as e:
                                        print(f"\n✗ Error: {e}")

                                if vendors_added > 0:
                                    print(f"\n✓ Successfully added {vendors_added} vendor(s)")
                                    input("Press Enter to continue...")

                            else:
                                print("\n✗ Invalid option!")
                else:
                    print("\n✗ Invalid item selection!")

            else:
                print("\n✗ Invalid option!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def buy_order_menu(game_state: GameState, player: Player) -> None:
    """Menu for setting buy orders (quantity and vendor selection per item) - supports up to 3 vendors per item."""
    # Check level requirement
    if player.store_level < 10:
        print("\n" + "=" * 100)
        print("MANUAL BUY ORDERS - LOCKED")
        print("=" * 100)
        print(f"\n⚠ Manual buy orders require Store Level 10 or higher.")
        print(f"Your current level: {player.store_level}")
        print(f"\nConsider using Auto Buy Orders instead (available at all levels)!")
        input("\nPress Enter to continue...")
        return

    while True:
        print("\n" + "=" * 100)
        print("MANUAL BUY ORDER MENU - Configure Automatic Purchasing (Up to 3 Vendors Per Item)")
        print("=" * 100)
        print("⚠ REQUIREMENT: Total warehouse space in orders must be ≥ 1000 to execute")
        print("=" * 100)
        print("\nCurrent Buy Orders:")
        print(f"{'Item':<15} {'Total Qty':>10} {'Vendors':<70}")
        print("-" * 100)

        for item in game_state.items:
            vendor_orders = player.get_buy_order(item.name)
            total_qty = sum(q for q, v in vendor_orders)
            if vendor_orders:
                vendor_strs = [f"{v} ({q})" for q, v in vendor_orders]
                vendor_display = ", ".join(vendor_strs)
            else:
                vendor_display = "(none)"
            print(f"{item.name:<15} {total_qty:>10} {vendor_display:<70}")

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

                # Item configuration submenu
                while True:
                    print(f"\n{'='*80}")
                    print(f"Configuring Buy Orders for: {item.name}")
                    print(f"{'='*80}")

                    vendor_orders = player.get_buy_order(item.name)
                    print(f"\nCurrent orders ({len(vendor_orders)}/3 vendors):")
                    if vendor_orders:
                        for i, (qty, vendor_name) in enumerate(vendor_orders, 1):
                            # Get vendor price and lead time
                            vendor = game_state.get_vendor(vendor_name)
                            if vendor:
                                price = vendor.get_price(item.name)
                                # Calculate effective lead time with player's upgrades
                                lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                                effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                                lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                                price_str = f"${price:.2f}" if price else "N/A"
                                print(f"  {i}. {vendor_name}: {qty} units @ {price_str} (lead: {lead_time_str})")
                    else:
                        print("  (no vendors configured)")

                    print(f"\nOptions:")
                    print(f"  1. Add/update vendor (max 3)")
                    if vendor_orders:
                        print(f"  2. Remove vendor")
                        print(f"  3. Clear all vendors")
                    if len(vendor_orders) < 3:
                        print(f"  4. Add multiple vendors at once")
                    print(f"  0. Back to item list")

                    sub_choice = input(f"\nSelect option: ").strip()

                    if sub_choice == "0":
                        break
                    elif sub_choice == "1":
                        # Add/update vendor
                        if len(vendor_orders) >= 3:
                            print(f"\n⚠ Already have 3 vendors. Select a vendor to update:")
                            for i, (qty, vendor_name) in enumerate(vendor_orders, 1):
                                print(f"  {i}. {vendor_name}")
                            print(f"  0. Cancel")

                            update_choice = input(f"\nSelect vendor to update (0-{len(vendor_orders)}): ").strip()
                            try:
                                update_num = int(update_choice)
                                if update_num == 0:
                                    continue
                                elif 1 <= update_num <= len(vendor_orders):
                                    # User wants to update this vendor
                                    qty_to_update, vendor_to_update = vendor_orders[update_num - 1]
                                    print(f"\nUpdating: {vendor_to_update} (currently {qty_to_update} units)")

                                    # Show vendor list
                                    print("\nAvailable Vendors:")
                                    for i, vendor in enumerate(game_state.vendors, 1):
                                        price = vendor.get_price(item.name, 1)  # Show base price
                                        min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                                        vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                                        req_parts = []
                                        if vendor.required_reputation:
                                            req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                                        if vendor.required_level:
                                            req_parts.append(f"lvl: {vendor.required_level}")
                                        rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                                        # Calculate effective lead time with player's upgrades
                                        lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                                        effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                                        lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                                        if price:
                                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ${price:.2f} (lead: {lead_time_str})")
                                        else:
                                            status = "(not in stock today)" if vendor.selection_type == "random_daily" else "(not available)"
                                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - {status}")

                                    vendor_choice = input(f"\nSelect new vendor (1-{len(game_state.vendors)}, 0 to cancel): ").strip()
                                    vendor_num = int(vendor_choice)
                                    if vendor_num == 0:
                                        continue
                                    elif 1 <= vendor_num <= len(game_state.vendors):
                                        selected_vendor = game_state.vendors[vendor_num - 1]

                                        quantity_str = input(f"Enter new quantity (0 to remove): ").strip()
                                        quantity = int(quantity_str)

                                        if quantity == 0:
                                            # Remove this vendor
                                            player.remove_vendor_from_buy_order(item.name, vendor_to_update)
                                            print(f"\n✓ Removed {vendor_to_update} from buy order")
                                        elif quantity > 0:
                                            # Check minimum purchase
                                            if selected_vendor.min_purchase is not None and quantity < selected_vendor.min_purchase:
                                                print(f"\n✗ {selected_vendor.name} requires minimum {selected_vendor.min_purchase} units")
                                                input("Press Enter to continue...")
                                                continue

                                            # Remove old vendor and add new one
                                            player.remove_vendor_from_buy_order(item.name, vendor_to_update)
                                            player.add_vendor_to_buy_order(item.name, quantity, selected_vendor.name)
                                            print(f"\n✓ Updated: {quantity} {item.name} from {selected_vendor.name}")
                                        else:
                                            print("\n✗ Quantity must be non-negative!")
                                            input("Press Enter to continue...")
                                else:
                                    print("\n✗ Invalid selection!")
                                    input("Press Enter to continue...")
                            except ValueError:
                                print("\n✗ Invalid input!")
                                input("Press Enter to continue...")
                        else:
                            # Add new vendor
                            print("\nAvailable Vendors:")
                            for i, vendor in enumerate(game_state.vendors, 1):
                                price = vendor.get_price(item.name, 1)  # Show base price
                                min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                                vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                                req_parts = []
                                if vendor.required_reputation:
                                    req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                                if vendor.required_level:
                                    req_parts.append(f"lvl: {vendor.required_level}")
                                rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                                # Calculate effective lead time with player's upgrades
                                lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                                effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                                lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                                if price:
                                    print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ${price:.2f} (lead: {lead_time_str})")
                                else:
                                    status = "(not in stock today)" if vendor.selection_type == "random_daily" else "(not available)"
                                    print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - {status}")

                            vendor_choice = input(f"\nEnter vendor number and quantity (e.g., '2 100'), or just vendor number (0 to cancel): ").strip()
                            try:
                                # Parse input - support both "vendor_num quantity" and just "vendor_num"
                                parts = vendor_choice.split()
                                vendor_num = int(parts[0])

                                if vendor_num == 0:
                                    continue
                                elif 1 <= vendor_num <= len(game_state.vendors):
                                    selected_vendor = game_state.vendors[vendor_num - 1]

                                    # Get quantity - either from second part or prompt
                                    if len(parts) >= 2:
                                        quantity = int(parts[1])
                                    else:
                                        quantity_str = input(f"Enter quantity to buy: ").strip()
                                        quantity = int(quantity_str)

                                    if quantity > 0:
                                        # Check minimum purchase
                                        if selected_vendor.min_purchase is not None and quantity < selected_vendor.min_purchase:
                                            print(f"\n✗ {selected_vendor.name} requires minimum {selected_vendor.min_purchase} units")
                                            input("Press Enter to continue...")
                                            continue

                                        success = player.add_vendor_to_buy_order(item.name, quantity, selected_vendor.name)
                                        if success:
                                            print(f"\n✓ Added: {quantity} {item.name} from {selected_vendor.name}")
                                        else:
                                            print(f"\n✗ Failed to add vendor (limit reached or duplicate)")
                                            input("Press Enter to continue...")
                                    else:
                                        print("\n✗ Quantity must be positive!")
                                        input("Press Enter to continue...")
                                else:
                                    print("\n✗ Invalid vendor selection!")
                                    input("Press Enter to continue...")
                            except ValueError:
                                print("\n✗ Invalid input!")
                                input("Press Enter to continue...")

                    elif sub_choice == "2" and vendor_orders:
                        # Remove vendor
                        print("\nSelect vendor to remove:")
                        for i, (qty, vendor_name) in enumerate(vendor_orders, 1):
                            print(f"  {i}. {vendor_name} ({qty} units)")
                        print(f"  0. Cancel")

                        remove_choice = input(f"\nSelect vendor (0-{len(vendor_orders)}): ").strip()
                        try:
                            remove_num = int(remove_choice)
                            if remove_num == 0:
                                continue
                            elif 1 <= remove_num <= len(vendor_orders):
                                qty, vendor_name = vendor_orders[remove_num - 1]
                                player.remove_vendor_from_buy_order(item.name, vendor_name)
                                print(f"\n✓ Removed {vendor_name} from buy order")
                            else:
                                print("\n✗ Invalid selection!")
                                input("Press Enter to continue...")
                        except ValueError:
                            print("\n✗ Invalid input!")
                            input("Press Enter to continue...")

                    elif sub_choice == "3" and vendor_orders:
                        # Clear all vendors
                        confirm = input(f"\nClear all vendors for {item.name}? (y/n): ").strip().lower()
                        if confirm == 'y':
                            player.clear_buy_order(item.name)
                            print(f"\n✓ Cleared all buy orders for {item.name}")

                    elif sub_choice == "4" and len(vendor_orders) < 3:
                        # Add multiple vendors at once
                        print("\nAvailable Vendors:")
                        for i, vendor in enumerate(game_state.vendors, 1):
                            price = vendor.get_price(item.name, 1)  # Show base price
                            min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                            vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                            req_parts = []
                            if vendor.required_reputation:
                                req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                            if vendor.required_level:
                                req_parts.append(f"lvl: {vendor.required_level}")
                            rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                            # Calculate effective lead time with player's upgrades
                            lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                            effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                            lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                            if price:
                                print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ${price:.2f} (lead: {lead_time_str})")
                            else:
                                status = "(not in stock today)" if vendor.selection_type == "random_daily" else "(not available)"
                                print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - {status}")

                        slots_available = 3 - len(vendor_orders)
                        print(f"\nEnter up to {slots_available} vendor(s) in format: vendor_number quantity")
                        print(f"One per line, or press Enter to finish")

                        vendors_added = 0
                        while vendors_added < slots_available:
                            try:
                                vendor_input = input(f"\nVendor {vendors_added + 1} (or Enter to finish): ").strip()
                                if not vendor_input:
                                    break

                                parts = vendor_input.split()
                                if len(parts) != 2:
                                    print("\n✗ Invalid format! Use: vendor_number quantity (e.g., '2 100')")
                                    continue

                                vendor_num = int(parts[0])
                                quantity = int(parts[1])

                                if vendor_num < 1 or vendor_num > len(game_state.vendors):
                                    print(f"\n✗ Invalid vendor number! Must be 1-{len(game_state.vendors)}")
                                    continue

                                selected_vendor = game_state.vendors[vendor_num - 1]

                                if quantity <= 0:
                                    print("\n✗ Quantity must be positive!")
                                    continue

                                # Check minimum purchase
                                if selected_vendor.min_purchase is not None and quantity < selected_vendor.min_purchase:
                                    print(f"\n✗ {selected_vendor.name} requires minimum {selected_vendor.min_purchase} units")
                                    continue

                                success = player.add_vendor_to_buy_order(item.name, quantity, selected_vendor.name)
                                if success:
                                    print(f"✓ Added: {quantity} {item.name} from {selected_vendor.name}")
                                    vendors_added += 1
                                    # Update vendor_orders for current display
                                    vendor_orders = player.get_buy_order(item.name)
                                else:
                                    print(f"\n✗ Failed to add vendor (limit reached or duplicate)")

                            except ValueError:
                                print("\n✗ Invalid input! Use numbers only (e.g., '2 100')")
                            except Exception as e:
                                print(f"\n✗ Error: {e}")

                        if vendors_added > 0:
                            print(f"\n✓ Successfully added {vendors_added} vendor(s)")
                            input("Press Enter to continue...")

                    else:
                        print("\n✗ Invalid option!")
                        input("Press Enter to continue...")
            else:
                print("\n✗ Invalid item selection!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def recurring_buy_order_menu(game_state: GameState, player: Player) -> None:
    """Menu for managing recurring buy orders (scheduled auto-buy every N days)."""
    while True:
        print("\n" + "=" * 100)
        print("RECURRING BUY ORDERS - Automatic Purchasing Every N Days")
        print("=" * 100)
        print("\nCurrent Recurring Orders:")

        if not player.recurring_buy_orders:
            print("  (no recurring orders set)")
        else:
            print(f"{'#':<4} {'Item':<20} {'Vendor':<25} {'Qty':>8} {'Every':>8} {'Last Run':>10}")
            print("-" * 100)
            for i, order in enumerate(player.recurring_buy_orders, 1):
                days_since = game_state.day - order.last_executed_day
                last_run_str = f"Day {order.last_executed_day}" if order.last_executed_day > 0 else "Never"
                print(f"{i:<4} {order.item_name:<20} {order.vendor_name:<25} {order.quantity:>8} {order.interval_days}d {last_run_str:>10}")

        print("\nOptions:")
        print("  1. Add New Recurring Order")
        if player.recurring_buy_orders:
            print("  2. Edit Existing Recurring Order (change vendor/qty/interval)")
            print("  3. Cancel Recurring Order (costs $500)")
        print("  0. Back to Auto Buy Menu")

        try:
            choice = input("\nSelect option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                # Add new recurring order
                print("\nSelect item for recurring order:")
                for i, item in enumerate(game_state.items, 1):
                    current_inv = player.inventory.get(item.name, 0)
                    print(f"  {i}. {item.name} (current stock: {current_inv})")
                print("  0. Cancel")

                item_choice = input(f"\nSelect item (0-{len(game_state.items)}): ").strip()
                item_num = int(item_choice)

                if item_num == 0:
                    continue
                elif 1 <= item_num <= len(game_state.items):
                    item = game_state.items[item_num - 1]

                    # Select vendor
                    print("\nAvailable Vendors:")
                    for i, vendor in enumerate(game_state.vendors, 1):
                        min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                        vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                        req_parts = []
                        if vendor.required_reputation:
                            req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                        if vendor.required_level:
                            req_parts.append(f"lvl: {vendor.required_level}")
                        rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                        # Calculate effective lead time with player's upgrades
                        lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                        effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                        lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"

                        # Check if vendor would sell this item based on their criteria
                        market_price = game_state.market_prices.get(item.name, item.base_price)
                        if vendor_would_sell_item(vendor, item, market_price):
                            # Calculate estimated price
                            estimated_price = market_price * vendor.pricing_multiplier
                            discount = player.get_vendor_discount(vendor.name, game_state.day)
                            final_price = estimated_price * (1 - discount)
                            discount_text = f" (-{discount*100:.0f}%)" if discount > 0 else ""
                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ~${final_price:.2f}{discount_text} (lead: {lead_time_str})")
                        else:
                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - (not available)")

                    vendor_choice = input(f"\nSelect vendor (1-{len(game_state.vendors)}, 0 to cancel): ").strip()
                    vendor_num = int(vendor_choice)

                    if vendor_num == 0:
                        continue
                    elif 1 <= vendor_num <= len(game_state.vendors):
                        vendor = game_state.vendors[vendor_num - 1]

                        # Get quantity
                        quantity_str = input("Enter quantity to buy: ").strip()
                        quantity = int(quantity_str)

                        if quantity <= 0:
                            print("\n✗ Quantity must be positive!")
                            input("Press Enter to continue...")
                            continue

                        # Get interval
                        interval_str = input("Execute every how many days? (e.g., 3 for every 3 days): ").strip()
                        interval = int(interval_str)

                        if interval <= 0:
                            print("\n✗ Interval must be positive!")
                            input("Press Enter to continue...")
                            continue

                        # Create the order (no cost to set up)
                        new_order = RecurringBuyOrder(
                            item_name=item.name,
                            vendor_name=vendor.name,
                            quantity=quantity,
                            interval_days=interval,
                            last_executed_day=0
                        )
                        player.recurring_buy_orders.append(new_order)
                        print(f"\n✓ Added recurring order: {quantity} {item.name} from {vendor.name} every {interval} days")
                        input("Press Enter to continue...")

            elif choice == "2" and player.recurring_buy_orders:
                # Edit existing recurring order
                print("\nSelect recurring order to edit:")
                for i, order in enumerate(player.recurring_buy_orders, 1):
                    print(f"  {i}. {order.item_name} ({order.quantity} from {order.vendor_name} every {order.interval_days}d)")
                print("  0. Back")

                edit_choice = input(f"\nSelect order to edit (0-{len(player.recurring_buy_orders)}): ").strip()
                edit_num = int(edit_choice)

                if edit_num == 0:
                    continue
                elif 1 <= edit_num <= len(player.recurring_buy_orders):
                    order_to_edit = player.recurring_buy_orders[edit_num - 1]

                    print(f"\n--- Editing Recurring Order for {order_to_edit.item_name} ---")
                    print(f"Current: {order_to_edit.quantity} from {order_to_edit.vendor_name} every {order_to_edit.interval_days} days")
                    print("\nWhat would you like to change?")
                    print("  1. Change Vendor")
                    print("  2. Change Quantity")
                    print("  3. Change Interval (days)")
                    print("  4. Change All")
                    print("  0. Cancel")

                    edit_option = input("\nSelect option: ").strip()

                    if edit_option == "0":
                        continue
                    elif edit_option in ["1", "4"]:
                        # Change vendor
                        print("\nAvailable Vendors:")
                        # Get the item object for this order
                        order_item = game_state.items_by_name.get(order_to_edit.item_name)
                        if not order_item:
                            print(f"Error: Item {order_to_edit.item_name} not found!")
                            continue

                        for i, vendor in enumerate(game_state.vendors, 1):
                            min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                            vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                            req_parts = []
                            if vendor.required_reputation:
                                req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                            if vendor.required_level:
                                req_parts.append(f"lvl: {vendor.required_level}")
                            rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                            # Calculate effective lead time with player's upgrades
                            lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                            effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                            lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"

                            # Check if vendor would sell this item based on their criteria
                            market_price = game_state.market_prices.get(order_to_edit.item_name, order_item.base_price)
                            if vendor_would_sell_item(vendor, order_item, market_price):
                                # Calculate estimated price
                                estimated_price = market_price * vendor.pricing_multiplier
                                discount = player.get_vendor_discount(vendor.name, game_state.day)
                                final_price = estimated_price * (1 - discount)
                                discount_text = f" (-{discount*100:.0f}%)" if discount > 0 else ""
                                print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ~${final_price:.2f}{discount_text} (lead: {lead_time_str})")
                            else:
                                print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - (not available)")

                        vendor_choice = input(f"\nSelect new vendor (1-{len(game_state.vendors)}, 0 to keep current): ").strip()
                        vendor_num = int(vendor_choice)

                        if vendor_num > 0 and 1 <= vendor_num <= len(game_state.vendors):
                            order_to_edit.vendor_name = game_state.vendors[vendor_num - 1].name

                    if edit_option in ["2", "4"]:
                        # Change quantity
                        quantity_str = input(f"Enter new quantity (current: {order_to_edit.quantity}, 0 to keep): ").strip()
                        quantity = int(quantity_str)
                        if quantity > 0:
                            order_to_edit.quantity = quantity

                    if edit_option in ["3", "4"]:
                        # Change interval
                        interval_str = input(f"Enter new interval in days (current: {order_to_edit.interval_days}, 0 to keep): ").strip()
                        interval = int(interval_str)
                        if interval > 0:
                            order_to_edit.interval_days = interval

                    print(f"\n✓ Updated recurring order for {order_to_edit.item_name}")
                    print(f"New settings: {order_to_edit.quantity} from {order_to_edit.vendor_name} every {order_to_edit.interval_days} days")
                    input("Press Enter to continue...")

            elif choice == "3" and player.recurring_buy_orders:
                # Cancel recurring order
                print("\nSelect recurring order to cancel:")
                for i, order in enumerate(player.recurring_buy_orders, 1):
                    print(f"  {i}. {order.item_name} ({order.quantity} from {order.vendor_name} every {order.interval_days}d)")
                print("  0. Back")

                cancel_choice = input(f"\nSelect order to cancel (0-{len(player.recurring_buy_orders)}): ").strip()
                cancel_num = int(cancel_choice)

                if cancel_num == 0:
                    continue
                elif 1 <= cancel_num <= len(player.recurring_buy_orders):
                    order_to_cancel = player.recurring_buy_orders[cancel_num - 1]
                    cancellation_cost = 500

                    print(f"\n⚠ WARNING: Canceling this order will cost ${cancellation_cost:.2f}")
                    print(f"Order: {order_to_cancel.quantity} {order_to_cancel.item_name} from {order_to_cancel.vendor_name}")
                    confirm = input("Type 'yes' to confirm cancellation: ").strip().lower()

                    if confirm == "yes":
                        if player.cash >= cancellation_cost:
                            player.cash -= cancellation_cost
                            player.recurring_buy_orders.pop(cancel_num - 1)
                            print(f"\n✓ Recurring order cancelled. Paid ${cancellation_cost:.2f} cancellation fee.")
                        else:
                            print(f"\n✗ Insufficient cash! Need ${cancellation_cost:.2f}, have ${player.cash:.2f}")
                        input("Press Enter to continue...")
                    else:
                        print("\nCancellation aborted.")
                        input("Press Enter to continue...")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")
            input("Press Enter to continue...")


def stock_minimum_restock_menu(game_state: GameState, player: Player) -> None:
    """Menu for managing stock minimum auto-restock (threshold-based auto-buy)."""
    while True:
        print("\n" + "=" * 100)
        print("STOCK MINIMUM AUTO-RESTOCK - Automatic Reordering When Stock Falls Below Threshold")
        print("=" * 100)
        print("\nCurrent Stock Minimum Settings:")

        if not player.stock_minimum_restock:
            print("  (no auto-restock rules set)")
        else:
            print(f"{'Item':<20} {'Current Stock':>15} {'Minimum':>10} {'Vendor':<25}")
            print("-" * 100)
            for item_name, (minimum, vendor_name) in player.stock_minimum_restock.items():
                current = player.inventory.get(item_name, 0)
                status = "✓ OK" if current >= minimum else "⚠ LOW"
                print(f"{item_name:<20} {current:>15} {minimum:>10} {vendor_name:<25} {status}")

        print("\nOptions:")
        print("  1. Set/Update Stock Minimum (setting to 0 removes it and costs $500)")
        print("  2. Bulk Change Vendor for All Set Items")
        print("  3. Bulk Change Minimum Quantity for All Set Items")
        print("  0. Back to Auto Buy Menu")

        try:
            choice = input("\nSelect option: ").strip()

            if choice == "0":
                break
            elif choice == "2":
                # Bulk change vendor for all set items
                if not player.stock_minimum_restock:
                    print("\n✗ No auto-restock items configured!")
                    input("Press Enter to continue...")
                    continue

                print("\nBulk Change Vendor - This will change the vendor for ALL currently set items")
                print(f"Currently configured items: {len(player.stock_minimum_restock)}")

                print("\nAvailable Vendors:")
                for i, vendor in enumerate(game_state.vendors, 1):
                    min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                    vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                    req_parts = []
                    if vendor.required_reputation:
                        req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                    if vendor.required_level:
                        req_parts.append(f"lvl: {vendor.required_level}")
                    rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                    lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                    effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                    lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"
                    print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} (lead: {lead_time_str})")

                vendor_choice = input(f"\nSelect new vendor for all items (1-{len(game_state.vendors)}, 0 to cancel): ").strip()
                vendor_num = int(vendor_choice)

                if vendor_num == 0:
                    continue
                elif 1 <= vendor_num <= len(game_state.vendors):
                    selected_vendor_name = game_state.vendors[vendor_num - 1].name

                    # Update all items
                    updated_count = 0
                    for item_name, (minimum, old_vendor) in list(player.stock_minimum_restock.items()):
                        player.stock_minimum_restock[item_name] = (minimum, selected_vendor_name)
                        updated_count += 1

                    print(f"\n✓ Updated vendor to '{selected_vendor_name}' for {updated_count} items")
                    input("Press Enter to continue...")
                else:
                    print("\n✗ Invalid vendor selection!")
                    input("Press Enter to continue...")

            elif choice == "3":
                # Bulk change minimum quantity for all set items
                if not player.stock_minimum_restock:
                    print("\n✗ No auto-restock items configured!")
                    input("Press Enter to continue...")
                    continue

                print("\nBulk Change Minimum Quantity - This will change the minimum for ALL currently set items")
                print(f"Currently configured items: {len(player.stock_minimum_restock)}")

                min_str = input(f"\nSet new minimum quantity for all items (0 to cancel): ").strip()
                minimum = int(min_str)

                if minimum == 0:
                    print("\n✗ Bulk change cancelled (use option 1 to remove individual items)")
                    input("Press Enter to continue...")
                    continue
                elif minimum < 0:
                    print("\n✗ Minimum cannot be negative!")
                    input("Press Enter to continue...")
                    continue

                # Update all items
                updated_count = 0
                for item_name, (old_minimum, vendor) in list(player.stock_minimum_restock.items()):
                    player.stock_minimum_restock[item_name] = (minimum, vendor)
                    updated_count += 1

                print(f"\n✓ Updated minimum quantity to {minimum} for {updated_count} items")
                input("Press Enter to continue...")

            elif choice == "1":
                # Set/Update stock minimum
                print("\nSelect item to set/update stock minimum:")
                for i, item in enumerate(game_state.items, 1):
                    current_inv = player.inventory.get(item.name, 0)
                    existing = player.stock_minimum_restock.get(item.name)
                    if existing:
                        min_qty, vendor = existing
                        print(f"  {i}. {item.name} (stock: {current_inv}, min: {min_qty}, vendor: {vendor})")
                    else:
                        print(f"  {i}. {item.name} (stock: {current_inv}, no auto-restock set)")
                print("  0. Cancel")

                item_choice = input(f"\nSelect item (0-{len(game_state.items)}): ").strip()
                item_num = int(item_choice)

                if item_num == 0:
                    continue
                elif 1 <= item_num <= len(game_state.items):
                    item = game_state.items[item_num - 1]
                    existing = player.stock_minimum_restock.get(item.name)

                    # Show current settings if any
                    if existing:
                        min_qty, current_vendor = existing
                        print(f"\nCurrent settings: Minimum {min_qty} from {current_vendor}")
                        print("(Enter 0 for minimum to remove auto-restock - costs $500)")
                    else:
                        print(f"\nNo auto-restock currently set for {item.name}")

                    # Get minimum stock level
                    min_str = input(f"Set minimum stock level for {item.name} (0 to remove): ").strip()
                    minimum = int(min_str)

                    if minimum < 0:
                        print("\n✗ Minimum cannot be negative!")
                        input("Press Enter to continue...")
                        continue

                    # If setting to 0, this is a removal (costs $500)
                    if minimum == 0:
                        if item.name in player.stock_minimum_restock:
                            cancellation_cost = 500
                            print(f"\n⚠ WARNING: Removing auto-restock costs ${cancellation_cost:.2f}")
                            confirm = input("Type 'yes' to confirm removal: ").strip().lower()

                            if confirm == "yes":
                                if player.cash >= cancellation_cost:
                                    player.cash -= cancellation_cost
                                    del player.stock_minimum_restock[item.name]
                                    print(f"\n✓ Auto-restock removed for {item.name}. Paid ${cancellation_cost:.2f} cancellation fee.")
                                else:
                                    print(f"\n✗ Insufficient cash! Need ${cancellation_cost:.2f}, have ${player.cash:.2f}")
                                input("Press Enter to continue...")
                            else:
                                print("\nRemoval aborted.")
                                input("Press Enter to continue...")
                        else:
                            print(f"\n✗ {item.name} doesn't have auto-restock set!")
                            input("Press Enter to continue...")
                        continue

                    # If setting to positive value, select vendor
                    print("\nAvailable Vendors:")
                    for i, vendor in enumerate(game_state.vendors, 1):
                        min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                        vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                        req_parts = []
                        if vendor.required_reputation:
                            req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                        if vendor.required_level:
                            req_parts.append(f"lvl: {vendor.required_level}")
                        rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                        # Calculate effective lead time with player's upgrades
                        lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                        effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                        lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"

                        # Check if vendor would sell this item based on their criteria
                        market_price = game_state.market_prices.get(item.name, item.base_price)
                        if vendor_would_sell_item(vendor, item, market_price):
                            # Calculate estimated price
                            estimated_price = market_price * vendor.pricing_multiplier
                            discount = player.get_vendor_discount(vendor.name, game_state.day)
                            final_price = estimated_price * (1 - discount)
                            discount_text = f" (-{discount*100:.0f}%)" if discount > 0 else ""
                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ~${final_price:.2f}{discount_text} (lead: {lead_time_str})")
                        else:
                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - (not available)")

                    # If updating, show option to keep current vendor
                    if existing:
                        print(f"\nCurrent vendor: {current_vendor}")
                        vendor_choice = input(f"\nSelect vendor (1-{len(game_state.vendors)}, 0 to keep current): ").strip()
                    else:
                        vendor_choice = input(f"\nSelect vendor (1-{len(game_state.vendors)}, 0 to cancel): ").strip()

                    vendor_num = int(vendor_choice)

                    if vendor_num == 0:
                        if existing:
                            # Keep current vendor
                            selected_vendor_name = current_vendor
                        else:
                            # Cancel
                            continue
                    elif 1 <= vendor_num <= len(game_state.vendors):
                        selected_vendor_name = game_state.vendors[vendor_num - 1].name
                    else:
                        print("\n✗ Invalid vendor selection!")
                        input("Press Enter to continue...")
                        continue

                    # Check if item is packaged
                    package_info = ""
                    if item.size < 5.0 and item.category != "Luxury":
                        _, items_per_package, _ = get_package_info(item, "standard")
                        package_info = f" (will buy in packages of {items_per_package})"

                    # Set/update the minimum (free to set up or update)
                    action = "Updated" if existing else "Set"
                    player.stock_minimum_restock[item.name] = (minimum, selected_vendor_name)
                    print(f"\n✓ {action} auto-restock: {item.name} minimum {minimum} from {selected_vendor_name}{package_info}")
                    input("Press Enter to continue...")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")
            input("Press Enter to continue...")


def category_minimum_restock_menu(game_state: GameState, player: Player) -> None:
    """Menu for managing category-wide stock minimum auto-restock."""
    while True:
        print("\n" + "=" * 100)
        print("CATEGORY AUTO-RESTOCK - Automatic Reordering For All Items In A Category")
        print("=" * 100)
        print("\nCurrent Category Auto-Restock Settings:")

        if not player.category_minimum_restock:
            print("  (no category auto-restock rules set)")
        else:
            print(f"{'Category':<25} {'Items in Category':>18} {'Minimum Per Item':>18} {'Vendor':<25}")
            print("-" * 100)
            for category_name, (minimum, vendor_name) in player.category_minimum_restock.items():
                # Count items in this category
                category_items = [item for item in game_state.items if item.category == category_name]
                item_count = len(category_items)
                print(f"{category_name:<25} {item_count:>18} {minimum:>18} {vendor_name:<25}")

        print("\nOptions:")
        print("  1. Set/Update Category Auto-Restock (setting to 0 removes it and costs $500)")
        print("  0. Back to Auto Buy Menu")

        try:
            choice = input("\nSelect option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                # Set/Update category minimum
                print("\nSelect category to set/update auto-restock:")

                # Get all unique categories sorted by importance
                categories_sorted = sorted(PRODUCT_CATEGORIES.keys(), key=lambda c: PRODUCT_CATEGORIES[c], reverse=True)

                for i, category in enumerate(categories_sorted, 1):
                    # Count items in this category
                    category_items = [item for item in game_state.items if item.category == category]
                    item_count = len(category_items)

                    # Check if auto-restock is set
                    existing = player.category_minimum_restock.get(category)
                    if existing:
                        min_qty, vendor = existing
                        # Calculate average stock
                        total_stock = sum(player.inventory.get(item.name, 0) for item in category_items)
                        avg_stock = total_stock / item_count if item_count > 0 else 0
                        print(f"  {i}. {category} ({item_count} items, avg stock: {avg_stock:.1f}, min: {min_qty}, vendor: {vendor})")
                    else:
                        # Calculate average stock
                        total_stock = sum(player.inventory.get(item.name, 0) for item in category_items)
                        avg_stock = total_stock / item_count if item_count > 0 else 0
                        print(f"  {i}. {category} ({item_count} items, avg stock: {avg_stock:.1f}, no auto-restock set)")

                print("  0. Cancel")

                cat_choice = input(f"\nSelect category (0-{len(categories_sorted)}): ").strip()
                cat_num = int(cat_choice)

                if cat_num == 0:
                    continue
                elif 1 <= cat_num <= len(categories_sorted):
                    category = categories_sorted[cat_num - 1]
                    existing = player.category_minimum_restock.get(category)

                    # Show current settings if any
                    if existing:
                        min_qty, current_vendor = existing
                        print(f"\nCurrent settings: Minimum {min_qty} per item from {current_vendor}")
                        print("(Enter 0 for minimum to remove auto-restock - costs $500)")
                    else:
                        print(f"\nNo auto-restock currently set for {category}")

                    # Get minimum stock level
                    min_str = input(f"Set minimum stock level PER ITEM for {category} (0 to remove): ").strip()
                    minimum = int(min_str)

                    if minimum < 0:
                        print("\n✗ Minimum cannot be negative!")
                        input("Press Enter to continue...")
                        continue

                    # If setting to 0, this is a removal (costs $500)
                    if minimum == 0:
                        if category in player.category_minimum_restock:
                            cancellation_cost = 500
                            print(f"\n⚠ WARNING: Removing category auto-restock costs ${cancellation_cost:.2f}")
                            confirm = input("Type 'yes' to confirm removal: ").strip().lower()

                            if confirm == "yes":
                                if player.cash >= cancellation_cost:
                                    player.cash -= cancellation_cost
                                    del player.category_minimum_restock[category]
                                    print(f"\n✓ Category auto-restock removed for {category}. Paid ${cancellation_cost:.2f} cancellation fee.")
                                else:
                                    print(f"\n✗ Insufficient cash! Need ${cancellation_cost:.2f}, have ${player.cash:.2f}")
                                input("Press Enter to continue...")
                            else:
                                print("\nRemoval aborted.")
                                input("Press Enter to continue...")
                        else:
                            print(f"\n✗ {category} doesn't have category auto-restock set!")
                            input("Press Enter to continue...")
                        continue

                    # If setting to positive value, select vendor
                    print("\nAvailable Vendors:")

                    # Get a sample item from this category to check vendor compatibility
                    category_items = [item for item in game_state.items if item.category == category]
                    sample_item = category_items[0] if category_items else None

                    for i, vendor in enumerate(game_state.vendors, 1):
                        min_text = f" (min: {vendor.min_purchase})" if vendor.min_purchase else ""
                        vol_text = " [volume pricing]" if vendor.volume_pricing_tiers else ""
                        req_parts = []
                        if vendor.required_reputation:
                            req_parts.append(f"rep: {vendor.required_reputation:.0f}")
                        if vendor.required_level:
                            req_parts.append(f"lvl: {vendor.required_level}")
                        rep_text = f" [req {', '.join(req_parts)}]" if req_parts else ""
                        # Calculate effective lead time with player's upgrades
                        lead_time_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "lead_time_reduction")
                        effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))
                        lead_time_str = f"{effective_lead_time}d" if effective_lead_time > 0 else "instant"

                        # Check if vendor would sell items from this category
                        if sample_item:
                            market_price = game_state.market_prices.get(sample_item.name, sample_item.base_price)
                            if vendor_would_sell_item(vendor, sample_item, market_price):
                                # Calculate estimated price for sample item
                                estimated_price = market_price * vendor.pricing_multiplier
                                discount = player.get_vendor_discount(vendor.name, game_state.day)
                                final_price = estimated_price * (1 - discount)
                                discount_text = f" (-{discount*100:.0f}%)" if discount > 0 else ""
                                print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - ~${final_price:.2f}{discount_text} (lead: {lead_time_str})")
                            else:
                                print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} - (may not have all items)")
                        else:
                            print(f"  {i}. {vendor.name}{min_text}{vol_text}{rep_text} (lead: {lead_time_str})")

                    # If updating, show option to keep current vendor
                    if existing:
                        print(f"\nCurrent vendor: {current_vendor}")
                        vendor_choice = input(f"\nSelect vendor (1-{len(game_state.vendors)}, 0 to keep current): ").strip()
                    else:
                        vendor_choice = input(f"\nSelect vendor (1-{len(game_state.vendors)}, 0 to cancel): ").strip()

                    vendor_num = int(vendor_choice)

                    if vendor_num == 0:
                        if existing:
                            # Keep current vendor
                            selected_vendor_name = current_vendor
                        else:
                            # Cancel
                            continue
                    elif 1 <= vendor_num <= len(game_state.vendors):
                        selected_vendor_name = game_state.vendors[vendor_num - 1].name
                    else:
                        print("\n✗ Invalid vendor selection!")
                        input("Press Enter to continue...")
                        continue

                    # Set/update the minimum (free to set up or update)
                    action = "Updated" if existing else "Set"
                    player.category_minimum_restock[category] = (minimum, selected_vendor_name)
                    item_count = len(category_items)
                    print(f"\n✓ {action} category auto-restock: {category} minimum {minimum} per item from {selected_vendor_name}")
                    print(f"   This applies to {item_count} items in the {category} category")
                    input("Press Enter to continue...")
                else:
                    print("\n✗ Invalid category selection!")
                    input("Press Enter to continue...")
            else:
                print("\n✗ Invalid choice!")
                input("Press Enter to continue...")

        except ValueError:
            print("\n✗ Invalid input!")
            input("Press Enter to continue...")


def auto_buy_orders_menu(game_state: GameState, player: Player) -> None:
    """Main menu for auto buy order features (recurring orders, stock minimum restock, and category restock)."""
    while True:
        print("\n" + "=" * 80)
        print("AUTO BUY ORDERS - Automated Purchasing Management")
        print("=" * 80)
        print("\nOptions:")
        print("  1. Recurring Buy Orders (Schedule orders every N days)")
        print("  2. Stock Minimum Auto-Restock (Auto-buy when stock falls below threshold)")
        print("  3. Category Auto-Restock (Auto-restock all items in a category)")
        print("  0. Back to Main Menu")

        try:
            choice = input("\nSelect option (0-3): ").strip()

            if choice == "0":
                break
            elif choice == "1":
                recurring_buy_order_menu(game_state, player)
            elif choice == "2":
                stock_minimum_restock_menu(game_state, player)
            elif choice == "3":
                category_minimum_restock_menu(game_state, player)
            else:
                print("\n✗ Invalid choice!")
                input("Press Enter to continue...")

        except ValueError:
            print("\n✗ Invalid input!")
            input("Press Enter to continue...")


def warehouse_menu(game_state: GameState, player: Player) -> None:
    """Menu for managing warehouses, upgrades, and workers."""
    WORKER_HIRE_COST = 500.0
    WORKER_MONTHLY_WAGE = 500.0

    while True:
        print("\n" + "=" * 70)
        print("WAREHOUSE MANAGEMENT MENU")
        print("=" * 70)
        print(f"\nYour Cash: ${player.cash:.2f}")
        inventory_size_used = player.get_inventory_size_used(game_state.items_by_name)
        total_items = sum(player.inventory.values())
        print(f"Current Inventory: {inventory_size_used:.1f}/{player.get_max_inventory()} space ({total_items} items)")
        print(f"\nWarehouses: {len(player.warehouses)}/4")

        # Display warehouse information
        print("\n" + "-" * 70)
        total_workers = 0
        for i, warehouse in enumerate(player.warehouses):
            capacity = warehouse.level * 500
            print(f"  Warehouse {i + 1}: Level {warehouse.level}/10 | {warehouse.workers}/5 workers | Capacity: {capacity}")
            total_workers += warehouse.workers

        print("-" * 70)

        # Calculate wages
        wage_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "wage_reduction")
        actual_worker_wage = max(0, WORKER_MONTHLY_WAGE - wage_reduction)
        marketing_agent_wage = max(0, 1000.0 - wage_reduction)
        total_employees = total_workers + player.marketing_agents
        total_monthly_wages = (total_workers * actual_worker_wage) + (player.marketing_agents * marketing_agent_wage)

        print(f"\nEmployees:")
        print(f"  Warehouse Workers: {total_workers} (${actual_worker_wage:.2f}/month each)")
        print(f"  Marketing Agents: {player.marketing_agents} (${marketing_agent_wage:.2f}/month each)")
        print(f"  Total monthly wages: ${total_monthly_wages:.2f}")

        # Show days until next wage payment
        days_until_payment = 30 - (game_state.day - player.last_wage_payment_day)
        if total_employees > 0:
            print(f"  Next wage payment: Day {player.last_wage_payment_day + 30} ({days_until_payment} days)")

        # Calculate costs
        total_level = player.get_total_warehouse_level()
        upgrade_cost = 5000.0 * total_level
        new_warehouse_cost = 20000.0 * len(player.warehouses)

        print("\nOptions:")
        print(f"  1. Upgrade Warehouse (Cost: ${upgrade_cost:.2f})")
        if len(player.warehouses) < 4:
            print(f"  2. Buy New Warehouse (Cost: ${new_warehouse_cost:.2f})")
        else:
            print(f"  2. Buy New Warehouse (Max 4 warehouses reached)")
        print(f"  3. Hire Warehouse Worker (Cost: ${WORKER_HIRE_COST:.2f})")
        print("  0. Back to Main Menu")

        try:
            choice = input("\nSelect option (0-3): ")
            choice_num = int(choice)

            if choice_num == 0:
                break
            elif choice_num == 1:
                # Upgrade warehouse submenu
                print("\nWhich warehouse to upgrade?")
                for i, warehouse in enumerate(player.warehouses):
                    status = f"(Level {warehouse.level}/10)" if warehouse.level < 10 else "(Max Level)"
                    print(f"  {i + 1}. Warehouse {i + 1} {status}")
                print("  0. Cancel")

                try:
                    w_choice = input("\nSelect warehouse (0-{}): ".format(len(player.warehouses)))
                    w_num = int(w_choice)

                    if w_num == 0:
                        continue
                    if 1 <= w_num <= len(player.warehouses):
                        warehouse = player.warehouses[w_num - 1]
                        if warehouse.level >= 10:
                            print(f"\n✗ Warehouse {w_num} is already at max level (10)")
                        elif player.cash < upgrade_cost:
                            print(f"\n✗ Not enough cash! Need ${upgrade_cost:.2f}, have ${player.cash:.2f}")
                        else:
                            if player.upgrade_warehouse(w_num - 1):
                                print(f"\n✓ Upgraded Warehouse {w_num} to Level {warehouse.level}")
                                print(f"  Capacity increased to {warehouse.level * 500} items")
                                next_cost = 5000.0 * player.get_total_warehouse_level()
                                print(f"  Next upgrade will cost: ${next_cost:.2f}")
                            else:
                                print("\n✗ Failed to upgrade warehouse")
                    else:
                        print("\n✗ Invalid warehouse number!")
                except (ValueError, IndexError):
                    print("\n✗ Invalid input!")

            elif choice_num == 2:
                if len(player.warehouses) >= 4:
                    print("\n✗ Maximum warehouses (4) reached!")
                elif player.cash < new_warehouse_cost:
                    print(f"\n✗ Not enough cash! Need ${new_warehouse_cost:.2f}, have ${player.cash:.2f}")
                else:
                    if player.buy_warehouse():
                        print(f"\n✓ Bought new warehouse for ${new_warehouse_cost:.2f}")
                        print(f"  Total warehouses: {len(player.warehouses)}/4")
                        next_cost = 20000.0 * len(player.warehouses)
                        print(f"  Next warehouse will cost: ${next_cost:.2f}")
                    else:
                        print("\n✗ Failed to buy warehouse")

            elif choice_num == 3:
                # Hire worker submenu
                print("\nWhich warehouse to hire for?")
                for i, warehouse in enumerate(player.warehouses):
                    status = f"({warehouse.workers}/5 workers)" if warehouse.workers < 5 else "(Full - 5/5)"
                    print(f"  {i + 1}. Warehouse {i + 1} {status}")
                print("  0. Cancel")

                try:
                    w_choice = input("\nSelect warehouse (0-{}): ".format(len(player.warehouses)))
                    w_num = int(w_choice)

                    if w_num == 0:
                        continue
                    if 1 <= w_num <= len(player.warehouses):
                        warehouse = player.warehouses[w_num - 1]
                        if warehouse.workers >= 5:
                            print(f"\n✗ Warehouse {w_num} is full (5/5 workers)")
                        elif player.cash < WORKER_HIRE_COST:
                            print(f"\n✗ Not enough cash! Need ${WORKER_HIRE_COST:.2f}, have ${player.cash:.2f}")
                        else:
                            if player.hire_warehouse_worker(w_num - 1):
                                print(f"\n✓ Hired worker for Warehouse {w_num}")
                                print(f"  Cost: ${WORKER_HIRE_COST:.2f}")
                                print(f"  Workers: {warehouse.workers}/5")
                                print(f"  New max inventory: {player.get_max_inventory()} items")
                            else:
                                print("\n✗ Failed to hire worker")
                    else:
                        print("\n✗ Invalid warehouse number!")
                except (ValueError, IndexError):
                    print("\n✗ Invalid input!")

            else:
                print("\n✗ Invalid option!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def discard_inventory_menu(game_state: GameState, player: Player) -> None:
    """Menu for discarding inventory items."""
    while True:
        print("\n" + "=" * 70)
        print("DISCARD INVENTORY MENU")
        print("=" * 70)
        print(f"\nYour Cash: ${player.cash:.2f}")

        # Show current inventory
        inventory_size_used = player.get_inventory_size_used(game_state.items_by_name)
        total_items = sum(player.inventory.values())
        print(f"Current Inventory: {inventory_size_used:.1f}/{player.get_max_inventory()} space ({total_items} items)")

        if not player.inventory:
            print("\n✗ Your inventory is empty. Nothing to discard.")
            input("\nPress Enter to continue...")
            break

        # Display inventory items
        print("\n" + "-" * 70)
        print(f"{'#':<4} {'Item':<25} {'Quantity':>10} {'Size Each':>12} {'Total Size':>12}")
        print("-" * 70)

        inventory_items = []
        for idx, (item_name, qty) in enumerate(sorted(player.inventory.items()), 1):
            if qty > 0:  # Only show items with quantity > 0
                item_obj = game_state.items_by_name.get(item_name)
                size = item_obj.size if item_obj else 1.0
                total_size = size * qty
                print(f"{idx:<4} {item_name:<25} {qty:>10} {size:>12.1f} {total_size:>12.1f}")
                inventory_items.append((item_name, qty))

        print("-" * 70)
        print("\nOptions:")
        print("  Enter item # to discard")
        print("  0. Back to Main Menu")

        try:
            choice = input("\nSelect item (0-{}): ".format(len(inventory_items)))
            choice_num = int(choice)

            if choice_num == 0:
                break

            if 1 <= choice_num <= len(inventory_items):
                item_name, current_qty = inventory_items[choice_num - 1]

                # Submenu for discard amount
                print(f"\n{item_name} - Current Quantity: {current_qty}")
                print("\nDiscard Options:")
                print("  1. Discard specific amount")
                print("  2. Discard all")
                print("  0. Cancel")

                discard_choice = input("\nSelect option (0-2): ")
                discard_num = int(discard_choice)

                if discard_num == 0:
                    continue
                elif discard_num == 1:
                    # Discard specific amount
                    amount_str = input(f"\nEnter amount to discard (1-{current_qty}): ")
                    amount = int(amount_str)

                    if amount <= 0:
                        print("\n✗ Amount must be greater than 0")
                    elif amount > current_qty:
                        print(f"\n✗ You only have {current_qty} {item_name}")
                    else:
                        # Confirm discard
                        confirm = input(f"\nAre you sure you want to discard {amount} {item_name}? (y/n): ").strip().lower()
                        if confirm == 'y':
                            player.inventory[item_name] -= amount
                            if player.inventory[item_name] == 0:
                                del player.inventory[item_name]
                            print(f"\n✓ Discarded {amount} {item_name}")
                        else:
                            print("\n✗ Discard cancelled")

                    input("\nPress Enter to continue...")

                elif discard_num == 2:
                    # Discard all
                    confirm = input(f"\nAre you sure you want to discard ALL {current_qty} {item_name}? (y/n): ").strip().lower()
                    if confirm == 'y':
                        del player.inventory[item_name]
                        print(f"\n✓ Discarded all {current_qty} {item_name}")
                    else:
                        print("\n✗ Discard cancelled")

                    input("\nPress Enter to continue...")
                else:
                    print("\n✗ Invalid option!")
            else:
                print("\n✗ Invalid item number!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def employee_menu(game_state: GameState, player: Player) -> None:
    """Menu for hiring cashiers and marketing agents."""

    while True:
        print("\n" + "=" * 60)
        print("EMPLOYEE MENU - Hire Staff")
        print("=" * 60)
        print(f"\nYour Cash: ${player.cash:.2f}")
        print(f"Store Level: {player.store_level}")
        print(f"\nCurrent Employees:")
        print(f"  Cashiers: {player.cashiers} (Handle 200 customers/day each)")
        print(f"  Marketing Agents: {player.marketing_agents} (Boost customer attraction)")

        # Total employees including warehouse workers
        total_warehouse_workers = sum(w.workers for w in player.warehouses)
        total_employees = total_warehouse_workers + player.cashiers + player.marketing_agents

        # Calculate actual wages with upgrades
        wage_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "wage_reduction")
        worker_wage = max(0, 500.0 - wage_reduction)
        cashier_wage = max(0, 500.0 - wage_reduction)
        agent_wage = max(0, 1000.0 - wage_reduction)
        total_monthly_wages = (total_warehouse_workers * worker_wage) + (player.cashiers * cashier_wage) + (player.marketing_agents * agent_wage)

        print(f"  Warehouse Workers (in Warehouse menu): {total_warehouse_workers}")
        print(f"  Total monthly wages: ${total_monthly_wages:.2f}")

        # Show customer capacity
        customer_capacity = 100 + (player.cashiers * 200)
        print(f"\nCustomer Capacity: {customer_capacity} customers/day (100 base + {player.cashiers * 200} from cashiers)")
        print(f"Note: Going over capacity reduces CAS through soft penalty")

        if wage_reduction > 0:
            print(f"\nMonthly Wage per Cashier: ${cashier_wage:.2f} (reduced from $500.00)")
            print(f"Monthly Wage per Agent: ${agent_wage:.2f} (reduced from $1000.00)")
        else:
            print(f"\nMonthly Wage per Cashier: ${cashier_wage:.2f}")
            print(f"Monthly Wage per Agent: ${agent_wage:.2f}")

        # Show days until next wage payment
        days_until_payment = 30 - (game_state.day - player.last_wage_payment_day)
        if total_employees > 0:
            print(f"Next wage payment: Day {player.last_wage_payment_day + 30} ({days_until_payment} days)")
        print(f"Note: Wages paid every 30 days for ALL employees (including newly hired)")

        # Calculate costs
        cashier_cost = 500.0
        marketing_cost = 1000.0 * (5 ** player.marketing_agents)

        print("\nOptions:")
        print("  [For warehouse workers, use: 9. Warehouse Management]")
        print(f"  1. Hire Cashier (Handle more customers) - ${cashier_cost:.2f}")
        if player.store_level >= 5:
            print(f"  2. Hire Marketing Agent (Boost CAS) - ${marketing_cost:.2f}")
        else:
            print(f"  2. Hire Marketing Agent (Requires Level 5+)")
        print("  0. Back to Main Menu")

        try:
            choice = input("\nSelect option (0-2): ")
            choice_num = int(choice)

            if choice_num == 0:
                break
            elif choice_num == 1:
                if player.cash < cashier_cost:
                    print(f"\n✗ Not enough cash! Need ${cashier_cost:.2f}, have ${player.cash:.2f}")
                else:
                    success = player.hire_employee("cashier")
                    if success:
                        print(f"\n✓ Hired Cashier for ${cashier_cost:.2f}")
                        new_capacity = 100 + (player.cashiers * 200)
                        print(f"  New customer capacity: {new_capacity} customers/day")
                    else:
                        print("\n✗ Failed to hire Cashier")
            elif choice_num == 2:
                if player.store_level < 5:
                    print(f"\n✗ Requires Store Level 5+! (Current: {player.store_level})")
                elif player.cash < marketing_cost:
                    print(f"\n✗ Not enough cash! Need ${marketing_cost:.2f}, have ${player.cash:.2f}")
                else:
                    success = player.hire_employee("marketing_agent")
                    if success:
                        print(f"\n✓ Hired Marketing Agent for ${marketing_cost:.2f}")
                        next_cost = 1000.0 * (5 ** player.marketing_agents)
                        print(f"  Next Marketing Agent will cost: ${next_cost:.2f}")
                    else:
                        print("\n✗ Failed to hire Marketing Agent")
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
    if upgrade.effect_type == "xp_gain":
        return f"+{int(upgrade.effect_value)}% XP gain"
    elif upgrade.effect_type == "vendor_discount":
        return f"+{int(upgrade.effect_value)}% discount at {upgrade.vendor_name}"
    elif upgrade.effect_type == "wage_reduction":
        return f"-${int(upgrade.effect_value)} monthly wage per employee (from $1000 to $900)"
    elif upgrade.effect_type == "lead_time_reduction":
        return f"-{int(upgrade.effect_value)} day lead time for all vendors"
    elif upgrade.effect_type == "production_line":
        return f"Own production for {upgrade.vendor_name} (50% market price)"
    return "Unknown effect"


def pricing_menu(game_state: GameState, player: Player) -> None:
    """Menu for setting category-based pricing as a percentage below market."""
    items_by_name = {item.name: item for item in game_state.items}

    while True:
        # Get items from inventory, buy orders, and auto-features
        relevant_item_names = set()
        relevant_categories = set()

        # Add items from inventory
        for item_name, qty in player.inventory.items():
            if qty > 0:
                relevant_item_names.add(item_name)

        # Add items from buy orders
        for item_name, vendor_list in player.buy_orders.items():
            total_qty = sum(q for q, v in vendor_list)
            if total_qty > 0:
                relevant_item_names.add(item_name)

        # Add items from recurring buy orders
        for order in player.recurring_buy_orders:
            relevant_item_names.add(order.item_name)

        # Add items from auto-restock
        for item_name in player.stock_minimum_restock.keys():
            relevant_item_names.add(item_name)

        # Add categories from category auto-restock
        for category_name in player.category_minimum_restock.keys():
            relevant_categories.add(category_name)

        # Get categories that have items in inventory, buy orders, or auto-features
        categories_with_items = {}
        for item_name in relevant_item_names:
            if item_name in items_by_name:
                item = items_by_name[item_name]
                if item.category not in categories_with_items:
                    categories_with_items[item.category] = []
                categories_with_items[item.category].append(item)

        # Add categories from category auto-restock (include all items in those categories)
        for category_name in relevant_categories:
            if category_name not in categories_with_items:
                categories_with_items[category_name] = []
            # Add all items from this category
            for item in game_state.items:
                if item.category == category_name and item not in categories_with_items[category_name]:
                    categories_with_items[category_name].append(item)

        if not categories_with_items:
            print("\n" + "=" * 70)
            print("CATEGORY PRICING - Set Prices by Category")
            print("=" * 70)
            print("\nYou have no items in inventory, buy orders, or auto-features to price.")
            input("\nPress Enter to return to main menu...")
            break

        print("\n" + "=" * 70)
        print("CATEGORY PRICING - Set Prices by Category")
        print("=" * 70)
        print("\nSet pricing as a percentage below market price for all items in a category.")
        print("Prices will automatically update when market prices change.")

        # Display categories with their info
        print(f"\n{'Category':<25} {'Imp':>3} {'Items':>5} {'Pricing':>12} {'Price Range'}")
        print("-" * 70)

        # Sort categories by importance (descending) then name
        sorted_categories = sorted(categories_with_items.keys(),
                                  key=lambda c: (-PRODUCT_CATEGORIES.get(c, 0), c))

        for category in sorted_categories:
            items_in_cat = categories_with_items[category]
            importance = PRODUCT_CATEGORIES.get(category, 0)
            num_items = len(items_in_cat)

            # Get current pricing percentage
            pricing_pct = player.get_category_pricing_percent(category)
            if pricing_pct is not None:
                if pricing_pct > 0:
                    pricing_str = f"{pricing_pct:.1f}% below"
                elif pricing_pct < 0:
                    pricing_str = f"{abs(pricing_pct):.1f}% above"
                else:
                    pricing_str = "At market"
            else:
                pricing_str = "Not set"

            # Calculate price range for items in this category
            market_prices_in_cat = [game_state.market_prices.get(item.name, 0) for item in items_in_cat]
            if market_prices_in_cat:
                min_price = min(market_prices_in_cat)
                max_price = max(market_prices_in_cat)
                if min_price == max_price:
                    price_range = f"${min_price:.2f}"
                else:
                    price_range = f"${min_price:.2f}-${max_price:.2f}"
            else:
                price_range = "N/A"

            print(f"{category:<25} {importance:>3} {num_items:>5} {pricing_str:>12} {price_range}")

        print("\n" + "-" * 70)
        print("Importance levels: 3 = Essentials, 2 = Non-essentials, 1 = Luxury")
        print("\nSelect a category to set pricing:")
        for i, category in enumerate(sorted_categories, 1):
            print(f"  {i}. {category}")
        print(f"  0. Back to Main Menu")

        try:
            choice = input(f"\nSelect category (0-{len(sorted_categories)}): ").strip()
            choice_num = int(choice)

            if choice_num == 0:
                break

            if 1 <= choice_num <= len(sorted_categories):
                category = sorted_categories[choice_num - 1]
                items_in_cat = categories_with_items[category]
                importance = PRODUCT_CATEGORIES.get(category, 0)
                current_pct = player.get_category_pricing_percent(category)

                print(f"\n" + "=" * 70)
                print(f"PRICING: {category}")
                print("=" * 70)
                print(f"Importance: {importance} ({'Essentials' if importance == 3 else 'Non-essentials' if importance == 2 else 'Luxury'})")
                print(f"Items in this category: {len(items_in_cat)}")

                # Show some example items
                print(f"\nExample items in this category:")
                for item in items_in_cat[:5]:
                    market_price = game_state.market_prices.get(item.name, 0)
                    print(f"  - {item.name}: Market ${market_price:.2f}")
                if len(items_in_cat) > 5:
                    print(f"  ... and {len(items_in_cat) - 5} more")

                if current_pct is not None:
                    print(f"\nCurrent pricing: {current_pct:.1f}% {'below' if current_pct > 0 else 'above'} market")
                else:
                    print(f"\nCurrent pricing: Not set")

                print("\nEnter percentage below market price:")
                print("  Positive = below market (e.g., 5 = 5% cheaper than market)")
                print("  Negative = above market (e.g., -5 = 5% more expensive than market)")
                print("  0 = exactly at market price")

                percent_str = input(f"\nPercentage below market (or Enter to cancel): ").strip()

                if percent_str:
                    try:
                        percent = float(percent_str)

                        # Set the category pricing
                        player.set_category_pricing(category, percent, game_state.market_prices, items_by_name)

                        # Show results
                        print(f"\n✓ Pricing set for {category}!")
                        print(f"  All {len(items_in_cat)} items will be priced at {percent:.1f}% {'below' if percent > 0 else 'above'} market")
                        print(f"  Prices will automatically update when market prices change")

                        # Show a few example prices
                        print(f"\nExample new prices:")
                        for item in items_in_cat[:3]:
                            market_price = game_state.market_prices.get(item.name, 0)
                            your_price = player.prices.get(item.name, 0)
                            print(f"  {item.name}: Market ${market_price:.2f} → Your ${your_price:.2f}")

                    except ValueError:
                        print("✗ Invalid percentage! No changes made.")
                else:
                    print("✗ Cancelled.")

                input("\nPress Enter to continue...")
            else:
                print("\n✗ Invalid category selection!")

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


# -------------------------------------------------------------------
# Loan System
# -------------------------------------------------------------------

@dataclass
class LoanOffer:
    """Represents a loan offer from a lender."""
    lender_name: str
    amount: float
    days_to_repay: int
    interest_rate: float  # Full interest rate (e.g., 0.10 for 10%)
    early_interest_rate: float  # Early payoff interest rate (1/10th of normal)
    min_level: int = 0  # Minimum store level required (0 = no requirement)
    min_reputation: float = 0.0  # Minimum reputation required (0 = no requirement)


def get_available_loan_offers() -> List[LoanOffer]:
    """Get list of all available loan offers."""
    return [
        LoanOffer("Quick Cash Inc.", 2000.0, 10, 0.10, 0.01, min_level=0, min_reputation=0.0),
        LoanOffer("Medium Lenders Co.", 5000.0, 30, 0.05, 0.005, min_level=5, min_reputation=0.0),
        LoanOffer("Huge Capital Ltd.", 20000.0, 30, 0.02, 0.002, min_level=15, min_reputation=0.0),
        LoanOffer("Tottally Not Shady Deals", 4000.0, 5, 0.20, 0.02, min_level=0, min_reputation=0.0),
        LoanOffer("Government Bank", 50000.0, 60, 0.10, 0.01, min_level=20, min_reputation=100.0),
    ]


def loans_menu(game_state: GameState, player: Player) -> None:
    """Menu for managing loans - taking new loans and paying back existing ones."""
    while True:
        print("\n" + "=" * 70)
        print("LOANS MENU")
        print("=" * 70)
        print(f"\nYour Cash: ${player.cash:.2f}")

        # Display active loans
        if player.loans:
            total_debt = sum(loan.remaining_balance for loan in player.loans)
            print(f"\n💳 Active Loans (Total Debt: ${total_debt:,.2f}):")
            for i, loan in enumerate(player.loans, 1):
                days_remaining = loan.due_day - game_state.day
                interest_amount = loan.remaining_balance - loan.principal
                print(f"\n  {i}. {loan.lender_name}")
                print(f"     Principal: ${loan.principal:,.2f}")
                print(f"     Current Balance: ${loan.remaining_balance:,.2f} (includes ${interest_amount:,.2f} interest)")
                print(f"     Due: Day {loan.due_day} ({days_remaining} days remaining)")
                if days_remaining < 0:
                    print(f"     ⚠️  OVERDUE by {abs(days_remaining)} days!")
        else:
            print("\n💳 No active loans")

        # Display loan offers - separate available and locked
        all_offers = get_available_loan_offers()
        available_offers = []
        locked_offers = []

        for offer in all_offers:
            meets_level = player.store_level >= offer.min_level
            meets_reputation = player.reputation >= offer.min_reputation
            if meets_level and meets_reputation:
                available_offers.append(offer)
            else:
                locked_offers.append(offer)

        # Show available offers
        print("\n🏦 Available Loan Offers:")
        if available_offers:
            for i, offer in enumerate(available_offers, 1):
                total_with_interest = offer.amount * (1 + offer.interest_rate)
                early_payoff_interest = offer.amount * offer.early_interest_rate
                print(f"\n  {i}. {offer.lender_name}")
                print(f"     Amount: ${offer.amount:,.2f}")
                print(f"     Repayment Period: {offer.days_to_repay} days")
                print(f"     Interest Rate: {offer.interest_rate * 100:.1f}% (Total: ${total_with_interest:,.2f})")
                print(f"     Early Payoff: {offer.early_interest_rate * 100:.1f}% interest (Total: ${offer.amount + early_payoff_interest:,.2f})")
        else:
            print("  (No loans available at your level)")

        # Show locked offers
        if locked_offers:
            print("\n🔒 Locked Loan Offers:")
            for offer in locked_offers:
                requirements = []
                if offer.min_level > player.store_level:
                    requirements.append(f"Level {offer.min_level} (you: {player.store_level})")
                if offer.min_reputation > player.reputation:
                    requirements.append(f"Reputation {offer.min_reputation:.0f} (you: {player.reputation:.0f})")
                req_str = ", ".join(requirements)
                total_with_interest = offer.amount * (1 + offer.interest_rate)
                print(f"\n  🔒 {offer.lender_name} - ${offer.amount:,.2f} at {offer.interest_rate * 100:.1f}%")
                print(f"     Requires: {req_str}")

        print("\n  t. Take a new loan")
        if player.loans:
            print("  p. Pay back a loan")
        print("  0. Back to Main Menu")

        try:
            choice = input("\nSelect option (t, p, 0): ").strip().lower()

            if choice == '0':
                break
            elif choice == 't':
                # Take new loan submenu - only pass available offers
                if available_offers:
                    take_loan_submenu(game_state, player, available_offers)
                else:
                    print("\n✗ No loans available at your current level and reputation!")
                    input("\nPress Enter to continue...")
            elif choice == 'p' and player.loans:
                # Pay back loan submenu
                pay_loan_submenu(game_state, player)
            else:
                print("\n✗ Invalid option!")
                input("\nPress Enter to continue...")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")
            input("\nPress Enter to continue...")


def take_loan_submenu(game_state: GameState, player: Player, offers: List[LoanOffer]) -> None:
    """Submenu for taking a new loan."""
    print("\n" + "=" * 70)
    print("TAKE A LOAN")
    print("=" * 70)

    for i, offer in enumerate(offers, 1):
        total_with_interest = offer.amount * (1 + offer.interest_rate)
        print(f"\n  {i}. {offer.lender_name} - ${offer.amount:,.2f}")
        print(f"     Must repay ${total_with_interest:,.2f} by day {game_state.day + offer.days_to_repay}")

    print("\n  0. Cancel")

    try:
        choice = input(f"\nSelect loan to take (1-{len(offers)}, 0 to cancel): ").strip()
        choice_num = int(choice)

        if choice_num == 0:
            return

        if 1 <= choice_num <= len(offers):
            offer = offers[choice_num - 1]

            # Check if player already has a loan from this lender
            existing_loan = any(loan.lender_name == offer.lender_name for loan in player.loans)
            if existing_loan:
                print(f"\n✗ You already have an active loan from {offer.lender_name}!")
                print(f"   Please pay off your existing loan before taking another one from this lender.")
                input("\nPress Enter to continue...")
                return

            # Confirm loan
            total_with_interest = offer.amount * (1 + offer.interest_rate)
            print(f"\n📋 Loan Summary:")
            print(f"   Lender: {offer.lender_name}")
            print(f"   Amount: ${offer.amount:,.2f}")
            print(f"   Interest: {offer.interest_rate * 100:.1f}%")
            print(f"   Total to repay: ${total_with_interest:,.2f}")
            print(f"   Due date: Day {game_state.day + offer.days_to_repay}")

            confirm = input("\nConfirm loan? (y/n): ").strip().lower()
            if confirm == 'y':
                # Create and add loan
                loan = Loan(
                    lender_name=offer.lender_name,
                    principal=offer.amount,
                    remaining_balance=total_with_interest,
                    interest_rate=offer.interest_rate,
                    early_interest_rate=offer.early_interest_rate,
                    due_day=game_state.day + offer.days_to_repay,
                    taken_day=game_state.day
                )
                player.loans.append(loan)
                player.cash += offer.amount

                print(f"\n✓ Loan approved! ${offer.amount:,.2f} added to your cash.")
                print(f"  Remember to repay ${total_with_interest:,.2f} by day {loan.due_day}!")
            else:
                print("\n✗ Loan cancelled.")
        else:
            print("\n✗ Invalid loan selection!")

    except (ValueError, IndexError):
        print("\n✗ Invalid input!")

    input("\nPress Enter to continue...")


def pay_loan_submenu(game_state: GameState, player: Player) -> None:
    """Submenu for paying back a loan."""
    print("\n" + "=" * 70)
    print("PAY BACK A LOAN")
    print("=" * 70)
    print(f"\nYour Cash: ${player.cash:.2f}")

    for i, loan in enumerate(player.loans, 1):
        days_remaining = loan.due_day - game_state.day
        is_early = days_remaining > 0

        # Calculate early payoff amount
        if is_early:
            early_payoff_amount = loan.principal * (1 + loan.early_interest_rate)
        else:
            early_payoff_amount = loan.remaining_balance

        print(f"\n  {i}. {loan.lender_name}")
        print(f"     Balance Due: ${loan.remaining_balance:,.2f}")
        if is_early:
            print(f"     Early Payoff: ${early_payoff_amount:,.2f} (saves ${loan.remaining_balance - early_payoff_amount:,.2f})")
        print(f"     Due: Day {loan.due_day} ({days_remaining} days {'remaining' if days_remaining > 0 else 'overdue'})")

    print("\n  0. Cancel")

    try:
        choice = input(f"\nSelect loan to pay (1-{len(player.loans)}, 0 to cancel): ").strip()
        choice_num = int(choice)

        if choice_num == 0:
            return

        if 1 <= choice_num <= len(player.loans):
            loan = player.loans[choice_num - 1]
            days_remaining = loan.due_day - game_state.day
            is_early = days_remaining > 0

            # Determine payment amount
            if is_early:
                payment_amount = loan.principal * (1 + loan.early_interest_rate)
                print(f"\n💰 Early Payoff: ${payment_amount:,.2f}")
                print(f"   (Saves ${loan.remaining_balance - payment_amount:,.2f} in interest)")
            else:
                payment_amount = loan.remaining_balance
                print(f"\n💰 Full Payment: ${payment_amount:,.2f}")

            if player.cash < payment_amount:
                print(f"\n✗ Not enough cash! Need ${payment_amount:,.2f}, have ${player.cash:.2f}")
                input("\nPress Enter to continue...")
                return

            confirm = input(f"\nPay ${payment_amount:,.2f} to {loan.lender_name}? (y/n): ").strip().lower()
            if confirm == 'y':
                player.cash -= payment_amount
                player.loans.remove(loan)
                print(f"\n✓ Loan paid off! ${payment_amount:,.2f} paid to {loan.lender_name}.")
                if is_early:
                    print(f"  You saved ${loan.remaining_balance - payment_amount:,.2f} by paying early!")
            else:
                print("\n✗ Payment cancelled.")
        else:
            print("\n✗ Invalid loan selection!")

    except (ValueError, IndexError):
        print("\n✗ Invalid input!")

    input("\nPress Enter to continue...")


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
        total_workers = sum(w.workers for w in player.warehouses)
        print(f"Warehouses: {len(player.warehouses)}/4 | Workers: {total_workers} | Capacity: {player.get_max_inventory()}")
        print(f"Marketing Agents: {player.marketing_agents}")

        # Show loan debt if any
        if player.loans:
            total_debt = sum(loan.remaining_balance for loan in player.loans)
            print(f"Total Debt: ${total_debt:,.2f}")

        print("\nOptions:")
        print("  1. Pass Day (Simulate)")
        print("  2. View Market Prices")
        print("  3. View Vendors")
        print("  4. Auto Buy Orders (Recurring & Stock Minimum)")
        print("  5. Manual Buy Orders (Level 10+, 1000 space minimum)")
        print("  6. Set Sale Prices")
        print("  7. Hire Employees")
        print("  8. View Your Store Status")
        print("  9. Store Upgrades")
        print(" 10. Loans")
        print(" 11. Warehouse Management")
        print(" 12. Discard Inventory")
        print("  c. Customer Forecast")
        print("  s. Save Game")
        print("  0. Quit Game")

        try:
            choice = input("\nSelect option (0-12, c, s): ").strip().lower()

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
                auto_buy_orders_menu(game_state, player)
            elif choice_num == 5:
                buy_order_menu(game_state, player)
            elif choice_num == 6:
                pricing_menu(game_state, player)
            elif choice_num == 7:
                employee_menu(game_state, player)
            elif choice_num == 8:
                display_player_status(player, game_state)
                input("\nPress Enter to continue...")
            elif choice_num == 9:
                upgrades_menu(game_state, player)
            elif choice_num == 10:
                loans_menu(game_state, player)
            elif choice_num == 11:
                warehouse_menu(game_state, player)
            elif choice_num == 12:
                discard_inventory_menu(game_state, player)
            else:
                print("\n✗ Invalid option!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


# -------------------------------------------------------------------
# Save/Load System
# -------------------------------------------------------------------

SAVE_FILE = "economy_sim_save_2_0.json"

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
            {"name": item.name, "base_cost": item.base_cost, "base_price": item.base_price, "category": item.category, "size": item.size}
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
                "lead_time": vendor.lead_time,
                "volume_pricing_tiers": vendor.volume_pricing_tiers,
                "required_reputation": vendor.required_reputation,
                "required_level": vendor.required_level,
                "allowed_categories": vendor.allowed_categories,
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
                "restockers": player.restockers,
                "marketing_agents": player.marketing_agents,
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
                "reputation": player.reputation,
                "average_fulfillment_pct": player.average_fulfillment_pct,
                "allocated_average_fulfillment_pct": player.allocated_average_fulfillment_pct,
                "overflow_average_fulfillment_pct": player.overflow_average_fulfillment_pct,
                "pending_deliveries": player.pending_deliveries,
                "warehouses": [
                    {
                        "level": warehouse.level,
                        "workers": warehouse.workers,
                    }
                    for warehouse in player.warehouses
                ],
                "loans": [
                    {
                        "lender_name": loan.lender_name,
                        "principal": loan.principal,
                        "remaining_balance": loan.remaining_balance,
                        "interest_rate": loan.interest_rate,
                        "early_interest_rate": loan.early_interest_rate,
                        "due_day": loan.due_day,
                        "taken_day": loan.taken_day,
                    }
                    for loan in player.loans
                ],
                "price_history": player.price_history,
                "recurring_buy_orders": [
                    {
                        "item_name": order.item_name,
                        "vendor_name": order.vendor_name,
                        "quantity": order.quantity,
                        "interval_days": order.interval_days,
                        "last_executed_day": order.last_executed_day,
                    }
                    for order in player.recurring_buy_orders
                ],
                "stock_minimum_restock": {k: list(v) for k, v in player.stock_minimum_restock.items()},
                "category_minimum_restock": {k: list(v) for k, v in player.category_minimum_restock.items()},
                "category_pricing": player.category_pricing,
                "category_sales_history": {str(k): v for k, v in player.category_sales_history.items()},  # Convert day (int) to str for JSON
                "items_stocked_today": list(player.items_stocked_today),
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
        "item_demand": game_state.item_demand,
    }


def deserialize_game_state(data: dict) -> GameState:
    """Load GameState from a JSON dictionary."""
    # Recreate config
    config = GameConfig(
        starting_cash=data["config"]["starting_cash"],
        num_days=data["config"]["num_days"],
        customers_per_day=data["config"]["customers_per_day"],
    )

    # Recreate items with backward compatibility for missing category and size
    items = []
    for item_data in data["items"]:
        # Try to find matching item in PRODUCT_CATALOG for backward compatibility
        matching_item = next((item for item in PRODUCT_CATALOG if item.name == item_data["name"]), None)

        # Get category from saved data, or look it up in PRODUCT_CATALOG, or use default
        category = item_data.get("category")
        if not category:
            category = matching_item.category if matching_item else "Food & Groceries"

        # Get size from saved data, or look it up in PRODUCT_CATALOG, or use default
        size = item_data.get("size")
        if size is None:
            size = matching_item.size if matching_item else 1.0

        items.append(Item(
            name=item_data["name"],
            base_cost=item_data["base_cost"],
            base_price=item_data["base_price"],
            category=category,
            size=size
        ))

    # Recreate vendors with backward compatibility for lead_time
    # Map vendor names to their default lead times for backward compatibility
    default_lead_times = {
        "Lucky Deal Trader": 4,
        "Discount Wholesale Co.": 3,
        "Budget Goods Ltd.": 1,
        "Premium Select Inc.": 1,
        "Instant Goods Ltd.": 0,
        "Universal Supply Corp.": 0,
        "Bulk Goods Co.": 1,
        "Cheap Goods Co.": 3,
        "VIP Goods Co.": 1,
    }

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
            lead_time=vendor_data.get("lead_time", default_lead_times.get(vendor_data["name"], 0)),
            volume_pricing_tiers=[tuple(tier) for tier in vendor_data["volume_pricing_tiers"]] if vendor_data.get("volume_pricing_tiers") else None,
            required_reputation=vendor_data.get("required_reputation"),
            required_level=vendor_data.get("required_level"),
            allowed_categories=vendor_data.get("allowed_categories"),
        )
        for vendor_data in data["vendors"]
    ]

    # Backward compatibility: Add any missing vendors from the current vendor list
    # This ensures that if new vendors are added to the game, old save files will get them
    current_vendor_names = {v.name for v in vendors}
    all_vendors = create_vendors()  # Get the current full vendor list

    for default_vendor in all_vendors:
        if default_vendor.name not in current_vendor_names:
            # Add the missing vendor
            vendors.append(default_vendor)
            print(f"✓ Added new vendor to saved game: {default_vendor.name}")

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

        # Convert buy_orders back to lists (needed for append operations)
        buy_orders = {k: list(v) for k, v in player_data["buy_orders"].items()}

        # Recreate warehouses
        warehouses = [
            Warehouse(
                level=warehouse_data["level"],
                workers=warehouse_data["workers"],
            )
            for warehouse_data in player_data.get("warehouses", [Warehouse()])
        ]
        # Ensure at least 1 warehouse for backward compatibility
        if not warehouses:
            warehouses = [Warehouse()]

        # Recreate loans
        loans = [
            Loan(
                lender_name=loan_data["lender_name"],
                principal=loan_data["principal"],
                remaining_balance=loan_data["remaining_balance"],
                interest_rate=loan_data["interest_rate"],
                early_interest_rate=loan_data["early_interest_rate"],
                due_day=loan_data["due_day"],
                taken_day=loan_data["taken_day"],
            )
            for loan_data in player_data.get("loans", [])
        ]

        # Recreate recurring buy orders
        recurring_buy_orders = [
            RecurringBuyOrder(
                item_name=order_data["item_name"],
                vendor_name=order_data["vendor_name"],
                quantity=order_data["quantity"],
                interval_days=order_data["interval_days"],
                last_executed_day=order_data["last_executed_day"],
            )
            for order_data in player_data.get("recurring_buy_orders", [])
        ]

        # Recreate stock minimum restock (convert lists back to tuples)
        stock_minimum_restock = {
            k: tuple(v) for k, v in player_data.get("stock_minimum_restock", {}).items()
        }

        # Recreate category minimum restock (convert lists back to tuples)
        category_minimum_restock = {
            k: tuple(v) for k, v in player_data.get("category_minimum_restock", {}).items()
        }

        # Load category pricing
        category_pricing = player_data.get("category_pricing", {})

        # Load category sales history (convert str keys back to int)
        category_sales_history_raw = player_data.get("category_sales_history", {})
        category_sales_history = {int(k): v for k, v in category_sales_history_raw.items()}

        # Load items stocked today
        items_stocked_today = set(player_data.get("items_stocked_today", []))

        player = Player(
            name=player_data["name"],
            cash=player_data["cash"],
            inventory=player_data["inventory"],
            prices=player_data["prices"],
            buy_orders=buy_orders,
            restockers=player_data.get("restockers", 0),  # Backward compatibility
            marketing_agents=player_data.get("marketing_agents", 0),  # Backward compatibility
            store_level=player_data["store_level"],
            experience=player_data["experience"],
            item_costs=player_data["item_costs"],
            purchased_upgrades=purchased_upgrades,
            is_human=player_data["is_human"],
            last_wage_payment_day=player_data.get("last_wage_payment_day", 0),
            vendor_partnership_expiration=player_data.get("vendor_partnership_expiration", {}),
            reputation=player_data.get("reputation", 0.0),
            average_fulfillment_pct=player_data.get("average_fulfillment_pct", 70.0),
            allocated_average_fulfillment_pct=player_data.get("allocated_average_fulfillment_pct", 70.0),
            overflow_average_fulfillment_pct=player_data.get("overflow_average_fulfillment_pct", 70.0),
            pending_deliveries=[tuple(delivery) for delivery in player_data.get("pending_deliveries", [])],
            warehouses=warehouses,
            loans=loans,
            price_history=player_data.get("price_history", {}),
            recurring_buy_orders=recurring_buy_orders,
            stock_minimum_restock=stock_minimum_restock,
            category_minimum_restock=category_minimum_restock,
            category_pricing=category_pricing,
            category_sales_history=category_sales_history,
            items_stocked_today=items_stocked_today,
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
        item_demand=data.get("item_demand", {}),
    )

    # Backward compatibility: Initialize item_demand for any items that don't have it
    if game_state.item_demand:
        for item in game_state.items:
            if item.name not in game_state.item_demand:
                game_state.item_demand[item.name] = 1.0
    else:
        # If no item_demand data at all, initialize it
        game_state.item_demand = initialize_item_demand(game_state.items)

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
                # Refresh vendor inventory to ensure vendors have proper stock for current day
                refresh_vendor_inventory(game_state.vendors, game_state.items, game_state.market_prices)
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
        print(f"Customers formula: (num_players × 50) + (day_number × 5) + scaling bonuses")

        # Initialize items, vendors
        items = create_default_items()
        vendors = create_vendors()
        market_prices = initialize_market_prices(items)
        item_demand = initialize_item_demand(items)

        # Initialize vendor inventory for day 1
        refresh_vendor_inventory(vendors, items, market_prices)

        all_players = human_players

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
            unlocked_product_indices=list(range(60)),  # Start with first 60 products unlocked
            item_demand=item_demand,
        )

        # Set global game state for signal handler
        _current_game_state = game_state

        # Show initial setup
        print("\n" + "=" * 60)
        print("GAME SETUP COMPLETE")
        print("=" * 60)
        print(f"\nPlayers:")
        for player in human_players:
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
