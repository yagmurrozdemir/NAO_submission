# planner.py
#
# High-level search / planning logic to build a full choreography:
#   - obey the fixed mandatory order
#   - optionally adapt to a song length (S7)
#   - guarantee we never exceed a hard global time cap
#
# This file is pure planning logic – no NAOqi, no file I/O.

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pose_definitions import (
    Pose,
    all_intermediate_poses,
    total_duration,
)
from choreography_structure import (
    mandatory_order,
    compute_uniform_segment_times,
    DEFAULT_TOTAL_TIME_SECONDS,
    ABSOLUTE_MAX_SECONDS,
)

# Small logical state is just a dict[str, bool], e.g. {"standing": True}
State = Dict[str, bool]


@dataclass(frozen=True)
class SegmentPlan:
    """Plan for one segment: start mandatory -> intermediates -> end mandatory."""
    start: Pose
    end: Pose
    intermediates: List[Pose]


# -------------------------------------------------------------------
# Required intermediates (fixed 5 for the feasibility check)
# -------------------------------------------------------------------

REQUIRED_INTERMEDIATE_FILE_IDS: List[str] = [
    "1-Rotation_handgun_object",
    "9-Diagonal_left",
    "10-Diagonal_right",
    "7-Move_forward",
    "8-Move_backward",
]


def required_intermediate_poses() -> List[Pose]:
    """
    Resolve the fixed 5 required intermediates by file_id from the full
    intermediate pool.
    """
    pool = all_intermediate_poses()
    by_id = {p.file_id: p for p in pool}
    result: List[Pose] = []
    for fid in REQUIRED_INTERMEDIATE_FILE_IDS:
        pose = by_id.get(fid)
        if pose is None:
            print(
                "[PLAN] WARNING: required intermediate '{}' not found in all_intermediate_poses()."
                .format(fid)
            )
        else:
            result.append(pose)
    return result


def required_poses_for_time_check() -> List[Pose]:
    """
    The "required positions" used in the hard-cap feasibility check:
    all mandatory poses (from mandatory_order()) + the fixed 5 intermediates.
    """
    mand = mandatory_order()
    interms = required_intermediate_poses()
    return mand + interms


# -------------------------------------------------------------------
# Utilities for logical state
# -------------------------------------------------------------------

def apply_pose(state: State, pose: Pose) -> State:
    """
    Apply pose.post to the state and return a new state dict.
    """
    new_state = dict(state)
    for k, v in pose.post.items():
        new_state[k] = v
    return new_state


def state_satisfies(state: State, req: Dict[str, bool]) -> bool:
    """
    Check if 'state' satisfies all requirements in 'req'.
    Empty req means "no constraint".
    """
    for k, v in req.items():
        if k in state and state[k] != v:
            return False
    return True


# -------------------------------------------------------------------
# Planning per segment (between mandatory[i] and mandatory[i+1])
# -------------------------------------------------------------------

MAX_INTERMEDIATES_PER_SEGMENT = 6


def _plan_segment_internal(
    start_state: State,
    end_pose: Pose,
    intermediates_pool: List[Pose],
    time_budget_for_segment: float,
    mode: str = "min",  # "min" or "max"
) -> Optional[List[Pose]]:
    """
    Core segment planner used by both min- and max-time variants.

    All times here are in RAW seconds (pose.duration), as in the original
    implementation. Any speed_factor is handled at the top level by scaling
    the global time budgets, not by changing pose.duration.
    """
    assert mode in ("min", "max")

    # For "min" we can immediately bail out if we already satisfy end preconditions.
    if mode == "min" and state_satisfies(start_state, end_pose.pre):
        return []

    Node = Tuple[State, float, List[Pose]]
    q: deque[Node] = deque()
    q.append((start_state, 0.0, []))

    visited = set()  # (frozenset(state.items()), rounded_time, path_len)

    best_path: Optional[List[Pose]] = None
    best_time: float = -1.0

    while q:
        state, t_used, path = q.popleft()

        # Check if this node already satisfies end preconditions.
        if state_satisfies(state, end_pose.pre):
            if mode == "min":
                # First solution = shortest
                return path
            else:
                # mode == "max": keep the best-so-far, but continue exploring
                if t_used > best_time:
                    best_time = t_used
                    best_path = path

        if len(path) >= MAX_INTERMEDIATES_PER_SEGMENT:
            continue

        key = (frozenset(state.items()), round(t_used, 2), len(path))
        if key in visited:
            continue
        visited.add(key)

        for pose in intermediates_pool:
            if not state_satisfies(state, pose.pre):
                continue
            new_time = t_used + pose.duration
            if new_time > time_budget_for_segment + 1e-6:
                continue
            new_state = apply_pose(state, pose)
            new_path = path + [pose]
            q.append((new_state, new_time, new_path))

    # No more nodes to explore
    if mode == "max":
        return best_path  # may be None if no state satisfies end_pose.pre
    return None


def plan_segment_min(
    start_state: State,
    end_pose: Pose,
    intermediates_pool: List[Pose],
    time_budget_for_segment: float,
) -> Optional[List[Pose]]:
    return _plan_segment_internal(
        start_state, end_pose, intermediates_pool, time_budget_for_segment, mode="min"
    )


def plan_segment_max(
    start_state: State,
    end_pose: Pose,
    intermediates_pool: List[Pose],
    time_budget_for_segment: float,
) -> Optional[List[Pose]]:
    return _plan_segment_internal(
        start_state, end_pose, intermediates_pool, time_budget_for_segment, mode="max"
    )


# -------------------------------------------------------------------
# Top-level planner (min & max variants)
# -------------------------------------------------------------------

def _plan_full_choreography_generic(
    song_length_seconds: Optional[float],
    mode: str,
    speed_factor: float = 1.0,
) -> Optional[List[Pose]]:
    """
    Internal implementation used by both:
        - plan_full_choreography_min  (mode="min")
        - plan_full_choreography_max  (mode="max")

    mode == "min":
        behaves like your original planner: shortest choreography
        that respects mandatory order and cap.

    mode == "max":
        tries to make each segment as long as possible (without
        exceeding the cap), i.e. saturate the available intermediate budget.

    IMPORTANT:
        - pose.duration is always in RAW seconds (measured at speed_factor = 1.0).
        - We model speed_factor by scaling the *time cap* in raw seconds:
              hard_cap_raw = hard_cap_effective * speed_factor
          so that:
              total_duration_raw <= hard_cap_raw
          is equivalent to:
              effective_time = total_duration_raw / speed_factor <= hard_cap_effective
    """
    assert mode in ("min", "max")
    if speed_factor <= 0.0:
        raise ValueError("speed_factor must be positive, got {}".format(speed_factor))

    if song_length_seconds is None:
        desired_total = DEFAULT_TOTAL_TIME_SECONDS
        print("[PLAN] No song length provided; using default {:.2f}s.".format(desired_total))
    else:
        desired_total = float(song_length_seconds)
        print("[PLAN] Using song length ≈ {:.2f}s from MP3 / caller.".format(desired_total))

    # Effective cap in seconds (what the assignment / song sees)
    hard_cap_effective = min(desired_total, ABSOLUTE_MAX_SECONDS)
    # Raw cap in pose.duration time
    hard_cap_raw = hard_cap_effective * speed_factor

    mand = mandatory_order()

    # Required set for feasibility check: mandatory + 5 fixed intermediates.
    required_for_check = required_poses_for_time_check()
    required_time_raw = total_duration(required_for_check)
    if required_time_raw > hard_cap_raw + 1e-6:
        print(
            "[PLAN] Mandatory + 5 required intermediates take {:.2f}s (raw), "
            "which exceeds raw hard cap {:.2f}s (effective {:.2f}s, speed_factor {:.2f})."
            .format(required_time_raw, hard_cap_raw, hard_cap_effective, speed_factor)
        )
        return None

    # Mandatory-only backbone in raw seconds
    mand_time_raw = total_duration(mand)
    if mand_time_raw > hard_cap_raw + 1e-6:
        # This should not happen if the required-set check above passed,
        # but we keep it as a guard.
        print(
            "[PLAN] Mandatory poses alone take {:.2f}s (raw), which exceeds raw hard cap {:.2f}s."
            .format(mand_time_raw, hard_cap_raw)
        )
        return None

    # Raw intermediate budget
    interm_budget_total = hard_cap_raw - mand_time_raw

    # Segment targets are in effective seconds; scale to raw
    segment_targets_effective = compute_uniform_segment_times(hard_cap_effective)
    segment_targets_raw = [t * speed_factor for t in segment_targets_effective]

    intermediates_pool = all_intermediate_poses()

    full_sequence: List[Pose] = []
    current_state: State = {}

    # Apply the first mandatory pose
    first = mand[0]
    full_sequence.append(first)
    current_state = apply_pose(current_state, first)
    interm_budget_used = 0.0  # in raw seconds

    print(
        "[PLAN] Hard cap (effective) {:.2f}s, mandatory_time (raw) {:.2f}s, "
        "intermediate budget (raw) {:.2f}s. (speed_factor = {:.2f})"
        .format(hard_cap_effective, mand_time_raw, interm_budget_total, speed_factor)
    )

    num_segments = len(mand) - 1
    for idx in range(num_segments):
        start_pose = mand[idx]
        end_pose = mand[idx + 1]

        remaining_budget = interm_budget_total - interm_budget_used
        if remaining_budget < -1e-6:
            print(
                "[PLAN] No remaining intermediate budget before segment {}; planning failed."
                .format(idx)
            )
            return None

        soft_target_raw = (
            segment_targets_raw[idx] if idx < len(segment_targets_raw) else remaining_budget
        )
        segment_budget = min(
            soft_target_raw if soft_target_raw > 0.0 else remaining_budget,
            remaining_budget,
        )

        if segment_budget <= 1e-6:
            # No budget left for intermediates; we can only go directly,
            # if preconditions allow it.
            if not state_satisfies(current_state, end_pose.pre):
                print(
                    "[PLAN] Segment {}: no intermediate budget and cannot reach "
                    "next mandatory directly."
                    .format(idx)
                )
                return None
            full_sequence.append(end_pose)
            current_state = apply_pose(current_state, end_pose)
            continue

        # Plan intermediates for this segment
        if mode == "min":
            seg_interms = plan_segment_min(
                start_state=current_state,
                end_pose=end_pose,
                intermediates_pool=intermediates_pool,
                time_budget_for_segment=segment_budget,
            )
            # relax once to remaining_budget if needed
            if seg_interms is None and remaining_budget > segment_budget + 1e-6:
                seg_interms = plan_segment_min(
                    start_state=current_state,
                    end_pose=end_pose,
                    intermediates_pool=intermediates_pool,
                    time_budget_for_segment=remaining_budget,
                )
        else:
            # mode == "max"
            seg_interms = plan_segment_max(
                start_state=current_state,
                end_pose=end_pose,
                intermediates_pool=intermediates_pool,
                time_budget_for_segment=remaining_budget,
            )

        if seg_interms is None:
            print(
                "[PLAN] Failed to plan segment {}: {} → {} within remaining raw budget {:.2f}s."
                .format(idx, start_pose.label, end_pose.label, remaining_budget)
            )
            return None

        # Append intermediates and end_pose
        for p in seg_interms:
            full_sequence.append(p)
            current_state = apply_pose(current_state, p)
            interm_budget_used += p.duration

        full_sequence.append(end_pose)
        current_state = apply_pose(current_state, end_pose)

    total_raw = total_duration(full_sequence)
    if total_raw > hard_cap_raw + 1e-6:
        print(
            "[PLAN] Internal error: planned total {:.2f}s (raw) exceeds raw hard cap {:.2f}s."
            .format(total_raw, hard_cap_raw)
        )
        return None

    total_effective = total_raw / speed_factor
    print(
        "[PLAN] Found choreography with total duration {:.2f}s (effective) "
        "(raw {:.2f}s, effective cap {:.2f}s, speed_factor {:.2f})"
        .format(total_effective, total_raw, hard_cap_effective, speed_factor)
    )
    print("[PLAN] Total poses: {}".format(len(full_sequence)))
    return full_sequence


def plan_full_choreography(
    song_length_seconds: Optional[float] = None,
    speed_factor: float = 1.0,
) -> Optional[List[Pose]]:
    """
    Backwards-compatible: "min" mode (original behavior), with an optional
    speed_factor that scales the global time cap in raw seconds.

    EXTRA REQUIREMENT (assignment-specific):
    The returned choreography must contain:
        - all mandatory poses (from mandatory_order())
        - all 5 fixed required intermediates (REQUIRED_INTERMEDIATE_FILE_IDS)
      at least once.

    We first call the generic planner in "min" mode, then, if any of the
    5 required intermediates are missing, we insert them just before the
    final mandatory pose (Crouch), provided we stay within the global cap.
    """
    # 1) Run the generic min planner (no extra constraints).
    seq = _plan_full_choreography_generic(
        song_length_seconds, mode="min", speed_factor=speed_factor
    )
    if seq is None:
        return None

    # 2) Check which required intermediates are already present.
    present_ids = {p.file_id for p in seq}
    req_poses = required_intermediate_poses()
    req_ids_in_order = [p.file_id for p in req_poses]
    missing_ids = [fid for fid in req_ids_in_order if fid not in present_ids]

    if not missing_ids:
        # Already contains all 5 required intermediates; nothing to do.
        return seq

    # 3) Map file_id -> Pose for intermediates so we can resolve missing ones.
    interm_pool = all_intermediate_poses()
    by_id = {p.file_id: p for p in interm_pool}
    missing_poses: List[Pose] = []
    for fid in missing_ids:
        pose = by_id.get(fid)
        if pose is None:
            print(
                "[PLAN] WARNING: required intermediate '{}' not found in intermediate pool; "
                "cannot enforce its presence.".format(fid)
            )
        else:
            missing_poses.append(pose)

    if not missing_poses:
        # All missing ones were unknown; just return original sequence.
        return seq

    # 4) Compute global raw cap again (same logic as in _plan_full_choreography_generic).
    if song_length_seconds is None:
        desired_total = DEFAULT_TOTAL_TIME_SECONDS
    else:
        desired_total = float(song_length_seconds)
    hard_cap_effective = min(desired_total, ABSOLUTE_MAX_SECONDS)
    hard_cap_raw = hard_cap_effective * speed_factor

    # How much extra raw time do we add if we insert all missing poses?
    extra_raw = sum(p.duration for p in missing_poses)
    current_raw = total_duration(seq)
    new_total_raw = current_raw + extra_raw

    if new_total_raw > hard_cap_raw + 1e-6:
        # In theory this should not happen, because we earlier checked that
        # (mandatory + all 5 required) fits inside hard_cap_raw. However,
        # we keep this guard for robustness.
        print(
            "[PLAN] WARNING: cannot insert all required intermediates without exceeding "
            "raw cap. Leaving min choreography unchanged."
        )
        return seq

    # 5) Insert the missing intermediates just before the final mandatory pose.
    mand = mandatory_order()
    last_mandatory = mand[-1]  # typically Crouch
    last_idx = None
    for i, p in enumerate(seq):
        if p.file_id == last_mandatory.file_id:
            last_idx = i
    if last_idx is None:
        # Fallback: if for some reason final mandatory is not found, append at end.
        last_idx = len(seq)

    # Insert missing poses in the fixed required order.
    new_seq = seq[:last_idx] + missing_poses + seq[last_idx:]

    new_total_raw = total_duration(new_seq)
    new_total_effective = new_total_raw / speed_factor
    print(
        "[PLAN] Enforced presence of all 5 required intermediates in min choreography. "
        "New total duration (raw) {:.2f}s, (effective) {:.2f}s."
        .format(new_total_raw, new_total_effective)
    )
    print("[PLAN] Total poses after enforcement: {}".format(len(new_seq)))

    return new_seq


def plan_full_choreography_maximal(
    song_length_seconds: Optional[float] = None,
    speed_factor: float = 1.0,
) -> Optional[List[Pose]]:
    """
    "Max" mode: tries to saturate the time budget with intermediates.
    The budget is scaled in raw seconds by speed_factor.
    """
    return _plan_full_choreography_generic(
        song_length_seconds, mode="max", speed_factor=speed_factor
    )

