import numpy as np
from backend.utils.signal_processing import bandpass_filter, extract_enf_stft_qifft
from backend.core.rolling_shutter import RollingShutterModel

class ENFExtractor:
    def __init__(self, nominal_freq=50.0):
        self.nominal_freq = nominal_freq
        
    def extract_from_audio(self, audio_signal, fs):
        """
        Extracts ENF signal from audio data.
        """
        if audio_signal is None or len(audio_signal) == 0:
            return None, None
            
        # Bandpass filter around nominal frequency
        # For 50Hz, filter 49.0 - 51.0 Hz. For 60Hz, filter 59.0 - 61.0 Hz.
        lowcut = self.nominal_freq - 1.0
        highcut = self.nominal_freq + 1.0
        
        filtered_signal = bandpass_filter(audio_signal, lowcut, highcut, fs)
        
        # Extract ENF using STFT + QIFFT
        times, enf_values = extract_enf_stft_qifft(
            filtered_signal, 
            fs, 
            nominal_freq=self.nominal_freq, 
            window_size_sec=16, 
            step_size_sec=1
        )
        
        return times, enf_values

    def extract_from_video(self, row_signal, fps, height):
        """
        Extracts ENF signal from video row-wise luminance.
        Uses rolling shutter physics to reconstruct a uniform high-rate signal.
        Note: Lighting flickers at 2x the power grid frequency (100Hz or 120Hz).
        """
        if row_signal is None or len(row_signal) == 0:
            return None, None
            
        # Reconstruct uniform signal from rolling shutter row measurements
        rs_model = RollingShutterModel(frame_rate=fps, height=height)
        uniform_times, uniform_signal, fs_uniform = rs_model.reconstruct_uniform_signal(row_signal)
        
        if len(uniform_signal) == 0:
            return None, None
            
        # Video flicker frequency is 2x nominal grid frequency
        nominal_flicker_freq = 2 * self.nominal_freq
        
        # Bandpass filter around flicker frequency
        lowcut = nominal_flicker_freq - 2.0
        highcut = nominal_flicker_freq + 2.0
        
        filtered_signal = bandpass_filter(uniform_signal, lowcut, highcut, fs_uniform)
        
        # Extract flicker frequency profile
        times, flicker_values = extract_enf_stft_qifft(
            filtered_signal, 
            fs_uniform, 
            nominal_freq=nominal_flicker_freq, 
            window_size_sec=16, 
            step_size_sec=1
        )
        
        # Map flicker frequency back to grid ENF (divide by 2)
        enf_values = [f / 2.0 for f in flicker_values]
        
        return times, enf_values
