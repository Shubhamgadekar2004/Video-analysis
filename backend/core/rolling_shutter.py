import numpy as np
from scipy.interpolate import interp1d

class RollingShutterModel:
    def __init__(self, frame_rate=30.0, height=1080, t_ro_sec=None):
        """
        frame_rate: Video frames per second (fps)
        height: Number of rows in each frame
        t_ro_sec: Row readout time. If None, it will be estimated.
        """
        self.fps = frame_rate
        self.height = height
        self.t_frame = 1.0 / self.fps if self.fps > 0 else 0.033
        
        # If row readout time is not specified, assume active readout occupies 90% of frame time
        if t_ro_sec is None:
            self.t_ro = (0.90 * self.t_frame) / self.height
        else:
            self.t_ro = t_ro_sec
            
        self.t_active = self.height * self.t_ro
        self.t_idle = self.t_frame - self.t_active
        
        # Effective row sampling rate
        self.fs_row = 1.0 / self.t_ro

    def reconstruct_uniform_signal(self, row_signal):
        """
        Reconstructs a uniform timeline from the raw row signal.
        The idle periods between frames create gaps where no measurements are taken.
        We interpolate these gaps to get a uniform high-rate signal.
        """
        num_frames = len(row_signal) // self.height
        if num_frames == 0:
            return np.array([])
            
        # Create timestamps for all actual samples
        actual_times = []
        for f in range(num_frames):
            frame_start = f * self.t_frame
            for r in range(self.height):
                actual_times.append(frame_start + r * self.t_ro)
                
        actual_times = np.array(actual_times)
        actual_values = row_signal[:len(actual_times)]
        
        # Define a uniform high-rate grid with fs = self.fs_row
        t_start = actual_times[0]
        t_end = actual_times[-1]
        
        # We target a lower resampled frequency (e.g. 1000 Hz) to avoid enormous arrays
        fs_target = 1000.0
        uniform_times = np.arange(t_start, t_end, 1.0 / fs_target)
        
        # Use linear interpolation to fill in gaps during idle periods
        interp_func = interp1d(actual_times, actual_values, kind='linear', fill_value="extrapolate")
        uniform_values = interp_func(uniform_times)
        
        return uniform_times, uniform_values, fs_target
