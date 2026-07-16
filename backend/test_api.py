import requests
import time
import sys

def run_integration_test():
    url_base = "http://localhost:8085"
    print(f"Connecting to server at {url_base}...")
    
    # 1. Generate demo video
    print("Step 1: Generating tampered demo video (30s, 50Hz, Europe)...")
    try:
        res = requests.post(f"{url_base}/api/demo/generate", json={
            "duration": 10,
            "nominal_freq": 50.0,
            "tampered": True,
            "grid_region": "EUROPE"
        })
        res.raise_for_status()
        demo_data = res.json()
        file_id = demo_data["file_id"]
        print(f"Generated file successfully. File ID: {file_id}")
    except Exception as e:
        print(f"Failed to generate demo video: {e}")
        return False
        
    # 2. Trigger analysis
    print("Step 2: Triggering ENF analysis pipeline...")
    try:
        res = requests.post(f"{url_base}/api/analyze", json={
            "file_id": file_id,
            "nominal_freq": 50.0,
            "enf_source": "video"
        })
        res.raise_for_status()
        print("Analysis successfully scheduled.")
    except Exception as e:
        print(f"Failed to trigger analysis: {e}")
        return False
        
    # 3. Poll status
    print("Step 3: Polling analysis status...")
    status = "pending"
    elapsed = 0
    while status in ["pending", "processing"] and elapsed < 60:
        time.sleep(2)
        elapsed += 2
        try:
            res = requests.get(f"{url_base}/api/analysis/{file_id}")
            res.raise_for_status()
            analysis_data = res.json()
            status = analysis_data["status"]
            print(f"Elapsed: {elapsed}s | Status: {status}")
        except Exception as e:
            print(f"Failed to fetch status: {e}")
            return False
            
    if status == "completed":
        print("\n=== Integration Test Passed ===")
        print(f"Filename: {analysis_data['filename']}")
        print(f"Status: {analysis_data['status']}")
        
        results = analysis_data["results"]
        auth_report = results["auth_report"]
        tampering_report = results["tampering_report"]
        
        print(f"Nominal frequency: {analysis_data['nominal_freq']} Hz")
        print(f"Authentication status: {'MATCHED' if auth_report['matched'] else 'UNMATCHED'}")
        print(f"Max correlation: {auth_report['max_correlation']:.4f}")
        print(f"Estimated time: {auth_report['best_time']}")
        print(f"Tampering risk score: {tampering_report['risk_score']*100:.1f}%")
        print(f"Number of frequency jumps: {len(tampering_report['discontinuities'])}")
        
        # Verify reports and plots exist
        report_pdf = f"reports/ENF_Forensic_Report_{file_id}.pdf"
        comparison_plot = f"reports/plots/{file_id}_comparison.png"
        
        print(f"PDF Report path: {analysis_data['has_report']}")
        return True
    else:
        print(f"\n=== Integration Test Failed: status is {status} ===")
        if "error_message" in analysis_data:
            print(f"Error: {analysis_data['error_message']}")
        return False

if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)
