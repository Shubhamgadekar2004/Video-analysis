// API Helper wrapper for ENF Forensic Shield

const API_BASE = ""; // Relative paths since hosted on same server

const API = {
    async getDashboardStats() {
        const res = await fetch(`${API_BASE}/api/dashboard/stats`);
        if (!res.ok) throw new Error("Failed to load dashboard statistics.");
        return res.json();
    },
    
    async getRecentCases() {
        // We can write a custom endpoint or query cases. 
        // For simplicity, let's query all analysis cases by building a simple list on server, 
        // or just return from dashboard stats / mock database query.
        // Let's create an endpoint in routes if needed, or query from cases. 
        // Actually let's fetch list of analyses. 
        // Wait, did we create a list endpoint in routes.py?
        // Let's check routes.py. Ah, we have `/api/analysis/{analysis_id}`, `/api/dashboard/stats`.
        // Wait, did we write an endpoint to get the list of recent cases?
        // Let's check: we didn't explicitly write `/api/cases`!
        // Oh, let's look at the database. We can query all cases or build a quick endpoint.
        // Let's add `/api/cases` to routes.py or query it. Let's add it to routes.py as a small contiguous block!
        // But first let's finish api.js and assume it returns a list of recent analyses.
        const res = await fetch(`${API_BASE}/api/cases`);
        if (!res.ok) throw new Error("Failed to load cases.");
        return res.json();
    },
    
    async uploadFile(file, onProgress) {
        const formData = new FormData();
        formData.append("file", file);
        
        // Use standard Fetch (progress is not easily tracked with fetch, but we can do a simple upload)
        const res = await fetch(`${API_BASE}/api/upload`, {
            method: "POST",
            body: formData
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to upload file.");
        }
        return res.json();
    },
    
    async startAnalysis(fileId, nominalFreq, enfSource) {
        const res = await fetch(`${API_BASE}/api/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                file_id: fileId,
                nominal_freq: parseFloat(nominalFreq),
                enf_source: enfSource
            })
        });
        if (!res.ok) throw new Error("Failed to trigger analysis.");
        return res.json();
    },
    
    async getAnalysis(analysisId) {
        const res = await fetch(`${API_BASE}/api/analysis/${analysisId}`);
        if (!res.ok) throw new Error("Failed to load analysis details.");
        return res.json();
    },
    
    async getReferences() {
        const res = await fetch(`${API_BASE}/api/reference`);
        if (!res.ok) throw new Error("Failed to load references.");
        return res.json();
    },
    
    async generateDemo(duration, nominalFreq, tampered, gridRegion) {
        const res = await fetch(`${API_BASE}/api/demo/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                duration,
                nominal_freq: parseFloat(nominalFreq),
                tampered,
                grid_region: gridRegion
            })
        });
        if (!res.ok) throw new Error("Failed to generate demo video.");
        return res.json();
    }
};
