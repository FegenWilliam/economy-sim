# Customer System Guide

This guide explains how the customer system works in the economy simulation game.

## Overview

The customer system is designed to simulate realistic shopping behavior where customers have budgets, preferences, and shopping strategies. They compare prices across stores and make purchasing decisions based on affordability and price competitiveness.

---

## Customer Generation

### Base Customer Count
The number of customers per day is calculated using this formula:

```
base_customer_count = (num_players × 15) + (day × 2)
```

Additionally, every 14 days, there's a permanent bonus of +20 customers.

Example:
- Day 1 with 2 players: (2 × 15) + (1 × 2) = **32 customers**
- Day 14 with 2 players: (2 × 15) + (14 × 2) + 20 = **78 customers**
- Day 28 with 2 players: (2 × 15) + (28 × 2) + 40 = **126 customers**

### Customer Types

#### Regular Customers (randomly selected)
1. **Low Budget** - $20 budget, max 5 items
2. **Medium Budget** - $50 budget, max 10 items
3. **High Budget** - $100 budget, max 15 items

#### Special Customers (30% spawn chance each if suitable items exist)
4. **Hoarder** - $40 budget, buys 3-10 units of ONE item only
5. **Rich Guy** - $400 budget, buys only items >$50, purchases 1-3 different expensive items
6. **Poor Man** - $10 budget, buys exactly 1 item <$10
7. **Kid** - $10 budget, buys exactly 2 items <$5

#### Uncapped Customers (special, no cashier limit)
8. **Uncapped** - $10,000 budget, buys exactly 1 expensive item (≥$100)
   - Start appearing at Day 50
   - Formula: `(day - 40) / 10` customers
   - Example: Day 50 = 1, Day 60 = 2, Day 70 = 3

---

## How Customers Generate Needs

### Step 1: Item Selection with Demand Weighting

Customers select items based on **demand multipliers** (0.1 to 2.0):
- **2.0 demand** = item is 20× more likely to be chosen than 0.1 demand item
- **1.0 demand** = normal/baseline chance
- **0.1 demand** = very low interest

The demand system affects which items customers want:
```python
# Higher demand items are weighted more heavily during selection
selected_item = weighted_random_choice(available_items, item_demand)
```

### Step 2: Regular Customer Shopping Logic

For **low/medium/high** budget customers:
1. Start with full budget
2. Keep buying items one at a time until:
   - Hit item limit (5/10/15 items respectively), OR
   - Run out of budget, OR
   - No more affordable items

Important: Regular customers buy **1 unit at a time** of different items to maximize variety.

### Step 3: Special Customer Logic

**Hoarders:**
- Find ONE item they can afford at least 3 units of
- Buy 3-10 units of that single item only
- Use demand weighting for item selection

**Rich Guys:**
- Only consider items >$50
- Select 1-3 different expensive items
- Buy 1-2 units of each selected item
- Stop when budget runs out

**Poor Man & Kids:**
- Filter to cheap items (<$10 or <$5)
- Use demand weighting for selection
- Buy fixed quantities (1 for poor man, 2 for kid)

**Uncapped:**
- Only buy items ≥$100 (expensive items)
- Buy exactly 1 unit
- Use demand weighting for selection

---

## Customer Purchasing Behavior

### The Shopping Algorithm

This is the most important part - here's how customers actually shop:

#### Step 1: Sort Needs by Price (Most Expensive First)
```python
# Customer prioritizes most expensive item first
needs_with_prices.sort(key=lambda x: x[1], reverse=True)
```

Why? Customers want to secure expensive items first before they sell out.

#### Step 2: Find Cheapest Store for Most Expensive Item

The customer:
1. Looks at their most expensive desired item
2. Gets all suppliers sorted by price (lowest first)
3. Checks if supplier has available cashier capacity
4. Chooses the cheapest supplier with capacity

```python
sorted_suppliers = customer.get_all_suppliers_sorted(
    game_state.players,
    most_expensive_need.item_name,
    most_expensive_need.quantity,
    game_state.market_prices
)
```

#### Step 3: Stay at That Store (if possible)

Once at a store, the customer tries to buy **all** their items from that store:
- Purchase everything the store has that they want
- At prices they find acceptable (within 15% of market price)
- Within their remaining budget

#### Step 4: Move to Next Store (if needed)

If the customer still has unfulfilled needs:
- Reset to find the cheapest store for the next most expensive item
- Repeat the process

### Important Rules

**Price Acceptance:** Customers only buy if price ≤ (market_price × 1.15)
```python
max_acceptable_price = market_price * 1.15  # 15% tolerance
```

**Budget Constraints:** Customers stop buying when:
```python
customer_spending >= customer_budget
```

**Quantity Adjustment:** If customer can't afford full quantity, they buy what they can:
```python
affordable_quantity = min(need.quantity, int(remaining_budget / supplier_price))
```

**Cashier Capacity Limits:** Regular customers count against your cashier limit:
```python
if customers_served[supplier.name] < supplier.get_max_customers():
    # This supplier can serve more customers
```

Uncapped customers **bypass** this limit.

---

## Why Customers Might Not Buy from You

This is likely why things "don't work as expected":

### 1. **Price Too High**
Your price exceeds market_price × 1.15
```
Market price: $10
Your price: $12 ❌ (20% markup - rejected!)
Your price: $11.40 ✓ (14% markup - accepted)
```

### 2. **Cashier Capacity Full**
You've hit your customer limit for the day:
```
Base capacity: 5 customers
With 2 cashiers: 5 + (2 × 10) = 25 customers
If 25 customers already served → no more customers accepted
```

### 3. **Out of Stock**
You have 0 inventory for the item customer wants:
```python
if player.inventory.get(item_name, 0) > 0:  # Must have stock
```

### 4. **No Price Set**
You haven't set a price for the item:
```python
if item_name in player.prices:  # Must have price set
```

### 5. **Competitor Has Better Price**
Customer chose a cheaper store for their most expensive item, then bought everything there:
```
Your store: Laptop $110, Bread $2
Competitor: Laptop $105, Bread $3

Customer wants: Laptop + Bread
→ Goes to competitor (cheaper laptop)
→ Buys BOTH items there (even though your bread is cheaper!)
```

### 6. **Customer Type Mismatch**
- Rich Guy won't buy items ≤$50
- Poor Man won't buy items ≥$10
- Kid won't buy items ≥$5
- Hoarder needs to afford 3+ units
- Uncapped only buys items ≥$100

### 7. **Wrong Day for Uncapped Customers**
Uncapped customers (big spenders) only appear Day 50+
```
Day 49: 0 uncapped customers
Day 50: 1 uncapped customer
Day 60: 2 uncapped customers
```

---

## Demand System Impact

### How Demand Affects Customers

**Item demand changes what customers want:**
- High demand (2.0): Customers are 4× more likely to want this vs normal demand (1.0)
- Low demand (0.1): Customers are 10× less likely to want this vs normal demand (1.0)

### Demand Updates Daily

Demand adjusts automatically based on sell-through rates:
```python
sell_through_rate = units_sold / starting_inventory

if sell_through_rate >= 0.8:    # 80%+ sold
    demand increases by 0.1-0.3
elif sell_through_rate <= 0.2:  # 20% or less sold
    demand decreases by 0.1-0.3
```

**Demand resets:**
- If demand >2.0 → reset to 1.0 (too hot)
- If demand <0.1 → reset to 0.5 (too cold)

---

## Practical Tips

### Maximizing Customer Sales

1. **Price Competitively**
   - Stay within 15% of market price
   - Being cheapest attracts customers first
   - They'll buy more items from you once there

2. **Increase Cashier Capacity**
   - Base: 5 customers/day
   - Each cashier: +10 customers/day
   - This is often the bottleneck!

3. **Stock Popular Items**
   - Check demand multipliers
   - High-demand items sell more
   - Keep inventory levels adequate

4. **Stock Expensive Items (Day 50+)**
   - Uncapped customers bring huge revenue
   - Need items ≥$100 base price
   - They bypass cashier limits

5. **Understand Customer Behavior**
   - Customers visit cheapest store for expensive items
   - Then buy everything else there too
   - Price your most expensive items competitively!

### Common Mistakes

❌ **Setting prices too high** - Customers won't buy at >15% markup
❌ **Ignoring cashier capacity** - You're turning away customers
❌ **Pricing cheap items competitively but not expensive ones** - Customers go to competitors for expensive items, then buy everything there
❌ **Running out of stock** - Can't sell what you don't have
❌ **Expecting consistent sales** - Demand fluctuates, customer types vary daily

---

## Example Scenario

**Your Store:**
- Laptop: $115 (market: $100)
- Bread: $2 (market: $2)
- Stock: 10 laptops, 50 bread
- Cashier capacity: 25 customers

**Competitor Store:**
- Laptop: $110 (market: $100)
- Bread: $2.50 (market: $2)
- Stock: 5 laptops, 30 bread
- Cashier capacity: 15 customers

**What Happens:**

Medium-budget customer wants: 1 Laptop + 1 Bread
1. Sorts by price: Laptop ($100) > Bread ($2)
2. Finds cheapest laptop: Competitor ($110 < $115)
3. Goes to competitor's store
4. Buys laptop for $110 ✓
5. Buys bread for $2.50 ✓ (even though yours is cheaper!)
6. Customer happy, you made $0

**Lesson:** Customers choose stores based on their **most expensive** desired item, then buy everything there. Price your high-value items competitively!

---

## Summary

The customer system is sophisticated and realistic:
- Customers have budgets and limits
- They shop smart (cheapest store for expensive items)
- They stay at one store when possible
- Price tolerance is 15% above market
- Cashier capacity limits daily customers
- Demand affects what customers want
- Different customer types have different behaviors

Understanding this system helps you optimize pricing, inventory, and capacity to maximize sales!
