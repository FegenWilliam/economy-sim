# econ_sim.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
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


# Product catalog - items that can be unlocked over time
PRODUCT_CATALOG = [
    # Groceries & Food
    Item("Bread", 2.0, 5.0, "Food & Groceries"),
    Item("Milk", 3.0, 6.0, "Food & Groceries"),
    Item("Eggs", 2.5, 5.5, "Food & Groceries"),
    Item("Bananas", 1.5, 3.5, "Fresh Produce"),
    Item("Batteries", 5.0, 10.0, "Household Essentials"),
    Item("Rice", 5.0, 10.0, "Food & Groceries"),
    Item("Coffee", 6.0, 12.0, "Food & Groceries"),
    Item("Toilet Paper", 8.0, 15.0, "Household Essentials"),
    Item("Vitamins", 12.0, 24.0, "Supplements"),
    Item("Cheese", 4.0, 8.0, "Food & Groceries"),
    Item("Butter", 3.5, 7.0, "Food & Groceries"),
    Item("Yogurt", 2.0, 4.5, "Food & Groceries"),
    Item("Cereal", 3.0, 6.5, "Food & Groceries"),
    Item("Pasta", 2.0, 4.0, "Food & Groceries"),
    Item("Canned Soup", 1.5, 3.5, "Food & Groceries"),
    Item("Frozen Pizza", 4.0, 8.5, "Food & Groceries"),
    Item("Ice Cream", 3.5, 7.5, "Food & Groceries"),
    Item("Soda", 1.5, 3.0, "Food & Groceries"),
    Item("Orange Juice", 3.0, 6.0, "Food & Groceries"),
    Item("Tea Bags", 3.0, 6.5, "Food & Groceries"),
    Item("Sugar", 2.0, 4.5, "Food & Groceries"),
    Item("Flour", 3.0, 6.0, "Food & Groceries"),
    Item("Cooking Oil", 4.0, 8.0, "Food & Groceries"),
    Item("Salt", 1.0, 2.5, "Food & Groceries"),
    Item("Pepper", 2.0, 4.5, "Food & Groceries"),
    Item("Ketchup", 2.5, 5.0, "Food & Groceries"),
    Item("Mustard", 2.0, 4.5, "Food & Groceries"),
    Item("Mayo", 3.0, 6.0, "Food & Groceries"),
    Item("BBQ Sauce", 3.5, 7.0, "Food & Groceries"),

    # Fresh Produce
    Item("Apples", 2.5, 5.5, "Fresh Produce"),
    Item("Oranges", 3.0, 6.0, "Fresh Produce"),
    Item("Grapes", 4.0, 8.5, "Fresh Produce"),
    Item("Strawberries", 4.5, 9.0, "Fresh Produce"),
    Item("Tomatoes", 2.5, 5.5, "Fresh Produce"),
    Item("Lettuce", 2.0, 4.5, "Fresh Produce"),
    Item("Carrots", 1.5, 3.5, "Fresh Produce"),
    Item("Potatoes", 2.0, 4.0, "Fresh Produce"),
    Item("Onions", 1.5, 3.5, "Fresh Produce"),

    # Household Items
    Item("Paper Towels", 5.0, 10.0, "Household Essentials"),
    Item("Dish Soap", 3.0, 6.5, "Household Essentials"),
    Item("Laundry Detergent", 8.0, 16.0, "Household Essentials"),
    Item("Trash Bags", 5.0, 10.5, "Household Essentials"),
    Item("Sponges", 2.5, 5.5, "Household Essentials"),
    Item("Aluminum Foil", 4.0, 8.5, "Household Essentials"),
    Item("Plastic Wrap", 3.5, 7.5, "Household Essentials"),
    Item("Light Bulbs", 6.0, 12.0, "Household Essentials"),
    Item("Candles", 4.0, 8.5, "Household Essentials"),
    Item("Air Freshener", 3.5, 7.5, "Household Essentials"),

    # Personal Care
    Item("Shampoo", 5.0, 10.0, "Personal Care"),
    Item("Conditioner", 5.0, 10.0, "Personal Care"),
    Item("Body Wash", 4.5, 9.0, "Personal Care"),
    Item("Toothpaste", 3.0, 6.5, "Personal Care"),
    Item("Toothbrush", 2.5, 5.5, "Personal Care"),
    Item("Deodorant", 4.0, 8.5, "Personal Care"),
    Item("Razor Blades", 8.0, 16.0, "Personal Care"),
    Item("Shaving Cream", 4.5, 9.0, "Personal Care"),
    Item("Hand Soap", 3.0, 6.5, "Personal Care"),
    Item("Hand Sanitizer", 3.5, 7.5, "Personal Care"),
    Item("Tissues", 2.5, 5.5, "Personal Care"),
    Item("Cotton Swabs", 2.0, 4.5, "Personal Care"),

    # Electronics
    Item("Phone Charger", 8.0, 16.0, "Electronics"),
    Item("USB Cable", 5.0, 10.0, "Electronics"),
    Item("Earbuds", 12.0, 25.0, "Electronics"),
    Item("Phone Case", 10.0, 20.0, "Electronics"),
    Item("Screen Protector", 6.0, 12.0, "Electronics"),
    Item("Mouse Pad", 7.0, 15.0, "Electronics"),
    Item("Keyboard", 25.0, 50.0, "Electronics"),
    Item("Computer Mouse", 15.0, 30.0, "Electronics"),
    Item("Webcam", 35.0, 70.0, "Electronics"),
    Item("Microphone", 40.0, 80.0, "Electronics"),
    Item("USB Flash Drive", 10.0, 20.0, "Electronics"),
    Item("SD Card", 12.0, 25.0, "Electronics"),
    Item("HDMI Cable", 8.0, 16.0, "Electronics"),
    Item("Power Strip", 15.0, 30.0, "Electronics"),
    Item("Desk Lamp", 20.0, 40.0, "Electronics"),
    Item("Alarm Clock", 12.0, 25.0, "Electronics"),
    Item("Calculator", 10.0, 20.0, "Electronics"),
    Item("Portable Speaker", 30.0, 60.0, "Electronics"),
    Item("Bluetooth Headphones", 45.0, 90.0, "Electronics"),

    # Office Supplies
    Item("Pens", 3.0, 6.5, "Office Supplies"),
    Item("Pencils", 2.5, 5.5, "Office Supplies"),
    Item("Notebooks", 4.0, 8.5, "Office Supplies"),
    Item("Sticky Notes", 3.5, 7.5, "Office Supplies"),
    Item("Stapler", 8.0, 16.0, "Office Supplies"),
    Item("Tape Dispenser", 6.0, 12.0, "Office Supplies"),
    Item("Scissors", 5.0, 10.0, "Office Supplies"),
    Item("Ruler", 2.0, 4.5, "Office Supplies"),
    Item("Binder", 4.5, 9.0, "Office Supplies"),
    Item("File Folders", 6.0, 12.5, "Office Supplies"),
    Item("Printer Paper", 15.0, 30.0, "Office Supplies"),

    # Mid-range Electronics & Gaming
    Item("Tablet", 150.0, 300.0, "Electronics"),
    Item("E-Reader", 80.0, 160.0, "Electronics"),
    Item("Smart Watch", 120.0, 240.0, "Luxury"),
    Item("Fitness Tracker", 60.0, 120.0, "Electronics"),
    Item("Wireless Earbuds", 70.0, 140.0, "Electronics"),
    Item("Gaming Mouse", 45.0, 90.0, "Gaming"),
    Item("Gaming Keyboard", 60.0, 120.0, "Gaming"),
    Item("Monitor", 150.0, 300.0, "Electronics"),
    Item("External Hard Drive", 55.0, 110.0, "Electronics"),
    Item("Wireless Router", 50.0, 100.0, "Electronics"),
    Item("Smart Plug", 15.0, 30.0, "Electronics"),
    Item("Security Camera", 40.0, 80.0, "Electronics"),
    Item("Video Doorbell", 80.0, 160.0, "Electronics"),

    # Appliances & Home Electronics
    Item("Coffee Maker", 40.0, 80.0, "Appliances"),
    Item("Toaster", 25.0, 50.0, "Appliances"),
    Item("Blender", 35.0, 70.0, "Appliances"),
    Item("Microwave", 80.0, 160.0, "Appliances"),
    Item("Air Fryer", 70.0, 140.0, "Appliances"),
    Item("Slow Cooker", 35.0, 70.0, "Appliances"),
    Item("Electric Kettle", 30.0, 60.0, "Appliances"),
    Item("Hair Dryer", 25.0, 50.0, "Appliances"),
    Item("Iron", 20.0, 40.0, "Appliances"),
    Item("Vacuum Cleaner", 120.0, 240.0, "Appliances"),
    Item("Fan", 35.0, 70.0, "Appliances"),
    Item("Space Heater", 45.0, 90.0, "Appliances"),
    Item("Humidifier", 40.0, 80.0, "Appliances"),
    Item("Air Purifier", 90.0, 180.0, "Appliances"),

    # Expensive Electronics & Gaming
    Item("Laptop", 400.0, 800.0, "Gaming"),
    Item("Gaming Console", 300.0, 600.0, "Gaming"),
    Item("4K TV", 350.0, 700.0, "Gaming"),
    Item("Soundbar", 150.0, 300.0, "Electronics"),
    Item("Noise-Cancelling Headphones", 180.0, 360.0, "Gaming"),
    Item("Drone", 250.0, 500.0, "Luxury"),
    Item("VR Headset", 300.0, 600.0, "Gaming"),
    Item("Digital Camera", 400.0, 800.0, "Luxury"),
    Item("Projector", 300.0, 600.0, "Electronics"),
    Item("Smart Thermostat", 120.0, 240.0, "Electronics"),
    Item("Robot Vacuum", 200.0, 400.0, "Appliances"),
    Item("Electric Scooter", 350.0, 700.0, "Luxury"),

    # Luxury Items
    Item("Designer Handbag", 600.0, 1200.0, "Luxury"),
    Item("Leather Wallet", 100.0, 200.0, "Luxury"),
    Item("Sunglasses", 150.0, 300.0, "Luxury"),
    Item("Perfume", 80.0, 160.0, "Luxury"),
    Item("Cologne", 70.0, 140.0, "Luxury"),
    Item("Watch", 200.0, 400.0, "Luxury"),
    Item("Jewelry Box", 60.0, 120.0, "Luxury"),
    Item("Gold Necklace", 500.0, 1000.0, "Luxury"),
    Item("Silver Bracelet", 150.0, 300.0, "Luxury"),
    Item("Diamond Earrings", 800.0, 1600.0, "Luxury"),
    Item("Designer Shoes", 300.0, 600.0, "Luxury"),
    Item("Leather Jacket", 250.0, 500.0, "Luxury"),
    Item("Cashmere Sweater", 180.0, 360.0, "Luxury"),
    Item("Silk Scarf", 80.0, 160.0, "Luxury"),
    Item("Designer Jeans", 120.0, 240.0, "Luxury"),

    # Sports & Outdoor
    Item("Yoga Mat", 20.0, 40.0, "Sports & Outdoor"),
    Item("Dumbbells", 30.0, 60.0, "Sports & Outdoor"),
    Item("Tennis Racket", 60.0, 120.0, "Sports & Outdoor"),
    Item("Basketball", 15.0, 30.0, "Sports & Outdoor"),
    Item("Camping Tent", 100.0, 200.0, "Sports & Outdoor"),
    Item("Sleeping Bag", 50.0, 100.0, "Sports & Outdoor"),
    Item("Hiking Boots", 80.0, 160.0, "Sports & Outdoor"),

    # More Groceries & Food
    Item("Peanut Butter", 4.0, 8.0, "Food & Groceries"),
    Item("Jelly", 3.0, 6.0, "Food & Groceries"),
    Item("Honey", 5.0, 10.0, "Food & Groceries"),
    Item("Maple Syrup", 6.0, 12.0, "Food & Groceries"),
    Item("Crackers", 3.0, 6.0, "Food & Groceries"),
    Item("Chips", 2.5, 5.0, "Food & Groceries"),
    Item("Pretzels", 2.5, 5.0, "Food & Groceries"),
    Item("Popcorn", 2.0, 4.0, "Food & Groceries"),
    Item("Cookies", 3.5, 7.0, "Food & Groceries"),
    Item("Cake Mix", 3.0, 6.0, "Food & Groceries"),
    Item("Brownie Mix", 3.0, 6.0, "Food & Groceries"),
    Item("Chocolate Bar", 1.5, 3.0, "Food & Groceries"),
    Item("Candy", 1.0, 2.5, "Food & Groceries"),
    Item("Gum", 1.0, 2.5, "Food & Groceries"),
    Item("Mints", 1.5, 3.0, "Food & Groceries"),
    Item("Granola Bars", 4.0, 8.0, "Food & Groceries"),
    Item("Energy Bars", 5.0, 10.0, "Food & Groceries"),
    Item("Protein Powder", 25.0, 50.0, "Supplements"),
    Item("Fish Oil", 15.0, 30.0, "Supplements"),
    Item("Canned Tuna", 1.5, 3.5, "Food & Groceries"),
    Item("Canned Beans", 1.5, 3.5, "Food & Groceries"),
    Item("Canned Corn", 1.5, 3.5, "Food & Groceries"),
    Item("Canned Tomatoes", 2.0, 4.0, "Food & Groceries"),
    Item("Tomato Sauce", 2.0, 4.5, "Food & Groceries"),
    Item("Spaghetti Sauce", 3.0, 6.5, "Food & Groceries"),
    Item("Hot Sauce", 2.5, 5.5, "Food & Groceries"),
    Item("Soy Sauce", 3.0, 6.0, "Food & Groceries"),
    Item("Vinegar", 2.0, 4.5, "Food & Groceries"),
    Item("Olive Oil", 8.0, 16.0, "Food & Groceries"),
    Item("Coconut Oil", 9.0, 18.0, "Food & Groceries"),
    Item("Protein Shake", 4.0, 8.0, "Supplements"),
    Item("Sports Drink", 2.0, 4.5, "Food & Groceries"),
    Item("Energy Drink", 3.0, 6.0, "Food & Groceries"),
    Item("Bottled Water", 1.0, 2.5, "Food & Groceries"),
    Item("Sparkling Water", 1.5, 3.5, "Food & Groceries"),
    Item("Iced Tea", 2.0, 4.5, "Food & Groceries"),
    Item("Lemonade", 2.5, 5.5, "Food & Groceries"),

    # Pet Supplies
    Item("Dog Food", 15.0, 30.0, "Pet Supplies"),
    Item("Cat Food", 12.0, 24.0, "Pet Supplies"),
    Item("Dog Treats", 5.0, 10.0, "Pet Supplies"),
    Item("Cat Treats", 4.0, 8.0, "Pet Supplies"),
    Item("Dog Toy", 6.0, 12.0, "Pet Supplies"),
    Item("Cat Toy", 4.0, 8.0, "Pet Supplies"),
    Item("Pet Bowl", 8.0, 16.0, "Pet Supplies"),
    Item("Pet Collar", 10.0, 20.0, "Pet Supplies"),
    Item("Pet Leash", 12.0, 24.0, "Pet Supplies"),
    Item("Cat Litter", 10.0, 20.0, "Pet Supplies"),
    Item("Fish Tank", 40.0, 80.0, "Pet Supplies"),
    Item("Fish Food", 4.0, 8.0, "Pet Supplies"),
    Item("Bird Cage", 50.0, 100.0, "Pet Supplies"),
    Item("Bird Seed", 6.0, 12.0, "Pet Supplies"),

    # Baby Products
    Item("Diapers", 20.0, 40.0, "Baby Products"),
    Item("Baby Wipes", 5.0, 10.0, "Baby Products"),
    Item("Baby Formula", 25.0, 50.0, "Baby Products"),
    Item("Baby Bottle", 8.0, 16.0, "Baby Products"),
    Item("Pacifier", 4.0, 8.0, "Baby Products"),
    Item("Baby Lotion", 6.0, 12.0, "Baby Products"),
    Item("Baby Shampoo", 5.0, 10.0, "Baby Products"),
    Item("Baby Powder", 4.0, 8.0, "Baby Products"),
    Item("Diaper Bag", 30.0, 60.0, "Baby Products"),
    Item("Baby Blanket", 15.0, 30.0, "Baby Products"),
    Item("Teething Ring", 5.0, 10.0, "Baby Products"),

    # Pharmacy & Health
    Item("Pain Reliever", 8.0, 16.0, "Health & Pharmacy"),
    Item("Cold Medicine", 10.0, 20.0, "Health & Pharmacy"),
    Item("Allergy Medicine", 12.0, 24.0, "Health & Pharmacy"),
    Item("Band-Aids", 4.0, 8.0, "Health & Pharmacy"),
    Item("First Aid Kit", 20.0, 40.0, "Health & Pharmacy"),
    Item("Thermometer", 15.0, 30.0, "Health & Pharmacy"),
    Item("Cough Drops", 3.0, 6.0, "Health & Pharmacy"),
    Item("Antacid", 6.0, 12.0, "Health & Pharmacy"),
    Item("Eye Drops", 8.0, 16.0, "Health & Pharmacy"),
    Item("Lip Balm", 2.0, 4.5, "Health & Pharmacy"),
    Item("Sunscreen", 10.0, 20.0, "Health & Pharmacy"),
    Item("Bug Spray", 7.0, 14.0, "Health & Pharmacy"),

    # Kitchen & Dining
    Item("Plates Set", 20.0, 40.0, "Kitchen & Dining"),
    Item("Bowls Set", 15.0, 30.0, "Kitchen & Dining"),
    Item("Cups Set", 12.0, 24.0, "Kitchen & Dining"),
    Item("Silverware Set", 25.0, 50.0, "Kitchen & Dining"),
    Item("Cooking Pot", 30.0, 60.0, "Kitchen & Dining"),
    Item("Frying Pan", 25.0, 50.0, "Kitchen & Dining"),
    Item("Baking Sheet", 12.0, 24.0, "Kitchen & Dining"),
    Item("Mixing Bowl", 10.0, 20.0, "Kitchen & Dining"),
    Item("Cutting Board", 15.0, 30.0, "Kitchen & Dining"),
    Item("Kitchen Knife", 20.0, 40.0, "Kitchen & Dining"),
    Item("Can Opener", 8.0, 16.0, "Kitchen & Dining"),
    Item("Bottle Opener", 5.0, 10.0, "Kitchen & Dining"),
    Item("Measuring Cups", 10.0, 20.0, "Kitchen & Dining"),
    Item("Measuring Spoons", 8.0, 16.0, "Kitchen & Dining"),
    Item("Spatula", 7.0, 14.0, "Kitchen & Dining"),
    Item("Whisk", 6.0, 12.0, "Kitchen & Dining"),
    Item("Tongs", 8.0, 16.0, "Kitchen & Dining"),
    Item("Ladle", 7.0, 14.0, "Kitchen & Dining"),
    Item("Colander", 12.0, 24.0, "Kitchen & Dining"),
    Item("Grater", 10.0, 20.0, "Kitchen & Dining"),

    # Home Decor
    Item("Picture Frame", 12.0, 24.0, "Home Decor"),
    Item("Wall Art", 25.0, 50.0, "Home Decor"),
    Item("Throw Pillow", 15.0, 30.0, "Home Decor"),
    Item("Blanket", 25.0, 50.0, "Household Essentials"),
    Item("Curtains", 30.0, 60.0, "Home Decor"),
    Item("Area Rug", 60.0, 120.0, "Home Decor"),
    Item("Table Lamp", 35.0, 70.0, "Home Decor"),
    Item("Floor Lamp", 50.0, 100.0, "Home Decor"),
    Item("Wall Clock", 20.0, 40.0, "Home Decor"),
    Item("Vase", 18.0, 36.0, "Home Decor"),
    Item("Candle Holder", 12.0, 24.0, "Home Decor"),
    Item("Plant Pot", 10.0, 20.0, "Home Decor"),
    Item("Fake Plant", 15.0, 30.0, "Home Decor"),
    Item("Mirror", 40.0, 80.0, "Home Decor"),

    # Garden & Outdoor
    Item("Garden Hose", 25.0, 50.0, "Sports & Outdoor"),
    Item("Sprinkler", 20.0, 40.0, "Sports & Outdoor"),
    Item("Garden Gloves", 8.0, 16.0, "Sports & Outdoor"),
    Item("Plant Seeds", 3.0, 6.0, "Sports & Outdoor"),
    Item("Fertilizer", 12.0, 24.0, "Sports & Outdoor"),
    Item("Potting Soil", 10.0, 20.0, "Sports & Outdoor"),
    Item("Weed Killer", 15.0, 30.0, "Sports & Outdoor"),
    Item("Lawn Mower", 200.0, 400.0, "Sports & Outdoor"),
    Item("Rake", 18.0, 36.0, "Sports & Outdoor"),
    Item("Shovel", 22.0, 44.0, "Sports & Outdoor"),
    Item("Garden Shears", 15.0, 30.0, "Sports & Outdoor"),
    Item("Watering Can", 12.0, 24.0, "Sports & Outdoor"),
    Item("BBQ Grill", 150.0, 300.0, "Sports & Outdoor"),
    Item("Charcoal", 10.0, 20.0, "Sports & Outdoor"),
    Item("Lighter Fluid", 6.0, 12.0, "Sports & Outdoor"),
    Item("Patio Furniture", 250.0, 500.0, "Luxury"),

    # Toys & Games
    Item("Board Game", 20.0, 40.0, "Toys & Games"),
    Item("Puzzle", 15.0, 30.0, "Toys & Games"),
    Item("Playing Cards", 5.0, 10.0, "Toys & Games"),
    Item("Action Figure", 12.0, 24.0, "Toys & Games"),
    Item("Doll", 18.0, 36.0, "Toys & Games"),
    Item("Stuffed Animal", 15.0, 30.0, "Toys & Games"),
    Item("Building Blocks", 25.0, 50.0, "Toys & Games"),
    Item("Art Supplies", 20.0, 40.0, "Toys & Games"),
    Item("Crayons", 4.0, 8.0, "Toys & Games"),
    Item("Coloring Book", 5.0, 10.0, "Toys & Games"),
    Item("Play-Doh", 8.0, 16.0, "Toys & Games"),
    Item("Remote Control Car", 40.0, 80.0, "Toys & Games"),
    Item("Nerf Gun", 25.0, 50.0, "Toys & Games"),
    Item("Water Gun", 10.0, 20.0, "Toys & Games"),
    Item("Frisbee", 8.0, 16.0, "Sports & Outdoor"),
    Item("Soccer Ball", 18.0, 36.0, "Sports & Outdoor"),
    Item("Football", 20.0, 40.0, "Sports & Outdoor"),
    Item("Baseball Glove", 35.0, 70.0, "Sports & Outdoor"),
    Item("Baseball Bat", 30.0, 60.0, "Sports & Outdoor"),

    # Automotive
    Item("Car Phone Mount", 15.0, 30.0, "Automotive"),
    Item("Car Charger", 12.0, 24.0, "Automotive"),
    Item("Jumper Cables", 25.0, 50.0, "Automotive"),
    Item("Car Air Freshener", 3.0, 6.0, "Automotive"),
    Item("Windshield Wiper", 18.0, 36.0, "Automotive"),
    Item("Motor Oil", 20.0, 40.0, "Automotive"),
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
    effect_type: str  # "max_customers", "max_items", "max_products", "xp_gain", "vendor_discount", "lead_time_reduction", "wage_reduction", "production_line"
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
    buy_orders: Dict[str, List[tuple]] = field(default_factory=dict)  # item_name -> [(quantity, vendor_name), ...] (up to 3 vendors)
    restockers: int = 0  # Each restocker adds 500 items per day capacity
    marketing_agents: int = 0  # Marketing agents boost customer attraction
    store_level: int = 1  # Limits how many different products can be stocked (starts at 3)
    experience: float = 0.0  # XP gained from profits
    item_costs: Dict[str, float] = field(default_factory=dict)  # Track cost per item for profit calculation
    purchased_upgrades: List['Upgrade'] = field(default_factory=list)  # Upgrades bought by this player
    is_human: bool = False  # Whether this is a human-controlled player
    reputation: float = 0.0  # Store reputation from -100 to 100, affects customer choice
    average_fulfillment_pct: float = 70.0  # Average % of customer needs fulfilled (used for scoring)
    last_wage_payment_day: int = 0  # Track when wages were last paid (for 30-day wage cycle)
    vendor_partnership_expiration: Dict[str, int] = field(default_factory=dict)  # upgrade_name -> expiration_day (for temporary vendor partnerships)
    price_history: Dict[str, float] = field(default_factory=dict)  # item_name -> previous_price (for consistency tracking)
    pending_deliveries: List[tuple] = field(default_factory=list)  # List of (item_name, quantity, cost_per_item, delivery_day) for orders with lead time

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

    def get_max_products(self) -> int:
        """Get max number of different products based on store level and upgrades."""
        base = 3 + (self.store_level - 1)  # Level 1 = 3, Level 2 = 4, etc.
        bonus = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "max_products")
        return int(base + bonus)

    def get_max_items_per_day(self) -> int:
        """Get max number of items that can be bought per day (buy order limit)."""
        base = 300 + ((self.store_level - 1) * 100)  # Base 300 items + 100 per level
        bonus = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "max_items")
        restocker_bonus = self.restockers * 500  # Each restocker adds 500 items per day
        return int(base + bonus + restocker_bonus)

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

    def hire_employee(self, employee_type: str) -> bool:
        """
        Hire an employee.
        - Restocker: $1000 upfront, $1000/month
        - Marketing Agent: 5x scaling cost (1k, 5k, 25k...), $1000/month, requires level 5+
        Returns True if successful, False if not enough cash or requirements not met.
        """
        if employee_type == "restocker":
            HIRING_COST = 1000.0
            if self.cash < HIRING_COST:
                return False
            self.cash -= HIRING_COST
            self.restockers += 1
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
        Pay monthly wages for all employees ($1000 per employee every 30 days).
        Only pays if 30 days have passed since last payment.
        Returns total wages paid (0 if not a payment day).
        """
        # Check if it's time to pay wages (every 30 days)
        if current_day - self.last_wage_payment_day < 30:
            return 0.0

        total_employees = self.restockers + self.marketing_agents

        # No wages if no employees
        if total_employees == 0:
            return 0.0

        monthly_wage_per_employee = 1000.0

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
        Tracks previous price for consistency bonus calculation.
        """
        if price <= 0:
            raise ValueError(f"Price must be positive: {price}")

        # Save previous price for consistency tracking
        if item_name in self.prices:
            self.price_history[item_name] = self.prices[item_name]

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
        Checks reputation requirements.
        """
        if quantity <= 0:
            return False

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
            # Use vendor pricing with volume discounts
            vendor_price = vendor.get_price(item_name, quantity)
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

        # Check if vendor has lead time
        if vendor.lead_time > 0 and game_state is not None:
            # Calculate effective lead time with any reductions from upgrades
            lead_time_reduction = sum(u.effect_value for u in self.purchased_upgrades if u.effect_type == "lead_time_reduction")
            effective_lead_time = max(0, vendor.lead_time - int(lead_time_reduction))

            # Add to pending deliveries instead of inventory (or immediate if lead time reduced to 0)
            if effective_lead_time > 0:
                delivery_day = game_state.day + effective_lead_time
                self.pending_deliveries.append((item_name, quantity, final_price, delivery_day))
            else:
                # Lead time reduced to 0, deliver immediately
                current_inventory = self.inventory.get(item_name, 0)
                current_cost = self.item_costs.get(item_name, 0)

                # Weighted average: (old_qty * old_cost + new_qty * new_cost) / total_qty
                new_total_qty = current_inventory + quantity
                if new_total_qty > 0:
                    weighted_cost = ((current_inventory * current_cost) + (quantity * final_price)) / new_total_qty
                    self.item_costs[item_name] = weighted_cost

                self.inventory[item_name] = new_total_qty
        else:
            # Immediate delivery - update inventory and weighted average cost
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
    customer_type: str = "medium"  # "low", "medium", "high", "uncapped", or special types
    budget: float = 0.0
    day: int = 0  # Current game day for budget scaling

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
            max_items = 10
        elif self.customer_type == "high":
            max_items = 15
        else:
            max_items = 5  # Default fallback

        # Keep buying items until we hit the item limit or run out of budget
        total_items = 0

        while total_items < max_items and remaining_budget > 0 and available_items:
            # Filter to only affordable items with valid pricing
            affordable_items = [
                item for item in available_items
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

    def choose_supplier_by_reputation(
        self,
        players: List[Player],
        needs: List[CustomerNeed],
        market_prices: Dict[str, float],
        items_by_name: Dict[str, Item],
        all_available_items: List[Item]
    ) -> Optional[Player]:
        """
        Choose a supplier based on reputation, discount scores, availability, and fulfillment.

        Formula:
        - reputation_multiplier = 10 ** (reputation / 100)
        - For each item in needs, calculate discount % weighted by importance (only for stocked items)
        - discount_score = sum((market_price - player_price) / market_price * 100 * importance)
        - item_stability = sum of (proximity_score + consistency_bonus) * importance for all stocked items
          * proximity_score: 10 if within 5% of market, -1 per 1% beyond 5%
          * consistency_bonus: +2 if price change <= 5% from previous
        - availability_multiplier based on % of catalog items in stock (global, not customer-specific):
          * >= 100%: ×1.2
          * >= 80%: ×1.1
          * < 50%: ×0.8
          * < 20%: ×0.5
        - fulfillment_multiplier based on average % customer needs fulfilled (from past performance):
          * <20%: ×0.5
          * 20-50%: ×0.9
          * 50-90%: ×1.0
          * 90-99%: ×1.4
          * 100%: ×2.0
        - final_score = (discount_score + item_stability) * reputation_multiplier * availability_multiplier * fulfillment_multiplier

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

            # Calculate GLOBAL availability: % of catalog items this store has in stock
            items_in_stock = sum(1 for qty in player.inventory.values() if qty > 0)
            availability_pct = (items_in_stock / total_catalog_items) * 100 if total_catalog_items > 0 else 0

            # Calculate availability multiplier
            if availability_pct >= 100:
                availability_multiplier = 1.2
            elif availability_pct >= 80:
                availability_multiplier = 1.1
            elif availability_pct < 20:
                availability_multiplier = 0.5
            elif availability_pct < 50:
                availability_multiplier = 0.8
            else:
                availability_multiplier = 1.0  # 50-79%

            # Calculate fulfillment multiplier based on historical performance
            fulfillment_pct = player.average_fulfillment_pct
            if fulfillment_pct >= 100:
                fulfillment_multiplier = 2.0
            elif fulfillment_pct >= 90:
                fulfillment_multiplier = 1.4
            elif fulfillment_pct >= 50:
                fulfillment_multiplier = 1.0
            elif fulfillment_pct >= 20:
                fulfillment_multiplier = 0.9
            else:
                fulfillment_multiplier = 0.5

            # Calculate reputation multiplier
            reputation = player.reputation
            reputation_multiplier = 10 ** (reputation / 100)

            # Calculate item stability score
            item_stability = calculate_item_stability(player, market_prices, items_by_name)

            # Calculate marketing effect (adds to both discount and stability)
            marketing_effect = calculate_marketing_effect(player, market_prices)

            # Calculate final score (marketing effect boosts both components)
            final_score = (discount_score + marketing_effect + item_stability + marketing_effect) * reputation_multiplier * availability_multiplier * fulfillment_multiplier

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
    starting_cash: float = 5000.0
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
    Returns first 6 items from product catalog.
    """
    # Start with first 6 items (Bread, Milk, Eggs, Coffee, Toilet Paper, Vitamins)
    return [PRODUCT_CATALOG[0], PRODUCT_CATALOG[1], PRODUCT_CATALOG[2],
            PRODUCT_CATALOG[3], PRODUCT_CATALOG[4], PRODUCT_CATALOG[5]]


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
    Create 7 vendors with different pricing and selection strategies.

    Vendor inventory is refreshed daily based on their selection type.
    """
    vendors = []

    # Vendor 1: Bulk Goods Co. - 85% of market price, min 100 per purchase, items $30 or less, 1 day lead time
    vendors.append(Vendor(
        name="Bulk Goods Co.",
        pricing_multiplier=0.85,
        selection_type="price_range",
        selection_params=0,
        min_purchase=100,
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

    # Vendor 3: Universal Supply Corp. - 105% of market price, all items available, instant delivery (no lead time)
    vendors.append(Vendor(
        name="Universal Supply Corp.",
        pricing_multiplier=1.05,
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

    return vendors


def refresh_vendor_inventory(vendors: List[Vendor], items: List[Item], market_prices: Dict[str, float]) -> None:
    """
    Refresh vendor inventory based on their selection type and current market prices.

    This should be called at the start of each day.
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
                    vendor.items[item.name] = market_price * vendor.pricing_multiplier

        elif vendor.selection_type == "price_threshold":
            # Select all items where market price is at or under threshold
            price_threshold = vendor.selection_params
            for item in available_items:
                market_price = market_prices.get(item.name, item.base_price)
                if market_price <= price_threshold:
                    vendor.items[item.name] = market_price * vendor.pricing_multiplier

        elif vendor.selection_type == "price_range":
            # Select items within a price range (min and/or max)
            for item in available_items:
                market_price = market_prices.get(item.name, item.base_price)
                # Check if price is within range
                if vendor.price_min is not None and market_price < vendor.price_min:
                    continue
                if vendor.price_max is not None and market_price > vendor.price_max:
                    continue
                vendor.items[item.name] = market_price * vendor.pricing_multiplier

        elif vendor.selection_type == "all":
            # Include all items
            for item in available_items:
                market_price = market_prices.get(item.name, item.base_price)
                vendor.items[item.name] = market_price * vendor.pricing_multiplier

        elif vendor.selection_type == "category":
            # Select items from allowed categories only (already filtered above)
            for item in available_items:
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

    # Step 2: Apply random changes to 1/4 of items
    num_items_to_update = max(1, (len(game_state.items) + 3) // 4)  # Ceiling division

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
        # Buyout capacity upgrades
        Upgrade(name="Warehouse Extension", cost=5000, effect_type="max_items", effect_value=400),
        Upgrade(name="Loading Dock", cost=10000, effect_type="max_items", effect_value=600),

        # Max different items upgrades
        Upgrade(name="Additional Shelving", cost=2000, effect_type="max_products", effect_value=2),
        Upgrade(name="Display Cases", cost=3500, effect_type="max_products", effect_value=3),

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

def apply_daily_price_fluctuation(market_prices: Dict[str, float], items: List[Item]) -> None:
    """
    Apply daily price fluctuation to 1-2 random items.
    Fluctuation ranges based on item importance:
    - Importance 3 (essentials): 3-6% (more stable)
    - Importance 2 (medium): 5-10% (baseline)
    - Importance 1 (luxury): 7-14% (more volatile)
    """
    if not items:
        return

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

    # Execute orders in order, respecting item limit
    for item_name, quantity, vendor, price in active_orders:
        if total_items_bought >= max_items:
            break  # Reached restocker limit

        # Check if player already has too many different products
        current_products = len([item for item, qty in player.inventory.items() if qty > 0])
        if player.inventory.get(item_name, 0) == 0 and current_products >= max_products:
            continue  # Skip this item, store is full of different products

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
# Daily simulation logic
# -------------------------------------------------------------------

def get_weighted_customer_type(day: int) -> str:
    """
    Returns a weighted random customer type based on the current day.

    Day ranges:
    - Below Day 30: Low=50%, Medium=40%, High=10%
    - Day 30-99: Low=30%, Medium=60%, High=10%
    - Day 100+: Low=10%, Medium=30%, High=60%
    """
    if day < 30:
        weights = {"low": 0.50, "medium": 0.40, "high": 0.10}
    elif day < 100:
        weights = {"low": 0.30, "medium": 0.60, "high": 0.10}
    else:
        weights = {"low": 0.10, "medium": 0.30, "high": 0.60}

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


def get_weighted_special_customer_type() -> str:
    """
    Returns a weighted random special customer type.

    Spawn rates:
    - Hoarder: 30%
    - Shoplifter: 15%
    - Party Prep Mom: 30%
    - Gamer: 10%
    - Christmas Dad: 10%
    - Lottery Winner: 4%
    - Youtuber: 1%
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


def calculate_player_cas(
    player: Player,
    market_prices: Dict[str, float],
    items_by_name: Dict[str, Item],
    all_available_items: List[Item]
) -> float:
    """
    Calculate Customer Attraction Score (CAS) for a player based on their overall store.
    This is used for weighted customer distribution.

    Formula:
    - reputation_multiplier = 10 ** (reputation / 100)
    - discount_score = sum of discount % for all stocked items
    - item_stability = sum of proximity and consistency scores
    - availability_multiplier based on % of catalog in stock
    - fulfillment_multiplier based on average fulfillment %
    - CAS = (discount_score + item_stability) * reputation_multiplier * availability_multiplier * fulfillment_multiplier

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

    # Calculate availability multiplier
    items_in_stock = sum(1 for qty in player.inventory.values() if qty > 0)
    availability_pct = (items_in_stock / total_catalog_items) * 100 if total_catalog_items > 0 else 0

    if availability_pct >= 100:
        availability_multiplier = 1.2
    elif availability_pct >= 80:
        availability_multiplier = 1.1
    elif availability_pct < 20:
        availability_multiplier = 0.5
    elif availability_pct < 50:
        availability_multiplier = 0.8
    else:
        availability_multiplier = 1.0

    # Calculate fulfillment multiplier
    fulfillment_pct = player.average_fulfillment_pct
    if fulfillment_pct >= 100:
        fulfillment_multiplier = 2.0
    elif fulfillment_pct >= 90:
        fulfillment_multiplier = 1.4
    elif fulfillment_pct >= 50:
        fulfillment_multiplier = 1.0
    elif fulfillment_pct >= 20:
        fulfillment_multiplier = 0.9
    else:
        fulfillment_multiplier = 0.5

    # Calculate reputation multiplier
    reputation_multiplier = 10 ** (player.reputation / 100)

    # Calculate item stability
    item_stability = calculate_item_stability(player, market_prices, items_by_name)

    # Calculate marketing effect (adds to both discount and stability)
    marketing_effect = calculate_marketing_effect(player, market_prices)

    # Calculate final CAS (marketing effect boosts both components)
    cas = (discount_score + marketing_effect + item_stability + marketing_effect) * reputation_multiplier * availability_multiplier * fulfillment_multiplier

    return cas


def assign_customers_by_cas(
    customers: List[Customer],
    players: List[Player],
    market_prices: Dict[str, float],
    items_by_name: Dict[str, Item],
    all_available_items: List[Item]
) -> Dict[str, List[Customer]]:
    """
    Assign customers to players based on weighted CAS distribution.

    Returns a dictionary mapping player name to list of assigned customers.
    """
    # Calculate CAS for each player
    player_cas = {}
    for player in players:
        cas = calculate_player_cas(player, market_prices, items_by_name, all_available_items)
        player_cas[player.name] = cas

    # Calculate total CAS
    total_cas = sum(player_cas.values())

    # If no players have any CAS, distribute evenly
    if total_cas == 0:
        # Equal distribution
        assignments = {player.name: [] for player in players}
        for i, customer in enumerate(customers):
            player = players[i % len(players)]
            assignments[player.name].append(customer)
        return assignments

    # Distribute customers based on CAS weights
    assignments = {player.name: [] for player in players}

    for customer in customers:
        # Weighted random selection
        rand = random.random() * total_cas
        cumulative = 0.0

        selected_player = None
        for player in players:
            cumulative += player_cas[player.name]
            if rand < cumulative:
                selected_player = player
                break

        # Fallback to first player if something goes wrong
        if selected_player is None:
            selected_player = players[0]

        assignments[selected_player.name].append(customer)

    return assignments


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

    # Calculate base customer count: num_players * 25 + scaled growth
    # Growth scales: +2/day base, +1 every 15 days (day 15: +3, day 30: +4, etc.)
    def calculate_scaled_customers(day):
        if day == 0:
            return 0
        full_periods = day // 15
        remaining_days = day % 15
        # Sum of customers from complete 15-day periods (arithmetic sequence)
        total = 15 * full_periods * (3 + full_periods) // 2 if full_periods > 0 else 0
        # Add customers from remaining days in current period
        current_rate = 2 + full_periods
        total += remaining_days * current_rate
        return total

    base_customer_count = len(game_state.players) * 25 + calculate_scaled_customers(game_state.day)

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

    # Track reputation changes per player (to be applied at end of day with limits)
    daily_reputation_changes = {player.name: 0 for player in game_state.players}

    # Track fulfillment percentages per player (to calculate average at end of day)
    daily_fulfillment_data = {player.name: [] for player in game_state.players}  # List of fulfillment % per customer

    # Track customer types for daily summary
    customer_type_stats = {
        'spawned': {'low': 0, 'medium': 0, 'high': 0},
        'bought_something': {'low': 0, 'medium': 0, 'high': 0},
        'found_nothing': {'low': 0, 'medium': 0, 'high': 0}
    }

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
        all_customers.append(customer)
        customer_type_stats['spawned'][customer_type] += 1


    # Track total demand per item (what customers want to buy today)
    daily_demand_per_item = {}  # item_name -> total quantity wanted

    # Build items dictionary for quick lookup (needed for CAS calculation)
    items_by_name = {item.name: item for item in game_state.items}

    # Assign customers to players based on weighted CAS distribution
    customer_assignments = assign_customers_by_cas(
        all_customers,
        game_state.players,
        game_state.market_prices,
        items_by_name,
        game_state.items
    )

    # Process customers for each player
    for player in game_state.players:
        assigned_customers = customer_assignments.get(player.name, [])

        for customer in assigned_customers:
            needs = customer.generate_daily_needs(game_state.items, game_state.market_prices, game_state.item_demand)

            # Track demand for each item the customer wants
            for need in needs:
                daily_demand_per_item[need.item_name] = daily_demand_per_item.get(need.item_name, 0) + need.quantity

            # Track customer spending against their budget
            customer_spending = 0.0
            customer_budget = customer.budget
            customer_counted_at_store = {}
            customer_bought_anything = False

            # Track original needs for reputation calculation
            original_needs_count = sum(need.quantity for need in needs)
            fulfilled_needs_count = 0

            remaining_needs = list(needs)

            # Customer will shop at their assigned player's store
            current_supplier = player
            visited_stores = [player.name]  # Track which stores this customer shopped at

            # Safety guard to prevent infinite loops if needs never resolve
            max_iterations = max(10, len(remaining_needs) * 10)
            iterations = 0

            while remaining_needs and customer_spending < customer_budget:
                iterations += 1
                if iterations > max_iterations:
                    # If we've looped too many times without clearing needs, mark remaining as unmet
                    for need in remaining_needs:
                        unmet_demand += need.quantity
                        unmet_demand_per_item[need.item_name] = (
                            unmet_demand_per_item.get(need.item_name, 0) + need.quantity
                        )
                    break

                # Try to purchase items from assigned supplier
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
                            remaining_budget = customer_budget - customer_spending

                            # Check if customer can afford this item (at least 1 unit)
                            if supplier_price > remaining_budget:
                                continue

                            # Adjust quantity based on remaining budget
                            affordable_quantity = min(need.quantity, int(remaining_budget / supplier_price))

                            # Purchase from current supplier
                            revenue, profit, actual_units_sold = current_supplier.sell_to_customer(
                                need.item_name, affordable_quantity, supplier_price
                            )

                            if revenue > 0:
                                # Track customer spending
                                customer_spending += revenue
                                fulfilled_needs_count += actual_units_sold

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

                                # Update need quantity or mark as purchased
                                if actual_units_sold >= need.quantity:
                                    purchased_needs.append(need)
                                else:
                                    need.quantity -= actual_units_sold

                                # Check if customer has hit their budget limit
                                if customer_spending >= customer_budget:
                                    break

            # Remove fully purchased items from remaining needs
            for need in purchased_needs:
                remaining_needs.remove(need)

            # Mark unmet demand and reset to find another store
            if remaining_needs and not purchased_needs:
                # Current supplier couldn't fulfill any more needs
                # Mark remaining as unmet and stop
                for need in remaining_needs:
                    unmet_demand += need.quantity
                    unmet_demand_per_item[need.item_name] = (
                        unmet_demand_per_item.get(need.item_name, 0) + need.quantity
                    )
                break

            # Continue shopping at same store if we made purchases
            if not remaining_needs or customer_spending >= customer_budget:
                break

        # Track reputation changes and fulfillment for all stores this customer visited
        # (Will be applied at end of day with limits)
        if original_needs_count > 0:
            fulfillment_percentage = (fulfilled_needs_count / original_needs_count) * 100  # Convert to percentage

            for store_name in visited_stores:
                # Track fulfillment percentage for this customer visit
                daily_fulfillment_data[store_name].append(fulfillment_percentage)

                # Track reputation changes based on fulfillment
                if fulfillment_percentage <= 30:
                    # 30% or less: -1 reputation
                    daily_reputation_changes[store_name] -= 1
                elif fulfillment_percentage >= 80:
                    # 80% or more: +1 reputation
                    daily_reputation_changes[store_name] += 1

                    # If 100% fulfilled at exactly one store, +2 total (so +1 additional)
                    if fulfillment_percentage >= 99.9 and len(visited_stores) == 1:
                        daily_reputation_changes[store_name] += 1
                # 50-79%: no change

        # Track customer type statistics
        if customer.customer_type in customer_type_stats['bought_something']:
            if not needs:
                # Customer had no needs generated - don't count them
                pass
            elif customer_bought_anything:
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

    # Step 5.6: Process special customers (no cashier limits, unique selection logic)
    special_customer_count = get_special_customer_count(game_state.day)
    if special_customer_count > 0:
        special_customers = []
        lottery_winner_spawned = False
        youtuber_spawned = False

        for i in range(special_customer_count):
            # Get weighted special customer type
            special_type = get_weighted_special_customer_type()

            # Enforce max 1 lottery winner and 1 youtuber per day
            if special_type == "lottery_winner":
                if lottery_winner_spawned:
                    special_type = "hoarder"  # Fallback to hoarder
                else:
                    lottery_winner_spawned = True
            elif special_type == "youtuber":
                if youtuber_spawned:
                    special_type = "hoarder"  # Fallback to hoarder
                else:
                    youtuber_spawned = True

            customer = Customer(name=f"Special_{i+1}", customer_type=special_type, day=game_state.day)
            special_customers.append(customer)

        # Process each special customer
        for customer in special_customers:
            # Build items dictionary for quick lookup
            items_by_name = {item.name: item for item in game_state.items}

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
                                "Shoplifter",
                                target.name,
                                f"Stole: {', '.join(stolen_items)}"
                            ))
                            # Apply reputation penalty for theft
                            daily_reputation_changes[target.name] -= 5
                continue

            # For other special customers, generate needs
            needs = customer.generate_daily_needs(game_state.items, game_state.market_prices, game_state.item_demand)

            if not needs:
                continue

            # Choose supplier using special customer logic
            supplier = customer.choose_supplier_for_special_customer(
                game_state.players, needs, game_state.market_prices, items_by_name, game_state.items
            )

            if not supplier:
                continue

            # Track purchases
            items_bought = []
            total_spent = 0.0

            for need in needs:
                if need.item_name in supplier.inventory and supplier.inventory[need.item_name] > 0:
                    if need.item_name in supplier.prices:
                        price = supplier.prices[need.item_name]
                        # Special customers bypass the 15% market price rule
                        revenue, profit, actual_units_sold = supplier.sell_to_customer(need.item_name, need.quantity, price)

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
                # Format special customer type for display
                customer_type_display = customer.customer_type.replace("_", " ").title()
                special_customer_events.append((
                    customer_type_display,
                    supplier.name,
                    f"Bought: {', '.join(items_bought[:3])}{'...' if len(items_bought) > 3 else ''} (${total_spent:.2f})"
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
            print(f"  {player.name}: ${wages:.2f} MONTHLY WAGE ({player.restockers} restockers, {player.marketing_agents} marketing agents)")
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
            uncapped_served = uncapped_customers_served[player.name]
            xp_needed = player.get_xp_for_next_level()

            # Calculate total items sold
            total_items_sold = sum(
                data['units_sold']
                for data in per_item_sales[player.name].values()
            )

            print(f"  {player.name}:")
            print(f"    Sales: ${sales:.2f} | Profit: ${profit:.2f} | Level: {player.store_level} | XP: {player.experience:.0f}/{xp_needed:.0f}")
            customer_info = f"Regular: {served}"
            if uncapped_customer_count > 0:
                customer_info += f" | 💎 Uncapped: {uncapped_served}"
            print(f"    Customers: {customer_info} | Items Sold: {total_items_sold} | Cash: ${player.cash:.2f}")

            # Show per-item sales breakdown
            if per_item_sales[player.name]:
                items_breakdown = []
                for item_name, data in sorted(per_item_sales[player.name].items()):
                    if data['units_sold'] > 0:
                        items_breakdown.append(f"{item_name}: {data['units_sold']}")
                if items_breakdown:
                    print(f"    Items: {', '.join(items_breakdown)}")

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
                    print(f"    Pricing: {pricing_str}")

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
            print(f"\n🌟 Special Customers Today:")
            for customer_type, target_name, details in special_customer_events:
                print(f"  {customer_type} → {target_name}: {details}")

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

    # Unlock new product every 5 days (at end of day, so players can buy it next day)
    if game_state.day % 5 == 0 and game_state.day > 0:
        new_product = unlock_new_product(game_state)
        if new_product and show_details:
            print(f"\n🎁 NEW PRODUCT UNLOCKED: {new_product.name} (${new_product.base_price:.2f})")
            print(f"   Total products available: {len(game_state.items)}")

    # Step 7.8: Apply daily reputation changes with limits and decay
    import math
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

        # Update average fulfillment percentage based on today's data
        if daily_fulfillment_data[player.name]:
            # Calculate average of today's fulfillment percentages
            today_avg = sum(daily_fulfillment_data[player.name]) / len(daily_fulfillment_data[player.name])
            player.average_fulfillment_pct = today_avg
        # If no customers visited today, keep previous average

        # Show reputation changes for all players
        if show_details:
            decay_text = f" (decay: -{decay_amount})" if decay_amount > 0 else ""
            change_text = f" (change: {rep_change:+d}{decay_text})" if (rep_change != 0 or decay_amount > 0) else ""
            print(f"\n📊 {player.name} Reputation: {player.reputation:.0f}{change_text}")
            if daily_fulfillment_data[player.name]:
                print(f"   Average Fulfillment: {player.average_fulfillment_pct:.1f}% (from {len(daily_fulfillment_data[player.name])} customers)")

            # Display CAS breakdown for this player
            display_cas_breakdown(player, game_state)

    # Step 8: Refresh vendor inventory for next day
    # Done at END of day so buy orders are set for current vendor inventory
    refresh_vendor_inventory(game_state.vendors, game_state.items, game_state.market_prices)

    # Step 9: Advance day counter
    game_state.day += 1

    # Step 9.25: Process pending deliveries for all players
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

            player.inventory[item_name] = new_total_qty

            if player.is_human and show_details:
                print(f"\n📦 Delivery arrived for {player.name}: {quantity}x {item_name}")

        # Update pending deliveries list
        player.pending_deliveries = remaining_deliveries

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

def calculate_item_stability(player: Player, market_prices: Dict[str, float], items_by_name: Dict[str, Item]) -> float:
    """
    Calculate item stability score to reward pricing close to market price and consistent pricing.

    Formula:
    For each item with stock:
    1. Price proximity score:
       - Starts at 10 if within 5% of market price
       - Decreases by 1 for each 1% beyond 5% difference
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

        # Calculate proximity score
        if price_diff_pct <= 5:
            proximity_score = 10.0
        else:
            # Decrease by 1 for each 1% beyond 5%
            proximity_score = max(0, 10 - (price_diff_pct - 5))

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


def display_cas_breakdown(player: Player, game_state: GameState) -> None:
    """Display Customer Attraction Score (CAS) breakdown for a player."""
    print(f"\n🎯 {player.name} - Customer Attraction Score (CAS):")

    # Build items_by_name dict for item_stability calculation
    items_by_name = {item.name: item for item in game_state.items}

    # Calculate reputation multiplier
    reputation_multiplier = 10 ** (player.reputation / 100)

    # Calculate discount score (sum across all stocked items)
    discount_score = 0.0
    total_discount_pct = 0.0
    items_counted = 0
    if player.inventory and player.prices:
        for item_name, qty in player.inventory.items():
            if qty > 0 and item_name in player.prices:
                market_price = game_state.market_prices.get(item_name, 0)
                if market_price > 0:
                    player_price = player.prices[item_name]
                    # Get item importance
                    item = next((i for i in game_state.items if i.name == item_name), None)
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
    item_stability = calculate_item_stability(player, game_state.market_prices, items_by_name)

    # Calculate global availability multiplier
    total_catalog_items = len(game_state.items)
    items_in_stock = sum(1 for qty in player.inventory.values() if qty > 0)
    availability_pct = (items_in_stock / total_catalog_items) * 100 if total_catalog_items > 0 else 0

    if availability_pct >= 100:
        availability_multiplier = 1.2
    elif availability_pct >= 80:
        availability_multiplier = 1.1
    elif availability_pct < 20:
        availability_multiplier = 0.5
    elif availability_pct < 50:
        availability_multiplier = 0.8
    else:
        availability_multiplier = 1.0

    # Calculate fulfillment multiplier
    fulfillment_pct = player.average_fulfillment_pct
    if fulfillment_pct >= 100:
        fulfillment_multiplier = 2.0
    elif fulfillment_pct >= 90:
        fulfillment_multiplier = 1.4
    elif fulfillment_pct >= 50:
        fulfillment_multiplier = 1.0
    elif fulfillment_pct >= 20:
        fulfillment_multiplier = 0.9
    else:
        fulfillment_multiplier = 0.5

    # Calculate marketing effect
    marketing_effect = calculate_marketing_effect(player, game_state.market_prices)

    # Calculate final CAS (marketing effect boosts both components)
    final_cas = (discount_score + marketing_effect + item_stability + marketing_effect) * reputation_multiplier * availability_multiplier * fulfillment_multiplier

    # Display compact breakdown
    print(f"   Reputation:              {player.reputation:.0f}")
    print(f"   Discount Score:          {total_discount_pct:.1f}% total across {items_counted} items (importance: {discount_score:.2f})")
    print(f"   Item Stability:          {item_stability:.2f}")
    if marketing_effect > 0:
        print(f"   Marketing Effect:        {marketing_effect:.2f} ({player.marketing_agents} agents)")
    print(f"   Availability Multiplier: {availability_multiplier:6.2f}x  ({items_in_stock}/{total_catalog_items} = {availability_pct:.0f}%)")
    print(f"   Fulfillment Multiplier:  {fulfillment_multiplier:6.2f}x  ({fulfillment_pct:.0f}% avg)")
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

        # Display current inventory
        print(f"   Current stock ({len(vendor.items)} items):")
        if vendor.items:
            for item_name, price in sorted(vendor.items.items()):
                market_price = game_state.market_prices.get(item_name, 0)
                print(f"      - {item_name}: ${price:.2f} (market: ${market_price:.2f})")
        else:
            print(f"      (no items available)")

    print("=" * 80)


def display_player_status(player: Player, game_state: GameState = None) -> None:
    """Display the player's current status."""
    print("\n" + "=" * 60)
    print(f"YOUR STORE: {player.name}")
    print("=" * 60)
    print(f"Cash: ${player.cash:.2f}")

    xp_needed = player.get_xp_for_next_level()
    print(f"\nStore Level: {player.store_level} (Max {player.get_max_products()} different products)")
    print(f"Experience: {player.experience:.0f}/{xp_needed:.0f} XP")

    print(f"\nEmployees:")
    print(f"  Restockers: {player.restockers} (Max {player.get_max_items_per_day()} items/day)")
    print(f"  Marketing Agents: {player.marketing_agents} (Boost customer attraction)")
    total_employees = player.restockers + player.marketing_agents
    monthly_wage = 1000.0
    wage_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "wage_reduction")
    actual_wage = max(0, monthly_wage - wage_reduction)
    print(f"  Monthly wages: ${total_employees * actual_wage:.2f} (${actual_wage:.2f}/employee)")

    print(f"\nInventory ({len([i for i, q in player.inventory.items() if q > 0])}/{player.get_max_products()} products):")
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
        print("  p. Set Sale Price (select item)")
        print("  c. Change All Prices (one by one)")
        print("  0. Back to Main Menu")

        try:
            choice = input("\nSelect option (b/p/c/0): ").strip().lower()

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

                                                # Check product limit
                                                products_with_orders = 0
                                                for check_item in game_state.items:
                                                    check_orders = player.get_buy_order(check_item.name)
                                                    if check_item.name == item.name:
                                                        # This item will have an order after we add
                                                        if len(check_orders) > 0 or quantity > 0:
                                                            products_with_orders += 1
                                                    else:
                                                        if len(check_orders) > 0:
                                                            products_with_orders += 1

                                                max_products = player.get_max_products()
                                                if products_with_orders > max_products:
                                                    print(f"\n✗ Exceeded product limit! Your store can only stock {max_products} different products.")
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

                                        # Check product limit
                                        products_with_orders = 0
                                        for check_item in game_state.items:
                                            check_orders = player.get_buy_order(check_item.name)
                                            if check_item.name == item.name:
                                                # This item will have an order after we add
                                                if len(check_orders) > 0 or vendors_added > 0:
                                                    products_with_orders += 1
                                            else:
                                                if len(check_orders) > 0:
                                                    products_with_orders += 1

                                        max_products = player.get_max_products()
                                        if products_with_orders > max_products:
                                            print(f"\n✗ Exceeded product limit! Your store can only stock {max_products} different products.")
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

            elif choice == 'p':
                # Set sale price
                print("\nSelect item to set sale price:")
                for i, item in enumerate(game_state.items, 1):
                    print(f"  {i}. {item.name}")
                print("  0. Cancel")

                item_choice = input(f"\nSelect item (0-{len(game_state.items)}): ")
                item_num = int(item_choice)

                if item_num == 0:
                    continue

                if 1 <= item_num <= len(game_state.items):
                    item = game_state.items[item_num - 1]
                    market_price = game_state.market_prices.get(item.name, 0)
                    current_price = player.prices.get(item.name, 0)

                    # Get vendor buy price for reference (cheapest among all vendors)
                    vendor_orders = player.get_buy_order(item.name)
                    vendor_buy_price = 0.0

                    own_price = player.get_production_line_price(item.name, market_price)
                    if own_price is not None:
                        vendor_buy_price = own_price
                    elif vendor_orders:
                        # Find cheapest vendor price
                        cheapest_price = float('inf')
                        for qty, vendor_name in vendor_orders:
                            for vendor in game_state.vendors:
                                if vendor.name == vendor_name:
                                    price = vendor.get_price(item.name)
                                    if price:
                                        discount = player.get_vendor_discount(vendor_name, game_state.day)
                                        actual_price = price * (1 - discount)
                                        if actual_price < cheapest_price:
                                            cheapest_price = actual_price
                                    break
                        if cheapest_price < float('inf'):
                            vendor_buy_price = cheapest_price

                    print(f"\n=== Setting Sale Price for {item.name} ===")
                    print(f"Market price: ${market_price:.2f}")
                    if vendor_buy_price > 0:
                        print(f"Your buy price: ${vendor_buy_price:.2f}")
                    print(f"Current sale price: ${current_price:.2f}")

                    price_str = input(f"Enter new sale price: $")
                    price = float(price_str)

                    if price >= 0:
                        player.set_price(item.name, price)
                        print(f"\n✓ Sale price set to ${price:.2f}")
                        if vendor_buy_price > 0:
                            margin = price - vendor_buy_price
                            margin_pct = (margin / vendor_buy_price) * 100 if vendor_buy_price > 0 else 0
                            print(f"  Margin: ${margin:.2f} ({margin_pct:.1f}%)")
                    else:
                        print("\n✗ Price must be positive!")
                else:
                    print("\n✗ Invalid item selection!")

            elif choice == 'c':
                # Change all prices
                print("\n" + "=" * 50)
                print("CHANGE ALL SALE PRICES")
                print("=" * 50)
                print("Press Enter to skip an item without changing its price.\n")

                for item in game_state.items:
                    market_price = game_state.market_prices.get(item.name, 0)
                    current_price = player.prices.get(item.name, 0)

                    # Get vendor buy price for reference (cheapest among all vendors)
                    vendor_orders = player.get_buy_order(item.name)
                    vendor_buy_price = 0.0

                    own_price = player.get_production_line_price(item.name, market_price)
                    if own_price is not None:
                        vendor_buy_price = own_price
                    elif vendor_orders:
                        # Find cheapest vendor price
                        cheapest_price = float('inf')
                        for qty, vendor_name in vendor_orders:
                            for vendor in game_state.vendors:
                                if vendor.name == vendor_name:
                                    price = vendor.get_price(item.name)
                                    if price:
                                        discount = player.get_vendor_discount(vendor_name, game_state.day)
                                        actual_price = price * (1 - discount)
                                        if actual_price < cheapest_price:
                                            cheapest_price = actual_price
                                    break
                        if cheapest_price < float('inf'):
                            vendor_buy_price = cheapest_price

                    print(f"\n{item.name}")
                    print(f"  Market: ${market_price:.2f}")
                    if vendor_buy_price > 0:
                        print(f"  Your buy price: ${vendor_buy_price:.2f}")
                    print(f"  Current sale price: ${current_price:.2f}")

                    price_str = input(f"  New sale price (or Enter to skip): $").strip()

                    if price_str:
                        try:
                            price = float(price_str)
                            if price >= 0:
                                player.set_price(item.name, price)
                                if vendor_buy_price > 0:
                                    margin = price - vendor_buy_price
                                    margin_pct = (margin / vendor_buy_price) * 100 if vendor_buy_price > 0 else 0
                                    print(f"  ✓ Price set to ${price:.2f} (margin: ${margin:.2f}, {margin_pct:.1f}%)")
                                else:
                                    print(f"  ✓ Price set to ${price:.2f}")
                            else:
                                print("  ✗ Price must be positive! Skipping...")
                        except ValueError:
                            print("  ✗ Invalid price! Skipping...")

                print("\n✓ Finished updating prices!")
                input("\nPress Enter to continue...")
            else:
                print("\n✗ Invalid option!")

        except (ValueError, IndexError):
            print("\n✗ Invalid input!")


def buy_order_menu(game_state: GameState, player: Player) -> None:
    """Menu for setting buy orders (quantity and vendor selection per item) - supports up to 3 vendors per item."""
    while True:
        print("\n" + "=" * 100)
        print("BUY ORDER MENU - Configure Automatic Purchasing (Up to 3 Vendors Per Item)")
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

                                        # Check product limit
                                        products_with_orders = 0
                                        for check_item in game_state.items:
                                            check_orders = player.get_buy_order(check_item.name)
                                            if check_item.name == item.name:
                                                # This item will have an order after we add
                                                if len(check_orders) > 0 or quantity > 0:
                                                    products_with_orders += 1
                                            else:
                                                if len(check_orders) > 0:
                                                    products_with_orders += 1

                                        max_products = player.get_max_products()
                                        if products_with_orders > max_products:
                                            print(f"\n✗ Exceeded product limit! Your store can only stock {max_products} different products.")
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

                                # Check product limit
                                products_with_orders = 0
                                for check_item in game_state.items:
                                    check_orders = player.get_buy_order(check_item.name)
                                    if check_item.name == item.name:
                                        # This item will have an order after we add
                                        if len(check_orders) > 0 or vendors_added > 0:
                                            products_with_orders += 1
                                    else:
                                        if len(check_orders) > 0:
                                            products_with_orders += 1

                                max_products = player.get_max_products()
                                if products_with_orders > max_products:
                                    print(f"\n✗ Exceeded product limit! Your store can only stock {max_products} different products.")
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


def employee_menu(game_state: GameState, player: Player) -> None:
    """Menu for hiring employees."""
    RESTOCKER_COST = 1000.0
    BASE_MONTHLY_WAGE = 1000.0

    while True:
        print("\n" + "=" * 60)
        print("EMPLOYEE MENU - Hire Staff")
        print("=" * 60)
        print(f"\nYour Cash: ${player.cash:.2f}")
        print(f"Store Level: {player.store_level}")
        print(f"\nCurrent Employees:")
        print(f"  Restockers: {player.restockers} (Max {player.get_max_items_per_day()} items/day)")
        print(f"  Marketing Agents: {player.marketing_agents} (Boost customer attraction)")
        total_employees = player.restockers + player.marketing_agents

        # Calculate actual wage with upgrades
        wage_reduction = sum(u.effect_value for u in player.purchased_upgrades if u.effect_type == "wage_reduction")
        actual_wage = max(0, BASE_MONTHLY_WAGE - wage_reduction)
        print(f"  Total monthly wages: ${total_employees * actual_wage:.2f}")

        if wage_reduction > 0:
            print(f"\nMonthly Wage: ${actual_wage:.2f} per employee (reduced from ${BASE_MONTHLY_WAGE:.2f})")
        else:
            print(f"\nMonthly Wage: ${actual_wage:.2f} per employee")

        # Show days until next wage payment
        days_until_payment = 30 - (game_state.day - player.last_wage_payment_day)
        if total_employees > 0:
            print(f"Next wage payment: Day {player.last_wage_payment_day + 30} ({days_until_payment} days)")
        print(f"Note: Wages paid every 30 days for ALL employees (including newly hired)")

        # Calculate marketing agent cost
        marketing_cost = 1000.0 * (5 ** player.marketing_agents)

        print("\nOptions:")
        print(f"  1. Hire Restocker (+500 items/day capacity) - ${RESTOCKER_COST:.2f}")
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
                if player.cash < RESTOCKER_COST:
                    print(f"\n✗ Not enough cash! Need ${RESTOCKER_COST:.2f}, have ${player.cash:.2f}")
                else:
                    success = player.hire_employee("restocker")
                    if success:
                        print(f"\n✓ Hired 1 restocker for ${RESTOCKER_COST:.2f}")
                        print(f"  New capacity: {player.get_max_items_per_day()} items/day")
                    else:
                        print("\n✗ Failed to hire restocker")
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
        return f"-${int(upgrade.effect_value)} monthly wage per employee (from $1000 to $900)"
    elif upgrade.effect_type == "lead_time_reduction":
        return f"-{int(upgrade.effect_value)} day lead time for all vendors"
    elif upgrade.effect_type == "production_line":
        return f"Own production for {upgrade.vendor_name} (50% market price)"
    return "Unknown effect"


def pricing_menu(game_state: GameState, player: Player) -> None:
    """Menu for setting prices."""
    while True:
        # Get items from both inventory and buy orders
        relevant_item_names = set()

        # Add items from inventory
        for item_name, qty in player.inventory.items():
            if qty > 0:
                relevant_item_names.add(item_name)

        # Add items from buy orders
        for item_name, vendor_list in player.buy_orders.items():
            total_qty = sum(q for q, v in vendor_list)
            if total_qty > 0:
                relevant_item_names.add(item_name)

        # Filter game items to only those relevant
        priceable_items = [item for item in game_state.items if item.name in relevant_item_names]

        if not priceable_items:
            print("\n" + "=" * 50)
            print("PRICING MENU - Set Your Prices")
            print("=" * 50)
            print("\nYou have no items in inventory or buy orders to price.")
            input("\nPress Enter to return to main menu...")
            break

        print("\n" + "=" * 50)
        print("PRICING MENU - Set Your Prices")
        print("=" * 50)

        # Show current market prices and player's prices
        print(f"\n{'Item':<15} {'Qty':>6} {'Market Price':>12} {'Your Price':>12}")
        print("-" * 60)
        for item in priceable_items:
            market_price = game_state.market_prices.get(item.name, 0)
            your_price = player.prices.get(item.name, 0)

            # Show inventory quantity, or "Ordered" if only in buy orders
            inv_qty = player.inventory.get(item.name, 0)
            if inv_qty > 0:
                qty_str = str(inv_qty)
            else:
                # Item is only in buy orders
                vendor_list = player.buy_orders.get(item.name, [])
                order_qty = sum(q for q, v in vendor_list)
                qty_str = f"({order_qty})"

            print(f"{item.name:<15} {qty_str:>6} ${market_price:>11.2f} ${your_price:>11.2f}")

        print("\nOptions:")
        print(f"  C. Change All (one by one)")
        print("\nSelect item to price:")
        for i, item in enumerate(priceable_items, 1):
            print(f"  {i}. {item.name}")
        print(f"  0. Back to Main Menu")

        try:
            choice = input(f"\nSelect option (0-{len(priceable_items)}, or C): ").strip()

            # Handle "Change All" option
            if choice.upper() == 'C':
                print("\n" + "=" * 50)
                print("CHANGE ALL PRICES")
                print("=" * 50)
                print("Press Enter to skip an item without changing its price.\n")

                for item in priceable_items:
                    market_price = game_state.market_prices.get(item.name, 0)
                    current_price = player.prices.get(item.name, 0)
                    inv_qty = player.inventory.get(item.name, 0)

                    # Display quantity info
                    if inv_qty > 0:
                        qty_display = f"Qty: {inv_qty}"
                    else:
                        vendor_list = player.buy_orders.get(item.name, [])
                        order_qty = sum(q for q, v in vendor_list)
                        qty_display = f"Ordered: {order_qty}"

                    print(f"\n{item.name} ({qty_display})")
                    print(f"Market price: ${market_price:.2f}")
                    print(f"Current price: ${current_price:.2f}")

                    price_str = input(f"New price (or Enter to skip): $").strip()

                    if price_str:  # Only update if user entered something
                        try:
                            price = float(price_str)
                            if price >= 0:
                                player.set_price(item.name, price)
                                print(f"✓ Price set to ${price:.2f}")
                            else:
                                print("✗ Price must be positive! Skipping...")
                        except ValueError:
                            print("✗ Invalid price! Skipping...")

                print("\n✓ Finished updating prices!")
                input("\nPress Enter to continue...")
                continue

            choice_num = int(choice)

            if choice_num == 0:
                break

            if 1 <= choice_num <= len(priceable_items):
                item = priceable_items[choice_num - 1]
                market_price = game_state.market_prices.get(item.name, 0)
                inv_qty = player.inventory.get(item.name, 0)

                # Display quantity info
                if inv_qty > 0:
                    qty_display = f"Qty: {inv_qty}"
                else:
                    vendor_list = player.buy_orders.get(item.name, [])
                    order_qty = sum(q for q, v in vendor_list)
                    qty_display = f"Ordered: {order_qty}"

                print(f"\nSetting price for {item.name} ({qty_display})")
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
        print(f"Employees: {player.restockers} restockers")
        print("\nOptions:")
        print("  1. Pass Day (Simulate)")
        print("  2. View Market Prices")
        print("  3. View Vendors")
        print("  4. Configure Buy Orders & Sale Prices")
        print("  5. Hire Employees")
        print("  6. View Your Store Status")
        print("  7. Store Upgrades")
        print("  c. Customer Forecast")
        print("  s. Save Game")
        print("  0. Quit Game")

        try:
            choice = input("\nSelect option (0-7, c, s): ").strip().lower()

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
                configure_orders_and_prices_menu(game_state, player)
            elif choice_num == 5:
                employee_menu(game_state, player)
            elif choice_num == 6:
                display_player_status(player, game_state)
                input("\nPress Enter to continue...")
            elif choice_num == 7:
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
            {"name": item.name, "base_cost": item.base_cost, "base_price": item.base_price, "category": item.category}
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
                "pending_deliveries": player.pending_deliveries,
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

    # Recreate items with backward compatibility for missing category
    items = []
    for item_data in data["items"]:
        # Get category from saved data, or look it up in PRODUCT_CATALOG, or use default
        category = item_data.get("category")
        if not category:
            # Try to find matching item in PRODUCT_CATALOG for backward compatibility
            matching_item = next((item for item in PRODUCT_CATALOG if item.name == item_data["name"]), None)
            category = matching_item.category if matching_item else "Food & Groceries"

        items.append(Item(
            name=item_data["name"],
            base_cost=item_data["base_cost"],
            base_price=item_data["base_price"],
            category=category
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
            pending_deliveries=[tuple(delivery) for delivery in player_data.get("pending_deliveries", [])],
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
        print(f"Customers formula: (num_players × 15) + day_number")

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
            unlocked_product_indices=[0, 1, 2],  # Start with first 3 products unlocked
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
