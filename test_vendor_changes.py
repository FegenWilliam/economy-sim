#!/usr/bin/env python3
"""Quick test script to verify vendor changes."""

from economy_sim import create_vendors, Vendor

def test_vendors():
    """Test that all vendor changes were applied correctly."""
    vendors = create_vendors()

    print("Testing vendor changes...")
    print(f"Total vendors: {len(vendors)} (expected: 8)")
    assert len(vendors) == 8, f"Expected 8 vendors, got {len(vendors)}"

    # Check each vendor
    vendor_specs = {
        "Bulk Goods Co.": {"pricing": 0.85, "lead_time": 1},
        "Instant Goods Ltd.": {
            "pricing": 0.98,
            "lead_time": 0,
            "selection_type": "price_threshold",
            "selection_params": 40.0,
        },
        "Universal Supply Corp.": {"pricing": 1.02, "lead_time": 0},
        "Bulk Master Co.": {"pricing": 1.10, "lead_time": 1},
        "Stock Masters Ltd": {"pricing": 0.80, "lead_time": 2},
        "Luxury House Co.": {"pricing": 0.98, "lead_time": 1},
        "Daily Essentials Co.": {"pricing": 0.90, "lead_time": 1},
        "Restocking Essentials Co.": {"pricing": 0.90, "lead_time": 1},
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

            # Optional selection settings when provided
            if "selection_type" in specs:
                assert vendor.selection_type == specs["selection_type"], \
                    f"{vendor.name}: expected selection_type {specs['selection_type']}, got {vendor.selection_type}"
            if "selection_params" in specs:
                assert vendor.selection_params == specs["selection_params"], \
                    f"{vendor.name}: expected selection_params {specs['selection_params']}, got {vendor.selection_params}"

    print("\n" + "=" * 60)
    print("✅ All vendor tests passed!")
    print("=" * 60)

if __name__ == "__main__":
    test_vendors()
