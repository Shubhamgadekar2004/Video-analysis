import requests
import time
import sys

def test_case(tampered):
    url_base = "http://localhost:8085"
    print(f"\n--- Testing Video: Tampered={tampered} ---")
    
    # 1. Generate video
    try:
        res = requests.post(f"{url_base}/api/demo/generate", json={
            "duration": 90,
            "nominal_freq": 50.0,
            "tampered": tampered,
            "grid_region": "EUROPE"
        })
        res.raise_for_status()
        file_id = res.json()["file_id"]
    except Exception as e:
        print(f"Failed to generate: {e}")
        return None
        
    # 2. Analyze
    try:
        requests.post(f"{url_base}/api/analyze", json={
            "file_id": file_id,
            "nominal_freq": 50.0,
            "enf_source": "video"
        }).raise_for_status()
    except Exception as e:
        print(f"Failed to analyze: {e}")
        return None
        
    # 3. Poll
    status = "pending"
    elapsed = 0
    while status in ["pending", "processing"] and elapsed < 90:
        time.sleep(2)
        elapsed += 2
        res = requests.get(f"{url_base}/api/analysis/{file_id}")
        status = res.json()["status"]
        
    if status == "completed":
        data = res.json()
        results = data["results"]
        risk = results["tampering_report"]["risk_score"]
        jumps = len(results["tampering_report"]["discontinuities"])
        print(f"Result for Tampered={tampered}: Status={status}, Risk={risk*100:.1f}%, Jumps={jumps}")
        return risk
    else:
        print(f"Failed status: {status}")
        return None

if __name__ == "__main__":
    print("Testing pipeline accuracy...")
    clean_risk = test_case(tampered=False)
    tampered_risk = test_case(tampered=True)
    
    print("\n=== Accuracy Report ===")
    print(f"Clean Video Risk: {clean_risk*100 if clean_risk is not None else 'N/A'}%")
    print(f"Tampered Video Risk: {tampered_risk*100 if tampered_risk is not None else 'N/A'}%")
    
    if clean_risk is not None and tampered_risk is not None:
        if clean_risk < 0.2 and tampered_risk > 0.5:
            print("SUCCESS: System is highly accurate! Clean is low-risk, Tampered is high-risk.")
            sys.exit(0)
        else:
            print("FAILURE: Risk scores are not distinctive.")
            sys.exit(1)
    else:
        sys.exit(1)
