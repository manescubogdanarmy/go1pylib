from SnD.lane_planner import generate_lanes, estimate_search_path_length

def test_generate_lanes_basic():
    lanes = generate_lanes(10.0, 5.0, 2.5)
    assert len(lanes) == 4  # 0,2.5,5,7.5
    assert abs(lanes[0].length - 5.0) < 1e-6


def test_estimate_length():
    lanes = generate_lanes(6.0, 4.0, 2.0)
    total = estimate_search_path_length(lanes)
    assert total > 0
