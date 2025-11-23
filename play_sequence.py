#!/usr/bin/env python3
"""
play_sequence.py
Option B: plan the choreography and export the resulting sequence
of motion script IDs to sequence.txt, to be executed by Choregraphe.

S7 behavior:
    - Optionally read an MP3 file and use its length (t_song).
    - Compute:
        t_min_feasible: shortest feasible choreography duration
        t_max_feasible: longest feasible choreography duration under MAX_TIME_LIMIT
    - Then:
        if t_min_feasible <= t_song <= t_max_feasible:
            use findBestPath(t_song)
        elif t_song > t_max_feasible:
            use path for t_max_feasible
        elif t_song < t_min_feasible:
            use path for t_min_feasible
    - If no --music is given, behave like original Option B.

The robot_ip / python2-bin args are kept for compatibility but are
NOT used in this Option B pipeline; execution will happen inside
Choregraphe using the exact teacher .py files.
"""

import argparse
import os
import sys

from planner import (
    plan_full_choreography,          # MIN mode (original behavior)
    plan_full_choreography_maximal,  # MAX mode (new)
)
from pose_definitions import total_duration

# ---------------------------------------------------------------
# Global constants
# ---------------------------------------------------------------
MAX_TIME_LIMIT = 117.0  # seconds, global hard cap from the assignment


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def export_sequence_to_file(sequence, speed_factor, path="sequence.txt"):
    """
    Write:
        Line 1 → speed factor (float)
        Remaining lines → file_ids (one per line)
    """
    with open(path, "w") as f:
        f.write(str(speed_factor) + "\n")   # <-- FIRST LINE: speed factor
        for p in sequence:
            f.write(p.file_id + "\n")

    abs_path = os.path.abspath(path)
    print("[INFO] Exported sequence to {}".format(abs_path))


def get_song_length_seconds(path: str):
    """
    Return the length of an MP3 in seconds using mutagen.
    If anything fails, return None and fall back to the pure-planner behavior.
    """
    if not path:
        return None
    if not os.path.exists(path):
        print("[WARN] Music file not found: {}".format(path))
        return None
    try:
        from mutagen.mp3 import MP3
    except ImportError:
        print("[WARN] mutagen not installed; ignoring --music and using pure planner.")
        return None
    try:
        audio = MP3(path)
        length = float(audio.info.length)
        print("[INFO] Detected song length ≈ {:.2f}s from {}".format(length, path))
        return length
    except Exception as e:
        print("[WARN] Could not read MP3 length ({}); ignoring --music.".format(e))
        return None


def find_first_path_in_range(min_dur, max_dur, cap_hint, speed_factor):
    """
    findFirstEncounteredPathThatHasDurationInRange(min_dur, max_dur).

    IMPORTANT FIX:
    We now use the **MAX** planner here so that the candidate tries
    to fill the budget up to cap_hint (instead of always returning
    the minimal 30s backbone).

    We:
        - call plan_full_choreography_maximal(song_length_seconds = cap_hint)
          with the given speed_factor (cap_hint is in *effective* seconds)
        - compute its actual effective duration T_eff = total_duration(seq) / speed_factor
        - if T_eff is in [min_dur, max_dur], we accept it, else return None.
    """
    if cap_hint <= 0.0:
        return None
    cap = min(cap_hint, MAX_TIME_LIMIT)

    # cap is in effective seconds; planner will interpret it that way.
    seq = plan_full_choreography_maximal(
        song_length_seconds=cap,
        speed_factor=speed_factor,
    )
    if seq is None:
        return None

    T_raw = total_duration(seq)
    T_eff = T_raw / speed_factor
    print("[PLAN] Candidate duration (effective) {:.2f}s for cap_hint {:.2f}s".format(T_eff, cap_hint))
    if min_dur <= T_eff <= max_dur + 1e-6:
        return seq
    return None


def find_best_path_for_duration(duration_amount, speed_factor):
    """
    Your findBestPath(duration_amount) exactly as specified:

        close_candidate: [0.9 * duration_amount, 1.0 * duration_amount]
        mid_candidate:   [0.7 * duration_amount, 0.9 * duration_amount]
        far_candidate:   [0.5 * duration_amount, 0.7 * duration_amount]
        any_candidate:   [0.0 * duration_amount, 0.5 * duration_amount]

    All durations here (duration_amount, window bounds) are in *effective*
    seconds (i.e., what the user / song sees). We match them against the
    effective durations of candidate sequences: total_duration(seq) / speed_factor.

    'First encountered' is modeled by trying windows in that order,
    each time using the MAX planner capped at the window's upper bound.
    """
    S = float(duration_amount)

    # 1) Close
    close_min = 0.9 * S
    close_max = 1.0 * S
    print("[PLAN] findBestPath: trying close window [{:.2f}, {:.2f}]".format(close_min, close_max))
    close_candidate = find_first_path_in_range(
        close_min, close_max, cap_hint=close_max, speed_factor=speed_factor
    )
    if close_candidate is not None:
        print("[PLAN] findBestPath: using close_candidate.")
        return close_candidate

    # 2) Mid
    mid_min = 0.7 * S
    mid_max = 0.9 * S
    print("[PLAN] findBestPath: trying mid window [{:.2f}, {:.2f}]".format(mid_min, mid_max))
    mid_candidate = find_first_path_in_range(
        mid_min, mid_max, cap_hint=mid_max, speed_factor=speed_factor
    )
    if mid_candidate is not None:
        print("[PLAN] findBestPath: using mid_candidate.")
        return mid_candidate

    # 3) Far
    far_min = 0.5 * S
    far_max = 0.7 * S
    print("[PLAN] findBestPath: trying far window [{:.2f}, {:.2f}]".format(far_min, far_max))
    far_candidate = find_first_path_in_range(
        far_min, far_max, cap_hint=far_max, speed_factor=speed_factor
    )
    if far_candidate is not None:
        print("[PLAN] findBestPath: using far_candidate.")
        return far_candidate

    # 4) Guarantee pass: 0.0x–0.5x
    any_min = 0.0 * S
    any_max = 0.5 * S
    print("[PLAN] findBestPath: trying any window [{:.2f}, {:.2f}]".format(any_min, any_max))
    any_candidate = find_first_path_in_range(
        any_min, any_max, cap_hint=any_max, speed_factor=speed_factor
    )
    if any_candidate is None:
        print("[BUG] findBestPath: no candidate found in [0.0, 0.5] window. "
              "This should not happen if t_min/t_max logic is correct.")
        return None
    print("[PLAN] findBestPath: using any_candidate.")
    return any_candidate


def choose_sequence_for_song(t_min_seq, t_max_seq, song_length, speed_factor):
    """
    Implements exactly:

        t_min_feasible = duration of t_min_seq
        t_max_feasible = duration of t_max_seq

        if t_song in [t_min_feasible, t_max_feasible]:
            return findBestPath(t_song)
        elif t_song > t_max_feasible:
            return t_max_seq
        elif t_song < t_min_feasible:
            return t_min_seq

    BUT:
    - Durations here are interpreted in *effective* seconds, i.e.
      total_duration(seq) / speed_factor, because t_song is the
      real-world song length, and the assignment’s 117s cap is also
      in real-world time.

    If song_length is None, we just return t_min_seq (original behavior).
    """
    # Effective durations of the minimal and maximal feasible choreographies.
    t_min_eff = total_duration(t_min_seq) / speed_factor
    t_max_eff = total_duration(t_max_seq) / speed_factor

    print("[PLAN] t_min_feasible (effective) ≈ {:.2f}s".format(t_min_eff))
    print("[PLAN] t_max_feasible (effective) ≈ {:.2f}s".format(t_max_eff))

    if song_length is None:
        print("[PLAN] No song length provided; using t_min_feasible choreography.")
        return t_min_seq

    t_song = float(song_length)
    print("[PLAN] t_song (from MP3) ≈ {:.2f}s".format(t_song))

    # Guard if for some reason t_max < t_min (should not happen)
    if t_max_eff < t_min_eff:
        print("[WARN] t_max_feasible < t_min_feasible; swapping.")
        t_min_eff, t_max_eff = t_max_eff, t_min_eff
        t_min_seq, t_max_seq = t_max_seq, t_min_seq

    # Case 1: normal case, song inside feasible band
    if t_min_eff - 1e-6 <= t_song <= t_max_eff + 1e-6:
        print("[PLAN] t_song within [t_min, t_max]; calling findBestPath(t_song).")
        seq = find_best_path_for_duration(t_song, speed_factor=speed_factor)
        if seq is not None:
            return seq

        # If something goes wrong, fall back to nearest feasible edge.
        if abs(t_song - t_min_eff) <= abs(t_song - t_max_eff):
            print("[PLAN] findBestPath failed; falling back to t_min_feasible.")
            return t_min_seq
        else:
            print("[PLAN] findBestPath failed; falling back to t_max_feasible.")
            return t_max_seq

    # Case 2: song longer than t_max_feasible
    if t_song > t_max_eff + 1e-6:
        print("[PLAN] t_song > t_max_feasible; using t_max_feasible choreography.")
        return t_max_seq

    # Case 3: song shorter than t_min_feasible
    print("[PLAN] t_song < t_min_feasible; using t_min_feasible choreography.")
    return t_min_seq


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Plan NAO choreography and export sequence.txt "
                    "for Choregraphe playback (Option B, song-aware)."
    )
    parser.add_argument(
        "robot_ip",
        help="(Unused in Option B) NAO robot IP address (e.g. 192.168.1.106)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9559,
        help="(Unused in Option B) NAOqi port (default: 9559)"
    )
    parser.add_argument(
        "--motions-dir",
        default="./motions",
        help="Directory containing motion scripts <file_id>.py "
             "(default: ./motions)"
    )
    # kept for compatibility; not used in Option B
    parser.add_argument(
        "--python2-bin",
        default="python2",
        help="(Unused in Option B) Python 2 executable to run motion scripts "
             "in Option A"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Unused in Option B; included for compatibility."
    )
    parser.add_argument(
        "--music",
        default=None,
        help="Optional path to an MP3 file. If provided, the song length "
             "will drive the choreography duration selection."
    )
    parser.add_argument(
        "--speed-factor",
        type=float,
        default=1.0,
        help="Global speed multiplier for motions in planning (1.0 = baseline)."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    speed_factor = float(args.speed_factor)

    motions_dir = os.path.abspath(args.motions_dir)
    print("[INFO] Motions directory: {}".format(motions_dir))
    print("[INFO] Robot (ignored in Option B): {}:{}".format(args.robot_ip, args.port))
    print("[INFO] Using speed_factor = {:.2f}".format(speed_factor))

    if not os.path.isdir(motions_dir):
        print("[ERROR] Motions directory does not exist: {}".format(motions_dir))
        sys.exit(1)

    # 0) Compute t_min_feasible: shortest total duration we can produce.
    print("[INFO] Planning t_min_feasible choreography (baseline, min mode)...")
    t_min_seq = plan_full_choreography(
        song_length_seconds=None,
        speed_factor=speed_factor,
    )
    if t_min_seq is None:
        print("[ERROR] Baseline planning failed; aborting.")
        sys.exit(1)
    print("[INFO] t_min_feasible planning success. Raw duration: {:.2f}s, "
          "effective ≈ {:.2f}s".format(
              total_duration(t_min_seq),
              total_duration(t_min_seq) / speed_factor)
    )

    # 1) Compute t_max_feasible: longest total duration under MAX_TIME_LIMIT (max mode).
    print("[INFO] Planning t_max_feasible choreography (cap = {:.2f}s, max mode)...".format(
        MAX_TIME_LIMIT)
    )
    t_max_seq = plan_full_choreography_maximal(
        song_length_seconds=MAX_TIME_LIMIT,
        speed_factor=speed_factor,
    )
    if t_max_seq is None:
        print("[WARN] No separate t_max_feasible found; "
              "using t_min_feasible for both min and max.")
        t_max_seq = t_min_seq

    # 2) Read song length, if provided
    t_song = get_song_length_seconds(args.music)

    # 3) Apply your policy (all in effective seconds)
    sequence = choose_sequence_for_song(t_min_seq, t_max_seq, t_song, speed_factor)

    # 4) Show the chosen sequence
    print("\n[SEQUENCE]")
    for i, p in enumerate(sequence):
        # Here we keep showing the raw per-pose duration from pose_definitions,
        # since it's just informational; the total is reported in effective seconds.
        print("  {idx:02d}. {fid:25s}  {label:15s}  {dur:5.2f}s".format(
            idx=i, fid=p.file_id, label=p.label, dur=p.duration
        ))
    print("")
    total_raw = total_duration(sequence)
    total_eff = total_raw / speed_factor
    print("[INFO] Final choreography duration (raw):      {:.2f} s".format(total_raw))
    print("[INFO] Final choreography duration (effective): {:.2f} s (speed_factor = {:.2f})".format(
        total_eff, speed_factor)
    )

    # 5) Export to sequence.txt for Choregraphe Option B
    export_sequence_to_file(sequence, args.speed_factor, path="sequence.txt")
    print("[INFO] Skipping local execution; use sequence.txt in Choregraphe.")
    return


if __name__ == "__main__":
    main()
