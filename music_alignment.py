from pose_definitions import total_duration

def compute_segment_times(song_duration, mandatory_sequence):
    n_segments = len(mandatory_sequence) - 1
    base_segment = song_duration / n_segments
    return [base_segment] * n_segments

def tune_segments(segment_times, tune_factor):
    return [t * tune_factor for t in segment_times]

def print_segment_plan(mandatory_sequence, segment_times):
    print("\n=== SEGMENT PLAN (S6) ===")
    print(f"Mandatory poses: {len(mandatory_sequence)}")
    print(f"Segments: {len(segment_times)}")
    for i, t in enumerate(segment_times):
        print(f"Segment {i}: {mandatory_sequence[i].label} → {mandatory_sequence[i+1].label}, {t:.3f} sec")
