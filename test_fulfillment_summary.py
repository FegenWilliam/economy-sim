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
