#!/usr/bin/env python3
"""Quick test script to verify vendor changes."""

from economy_sim import create_vendors, Vendor

def test_vendors():
    """Test that all vendor changes were applied correctly."""
    vendors = create_vendors()

    print("Testing vendor changes...")
    print(f"Total vendors: {len(vendors)} (expected: 9)")
    assert len(vendors) == 9, f"Expected 9 vendors, got {len(vendors)}"

    # Check each vendor
    vendor_specs = {
        "Lucky Deal Trader": {"pricing": 0.70, "lead_time": 4},
        "Discount Wholesale Co.": {"pricing": 0.80, "lead_time": 3},
        "Budget Goods Ltd.": {"pricing": 0.90, "lead_time": 1},
        "Premium Select Inc.": {"pricing": 0.95, "lead_time": 1},
        "Instant Goods Ltd.": {"pricing": 0.98, "lead_time": 0},
        "Universal Supply Corp.": {"pricing": 1.05, "lead_time": 0},
        "Bulk Goods Co.": {"pricing": 0.85, "lead_time": 1},
        "Cheap Goods Co.": {"pricing": 0.80, "lead_time": 3},
        "VIP Goods Co.": {"pricing": 0.95, "lead_time": 1}
    }

    for vendor in vendors:
        if vendor.name in vendor_specs:
            specs = vendor_specs[vendor.name]
            print(f"\n✓ {vendor.name}:")
            print(f"  Pricing: {vendor.pricing_multiplier*100:.0f}% (expected: {specs['pricing']*100:.0f}%)")
            print(f"  Lead Time: {vendor.lead_time} days (expected: {specs['lead_time']} days)")

            assert vendor.pricing_multiplier == specs["pricing"], \
                f"{vendor.name}: expected pricing {specs['pricing']}, got {vendor.pricing_multiplier}"
            assert vendor.lead_time == specs["lead_time"], \
                f"{vendor.name}: expected lead_time {specs['lead_time']}, got {vendor.lead_time}"

    # Check Instant Goods Ltd specifically
    instant_goods = next((v for v in vendors if v.name == "Instant Goods Ltd."), None)
    assert instant_goods is not None, "Instant Goods Ltd. not found"
    assert instant_goods.selection_type == "price_threshold", \
        f"Instant Goods Ltd: expected selection_type 'price_threshold', got {instant_goods.selection_type}"
    assert instant_goods.selection_params == 40.0, \
        f"Instant Goods Ltd: expected selection_params 40.0, got {instant_goods.selection_params}"

    # Check order: Instant Goods Ltd should be after Premium Select Inc (index 4 after index 3)
    vendor_names = [v.name for v in vendors]
    premium_idx = vendor_names.index("Premium Select Inc.")
    instant_idx = vendor_names.index("Instant Goods Ltd.")
    print(f"\n✓ Vendor order: Premium Select Inc. at index {premium_idx}, Instant Goods Ltd. at index {instant_idx}")
    assert instant_idx == premium_idx + 1, \
        f"Instant Goods Ltd should be right after Premium Select Inc."

    print("\n" + "=" * 60)
    print("✅ All vendor tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_vendors()
