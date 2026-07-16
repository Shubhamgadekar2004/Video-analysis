import os
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

def generate_enf_comparison_plot(times, extracted_enf, matched_ref_times, matched_ref_freqs, offset, output_path):
    """
    Saves a plot comparing the extracted ENF with the aligned reference ENF.
    """
    plt.figure(figsize=(10, 4.5))
    
    # Adjust extracted ENF to overlay on reference if needed for visualization, 
    # or show them together in separate subplots, or just overlay them.
    # Typically overlaying is great.
    
    # Apply offset correction to extracted to overlay nicely, or plot raw.
    # Overlay is best.
    plt.plot(times, np.array(extracted_enf) - offset, label='Extracted ENF (Aligned)', color='#10b981', linewidth=2)
    plt.plot(times, matched_ref_freqs, label='Reference ENF', color='#3b82f6', linestyle='--', linewidth=2)
    
    plt.title('ENF Comparison Profile')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Frequency (Hz)')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=150)
    plt.close()

def generate_spectrogram_plot(signal, fs, nominal_freq, output_path):
    """
    Generates and saves a high-res spectrogram around the nominal frequency.
    """
    plt.figure(figsize=(10, 4))
    
    # Compute spectrogram
    NFFT = min(4096, len(signal))
    if NFFT < 2:
        # Avoid crashing on extremely short signal
        return
        
    noverlap = max(0, NFFT - 128)
    if noverlap >= NFFT:
        noverlap = NFFT // 2
        
    plt.specgram(signal, NFFT=NFFT, Fs=fs, noverlap=noverlap, cmap='viridis')
    
    # Limit to nominal frequency band +/- 1.5 Hz
    plt.ylim(nominal_freq - 1.5, nominal_freq + 1.5)
    
    plt.title(f'Signal Spectrogram around {nominal_freq} Hz')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Frequency (Hz)')
    plt.colorbar(label='Intensity (dB)')
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=150)
    plt.close()

def generate_correlation_plot(correlations, output_path):
    """
    Saves a plot showing the correlation profile across sliding window shifts.
    """
    plt.figure(figsize=(10, 3.5))
    plt.plot(correlations, color='#ef4444', linewidth=1.5)
    plt.title('Sliding-Window Cross-Correlation Profile')
    plt.xlabel('Shift (seconds)')
    plt.ylabel('Pearson Correlation Coefficient')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=150)
    plt.close()
