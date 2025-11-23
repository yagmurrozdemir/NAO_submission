from planner import plan_full_choreography
from pose_definitions import total_duration

def main():
    seq = plan_full_choreography()
    if seq is None:
        print("Planning failed.")
        return

    print("PLANNING SUCCESS.")
    print(f"Total poses: {len(seq)}")
    print(f"Total duration: {total_duration(seq):.2f}s")

    print("\n=== PYTHON LIST FOR CHOREGRAPHE ===")
    print("[")
    for p in seq:
        print('    "{}",  # {} ({:.2f}s)'.format(p.file_id, p.label, p.duration))
    print("]")

if __name__ == "__main__":
    main()
