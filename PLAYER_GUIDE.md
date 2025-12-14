# Economy Simulation - Player Guide

Welcome to Economy Simulation! This guide will teach you everything you need to know to run a successful retail store and dominate the market.

## Table of Contents
- [Game Overview](#game-overview)
- [Getting Started](#getting-started)
- [Core Mechanics](#core-mechanics)
- [Daily Game Loop](#daily-game-loop)
- [Vendors & Purchasing](#vendors--purchasing)
- [Products & Pricing](#products--pricing)
- [Customers](#customers)
- [Employees](#employees)
- [Store Upgrades](#store-upgrades)
- [Strategy Guide](#strategy-guide)
- [Winning the Game](#winning-the-game)

---

## Game Overview

**Economy Simulation** is a turn-based retail management game where you compete to become the wealthiest store owner over 365 simulated days.

### Quick Facts
- **Starting Cash**: $3,000
- **Game Duration**: 365 days
- **Players**: 1-4 human players + 2 AI competitors
- **Goal**: Have the most cash at the end of the year
- **Gameplay**: Buy wholesale, sell retail, manage employees, expand your store

---

## Getting Started

### First Day Setup

When you start, you'll have:
- **$3,000 cash**
- **Access to 6 starting products**: Bread, Milk, Eggs, Coffee, Toilet Paper, Vitamins
- **Base capacity**:
  - 3 different product types
  - 20 customers per day
  - 200 items restocking capacity

### Main Menu Navigation

The game is menu-driven. Each day you can:

1. **Pass Day** - Advance to the next day (executes all transactions)
2. **View Market Prices** - Check current wholesale prices for all items
3. **View Vendors** - See which vendors carry which items and their pricing
4. **Configure Buy Orders & Sale Prices** - Set your purchasing and pricing strategy
5. **Hire Employees** - Add cashiers or restockers
6. **View Your Store Status** - Check your cash, inventory, XP, and level
7. **View Competitor Status** - See how AI competitors are performing
8. **Store Upgrades** - Purchase permanent improvements
9. **Customer Forecast** - Preview tomorrow's expected customers
10. **Save Game** - Save your progress
11. **Quit** - Exit the game

---

## Core Mechanics

### Money & Profit

Your success is measured in **cash**. Here's how money flows:

```
Profit = (Selling Price - Cost Price) × Units Sold
```

- **Buy** inventory from vendors at wholesale prices
- **Sell** to customers at retail prices you set
- **Pay** employee wages monthly (every 30 days)
- **Invest** in upgrades to increase capacity and efficiency

### Store Leveling

- Earn **1 XP per item sold**
- Level up to unlock more product slots
- Each level allows you to stock +1 additional product type
- XP Required = 500 × level + (10,000 × (level ÷ 10))

Example: Level 1→2 needs 500 XP, Level 10→11 needs 15,000 XP

### Capacity Limits

You have three main capacity constraints:

| Type | Base | Per Employee | Per Upgrade |
|------|------|--------------|-------------|
| **Product Types** | 3 | — | +2 or +3 |
| **Daily Customers** | 20 | +30 (Cashier) | +30 or +60 |
| **Daily Restocking** | 200 items | +200 (Restocker) | +400 or +600 |

---

## Daily Game Loop

Each day follows this sequence:

1. **Market Prices Update** - Prices fluctuate (typically ±5%)
2. **AI Players Take Actions** - Competitors adjust their strategies
3. **Your Buy Orders Execute** - Inventory arrives based on your orders
4. **Customers Shop** - Customers visit stores and make purchases
5. **Employee Wages Deducted** - Every 30 days ($500 per employee)
6. **Vendor Inventories Refresh** - Vendors restock for tomorrow
7. **Day Counter Advances** - Day increments by 1

### Special Events

- **Every 14 Days**: +20 permanent new customers join the market
- **Every 30 Days**:
  - One random item goes on -50% sale
  - One random item spikes to +50% price
  - Employee wages are paid
- **Demand Shifts**: Item popularity changes unpredictably (0.1x to 2.0x multiplier)

---

## Vendors & Purchasing

You buy inventory from **9 different vendors**, each with unique pricing, delivery times, and restrictions.

### The 9 Vendors

| Vendor Name | Price Multiplier | Delivery Time | Limits | Best For |
|-------------|------------------|---------------|--------|----------|
| **Lucky Deal Trader** | 70% | 4 days | 1 random item, max 100/day | Extreme savings (if you can wait) |
| **Discount Wholesale Co.** | 80% | 3 days | 5 random items, max 100/day | Good deals on select items |
| **Budget Goods Ltd.** | 90% | Instant | Items < $20 only | Cheap essentials |
| **Premium Select Inc.** | 95% | Instant | Items < $50 only | Mid-range items |
| **Instant Goods Ltd.** | 98% | Instant | Items < $40 only | Quick reliable stock |
| **Universal Supply Corp.** | 105% | Instant | ALL items available | Expensive but guaranteed availability |
| **Bulk Goods Co.** | 85% | 1 day | Min 100/order, items ≤ $30 | Volume discounts on cheap items |
| **Cheap Goods Co.** | 80% | 3 days | Min 500/order, items ≤ $10 | Massive volume discounts on basics |
| **VIP Goods Co.** | 95% | 1 day | Min 10/order, items ≥ $200 | Luxury and high-end items |

### Setting Buy Orders

- You can assign **up to 3 vendors per item**
- Orders execute from cheapest to most expensive
- Lead times delay delivery (order on Day 1 with 3-day lead = arrives Day 4)
- Plan ahead for delivery delays!

**Example Strategy:**
- Bread: Cheap Goods Co. (bulk, 80%), Budget Goods (instant backup), Universal Supply (emergency)
- Gaming Mouse ($50): Premium Select (95%), Universal Supply (105% backup)

---

## Products & Pricing

### Product Categories

The game features **80+ products** across categories:

- **Food & Groceries** (Bread, Milk, Cheese, Rice, Pasta, etc.)
- **Fresh Produce** (Apples, Bananas, Lettuce, Tomatoes, etc.)
- **Household Essentials** (Paper Towels, Soap, Detergent, Trash Bags, etc.)
- **Personal Care** (Shampoo, Toothpaste, Deodorant, etc.)
- **Electronics** (Phone Chargers, Headphones, Monitors, Laptops, etc.)
- **Gaming** (Gaming Mouse, Keyboard, Console, VR Headset, etc.)
- **Luxury Items** (Designer Handbags, Jewelry, Watches, etc.)
- **Home Appliances** (Coffee Maker, Microwave, Air Fryer, etc.)

### Starting Products (Day 1)

| Item | Base Cost | Base Price | Category |
|------|-----------|------------|----------|
| Bread | $2 | $5 | Food |
| Milk | $3 | $6 | Food |
| Eggs | $2.50 | $5.50 | Food |
| Coffee | $6 | $12 | Groceries |
| Toilet Paper | $8 | $15 | Household |
| Vitamins | $12 | $24 | Health |

### How Pricing Works

**Market Price** (changes daily ±5%)
- The wholesale price vendors charge
- Fluctuates based on market conditions
- Special events cause -50% or +50% spikes

**Your Selling Price** (you control this)
- Set your retail price for each item
- Customers accept prices up to **115% of market price**
- Higher prices = more profit per sale, but fewer customers buy
- Lower prices = more volume, less profit margin

**Vendor Pricing**
- Each vendor sells at their multiplier × Market Price
- Example: If Bread market price is $2:
  - Cheap Goods Co. charges $1.60 (80%)
  - Universal Supply charges $2.10 (105%)

### Item Importance Levels

Items have importance that affects customer demand:
- **High Importance (3)**: Food, household essentials, health products
- **Medium Importance (2)**: Electronics, appliances, office supplies
- **Low Importance (1)**: Luxury items, gaming gear

---

## Customers

### Customer Types & Budgets

Customers vary by budget and behavior:

| Type | Daily Budget | Behavior | Population % |
|------|--------------|----------|--------------|
| **Low-Spender** | $20 | Buys essentials only | 50% early, 10% late game |
| **Medium-Spender** | $50 | Mix of basic + mid-range | 40% early, 60% late game |
| **High-Spender** | $100-200+ | Buys expensive items | 10% early, 60% late game |
| **Uncapped** | $10,000 | Buys ONE expensive item (≥$100) | Unlocks Day 50+ |

### Customer Growth

- **Starting Customers**: 15 per player in the market
- **Daily Growth**: +2-4 customers per day (rate increases every 15 days)
- **Milestone Boosts**: +20 customers every 14 days

### How Customers Choose

Customers consider:
1. **Item Availability** - Do you have what they need?
2. **Price** - Is it within 15% of market price?
3. **Store Reputation** - How reliable is your store?
4. **Fulfillment Rate** - How often do you satisfy customer needs?

They shop at stores in order of preference until their needs are met or budget runs out.

### Special Customers (Starting Day 10)

Rare customers with unique behaviors:

| Type | Budget | Specialty | Chance |
|------|--------|-----------|--------|
| **Hoarder** | $500 | Buys 20-30 units of ONE item | 30% |
| **Party Prep Mom** | $200 | Needs party supplies, tableware | 30% |
| **Shoplifter** | $0 | Steals items (loss!) | 15% |
| **Gamer** | $600 | Wants gaming items specifically | 10% |
| **Christmas Dad** | $1,400 | Holiday shopping spree | 10% |
| **Lottery Winner** | $3,000 | Buys high-end luxury items | 4% |
| **Youtuber** | $10,000 | Buys everything expensive for videos | 1% |

**Pro Tip**: Special customers are rare but lucrative! Stock diverse, expensive items to capitalize on them.

---

## Employees

### Cashiers

**Cost**: $500/month (paid every 30 days)

**Benefit**: +30 customer capacity per cashier

- Base capacity: 20 customers/day
- Each cashier adds: +30 customers/day
- Upgrades available: Extra Cashier Station (+30), Express Checkout Lane (+60)

**When to Hire**: When you're consistently hitting your daily customer cap.

### Restockers

**Cost**: $500/month (paid every 30 days)

**Benefit**: +200 item restocking capacity per restocker

- Base capacity: 200 items/day
- Each restocker adds: +200 items/day
- Upgrades available: Warehouse Extension (+400), Loading Dock (+600)

**When to Hire**: When you're moving high volumes of inventory (especially cheap items in bulk).

### Monthly Costs

Employees are paid **every 30 days**:
- Day 30, Day 60, Day 90, etc.
- $500 per employee
- 3 employees = $1,500/month

**Cost-Saving Upgrade**: Employee Benefits Package ($20,000) reduces wages by $100/employee/month

---

## Store Upgrades

Permanent improvements to your store. One-time purchase.

### Capacity Upgrades

| Upgrade | Cost | Benefit |
|---------|------|---------|
| **Additional Shelving** | $2,000 | +2 product types |
| **Display Cases** | $3,500 | +3 product types |

### Employee Efficiency Upgrades

| Upgrade | Cost | Benefit |
|---------|------|---------|
| **Extra Cashier Station** | $3,000 | +30 customer capacity |
| **Express Checkout Lane** | $5,000 | +60 customer capacity |
| **Warehouse Extension** | $5,000 | +400 item restocking capacity |
| **Loading Dock** | $10,000 | +600 item restocking capacity |

### Progression Upgrades

| Upgrade | Cost | Benefit |
|---------|------|---------|
| **Business Course** | $2,000 | +10% XP gain |
| **MBA Program** | $5,000 | +25% XP gain |
| **Employee Benefits Package** | $20,000 | -$100 monthly cost per employee |

### Strategic Upgrades

| Upgrade | Cost | Benefit | Duration |
|---------|------|---------|----------|
| **Vendor Partnership (Budget)** | $5,000 | -5% at Budget Goods Ltd. | 30 days |
| **Vendor Partnership (Premium)** | $10,000 | -7% at Premium Select Inc. | 30 days |
| **Vendor Partnership (Universal)** | $30,000 | -10% at Universal Supply | 30 days |
| **Distribution Network** | $150,000 | -1 day delivery time (all vendors) | Permanent |

### Production Lines (Advanced)

Manufacture items at 50% market price:

| Production Line | Cost | Unlocks At | Items Produced |
|----------------|------|------------|----------------|
| **Basic Food** | $30,000 | Level 15 | Bread, Pasta, Rice, etc. |
| **Electronics** | $100,000 | Level 25 | Chargers, Headphones, etc. |
| **Luxury Goods** | $250,000 | Level 40 | Designer items, Jewelry, etc. |

---

## Strategy Guide

### Early Game (Days 1-30)

**Goals**: Build cash reserves, establish profitable items

1. **Focus on essentials** - Bread, Milk, Eggs are high-demand, low-cost
2. **Use instant delivery vendors** - Avoid stockouts while learning
3. **Price at 110-115% market** - Maximize margin while staying competitive
4. **Don't hire yet** - Save your money, base capacity is enough initially
5. **Monitor demand** - See which items sell out fastest

**Target**: $5,000-10,000 by Day 30

### Mid Game (Days 30-100)

**Goals**: Expand product range, hire first employees, increase volume

1. **Expand to mid-range items** ($10-50) - Coffee Maker, Shampoo, Office supplies
2. **Hire your first cashier** when hitting 20 customer cap regularly
3. **Use bulk vendors** - Cheap Goods Co. and Bulk Goods Co. for volume discounts
4. **Buy capacity upgrades** - Additional Shelving ($2k) for +2 products
5. **Consider vendor partnerships** - If one vendor dominates your supply
6. **Watch for special events** - Stock up before +50% price spikes, sell during -50% sales

**Target**: $25,000-50,000 by Day 100

### Late Game (Days 100-365)

**Goals**: Maximize profits, dominate high-end market

1. **Target uncapped customers** (Day 50+) - Stock expensive items ($100+)
2. **Use VIP Goods Co.** - 95% pricing on luxury items is excellent
3. **Hire multiple employees** - Scale up to handle 100+ customers/day
4. **Focus on high-margin items** - Electronics, Gaming, Luxury goods
5. **Consider Production Lines** - 50% manufacturing cost is huge savings
6. **Optimize portfolio** - Drop low-profit items, focus on winners
7. **Distribution Network** ($150k) - Eliminate lead times for flexibility

**Target**: $100,000+ by Day 365

### Advanced Tips

**Vendor Optimization**
- Always use 3 vendors per key item for price competition
- Mix instant delivery (safety) with delayed delivery (savings)
- Check vendor limits - don't rely on limited suppliers for high-volume items

**Pricing Strategy**
- Track market price changes - raise prices during spikes
- Lower prices slightly on overstocked items to clear inventory
- Keep prices consistent to maintain reputation

**Reputation Management**
- Reputation ranges from -100 to +100
- Built on: pricing consistency, availability, fulfillment rate
- Higher reputation = more customers choose you over competitors

**Cash Flow**
- Always keep $5,000+ reserve for emergencies
- Employee wages hit every 30 days - plan ahead
- Reinvest profits into upgrades that increase capacity

**Competitor Analysis**
- Check competitor status regularly (Menu option 7)
- If they're ahead, analyze: What items? What prices? More employees?
- Undercut their prices on high-volume items to steal market share

---

## Winning the Game

### Victory Condition

**The player with the most CASH at Day 365 wins!**

- Only liquid cash counts (not inventory value)
- Inventory doesn't convert to cash at game end
- Sell off inventory in final days to maximize cash

### Final Week Strategy (Days 358-365)

1. **Stop buying inventory** - No new orders that won't sell
2. **Lower prices aggressively** - Clear out all stock
3. **Avoid hiring** - No new employees this late
4. **Don't buy upgrades** - Cash is more valuable than improvements now
5. **Focus on volume** - Sell, sell, sell!

### Difficulty Scaling

The game gets harder as days progress:
- **Customer budgets increase** (high-spenders become majority)
- **Customer count grows** (more competition for their business)
- **Market volatility** (bigger price swings, demand shifts)
- **AI competitors improve** (they level up and expand too)

### Multiplayer

- 2-4 human players can compete
- Turn-based: all humans must "Pass Day" before day advances
- 2 AI competitors (Alice Corp, Bob Ltd) always play optimally
- Compete on same market - your success affects their opportunities

---

## Game Saves

- **Save/Load** via main menu option
- Single save file (`save.json`)
- Saves: day, cash, inventory, employees, upgrades, buy orders, prices
- Load on startup if save exists

---

## Quick Reference

### Key Formulas

```
Profit per Item = Selling Price - Cost Price
XP to Next Level = 500 × Level + (10,000 × (Level ÷ 10))
Customer Capacity = 20 + (30 × Cashiers) + Upgrades
Restocking Capacity = 200 + (200 × Restockers) + Upgrades
Product Slots = 3 + Level + Upgrades
```

### Important Thresholds

- **Day 10**: Special customers start appearing
- **Day 14**: +20 customer milestone boost
- **Day 30**: First employee wages due, price event
- **Day 50**: Uncapped customers unlock
- **Day 100**: Customer base shifts to 60% high-spenders
- **Every 14 days**: +20 customers
- **Every 30 days**: Employee wages, price events

### Optimal Starting Strategy

**Day 1-3:**
1. Set buy orders: 50 Bread, 50 Milk, 30 Eggs (Cheap Goods Co.)
2. Set prices: 115% of market price for all
3. Pass day and observe

**Day 4-7:**
1. Adjust based on sales data
2. Add Coffee and Toilet Paper if profitable
3. Increase quantities on items that sold out

**Day 8-14:**
1. Expand to all 6 starting items
2. Monitor which items have highest demand
3. Prepare for first special customers (Day 10)

**Day 15-30:**
1. Save for first upgrade (Additional Shelving $2k)
2. Expand product range to 5 items
3. Prepare for employee wages (Day 30)

---

## Troubleshooting

**Problem: Running out of cash**
- Solution: Lower buy order quantities, focus on high-margin items, delay hiring

**Problem: Items not selling**
- Solution: Lower prices to 100-105% market, check if item matches customer budgets

**Problem: Losing to competitors**
- Solution: Match their prices on popular items, expand product range, improve fulfillment rate

**Problem: Too many customers, not enough capacity**
- Solution: Hire cashiers (+30 each), buy checkout upgrades

**Problem: Can't restock enough items**
- Solution: Hire restockers (+200 each), buy warehouse upgrades

**Problem: Not leveling up fast enough**
- Solution: Sell more volume (cheap items work), buy XP boost upgrades

---

## Conclusion

Economy Simulation rewards smart planning, adaptability, and strategic thinking.

**Remember**:
- Buy low from vendors
- Sell high to customers
- Expand capacity strategically
- Watch competitors
- Adapt to market changes

Good luck, and may you become the wealthiest store owner in the market!

---

*For technical issues or questions, check the repository README or open an issue on GitHub.*
