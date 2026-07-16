import numpy as np
from backend.core.authenticator import ENFAuthenticator

class ENFTamperingDetector:
    def __init__(self, diff_threshold_hz=0.050):
        """
        diff_threshold_hz: Max expected frequency change in 1 second under normal grid conditions + estimation margin.
        """
        self.diff_threshold = diff_threshold_hz
        self.authenticator = ENFAuthenticator()

    def detect_discontinuities(self, enf_values, times, window_size=3):
        """
        Detects abrupt, persistent jumps in frequency using a bilateral median window.
        This filters out transient estimation noise/outliers.
        """
        # For extremely short clips, do not perform discontinuity analysis
        if len(enf_values) < 8:
            return []
            
        if len(enf_values) < 2 * window_size:
            # Fallback to simple diff for short signals
            window_size = max(1, len(enf_values) // 3)
            if window_size < 1:
                return []
                
        enf_values = np.array(enf_values)
        times = np.array(times)
        N = len(enf_values)
        
        # Calculate signal noise level using first differences
        diffs = np.abs(np.diff(enf_values))
        if len(diffs) > 0:
            noise_std = np.std(diffs)
            # The threshold is 3.5 times the noise std, with a minimum of 50 mHz and a max of 250 mHz
            adaptive_threshold = max(0.050, min(0.250, 3.5 * noise_std))
        else:
            adaptive_threshold = 0.050
            
        tampering_points = []
        for i in range(window_size, N - window_size):
            # Compute median frequency before and after the point
            left_window = enf_values[i - window_size : i]
            right_window = enf_values[i : i + window_size]
            
            left_med = np.median(left_window)
            right_med = np.median(right_window)
            
            diff = abs(left_med - right_med)
            
            # Verify there is a sharp transition at the boundary
            adj_jump = abs(enf_values[i] - enf_values[i - 1])
            
            if diff > adaptive_threshold and adj_jump > adaptive_threshold:
                tampering_points.append({
                    "time": float(times[i]),
                    "jump_hz": float(diff),
                    "index": i,
                    "type": "frequency_jump",
                    "severity": min(1.0, float(diff / (2 * adaptive_threshold)))
                })
                
        # Perform non-maximum suppression (NMS) to keep only the single peak jump for each event
        refined_points = []
        if tampering_points:
            tampering_points.sort(key=lambda x: x["time"])
            current_group = [tampering_points[0]]
            for p in tampering_points[1:]:
                if p["time"] - current_group[-1]["time"] <= window_size:
                    current_group.append(p)
                else:
                    best = max(current_group, key=lambda x: x["jump_hz"])
                    refined_points.append(best)
                    current_group = [p]
            if current_group:
                best = max(current_group, key=lambda x: x["jump_hz"])
                refined_points.append(best)
                
        return refined_points

    def detect_segment_splicing(self, extracted_enf, ref_timestamps, ref_frequencies, global_best_shift, segment_len_sec=30):
        """
        Verifies if local segments are consistent with the global match shift.
        If a segment's correlation at the expected global offset is low, it indicates splicing.
        """
        N = len(extracted_enf)
        if N < segment_len_sec * 2 or global_best_shift < 0:
            return {
                "spliced": False,
                "segments": []
            }
            
        num_segments = N // segment_len_sec
        segments = []
        spliced = False
        inconsistent_segments = []
        
        extracted_enf = np.array(extracted_enf)
        ref_frequencies = np.array(ref_frequencies)
        
        # We allow a search window (+/- 3 seconds) for local variations/jitter
        margin = 3 
        
        for i in range(num_segments):
            start_idx = i * segment_len_sec
            end_idx = start_idx + segment_len_sec
            seg_enf = extracted_enf[start_idx:end_idx]
            
            # Expected shift in reference
            exp_shift = global_best_shift + start_idx
            
            best_local_corr = -2.0
            best_local_shift = exp_shift
            
            for local_shift in range(max(0, exp_shift - margin), min(len(ref_frequencies) - len(seg_enf) + 1, exp_shift + margin + 1)):
                ref_window = ref_frequencies[local_shift : local_shift + len(seg_enf)]
                corr = self.authenticator.compute_correlation(seg_enf, ref_window)
                if corr > best_local_corr:
                    best_local_corr = corr
                    best_local_shift = local_shift
            
            # Since segments are short, we use 0.60 as consistency correlation threshold
            consistent = bool(best_local_corr >= 0.60)
            
            segments.append({
                "segment_idx": i,
                "start_time_sec": start_idx,
                "end_time_sec": end_idx,
                "matched": consistent,
                "correlation": float(best_local_corr),
                "best_ref_time": ref_timestamps[best_local_shift] if best_local_shift < len(ref_timestamps) else None,
                "best_shift": int(best_local_shift)
            })
            
            if not consistent:
                spliced = True
                inconsistent_segments.append(i)
                
        return {
            "spliced": spliced,
            "segments": segments,
            "inconsistent_segment_indices": inconsistent_segments
        }

    def run_tampering_analysis(self, extracted_enf, times, ref_timestamps=None, ref_frequencies=None):
        """
        Orchestrates both discontinuity detection and segment correlation consistency.
        """
        discontinuities = self.detect_discontinuities(extracted_enf, times)
        
        splicing_results = None
        if ref_timestamps is not None and ref_frequencies is not None:
            # Match globally first to establish the baseline timeline
            global_match = self.authenticator.find_best_match(extracted_enf, ref_timestamps, ref_frequencies)
            global_best_shift = global_match["best_shift"] if global_match["matched"] else -1
            
            splicing_results = self.detect_segment_splicing(
                extracted_enf, 
                ref_timestamps, 
                ref_frequencies,
                global_best_shift=global_best_shift
            )
            
        # Overall risk score calculation
        risk_score = 0.0
        if discontinuities:
            # Increase risk score by max severity of jump
            max_severity = max([d["severity"] for d in discontinuities])
            risk_score = max(risk_score, 0.4 + 0.6 * max_severity)
            
        if splicing_results and splicing_results["spliced"]:
            # Only flag splicing if we actually matched the file globally (splicing implies we have a valid baseline timeline)
            # If the file never matched globally, splicing_results['spliced'] will be False anyway (handled in detect_segment_splicing).
            risk_score = max(risk_score, 0.85)
            
        # If some segments match but others don't, it is highly suspicious of splicing.
        # If 100% of segments are unmatched, it's just a non-match (unverified), not necessarily tampered.
        if splicing_results:
            matched_segs = sum([1 for s in splicing_results["segments"] if s["matched"]])
            total_segs = len(splicing_results["segments"])
            if total_segs > 0:
                unmatched_ratio = (total_segs - matched_segs) / total_segs
                if 0.0 < unmatched_ratio < 1.0:
                    # Inconsistent matching across segments -> suspicious
                    risk_score = max(risk_score, 0.65 * unmatched_ratio)
                    
        return {
            "risk_score": float(risk_score),
            "discontinuities": discontinuities,
            "splicing_analysis": splicing_results
        }
