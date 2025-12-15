import pytest

import economy_sim as sim


def test_update_player_fulfillment_averages_and_formatting():
    player = sim.Player(name="test2")

    fulfillment_data = {"allocated": [100.0, 80.0], "overflow": [50.0]}
    sim.update_player_fulfillment_averages(player, fulfillment_data)

    assert player.average_fulfillment_pct == pytest.approx(76.666, rel=1e-3)
    assert player.allocated_average_fulfillment_pct == pytest.approx(90.0)
    assert player.overflow_average_fulfillment_pct == pytest.approx(50.0)

    summary = sim.format_fulfillment_summary(player, {"allocated": 2, "overflow": 1})

    assert "Average Fulfillment: 76.7%" in summary
    assert "Allocated Avg: 90.0% (2)" in summary
    assert "Overflow Avg: 50.0% (1)" in summary


def test_record_store_visit_metrics_counts_zero_needs_and_records_partial():
    visit_data = [
        {"store_name": "StoreA", "starting_needs": 0, "fulfilled": 0, "visit_type": "allocated"},
        {"store_name": "StoreA", "starting_needs": 5, "fulfilled": 2, "visit_type": "overflow"},
    ]
    daily_fulfillment_data = {"StoreA": {"allocated": [], "overflow": []}}
    fulfillment_visit_counts = {"StoreA": {"allocated": 0, "overflow": 0}}
    daily_reputation_changes = {"StoreA": 0}

    sim.record_store_visit_metrics(
        visit_data, daily_fulfillment_data, fulfillment_visit_counts, daily_reputation_changes
    )

    assert fulfillment_visit_counts == {"StoreA": {"allocated": 1, "overflow": 1}}
    assert daily_fulfillment_data["StoreA"]["allocated"] == [0.0]
    assert daily_fulfillment_data["StoreA"]["overflow"] == [40.0]
    assert daily_reputation_changes["StoreA"] == 0
