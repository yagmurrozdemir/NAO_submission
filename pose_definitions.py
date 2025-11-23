# pose_definitions.py
#
# Domain model for the NAO planning project.
# This file ONLY defines data: poses (mandatory & intermediate) and
# some helper functions. No search/planning logic here.
#
# IMPORTANT (S7):
#   - The "duration" values here are an *approximate planning model*,
#     NOT the exact physical durations of the NAO motions.
#   - At execution time you can:
#       * measure real durations with measure_durations.py
#       * choose a global speed_factor for ALMotion
#     without changing this file. The planner only needs
#     relative/approximate durations to schedule the dance.

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Pose:
    """
    A single NAO pose / movement.
    Attributes:
        label:    Logical short name we use in the planner
        file_id:  Base name of the motion file / script
                  (e.g. '14-StandInit' -> motions/14-StandInit.py)
        duration: Approximate duration of the movement in seconds
        pre:      Preconditions on a tiny logical state
        post:     Postconditions on the same logical state
    """
    label: str
    file_id: str
    duration: float
    pre: Dict[str, bool]
    post: Dict[str, bool]




"""

14-StandInit 4.523
16-Sit 22.716
17-SitRelax 9.845
11-Stand 23.157
Wipe_Forehead 6.499
Hello 5.848
15-StandZero 4.782
6-Crouch 5.688
1-Rotation_handgun_object 6.204
2-Right_arm 17.893
3-Double_movement 11.755
4-Arms_opening 13.927
5-Union_arms 10.183
7-Move_forward 7.556
8-Move_backward 5.092
9-Diagonal_left 5.396
10-Diagonal_right 5.389
13-Rotation_foot_LLeg 13.665
12-Rotation_foot_RLeg 11.506

"""

# -------------------------------------------------------------------
# Mandatory positions
# -------------------------------------------------------------------

# Fixed start and end

POSE_STAND_INIT = Pose(
    label="stand_init",
    file_id="14-StandInit",
    duration=4.523,        # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_CROUCH = Pose(
    label="crouch",
    file_id="6-Crouch",
    duration=5.688,        # measured
    pre={"standing": True},
    post={"standing": False},  # logically ends not-standing
)

POSE_SIT = Pose(
    label="sit",
    file_id="16-Sit",
    duration=22.716,
    pre={"standing": True},
    post={"standing": False},
)

POSE_SIT_RELAX = Pose(
    label="sit_relax",
    file_id="17-SitRelax",
    duration=9.845,        # measured
    pre={"standing": False},
    post={"standing": False},
)

POSE_STAND = Pose(
    label="stand",
    file_id="11-Stand",
    duration=23.157,       # last measured value (SitRelax -> Stand context)
    pre={"standing": False},
    post={"standing": True},
)

POSE_WIPE_FOREHEAD = Pose(
    label="wipe_forehead",
    file_id="Wipe_Forehead",   # motions/Wipe_Forehead.py
    duration=6.499,            # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_HELLO = Pose(
    label="hello",
    file_id="Hello",           # motions/Hello.py
    duration=5.848,            # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_STAND_ZERO = Pose(
    label="stand_zero",
    file_id="15-StandZero",
    duration=4.782,            # measured
    pre={"standing": True},
    post={"standing": True},
)


# Convenience groupings

def initial_pose() -> Pose:
    return POSE_STAND_INIT


def final_pose() -> Pose:
    return POSE_CROUCH


def inner_mandatory_poses() -> List[Pose]:
    """
    The 6 inner mandatory poses that must appear at least once somewhere
    between StandInit and Crouch. Their *logical* order is chosen in
    choreography_structure.mandatory_order().
    """
    return [
        POSE_HELLO,
        POSE_STAND_ZERO,
        POSE_SIT,
        POSE_SIT_RELAX,
        POSE_STAND,
        POSE_WIPE_FOREHEAD,
    ]


def all_mandatory_poses() -> List[Pose]:
    """
    Returns [fixed start] + inner mandatory + [fixed end].
    """
    return [initial_pose()] + inner_mandatory_poses() + [final_pose()]


# -------------------------------------------------------------------
# Intermediate positions from the slides (core set)
# -------------------------------------------------------------------

POSE_ROTATION_HANDGUN = Pose(
    label="rotation_handgun",
    file_id="1-Rotation_handgun_object",
    duration=6.204,   # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_RIGHT_ARM = Pose(
    label="right_arm",
    file_id="2-Right_arm",
    duration=17.893,  # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_DOUBLE_MOVEMENT = Pose(
    label="double_movement",
    file_id="3-Double_movement",
    duration=11.755,  # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_ARMS_OPENING = Pose(
    label="arms_opening",
    file_id="4-Arms_opening",
    duration=13.927,  # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_UNION_ARMS = Pose(
    label="union_arms",
    file_id="5-Union_arms",
    duration=10.183,  # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_MOVE_FORWARD = Pose(
    label="move_forward",
    file_id="7-Move_forward",
    duration=7.556,   # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_MOVE_BACKWARD = Pose(
    label="move_backward",
    file_id="8-Move_backward",
    duration=5.092,   # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_DIAGONAL_LEFT = Pose(
    label="diagonal_left",
    file_id="9-Diagonal_left",
    duration=5.396,   # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_DIAGONAL_RIGHT = Pose(
    label="diagonal_right",
    file_id="10-Diagonal_right",
    duration=5.389,   # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_ROTATION_FOOT_L = Pose(
    label="rotation_foot_left",
    file_id="13-Rotation_foot_LLeg",
    duration=13.665,  # measured
    pre={"standing": True},
    post={"standing": True},
)

POSE_ROTATION_FOOT_R = Pose(
    label="rotation_foot_right",
    file_id="12-Rotation_foot_RLeg",
    duration=11.506,  # measured
    pre={"standing": True},
    post={"standing": True},
)



# -------------------------------------------------------------------
# Additional intermediate positions (.crg-type and “fun” moves)
# (defined for completeness; currently NOT used in planning)
# -------------------------------------------------------------------

POSE_AIR_GUITAR = Pose(
    label="air_guitar",
    file_id="AirGuitar",
    duration=4.0,
    pre={"standing": True},
    post={"standing": True},
)

POSE_ARM_DANCE = Pose(
    label="arm_dance",
    file_id="ArmDance",
    duration=5.5,
    pre={"standing": True},
    post={"standing": True},
)

POSE_BIRTHDAY_DANCE = Pose(
    label="birthday_dance",
    file_id="Happy_Birthday",
    duration=10.0,
    pre={"standing": True},
    post={"standing": True},
)

POSE_SPRINKLER = Pose(
    label="sprinkler",
    file_id="Sprinkler",
    duration=10.0,
    pre={"standing": True},
    post={"standing": False},  # ends in some non-neutral posture
)

POSE_HANDS_ON_HIPS = Pose(
    label="hands_on_hips",
    file_id="Hands_on_Hips",
    duration=2.0,
    pre={"standing": True},
    post={"standing": True},
)

POSE_COME_ON = Pose(
    label="come_on",
    file_id="ComeOn",
    duration=3.5,
    pre={"standing": True},
    post={"standing": True},
)

POSE_DAB = Pose(
    label="dab",
    file_id="Dab",
    duration=6.0,
    pre={"standing": True},
    post={"standing": True},
)

POSE_DANCE_MOVE = Pose(
    label="dance_move",
    file_id="DanceMove",
    duration=6.0,
    pre={"standing": True},
    post={"standing": True},
)

POSE_PULP_FICTION = Pose(
    label="pulp_fiction",
    file_id="PulpFiction",
    duration=5.5,
    pre={"standing": True},
    post={"standing": True},
)

POSE_THE_ROBOT = Pose(
    label="the_robot",
    file_id="TheRobot",
    duration=6.0,
    pre={"standing": True},
    post={"standing": True},
)

POSE_SHUFFLE = Pose(
    label="shuffle",
    file_id="Shuffle",
    duration=6.8,
    pre={"standing": True},
    post={"standing": True},
)

POSE_WAVE = Pose(
    label="wave",
    file_id="Wave",
    duration=3.7,
    pre={"standing": True},
    post={"standing": True},
)

POSE_GLORY = Pose(
    label="glory",
    file_id="Glory",
    duration=3.3,
    pre={"standing": True},
    post={"standing": True},
)

POSE_CLAP = Pose(
    label="clap",
    file_id="Clap",
    duration=4.1,
    pre={"standing": True},
    post={"standing": True},
)

POSE_JOY = Pose(
    label="joy",
    file_id="Joy",
    duration=4.5,
    pre={"standing": True},
    post={"standing": True},
)

POSE_BOW = Pose(
    label="bow",
    file_id="Bow",
    duration=3.9,
    pre={"standing": True},
    post={"standing": True},
)


# -------------------------------------------------------------------
# Pools & utilities
# -------------------------------------------------------------------

def core_intermediate_poses() -> List[Pose]:
    """
    Exactly the intermediate positions listed in the slides (rotation,
    arms, move fwd/back, diagonals, etc.).
    """
    return [
        POSE_ROTATION_HANDGUN,
        POSE_RIGHT_ARM,
        POSE_DOUBLE_MOVEMENT,
        POSE_ARMS_OPENING,
        POSE_UNION_ARMS,
        POSE_MOVE_FORWARD,
        POSE_MOVE_BACKWARD,
        POSE_DIAGONAL_LEFT,
        POSE_DIAGONAL_RIGHT,
        POSE_ROTATION_FOOT_L,
        POSE_ROTATION_FOOT_R,
    ]


def crg_like_intermediate_poses() -> List[Pose]:
    """
    Intermediate poses that come from .crg dance-like motions.
    For now we return an empty list, because we do not have matching
    .py motion scripts for these poses. They are defined above only
    for completeness / future work.
    """
    return [
        # POSE_AIR_GUITAR,
        # POSE_ARM_DANCE,
        # POSE_BIRTHDAY_DANCE,
        # POSE_SPRINKLER,
    ]


def ornamental_intermediate_poses() -> List[Pose]:
    """
    Extra fun moves. Not required by the assignment.
    For now we also return an empty list, because we do not have
    .py motion scripts for these. Enable them one by one when you
    actually implement the corresponding motions.
    """
    return [
        # POSE_HANDS_ON_HIPS,
        # POSE_COME_ON,
        # POSE_DAB,
        # POSE_DANCE_MOVE,
        # POSE_PULP_FICTION,
        # POSE_THE_ROBOT,
        # POSE_SHUFFLE,
        # POSE_WAVE,
        # POSE_GLORY,
        # POSE_CLAP,
        # POSE_JOY,
        # POSE_BOW,
    ]


def all_intermediate_poses() -> List[Pose]:
    """
    Full pool of poses that can be used as intermediate ones.
    Currently this is just the core set; crg-like and ornamental
    pools are empty until you implement their .py scripts.
    """
    return (
        core_intermediate_poses()
        + crg_like_intermediate_poses()
        + ornamental_intermediate_poses()
    )


def all_known_poses() -> List[Pose]:
    """
    Convenience: all mandatory and all intermediate poses together.
    """
    return all_mandatory_poses() + all_intermediate_poses()


def total_duration(sequence: List[Pose]) -> float:
    """Sum durations of a sequence of poses."""
    return sum(p.duration for p in sequence)
