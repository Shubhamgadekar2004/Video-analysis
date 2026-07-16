import os
import subprocess
import numpy as np
import cv2
from scipy.io import wavfile
from backend.config import UPLOADS_DIR, FS_AUDIO_RESAMPLE

class VideoPreprocessor:
    def __init__(self, filepath):
        self.filepath = str(filepath)
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Video file not found: {self.filepath}")
            
        # Get video metadata
        self.cap = cv2.VideoCapture(self.filepath)
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video file: {self.filepath}")
            
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.frame_count / self.fps if self.fps > 0 else 0
        self.cap.release()

    def get_metadata(self):
        return {
            "duration": self.duration,
            "frame_rate": self.fps,
            "width": self.width,
            "height": self.height,
            "frame_count": self.frame_count
        }

    def extract_audio_signal(self):
        """
        Extracts the audio track from the video file, downsamples to FS_AUDIO_RESAMPLE,
        and returns a 1D numpy array of the audio.
        """
        output_wav = self.filepath + ".wav"
        
        # Call FFmpeg to extract mono audio at 1000 Hz
        cmd = [
            "ffmpeg", "-y",
            "-i", self.filepath,
            "-vn",                  # Disable video
            "-ac", "1",             # Mono channel
            "-ar", str(FS_AUDIO_RESAMPLE), # Resample rate
            output_wav
        ]
        
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            fs, audio_data = wavfile.read(output_wav)
            
            # Clean up temporary WAV file
            if os.path.exists(output_wav):
                os.remove(output_wav)
                
            # Convert to float normalized between -1.0 and 1.0
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                audio_data = audio_data.astype(np.float32) / 2147483648.0
            elif audio_data.dtype == np.uint8:
                audio_data = (audio_data.astype(np.float32) - 128.0) / 128.0
                
            return audio_data, fs
        except Exception as e:
            if os.path.exists(output_wav):
                try:
                    os.remove(output_wav)
                except:
                    pass
            print(f"Error extracting audio: {e}")
            return None, None

    def extract_video_luminance(self, max_frames=1800):
        """
        Reads frames from the video, selects a static/low-motion region of interest,
        and extracts the row-by-row average luminance signal to capture rolling shutter light flicker.
        """
        cap = cv2.VideoCapture(self.filepath)
        if not cap.isOpened():
            return None
            
        frames_to_process = min(self.frame_count, max_frames)
        
        # Read a small subset of frames first to compute temporal variance for static ROI detection
        sample_size = min(100, frames_to_process)
        sample_frames = []
        
        for _ in range(sample_size):
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sample_frames.append(gray)
            
        if not sample_frames:
            cap.release()
            return None
            
        # Detect static region: compute standard deviation across sample frames
        sample_stack = np.stack(sample_frames, axis=0)
        std_map = np.std(sample_stack, axis=0)
        
        # Select columns with low motion (low standard deviation)
        # Average std_map vertically to get column-wise variation
        col_std = np.mean(std_map, axis=0)
        
        # Pick 20% of columns with the lowest standard deviation
        num_cols_to_pick = max(10, int(self.width * 0.2))
        best_cols = np.argsort(col_std)[:num_cols_to_pick]
        
        # Reset capture to start
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        # Raw row signal accumulator
        # Each row is a sample. For frame n, row r, the time index is n * height + r
        row_signal = []
        
        for _ in range(frames_to_process):
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Extract only the low-motion columns for row averages
            # This filters out moving subjects/objects
            filtered_gray = gray[:, best_cols]
            
            # Compute average intensity for each row
            row_averages = np.mean(filtered_gray, axis=1)
            row_signal.extend(row_averages)
            
        cap.release()
        
        if not row_signal:
            return None
            
        row_signal = np.array(row_signal, dtype=np.float32)
        
        # Remove structural image content by high-pass filtering (subtract moving average)
        # A window size of 50 samples is good to remove structural spatial profiles
        window_len = 51
        box = np.ones(window_len) / window_len
        moving_avg = np.convolve(row_signal, box, mode='same')
        detrended_signal = row_signal - moving_avg
        
        return detrended_signal
