import os
import cv2
import numpy as np
from backend.config import UPLOADS_DIR

def generate_enf_test_video(output_filename, ref_frequencies, duration_sec=120, fps=30, height=480, width=640, tampered=False, nominal_freq=50.0):
    """
    Generates a synthetic MP4 video with embedded rolling shutter luminance fluctuations
    corresponding to the given reference ENF frequency profile.
    If tampered is True, it introduces a 5-second deletion in the middle.
    """
    output_path = UPLOADS_DIR / output_filename
    
    # VideoWriter settings
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height), isColor=False)
    
    # Calculate timing parameters
    t_frame = 1.0 / fps
    t_ro = (0.90 * t_frame) / height  # Active readout covers 90% of frame time
    
    num_frames = int(duration_sec * fps)
    
    # If tampered, we will delete 5 seconds of the ENF trace in the middle (e.g. at 60 seconds)
    tamper_frame_start = int(duration_sec * 0.5 * fps)
    tamper_frames_to_skip = int(5.0 * fps)
    
    # Flicker nominal frequency is 2x nominal grid frequency
    flicker_freq = 2 * nominal_freq
    
    # Interpolate ENF profile to get values at every second
    # ref_frequencies has a length of e.g. 14400 (4 hours)
    # We will pick a segment of ref_frequencies for the duration
    start_offset = 1000  # Offset to not start at zero
    
    # Pre-calculate row times
    row_indices = np.arange(height)
    row_offsets = row_indices * t_ro
    
    print(f"Generating test video: {output_filename} ({duration_sec}s, {'Tampered' if tampered else 'Untampered'})")
    
    frame_idx = 0
    actual_frame_count = 0
    
    while actual_frame_count < num_frames:
        # Determine ENF time index
        enf_time_idx = start_offset + int(actual_frame_count / fps)
        
        # If tampered and we reach the tampering zone, we skip ahead in the ENF profile
        # to simulate frame deletion (discontinuity)
        if tampered and actual_frame_count >= tamper_frame_start:
            enf_time_idx += int(5.0)  # skip 5 seconds in frequency profile
            
        if enf_time_idx >= len(ref_frequencies):
            enf_time_idx = len(ref_frequencies) - 1
            
        current_enf_hz = ref_frequencies[enf_time_idx]
        current_flicker_hz = current_enf_hz * 2.0
        
        # Base frame time
        t_base = actual_frame_count * t_frame
        
        # Calculate luminance for each row
        # I(r) = I_base * (1 + m * cos(2 * pi * f_flicker * (t_base + r * t_ro)))
        t_rows = t_base + row_offsets
        phase_rows = 2.0 * np.pi * current_flicker_hz * t_rows
        
        # Modulation depth of 3% (0.03) makes it subtle but extractable
        m = 0.03
        row_luminance = 128.0 * (1.0 + m * np.sin(phase_rows))
        
        # Create 2D gray image
        frame = np.tile(row_luminance[:, np.newaxis], (1, width)).astype(np.uint8)
        
        # Write frame
        out.write(frame)
        
        actual_frame_count += 1
        
    out.release()
    print(f"Completed writing test video: {output_path}")
    return output_path
