from SnD.pose import Pose, apply_forward, apply_turn
import math

def test_forward_and_turn():
    p = Pose()
    apply_forward(p, 1.0)  # heading 0 => +Y
    assert abs(p.y - 1.0) < 1e-6
    apply_turn(p, math.pi/2)  # now heading 90 deg
    apply_forward(p, 1.0)
    # heading 90 => +X
    assert abs(p.x - 1.0) < 1e-6
