// Frontend Application Logic - ENF Forensic Shield

document.addEventListener("DOMContentLoaded", () => {
    // Navigation routing
    const navItems = document.querySelectorAll(".nav-item");
    const views = document.querySelectorAll(".content-view");
    
    function navigateToView(viewId) {
        views.forEach(v => v.classList.remove("active-view"));
        navItems.forEach(n => n.classList.remove("active"));
        
        const targetView = document.getElementById(`view-${viewId}`);
        const targetNav = document.getElementById(`nav-${viewId}`);
        
        if (targetView) targetView.classList.add("active-view");
        if (targetNav) targetNav.classList.add("active");
        
        // Load data based on view
        if (viewId === "dashboard") {
            loadDashboard();
        } else if (viewId === "database") {
            loadDatabase();
        }
        
        // Update header title
        const pageTitle = document.getElementById("page-title");
        if (viewId === "dashboard") pageTitle.textContent = "Forensic Dashboard";
        else if (viewId === "analyze") pageTitle.textContent = "New Evidence Analysis";
        else if (viewId === "database") pageTitle.textContent = "Reference ENF Database";
        else if (viewId === "results") pageTitle.textContent = "Forensic Analysis Results";
    }
    
    // Setup Nav Clicks
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const viewId = item.getAttribute("href").substring(1);
            navigateToView(viewId);
        });
    });
    
    // Initial Load
    navigateToView("dashboard");
    
    // File Drag & Drop Setup
    const dropZone = document.getElementById("file-drop-zone");
    const fileInput = document.getElementById("video-file-input");
    const selectedFileDetails = document.getElementById("selected-file-details");
    const fileNameLabel = document.getElementById("file-name-label");
    const fileSizeLabel = document.getElementById("file-size-label");
    const removeFileBtn = document.getElementById("remove-file-btn");
    const startAnalysisBtn = document.getElementById("start-analysis-btn");
    
    let selectedFile = null;
    
    dropZone.addEventListener("click", () => fileInput.click());
    
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });
    
    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("dragover");
    });
    
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });
    
    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    removeFileBtn.addEventListener("click", () => {
        selectedFile = null;
        fileInput.value = "";
        selectedFileDetails.style.display = "none";
        dropZone.style.display = "flex";
        startAnalysisBtn.disabled = true;
    });
    
    function handleFileSelect(file) {
        selectedFile = file;
        fileNameLabel.textContent = file.name;
        
        // Format size
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        fileSizeLabel.textContent = `${sizeMB} MB`;
        
        dropZone.style.display = "none";
        selectedFileDetails.style.display = "flex";
        startAnalysisBtn.disabled = false;
    }
    
    // Form Submission & Analysis
    const analysisForm = document.getElementById("analysis-form");
    const processingContainer = document.getElementById("processing-container");
    const processingTitle = document.getElementById("processing-status-title");
    const processingDesc = document.getElementById("processing-status-desc");
    const progressBarFill = document.getElementById("progress-bar-fill");
    
    const stepUpload = document.getElementById("step-upload");
    const stepExtract = document.getElementById("step-extract");
    const stepAuth = document.getElementById("step-authenticate");
    const stepTampering = document.getElementById("step-tampering");
    
    analysisForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!selectedFile) return;
        
        // Show overlay
        processingContainer.style.display = "flex";
        resetProgressSteps();
        
        try {
            // Step 1: Upload File
            setStepState(stepUpload, "active");
            processingTitle.textContent = "Uploading Video File...";
            processingDesc.textContent = "Sending file to server for preprocessing.";
            progressBarFill.style.width = "15%";
            
            const uploadRes = await API.uploadFile(selectedFile);
            setStepState(stepUpload, "completed");
            
            // Step 2: Trigger analysis
            setStepState(stepExtract, "active");
            processingTitle.textContent = "Extracting ENF Signature...";
            processingDesc.textContent = "Processing audio track and CMOS rolling shutter flickering.";
            progressBarFill.style.width = "35%";
            
            const nominalFreq = document.getElementById("nominal-freq").value;
            const enfSource = document.getElementById("enf-source").value;
            
            const analyzeRes = await API.startAnalysis(uploadRes.file_id, nominalFreq, enfSource);
            
            // Start polling progress
            pollAnalysisProgress(analyzeRes.analysis_id);
            
        } catch (err) {
            processingContainer.style.display = "none";
            alert(err.message);
        }
    });
    
    // Polling Analysis Progress
    function pollAnalysisProgress(analysisId) {
        const interval = setInterval(async () => {
            try {
                const analysis = await API.getAnalysis(analysisId);
                
                if (analysis.status === "processing") {
                    // Update progress dynamically based on time/heuristics
                    progressBarFill.style.width = "50%";
                    setStepState(stepExtract, "completed");
                    setStepState(stepAuth, "active");
                    processingTitle.textContent = "Matching Grid database...";
                    processingDesc.textContent = "Comparing ENF frequency profile against reference DB.";
                } else if (analysis.status === "completed") {
                    clearInterval(interval);
                    
                    setStepState(stepAuth, "completed");
                    setStepState(stepTampering, "completed");
                    progressBarFill.style.width = "100%";
                    processingTitle.textContent = "Analysis Complete!";
                    processingDesc.textContent = "Redirecting to report viewer.";
                    
                    setTimeout(() => {
                        processingContainer.style.display = "none";
                        viewResults(analysisId);
                    }, 1000);
                } else if (analysis.status === "failed") {
                    clearInterval(interval);
                    processingContainer.style.display = "none";
                    alert(`Analysis failed: ${analysis.error_message}`);
                }
            } catch (err) {
                clearInterval(interval);
                processingContainer.style.display = "none";
                alert(`Error polling progress: ${err.message}`);
            }
        }, 1500);
    }
    
    function resetProgressSteps() {
        progressBarFill.style.width = "0%";
        [stepUpload, stepExtract, stepAuth, stepTampering].forEach(step => {
            step.className = "step";
            step.querySelector("i").className = "fa-solid fa-circle";
        });
    }
    
    function setStepState(stepElement, state) {
        stepElement.className = `step ${state}`;
        const icon = stepElement.querySelector("i");
        if (state === "completed") {
            icon.className = "fa-solid fa-check";
        } else if (state === "active") {
            icon.className = "fa-solid fa-circle-notch fa-spin";
        } else {
            icon.className = "fa-solid fa-circle";
        }
    }
    
    // Generate Demo Video Click
    const generateDemoBtn = document.getElementById("generate-demo-btn");
    generateDemoBtn.addEventListener("click", async () => {
        processingContainer.style.display = "flex";
        resetProgressSteps();
        
        try {
            setStepState(stepUpload, "active");
            processingTitle.textContent = "Synthesizing CMOS Rolling Shutter Video...";
            processingDesc.textContent = "Generating frame-by-frame light intensity hum.";
            progressBarFill.style.width = "25%";
            
            const region = document.getElementById("demo-region").value;
            const nominalFreq = region === "EUROPE" ? 50.0 : 60.0;
            const tampered = document.getElementById("demo-tampered").checked;
            
            const demoRes = await API.generateDemo(120, nominalFreq, tampered, region);
            setStepState(stepUpload, "completed");
            
            // Automatically launch analysis
            setStepState(stepExtract, "active");
            processingTitle.textContent = "Triggering Forensic Pipeline...";
            processingDesc.textContent = "Starting row-level pixel extraction.";
            progressBarFill.style.width = "50%";
            
            const analyzeRes = await API.startAnalysis(demoRes.file_id, nominalFreq, "video");
            pollAnalysisProgress(analyzeRes.analysis_id);
            
        } catch (err) {
            processingContainer.style.display = "none";
            alert(err.message);
        }
    });
    
    // Load Dashboard stats & cases list
    async function loadDashboard() {
        try {
            const stats = await API.getDashboardStats();
            document.getElementById("stat-total").textContent = stats.total_cases;
            document.getElementById("stat-tampered").textContent = stats.tampered_cases;
            
            // Calc average integrity
            const avgRisk = stats.average_risk_score;
            const integrityPercent = Math.max(0, Math.min(100, Math.round((1.0 - avgRisk) * 100)));
            document.getElementById("stat-integrity").textContent = `${integrityPercent}%`;
            
            const cases = await API.getRecentCases();
            const casesListBody = document.getElementById("recent-cases-list");
            casesListBody.innerHTML = "";
            
            if (cases.length === 0) {
                casesListBody.innerHTML = `<tr><td colspan="6" class="empty-state">No cases analyzed yet. Start a new analysis.</td></tr>`;
                return;
            }
            
            cases.forEach(c => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${c.id.substring(0, 8).toUpperCase()}</td>
                    <td>${c.filename}</td>
                    <td>${c.created_at || '-'}</td>
                    <td>${c.nominal_freq} Hz</td>
                    <td><span class="status-badge ${c.status}">${c.status}</span></td>
                    <td>
                        <button class="action-btn" onclick="viewResultsDirect('${c.id}')" ${c.status !== 'completed' ? 'disabled' : ''}>
                            <i class="fa-solid fa-eye"></i> View
                        </button>
                    </td>
                `;
                casesListBody.appendChild(tr);
            });
            
        } catch (err) {
            console.error("Error loading dashboard data:", err);
        }
    }
    
    // View Results page
    let enfChartInstance = null;
    
    async function viewResults(analysisId) {
        navigateToView("results");
        
        try {
            const res = await API.getAnalysis(analysisId);
            
            // 1. Fill Summary Box
            const authReport = res.results.auth_report;
            const tamperingReport = res.results.tampering_report;
            
            const badgeAuth = document.getElementById("badge-auth");
            const badgeAuthValue = document.getElementById("badge-auth-value");
            const badgeRisk = document.getElementById("badge-risk");
            const badgeRiskValue = document.getElementById("badge-risk-value");
            
            // Authentication badge styling
            if (authReport.matched) {
                badgeAuth.className = "result-badge authentic";
                badgeAuthValue.textContent = "AUTHENTIC";
            } else {
                badgeAuth.className = "result-badge tampered";
                badgeAuthValue.textContent = "UNMATCHED";
            }
            
            // Risk badge styling
            const riskPercent = Math.round(tamperingReport.risk_score * 100);
            badgeRiskValue.textContent = `${riskPercent}%`;
            if (tamperingReport.risk_score >= 0.5) {
                badgeRisk.className = "result-badge high";
            } else {
                badgeRisk.className = "result-badge low";
            }
            
            document.getElementById("res-matched-time").textContent = authReport.best_time || "N/A";
            document.getElementById("res-correlation").textContent = authReport.max_correlation.toFixed(4);
            document.getElementById("res-duration").textContent = `${res.duration.toFixed(2)} seconds`;
            document.getElementById("res-dimensions").textContent = `${res.width}x${res.height} @ ${res.frame_rate.toFixed(2)} fps`;
            
            // 2. Set PDF Download link
            document.getElementById("download-pdf-btn").href = `/api/analysis/${analysisId}/report`;
            
            // 3. Set Static Matplotlib Images
            const timestampSuffix = `?t=${new Date().getTime()}`;
            document.getElementById("spectrogram-image").src = `/reports/plots/${analysisId}_spectrogram.png${timestampSuffix}`;
            document.getElementById("correlation-image").src = `/reports/plots/${analysisId}_correlation.png${timestampSuffix}`;
            
            // 4. Render Interactive Chart.js comparing ENF
            renderInteractiveENFChart(res);
            
            // 5. Populate Tampering timeline
            const anomalyTimeline = document.getElementById("anomaly-timeline");
            const tamperingEmptyState = document.getElementById("tampering-empty-state");
            anomalyTimeline.innerHTML = "";
            
            const discons = tamperingReport.discontinuities;
            const splicing = tamperingReport.splicing_analysis;
            
            let hasAnomalies = false;
            
            if (discons && discons.length > 0) {
                hasAnomalies = true;
                discons.forEach(d => {
                    const card = document.createElement("div");
                    card.className = "anomaly-card";
                    card.innerHTML = `
                        <i class="fa-solid fa-scissors anomaly-icon"></i>
                        <div class="anomaly-info">
                            <span class="anomaly-title">Frequency Jump Discontinuity at ${d.time.toFixed(2)}s</span>
                            <span class="anomaly-desc">Frequency shifted abruptly by ${d.jump_hz.toFixed(4)} Hz. This exceeds natural grid variations and indicates frame deletion/edit.</span>
                        </div>
                    `;
                    anomalyTimeline.appendChild(card);
                });
            }
            
            if (splicing && splicing.spliced) {
                hasAnomalies = true;
                const card = document.createElement("div");
                card.className = "anomaly-card";
                card.innerHTML = `
                    <i class="fa-solid fa-triangle-exclamation anomaly-icon"></i>
                    <div class="anomaly-info">
                        <span class="anomaly-title">Splicing Alignment Inconsistency Detected</span>
                        <span class="anomaly-desc">Segment-wise cross correlation shows different portions of this recording align with non-contiguous time periods of the power grid database.</span>
                    </div>
                `;
                anomalyTimeline.appendChild(card);
            }
            
            if (hasAnomalies) {
                tamperingEmptyState.style.display = "none";
            } else {
                tamperingEmptyState.style.display = "block";
            }
            
        } catch (err) {
            alert(`Error loading results: ${err.message}`);
        }
    }
    
    function renderInteractiveENFChart(analysisResult) {
        const canvas = document.getElementById("enf-comparison-chart");
        if (!canvas) return;
        
        // Destroy existing chart to prevent canvas redraw bugs
        if (enfChartInstance) {
            enfChartInstance.destroy();
        }
        
        const resData = analysisResult.results;
        const timeAxis = resData.time_axis;
        const activeEnf = resData.video_enf || resData.audio_enf;
        
        // Get aligned reference ENF
        // To show alignment properly, we must align the timescales or offset
        // Since we slide matched segment, we can align the X index
        // The backend returns max_correlation, and we saved comparison plot on server.
        // We can show raw extracted ENF vs aligned reference ENF
        // Let's call API or fetch details. Wait! In routes.py, we only save the metadata. 
        // We don't save the full matched_ref_freqs in the results json (only in the report generation).
        // Wait, did we save it in results?
        // Let's check results: yes, we saved "results": { "audio_enf": ..., "video_enf": ..., "time_axis": ... }
        // Wait, but we didn't save the full `matched_ref_freqs` in `results_data` in routes.py!
        // Ah, in routes.py we saved:
        // results_data = { "audio_enf": ..., "video_enf": ..., "time_axis": ..., "auth_report": { "matched": ..., "max_correlation": ..., "best_time": ..., "offset_hz": ... }, "tampering_report": ... }
        // So we don't have the full reference timeseries array in the client to plot in Chart.js, only the static PNG comparison image!
        // That's totally fine: we can plot the Extracted ENF frequency profile alone interactively, 
        // showing the fluctuations, and display the dual comparison plot in the static Matplotlib image!
        // This is still super rich.
        
        const dataset = {
            labels: timeAxis.map(t => `${t.toFixed(1)}s`),
            datasets: [{
                label: 'Extracted ENF Profile (Hz)',
                data: activeEnf,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.05)',
                borderWidth: 2,
                tension: 0.1,
                pointRadius: 2,
                fill: true
            }]
        };
        
        enfChartInstance = new Chart(canvas, {
            type: 'line',
            data: dataset,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: '#94a3b8' }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#94a3b8', maxTicksLimit: 12 },
                        grid: { color: 'rgba(148, 163, 184, 0.05)' }
                    },
                    y: {
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(148, 163, 184, 0.05)' }
                    }
                }
            }
        });
    }
    
    // Back button in results
    const resultsBackBtn = document.getElementById("results-back-btn");
    resultsBackBtn.addEventListener("click", () => {
        navigateToView("dashboard");
    });
    
    // Load database details
    async function loadDatabase() {
        try {
            const refs = await API.getReferences();
            const dbListBody = document.getElementById("db-list-body");
            dbListBody.innerHTML = "";
            
            refs.forEach(r => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${r.id}</td>
                    <td>${r.name}</td>
                    <td><span class="status-badge completed">${r.grid_region}</span></td>
                    <td>${r.nominal_freq} Hz</td>
                    <td>${r.data_points}</td>
                `;
                dbListBody.appendChild(tr);
            });
        } catch (err) {
            console.error("Error loading reference databases:", err);
        }
    }
    
    // Bind global function for recent cases table rows
    window.viewResultsDirect = function(analysisId) {
        viewResults(analysisId);
    };
});
