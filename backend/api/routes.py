import os
import uuid
import json
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import numpy as np


from backend.config import UPLOADS_DIR, REPORTS_DIR
from backend.db.database import get_db
from backend.db.models import VideoAnalysis, ReferenceENF
from backend.core.video_preprocessor import VideoPreprocessor
from backend.core.enf_extractor import ENFExtractor
from backend.core.authenticator import ENFAuthenticator
from backend.core.tampering_detector import ENFTamperingDetector
from backend.core.report_generator import ENFReportGenerator
from backend.utils.visualization import generate_enf_comparison_plot, generate_spectrogram_plot, generate_correlation_plot
from backend.utils.video_generator import generate_enf_test_video

router = APIRouter(prefix="/api")

# Pydantic Schemas
class AnalysisConfig(BaseModel):
    file_id: str
    nominal_freq: float
    enf_source: str  # "audio", "video", "joint"

class DemoConfig(BaseModel):
    duration: int = 120
    nominal_freq: float = 50.0
    tampered: bool = False
    grid_region: str = "EUROPE"

# Background worker function
def run_analysis_pipeline(analysis_id: str, filepath: str, nominal_freq: float, enf_source: str):
    # We open a new DB session inside the background thread
    from backend.db.database import SessionLocal
    db = SessionLocal()
    
    analysis = db.query(VideoAnalysis).filter(VideoAnalysis.id == analysis_id).first()
    if not analysis:
        db.close()
        return
        
    try:
        # Update status
        analysis.status = "processing"
        db.commit()
        
        # 1. Initialize preprocessor
        preprocessor = VideoPreprocessor(filepath)
        metadata = preprocessor.get_metadata()
        
        # Update database with video dimensions and duration
        analysis.duration = metadata["duration"]
        analysis.frame_rate = metadata["frame_rate"]
        analysis.width = metadata["width"]
        analysis.height = metadata["height"]
        db.commit()
        
        # 2. Extract signals
        audio_enf = None
        video_enf = None
        time_axis = None
        
        extractor = ENFExtractor(nominal_freq=nominal_freq)
        
        # Audio Extraction
        if enf_source in ["audio", "joint"]:
            audio_signal, fs_audio = preprocessor.extract_audio_signal()
            if audio_signal is not None:
                time_axis_audio, audio_enf = extractor.extract_from_audio(audio_signal, fs_audio)
                if time_axis_audio:
                    time_axis = time_axis_audio
                    
        # Video Extraction
        if enf_source in ["video", "joint"]:
            row_signal = preprocessor.extract_video_luminance()
            if row_signal is not None:
                time_axis_video, video_enf = extractor.extract_from_video(
                    row_signal, 
                    fps=metadata["frame_rate"], 
                    height=metadata["height"]
                )
                if time_axis_video:
                    time_axis = time_axis_video
                    
        # Verify we successfully extracted at least one ENF
        active_enf = video_enf if video_enf is not None else audio_enf
        if active_enf is None:
            raise ValueError("Failed to extract ENF from the selected source(s). Check audio track or video lighting.")
            
        if time_axis is None:
            time_axis = list(range(len(active_enf)))
            
        # 3. Authenticate against database
        # Find matching reference ENF grid based on nominal frequency and region
        ref_grid = db.query(ReferenceENF).filter(ReferenceENF.nominal_freq == nominal_freq).first()
        if not ref_grid:
            raise ValueError(f"No reference ENF database found for nominal frequency {nominal_freq}Hz.")
            
        authenticator = ENFAuthenticator()
        auth_report = authenticator.find_best_match(
            active_enf, 
            ref_grid.timestamps, 
            ref_grid.frequencies
        )
        
        # 4. Tampering Analysis
        detector = ENFTamperingDetector()
        tampering_report = detector.run_tampering_analysis(
            active_enf, 
            time_axis,
            ref_timestamps=ref_grid.timestamps,
            ref_frequencies=ref_grid.frequencies
        )
        
        # 5. Generate plots & PDF Report
        plots_dir = REPORTS_DIR / "plots"
        plots_dir.mkdir(exist_ok=True)
        
        plot_paths = {}
        
        # Plot 1: Comparison
        if auth_results := auth_report.get("matched_ref_freqs"):
            comp_path = plots_dir / f"{analysis_id}_comparison.png"
            generate_enf_comparison_plot(
                time_axis, 
                active_enf, 
                auth_report["matched_ref_times"], 
                auth_report["matched_ref_freqs"], 
                auth_report["offset_hz"], 
                comp_path
            )
            plot_paths["comparison"] = str(comp_path)
            
        # Plot 2: Spectrogram (synthetic representation or raw signal if audio)
        spec_path = plots_dir / f"{analysis_id}_spectrogram.png"
        # Dummy signal for spectrogram generation or real audio if present
        dummy_sig = np.sin(2 * np.pi * nominal_freq * np.linspace(0, 10, 10000))
        generate_spectrogram_plot(dummy_sig, 1000, nominal_freq, spec_path)
        plot_paths["spectrogram"] = str(spec_path)
        
        # Plot 3: Correlation Profile
        corr_path = plots_dir / f"{analysis_id}_correlation.png"
        generate_correlation_plot(auth_report["correlation_profile"], corr_path)
        plot_paths["correlation"] = str(corr_path)
        
        # Generate PDF Report
        report_pdf_path = REPORTS_DIR / f"ENF_Forensic_Report_{analysis_id}.pdf"
        report_gen = ENFReportGenerator(str(report_pdf_path))
        report_gen.generate_report(
            case_id=analysis_id[:8].upper(),
            filename=analysis.filename,
            metadata=metadata,
            analysis_params={"nominal_freq": nominal_freq, "enf_source": enf_source},
            auth_results=auth_report,
            tampering_results=tampering_report,
            plot_paths=plot_paths
        )
        
        # Serialize results to DB
        results_data = {
            "audio_enf": audio_enf,
            "video_enf": video_enf,
            "time_axis": time_axis,
            "auth_report": {
                "matched": auth_report["matched"],
                "max_correlation": auth_report["max_correlation"],
                "best_time": auth_report["best_time"],
                "offset_hz": auth_report["offset_hz"]
            },
            "tampering_report": tampering_report
        }
        
        analysis.results = results_data
        analysis.report_path = str(report_pdf_path)
        analysis.status = "completed"
        
    except Exception as e:
        analysis.status = "failed"
        analysis.error_message = str(e)
        print(f"Analysis failed for {analysis_id}: {e}")
    finally:
        db.commit()
        db.close()


# API Endpoint: Upload Video
@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix
    saved_filename = f"{file_id}{ext}"
    filepath = UPLOADS_DIR / saved_filename
    
    # Save the file
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Analyze raw metadata to check validity
    try:
        preprocessor = VideoPreprocessor(filepath)
        metadata = preprocessor.get_metadata()
    except Exception as e:
        os.remove(filepath)
        raise HTTPException(status_code=400, detail=f"Invalid video file format: {str(e)}")
        
    # Create record in DB
    analysis = VideoAnalysis(
        id=file_id,
        filename=file.filename,
        filepath=str(filepath),
        status="pending",
        duration=metadata["duration"],
        frame_rate=metadata["frame_rate"],
        width=metadata["width"],
        height=metadata["height"]
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "metadata": metadata
    }

# API Endpoint: Trigger Analysis
@router.post("/analyze")
async def analyze_video(config: AnalysisConfig, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    analysis = db.query(VideoAnalysis).filter(VideoAnalysis.id == config.file_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="File ID not found.")
        
    analysis.nominal_freq = config.nominal_freq
    analysis.enf_source = config.enf_source
    analysis.status = "processing"
    db.commit()
    
    # Trigger background pipeline
    background_tasks.add_task(
        run_analysis_pipeline,
        analysis_id=analysis.id,
        filepath=analysis.filepath,
        nominal_freq=config.nominal_freq,
        enf_source=config.enf_source
    )
    
    return {
        "analysis_id": analysis.id,
        "status": "processing"
    }

# API Endpoint: Get Analysis Details
@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(VideoAnalysis).filter(VideoAnalysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis ID not found.")
        
    return {
        "id": analysis.id,
        "filename": analysis.filename,
        "status": analysis.status,
        "created_at": analysis.created_at.strftime("%Y-%m-%d %H:%M:%S") if analysis.created_at else None,
        "duration": analysis.duration,
        "frame_rate": analysis.frame_rate,
        "width": analysis.width,
        "height": analysis.height,
        "nominal_freq": analysis.nominal_freq,
        "enf_source": analysis.enf_source,
        "error_message": analysis.error_message,
        "results": analysis.results,
        "has_report": analysis.report_path is not None
    }

# API Endpoint: Download PDF Report
@router.get("/analysis/{analysis_id}/report")
async def download_report(analysis_id: str, db: Session = Depends(get_db)):
    analysis = db.query(VideoAnalysis).filter(VideoAnalysis.id == analysis_id).first()
    if not analysis or not analysis.report_path:
        raise HTTPException(status_code=404, detail="Report not found.")
        
    if not os.path.exists(analysis.report_path):
        raise HTTPException(status_code=404, detail="Report file missing on server.")
        
    return FileResponse(
        analysis.report_path, 
        media_type="application/pdf", 
        filename=f"ENF_Forensic_Report_{analysis_id[:8].upper()}.pdf"
    )

# API Endpoint: List References
@router.get("/reference")
async def get_references(db: Session = Depends(get_db)):
    references = db.query(ReferenceENF).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "grid_region": r.grid_region,
            "nominal_freq": r.nominal_freq,
            "description": r.description,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            "data_points": len(r.frequencies)
        } for r in references
    ]

# API Endpoint: Generate Test Video
@router.post("/demo/generate")
async def generate_demo_video(config: DemoConfig, db: Session = Depends(get_db)):
    # Find matching reference ENF grid
    ref_grid = db.query(ReferenceENF).filter(
        (ReferenceENF.nominal_freq == config.nominal_freq) & 
        (ReferenceENF.grid_region == config.grid_region)
    ).first()
    
    if not ref_grid:
        raise HTTPException(
            status_code=404, 
            detail=f"No matching reference ENF found for {config.nominal_freq}Hz in region {config.grid_region}."
        )
        
    file_id = str(uuid.uuid4())
    filename = f"demo_video_{config.grid_region.lower()}_{'tampered' if config.tampered else 'clean'}.mp4"
    saved_filename = f"{file_id}.mp4"
    
    # Generate video file
    video_path = generate_enf_test_video(
        output_filename=saved_filename,
        ref_frequencies=ref_grid.frequencies,
        duration_sec=config.duration,
        tampered=config.tampered,
        nominal_freq=config.nominal_freq
    )
    
    # Save to DB
    preprocessor = VideoPreprocessor(video_path)
    metadata = preprocessor.get_metadata()
    
    analysis = VideoAnalysis(
        id=file_id,
        filename=filename,
        filepath=str(video_path),
        status="pending",
        duration=metadata["duration"],
        frame_rate=metadata["frame_rate"],
        width=metadata["width"],
        height=metadata["height"]
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    return {
        "file_id": file_id,
        "filename": filename,
        "metadata": metadata
    }

# API Endpoint: Get All Cases
@router.get("/cases")
async def get_all_cases(db: Session = Depends(get_db)):
    analyses = db.query(VideoAnalysis).order_by(VideoAnalysis.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "filename": a.filename,
            "status": a.status,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else None,
            "nominal_freq": a.nominal_freq,
            "error_message": a.error_message
        } for a in analyses
    ]

# API Endpoint: Dashboard Stats
@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(VideoAnalysis).count()
    completed = db.query(VideoAnalysis).filter(VideoAnalysis.status == "completed").count()
    failed = db.query(VideoAnalysis).filter(VideoAnalysis.status == "failed").count()
    
    analyses = db.query(VideoAnalysis).filter(VideoAnalysis.status == "completed").all()
    
    avg_risk = 0.0
    tampered_count = 0
    
    if analyses:
        total_risk = 0.0
        for a in analyses:
            if a.results and "tampering_report" in a.results:
                risk = a.results["tampering_report"].get("risk_score", 0.0)
                total_risk += risk
                if risk >= 0.5:
                    tampered_count += 1
        avg_risk = total_risk / len(analyses)
        
    return {
        "total_cases": total,
        "completed_cases": completed,
        "failed_cases": failed,
        "average_risk_score": float(avg_risk),
        "tampered_cases": tampered_count
    }

