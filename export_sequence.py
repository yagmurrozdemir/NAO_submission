# export_sequence.py
#
# Run the planner and export the final sequence of poses
# as a simple text file for Choregraphe.

from planner import plan_full_choreography
from pose_definitions import total_duration

OUTPUT_PATH = "sequence.txt"  # you can make this absolute if you prefer

def main():
    seq = plan_full_choreography()
    if seq is None:
        print("Planning failed.")
        return

    print("PLANNING SUCCESS.")
    print(f"Total poses: {len(seq)}")
    print(f"Total duration: {total_duration(seq):.2f}s")

    # Write only file_ids, one per line, for Choregraphe
    with open(OUTPUT_PATH, "w") as f:
        for p in seq:
            f.write(p.file_id + "\n")

    print(f"Exported {len(seq)} poses to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
