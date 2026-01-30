/**
 * API Client for OCR Backend
 * Handles all HTTP requests and WebSocket communication
 */

const API_BASE = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws';

// WebSocket connection
let ws = null;
let wsReconnectTimeout = null;

/**
 * Connect to WebSocket server
 */
function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('✓ WebSocket connected');
            clearTimeout(wsReconnectTimeout);
        };

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleWebSocketMessage(msg);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected, reconnecting in 2s...');
            wsReconnectTimeout = setTimeout(connectWebSocket, 2000);
        };
    } catch (e) {
        console.error('Failed to connect WebSocket:', e);
        wsReconnectTimeout = setTimeout(connectWebSocket, 2000);
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(msg) {
    const job = state.jobs.find(j => j.id === msg.job_id);
    if (!job) return;

    switch (msg.type) {
        case 'job_status':
            job.status = msg.status;
            if (msg.progress !== undefined) job.progress = msg.progress;
            render();
            if (state.modalJobId === job.id) renderModal();
            break;

        case 'job_progress':
            job.progress = msg.progress;
            job.status = 'OCR진행중';
            render();
            if (state.modalJobId === job.id) {
                $('#modalBar').style.width = job.progress + '%';
                $('#modalLabel').textContent = Math.round(job.progress) + '%';
            }
            break;

        case 'file_complete':
            job.perFileResults[msg.file_id] = msg.result;
            render();
            if (state.modalJobId === job.id) renderResultEditor();
            break;

        case 'page_complete':
            // Live update for individual PDF page completion
            if (!job.perFileResults[msg.file_id]) {
                job.perFileResults[msg.file_id] = { pages: {}, isPdf: true };
            }
            job.perFileResults[msg.file_id].pages[msg.page] = msg.result;
            render();
            if (state.modalJobId === job.id) {
                renderResultEditor();
            }
            break;

        case 'job_complete':
            job.status = '완료';
            job.progress = 100;
            state.activeJobId = null;
            toast('완료', `"${job.name}" OCR 완료`);
            render();
            if (state.modalJobId === job.id) renderModal();
            processQueue(); // Process next job
            break;

        case 'job_error':
            job.status = '실패';
            state.activeJobId = null;
            toast('오류', msg.error || '알 수 없는 오류');
            render();
            if (state.modalJobId === job.id) renderModal();
            processQueue(); // Process next job
            break;

        case 'ocr_chunk':
            handleOcrChunk(msg);
            break;
    }
}

// ====================
// API Functions
// ====================

/**
 * Create new job with file upload
 */
async function apiCreateJob(formData) {
    const res = await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        body: formData
    });

    if (!res.ok) {
        throw new Error(`Failed to create job: ${res.statusText}`);
    }

    return await res.json();
}

/**
 * Get all jobs
 */
async function apiGetJobs() {
    const res = await fetch(`${API_BASE}/jobs`);
    const data = await res.json();
    return data.jobs || [];
}

/**
 * Enqueue job for processing
 */
async function apiEnqueueJob(jobId) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/enqueue`, {
        method: 'POST'
    });

    if (!res.ok) {
        throw new Error(`Failed to enqueue job: ${res.statusText}`);
    }

    return await res.json();
}

/**
 * Update page selection for a PDF file
 */
async function apiUpdateFilePageSelection(jobId, fileId, pagesSel) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/files/${fileId}/pages`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pagesSel })
    });

    if (!res.ok) {
        throw new Error(`Failed to update page selection: ${res.statusText}`);
    }

    return await res.json();
}

/**
 * Add files to existing job
 */
async function apiAddFilesToJob(jobId, files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    const res = await fetch(`${API_BASE}/jobs/${jobId}/files/add`, {
        method: 'POST',
        body: formData
    });

    if (!res.ok) {
        throw new Error(`Failed to add files: ${res.statusText}`);
    }

    return await res.json();
}

/**
 * Delete job
 */
async function apiDeleteJob(jobId) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
        method: 'DELETE'
    });

    if (!res.ok) {
        throw new Error(`Failed to delete job: ${res.statusText}`);
    }
}

/**
 * Update job name
 */
async function apiUpdateJobName(jobId, name) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/name`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });

    if (!res.ok) {
        throw new Error(`Failed to update job name: ${res.statusText}`);
    }

    return await res.json();
}

/**
 * Save edited result markdown
 */
async function apiSaveEditedResult(jobId, filename, content) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/results/${filename}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
    });

    if (!res.ok) {
        throw new Error(`Failed to save result: ${res.statusText}`);
    }

    return await res.json();
}

/**
 * Download single result file
 */
function apiDownloadResult(jobId, filename) {
    window.open(`${API_BASE}/jobs/${jobId}/results/${filename}`, '_blank');
}

/**
 * Download all results as ZIP
 */
function apiDownloadAllResults(jobId) {
    window.location.href = `${API_BASE}/jobs/${jobId}/results/download`;
}

/**
 * Batch download multiple jobs as ZIP
 */
async function apiBatchDownload(jobIds) {
    const res = await fetch(`${API_BASE}/batch/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_ids: jobIds })
    });

    if (!res.ok) {
        throw new Error(`Failed to batch download: ${res.statusText}`);
    }

    const blob = await res.blob();
    const contentDisp = res.headers.get('Content-Disposition') || '';
    let filename = 'batch_results.zip';

    if (contentDisp && contentDisp.includes('filename=')) {
        filename = contentDisp.split('filename=')[1].trim().replace(/"/g, '');
    }

    downloadBlob(blob, filename);
}

/**
 * Helper: Download blob
 */
function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

/**
 * Get system info (CUDA support, etc)
 */
async function apiGetSystemInfo() {
    const res = await fetch(`${API_BASE}/system/info`);
    return await res.json();
}



async function apiUpdateJobMode(jobId, newMode) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/mode`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode })
    });
    if (!response.ok) {
        throw new Error('Failed to update job mode');
    }
    return await response.json();
}

async function apiUpdateJobDevice(jobId, newDevice) {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/device`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device: newDevice })
    });
    if (!response.ok) {
        throw new Error('Failed to update job device');
    }
    return await response.json();
}



// ====================
// Initialize
// ====================

/**
 * Initialize API client
 * - Check system capabilities
 * - Connect WebSocket
 * - Load existing cards from backend
 */
async function initAPI() {
    try {
        // Get system info
        const systemInfo = await apiGetSystemInfo();
        state.cudaSupported = systemInfo.cudaSupported;
        console.log('System:', systemInfo);

        // Load existing cards (jobs) from backend
        const existingCards = await apiGetJobs();
        if (existingCards && existingCards.length > 0) {
            state.jobs = existingCards;
            console.log(`Loaded ${existingCards.length} existing cards from backend`);
            render(); // Re-render to show loaded cards
        }

        // Connect WebSocket
        connectWebSocket();

        return true;
    } catch (error) {
        console.error('Failed to initialize API:', error);
        toast('연결 오류', 'API 서버에 연결할 수 없습니다');
        return false;
    }
}
