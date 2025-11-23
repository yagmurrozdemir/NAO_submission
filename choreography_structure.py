# choreography_structure.py
#
# Defines the *structure* of the choreography that
# the planner will work with:
#   - a fixed mandatory order
#   - global timing parameters (defaults)
#   - a helper to split total time into per-segment targets
#
# No search logic here.

from typing import List

from pose_definitions import (
    Pose,
    initial_pose,
    final_pose,
    inner_mandatory_poses,
    total_duration,
)

# ---------------------------------------------------------------
# Global configuration parameters
# ---------------------------------------------------------------

# Default desired duration of the entire choreography (seconds).
# This is only a *fallback* if no song length is provided.
DEFAULT_TOTAL_TIME_SECONDS: float = 117.0

# Absolute hard cap: the planner will never return a sequence
# whose total duration exceeds this bound.
ABSOLUTE_MAX_SECONDS: float = 117.0


# ---------------------------------------------------------------
# Mandatory order (fixed)
# ---------------------------------------------------------------

def mandatory_order() -> List[Pose]:
    """
    Returns the ordered list of mandatory poses that define the
    backbone of the choreography.

    Fixed inner order:
        StandInit ->
        Sit ->
        SitRelax ->
        Stand ->
        WipeForehead ->
        Hello ->
        StandZero ->
        Crouch
    """
    return [
        initial_pose(),        # StandInit
        next(p for p in inner_mandatory_poses() if p.label == "hello"),
        next(p for p in inner_mandatory_poses() if p.label == "stand_zero"),
        next(p for p in inner_mandatory_poses() if p.label == "sit"),
        next(p for p in inner_mandatory_poses() if p.label == "sit_relax"),
        next(p for p in inner_mandatory_poses() if p.label == "stand"),
        next(p for p in inner_mandatory_poses() if p.label == "wipe_forehead"),
        final_pose(),          # Crouch
    ]


# ---------------------------------------------------------------
# Helper: compute uniform per-segment time *targets*
# ---------------------------------------------------------------

def compute_uniform_segment_times(total_time: float) -> List[float]:
    """
    Given a global total time, compute equal time *targets*
    for each segment between mandatory poses.

    Let M = mandatory_order().
    There are (len(M) - 1) segments. We subtract the total duration
    of the mandatory poses themselves and split the remaining time
    equally across the segments.

    These are SOFT targets: the planner is free to deviate if needed
    to guarantee solvability, but they can be used as hints.
    """
    mand = mandatory_order()
    num_segments = len(mand) - 1
    mandatory_time = total_duration(mand)
    remaining = total_time - mandatory_time

    if remaining <= 0:
        # Edge case: mandatory poses already consume >= total_time.
        # Then we just assign zeros; the planner will still work,
        # but segments have no additional "target" time to fill.
        return [0.0 for _ in range(num_segments)]

    per_segment = remaining / num_segments
    return [per_segment for _ in range(num_segments)]
