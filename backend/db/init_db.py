import sys
import os
from datetime import datetime, timedelta
import json
import numpy as np

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.db.database import engine, Base, SessionLocal
from backend.db.models import ReferenceENF
from backend.utils.synthetic_enf import generate_synthetic_enf

def init_database():
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if we already have reference data
    if db.query(ReferenceENF).count() > 0:
        print("Database already contains reference ENF data.")
        db.close()
        return
        
    print("Generating reference ENF data...")
    
    # Generate 4 hours (14400 seconds) of 50 Hz grid ENF
    times_50, freqs_50 = generate_synthetic_enf(duration_sec=14400, nominal_freq=50.0, seed=42)
    start_time_50 = datetime.now() - timedelta(hours=4)
    timestamps_50 = [(start_time_50 + timedelta(seconds=t)).strftime("%Y-%m-%d %H:%M:%S") for t in times_50]
    
    ref_50 = ReferenceENF(
        name="Europe Central Grid (Mock)",
        grid_region="EUROPE",
        nominal_freq=50.0,
        description="Europe grid 50Hz ENF mock reference database",
        timestamps=timestamps_50,
        frequencies=freqs_50
    )
    
    # Generate 4 hours (14400 seconds) of 60 Hz grid ENF
    times_60, freqs_60 = generate_synthetic_enf(duration_sec=14400, nominal_freq=60.0, seed=43)
    start_time_60 = datetime.now() - timedelta(hours=4)
    timestamps_60 = [(start_time_60 + timedelta(seconds=t)).strftime("%Y-%m-%d %H:%M:%S") for t in times_60]
    
    ref_60 = ReferenceENF(
        name="US Eastern Interconnection (Mock)",
        grid_region="US_EAST",
        nominal_freq=60.0,
        description="US Eastern Interconnection 60Hz ENF mock reference database",
        timestamps=timestamps_60,
        frequencies=freqs_60
    )
    
    db.add(ref_50)
    db.add(ref_60)
    
    db.commit()
    print("Database successfully initialized and seeded!")
    db.close()

if __name__ == "__main__":
    init_database()
