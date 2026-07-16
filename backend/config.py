import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"
DB_DIR = BASE_DIR / "db"

# Create directories if they don't exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{DB_DIR}/enf_analyzer.db"

# ENF Constants
NOMINAL_50 = 50.0
NOMINAL_60 = 60.0

# Signal Processing Settings
FS_AUDIO_RESAMPLE = 1000  # Resample audio to 1000Hz (ENF is near 50/60Hz, so 1000Hz is plenty)
FS_VIDEO_ROW_EFFECTIVE = 15000  # Effective row sampling rate for rolling shutter (~15kHz)

# Bandpass filters
BANDPASS_50 = (49.9, 50.1)
BANDPASS_60 = (59.9, 60.1)

# STFT Settings
STFT_WINDOW_SIZE_SEC = 16  # Window size in seconds
STFT_STEP_SIZE_SEC = 1    # Step size in seconds (overlap is window_size - step_size)
