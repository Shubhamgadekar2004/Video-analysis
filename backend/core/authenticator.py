import numpy as np

class ENFAuthenticator:
    def __init__(self, threshold=0.75):
        self.threshold = threshold

    def compute_correlation(self, signal, reference):
        """
        Compute Pearson correlation coefficient between signal and reference.
        Both arrays must be the same length.
        """
        if len(signal) != len(reference) or len(signal) == 0:
            return 0.0
            
        s_mean = np.mean(signal)
        r_mean = np.mean(reference)
        
        s_std = np.std(signal)
        r_std = np.std(reference)
        
        if s_std == 0 or r_std == 0:
            return 0.0
            
        cov = np.mean((signal - s_mean) * (reference - r_mean))
        return cov / (s_std * r_std)

    def find_best_match(self, extracted_enf, ref_timestamps, ref_frequencies):
        """
        Slides the extracted ENF along the longer reference ENF to find the best matching alignment.
        """
        N = len(extracted_enf)
        M = len(ref_frequencies)
        
        if N > M or N == 0 or M == 0:
            return {
                "matched": False,
                "max_correlation": 0.0,
                "best_shift": -1,
                "best_time": None,
                "correlation_profile": []
            }
            
        extracted_enf = np.array(extracted_enf)
        ref_frequencies = np.array(ref_frequencies)
        
        correlations = []
        best_corr = -2.0
        best_shift = 0
        
        # Slide window
        for shift in range(M - N + 1):
            ref_window = ref_frequencies[shift : shift + N]
            corr = self.compute_correlation(extracted_enf, ref_window)
            correlations.append(float(corr))
            
            if corr > best_corr:
                best_corr = corr
                best_shift = shift
                
        matched = best_corr >= self.threshold
        best_time = ref_timestamps[best_shift] if best_shift < len(ref_timestamps) else None
        
        # Get the overlapping segments
        matched_ref_freqs = ref_frequencies[best_shift : best_shift + N].tolist()
        matched_ref_times = ref_timestamps[best_shift : best_shift + N]
        
        # Calculate offset in Hz between the two signals to align them visually
        avg_offset = np.mean(extracted_enf - matched_ref_freqs)
        
        return {
            "matched": bool(matched),
            "max_correlation": float(best_corr),
            "best_shift": int(best_shift),
            "best_time": best_time,
            "correlation_profile": correlations,
            "matched_ref_freqs": matched_ref_freqs,
            "matched_ref_times": matched_ref_times,
            "offset_hz": float(avg_offset)
        }
