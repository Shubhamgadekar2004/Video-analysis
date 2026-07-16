import numpy as np
from scipy.signal import butter, filtfilt, stft

def bandpass_filter(data, lowcut, highcut, fs, order=4):
    """
    Apply Butterworth bandpass filter to the signal.
    """
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    
    # Ensure frequencies are within Nyquist limits
    low = max(0.001, min(low, 0.999))
    high = max(low + 0.001, min(high, 0.999))
    
    b, a = butter(order, [low, high], btype='band')
    y = filtfilt(b, a, data)
    return y

def qifft_refinement(X, k):
    """
    Perform Quadratic Interpolation of FFT magnitude peaks (QIFFT).
    X: FFT magnitude spectrum (1D numpy array)
    k: Bin index of the local peak
    Returns: Refined fractional bin index (k + delta)
    """
    if k <= 0 or k >= len(X) - 1:
        return float(k)
        
    alpha = X[k - 1]
    beta = X[k]
    gamma = X[k + 1]
    
    # Avoid division by zero or negative denominator
    denom = alpha - 2 * beta + gamma
    if abs(denom) < 1e-10:
        return float(k)
        
    delta = 0.5 * (alpha - gamma) / denom
    return float(k + delta)

def extract_enf_stft_qifft(signal, fs, nominal_freq, window_size_sec=16, step_size_sec=1):
    """
    Extracts ENF using STFT with Quadratic Interpolation (QIFFT).
    Returns (time_axis, enf_signal)
    """
    # Parameters
    nperseg = int(window_size_sec * fs)
    
    # Ensure nperseg is not greater than signal length
    if len(signal) < nperseg:
        nperseg = len(signal)
        
    noverlap = int((window_size_sec - step_size_sec) * fs)
    
    # Ensure noverlap is strictly less than nperseg
    if noverlap >= nperseg:
        step_samples = int(step_size_sec * fs)
        noverlap = max(0, nperseg - step_samples)
        
    if noverlap >= nperseg:
        noverlap = max(0, nperseg - 1)
    
    # Use zero padding for finer frequency resolution
    n_fft = max(nperseg, 32768)  # Generous FFT size for resolution
    
    # Compute STFT
    frequencies, times, Zxx = stft(signal, fs=fs, window='hamming', 
                                   nperseg=nperseg, noverlap=noverlap, nfft=n_fft)
    
    # Compute magnitude
    magnitude = np.abs(Zxx)
    
    # Define frequency band around nominal frequency
    band_width = 1.0  # +/- 1 Hz range
    f_min = nominal_freq - band_width
    f_max = nominal_freq + band_width
    
    band_indices = np.where((frequencies >= f_min) & (frequencies <= f_max))[0]
    if len(band_indices) == 0:
        # Fallback to closest indices
        band_indices = np.array([np.argmin(np.abs(frequencies - nominal_freq))])
        
    sub_freqs = frequencies[band_indices]
    
    enf_signal = []
    
    for t_idx in range(len(times)):
        spec_slice = magnitude[band_indices, t_idx]
        
        if len(spec_slice) == 0:
            enf_signal.append(nominal_freq)
            continue
            
        peak_idx_in_slice = np.argmax(spec_slice)
        peak_idx_global = band_indices[peak_idx_in_slice]
        
        # Apply QIFFT refinement
        refined_bin = qifft_refinement(magnitude[:, t_idx], peak_idx_global)
        
        # Convert bin back to frequency
        refined_freq = refined_bin * (fs / n_fft)
        enf_signal.append(refined_freq)
        
    return times.tolist(), enf_signal

def extract_enf_goertzel(signal, fs, nominal_freq, window_size_sec=16, step_size_sec=1, num_bins=11):
    """
    Extracts ENF using a multi-bin Goertzel filter bank around the nominal frequency.
    """
    # Goertzel is good for testing individual frequencies. 
    # Let's create a range of frequencies around nominal freq.
    freq_grid = np.linspace(nominal_freq - 1.0, nominal_freq + 1.0, num_bins)
    
    window_samples = int(window_size_sec * fs)
    step_samples = int(step_size_sec * fs)
    
    num_steps = (len(signal) - window_samples) // step_samples + 1
    if num_steps <= 0:
        return [], []
        
    times = []
    enf_signal = []
    
    for step in range(num_steps):
        start = step * step_samples
        end = start + window_samples
        segment = signal[start:end]
        
        # Calculate Goertzel magnitude for each frequency on the grid
        magnitudes = []
        for f in freq_grid:
            k = 2 * np.cos(2 * np.pi * f / fs)
            s_prev1 = 0.0
            s_prev2 = 0.0
            for x in segment:
                s = x + k * s_prev1 - s_prev2
                s_prev2 = s_prev1
                s_prev1 = s
            mag = s_prev1**2 + s_prev2**2 - k * s_prev1 * s_prev2
            magnitudes.append(mag)
            
        # Fit quadratic curve near peak to get refined frequency
        peak_idx = np.argmax(magnitudes)
        if 0 < peak_idx < len(freq_grid) - 1:
            alpha = magnitudes[peak_idx - 1]
            beta = magnitudes[peak_idx]
            gamma = magnitudes[peak_idx + 1]
            denom = alpha - 2 * beta + gamma
            if abs(denom) > 1e-10:
                delta = 0.5 * (alpha - gamma) / denom
                refined_freq = freq_grid[peak_idx] + delta * (freq_grid[1] - freq_grid[0])
            else:
                refined_freq = freq_grid[peak_idx]
        else:
            refined_freq = freq_grid[peak_idx]
            
        times.append(start / fs + window_size_sec / 2.0)
        enf_signal.append(refined_freq)
        
    return times, enf_signal
