import numpy as np
import random

def generate_synthetic_enf(duration_sec, fs=1, nominal_freq=50.0, seed=None):
    """
    Generates a realistic ENF signal using a mean-reverting random walk (Ornstein-Uhlenbeck-like process).
    fs: Sampling rate of the ENF timeseries (typically 1 Hz)
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)
        
    num_samples = int(duration_sec * fs)
    enf = np.zeros(num_samples)
    enf[0] = nominal_freq + np.random.normal(0, 0.01)
    
    # Parameters for random walk
    # sigma: size of frequency perturbations
    # theta: strength of mean reversion (grid control)
    sigma = 0.002
    theta = 0.02
    
    for i in range(1, num_samples):
        # Ornstein-Uhlenbeck process step
        df = -theta * (enf[i-1] - nominal_freq) + np.random.normal(0, sigma)
        enf[i] = enf[i-1] + df
        
    # Add occasional slightly larger variations to simulate load changes
    num_events = int(duration_sec / 300)  # one event every 5 mins on average
    for _ in range(num_events):
        idx = random.randint(0, num_samples - 1)
        length = random.randint(10, 60)
        magnitude = random.choice([-0.015, 0.015])
        # Smoothly apply the shift
        for j in range(length):
            if idx + j < num_samples:
                enf[idx + j] += magnitude * np.sin(np.pi * j / length)
                
    times = np.arange(num_samples) / fs
    return times.tolist(), enf.tolist()

def embed_enf_in_signal(enf_times, enf_values, fs_signal, duration_sec, snr_db=-10, nominal_freq=50.0):
    """
    Synthesizes a time-domain signal (e.g. audio hum or video luminance) 
    that contains an ENF frequency profile.
    """
    num_samples = int(duration_sec * fs_signal)
    t = np.arange(num_samples) / fs_signal
    
    # Interpolate ENF values to the high-rate time grid
    enf_interp = np.interp(t, enf_times, enf_values)
    
    # Calculate cumulative phase: phase(t) = 2 * pi * integral(f(tau) dtau)
    phase = 2 * np.pi * np.cumsum(enf_interp) / fs_signal
    
    # Generate clean ENF component (include second harmonic too!)
    clean_signal = np.sin(phase) + 0.3 * np.sin(2 * phase)
    
    # Add noise
    signal_power = np.mean(clean_signal**2)
    snr_linear = 10**(snr_db / 10.0)
    noise_power = signal_power / snr_linear
    noise = np.random.normal(0, np.sqrt(noise_power), num_samples)
    
    dirty_signal = clean_signal + noise
    return t, dirty_signal
