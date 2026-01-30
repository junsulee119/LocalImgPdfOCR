const state = {
    jobs: [],
    modalJobId: null,
    modalPreviewIndex: 0,   // left preview index
    modalResultIndex: 0,    // right md index
    cudaSupported: true,

    // ✅ job queue (front)
    queue: [],              // jobId[]
    activeJobId: null,      // currently running jobId

    // ✅ batch selection
    isSelectionMode: false,
    selectedJobIds: new Set(),
};

const $ = (q, el = document) => el.querySelector(q);
const uid = () => Math.random().toString(16).slice(2) + Date.now().toString(16);
const nowName = () => {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};
const extType = (name) => {
    const n = (name || '').toLowerCase();
    if (n.endsWith('.pdf')) return 'pdf';
    if (n.endsWith('.png') || n.endsWith('.jpg') || n.endsWith('.jpeg') || n.endsWith('.webp')) return 'img';
    return 'file';
};
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}
function toast(title, msg) {
    $('#toastTitle').textContent = title;
    $('#toastMsg').textContent = msg;
    const t = $('#toast');
    t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove('show'), 2200);
}

/* ===== Virtual File Helpers ===== */
/* ===== Virtual File Helpers ===== */
function parsePageSelection(sel, total) {
    if (!sel || sel === 'all') {
        return Array.from({ length: total }, (_, i) => i + 1);
    }
    const pages = new Set();
    sel.split(',').forEach(part => {
        part = part.trim();
        if (part.includes('-')) {
            const [s, e] = part.split('-').map(Number);
            if (s && e) {
                for (let i = s; i <= e; i++) pages.add(i);
            }
        } else {
            const p = Number(part);
            if (p) pages.add(p);
        }
    });
    // Filter by total
    return Array.from(pages).filter(p => p >= 1 && p <= total).sort((a, b) => a - b);
}

function createVirtualFileList(job, includeResults = false) {
    const virtualFiles = [];
    job.files.forEach(f => {
        if (f.type === 'pdf') {
            // Deciding which pages to show
            // 1. If result exists, use result pages (guaranteed processed)
            // 2. If running/done but no result yet? Show selected pages.
            // 3. If pending/ready? Show ALL pages. (Requirement 1)

            const isRunningOrDone = ['OCR진행중', '완료', '실패'].includes(job.status);

            let targetPages = [];
            const result = job.perFileResults?.[f.id];

            if (result && result.pages) {
                targetPages = Object.keys(result.pages).map(Number).sort((a, b) => a - b);
            } else {
                // For both running/done AND pre-start:
                // We ALWAYS respect the user's page selection (f.pagesSel)
                // If it's "all" (default), it shows all pages.
                // If user sets "1-3", it shows 1-3.
                targetPages = parsePageSelection(f.pagesSel, f.pageCount || 1);
            }

            targetPages.forEach(pageNum => {
                const vf = {
                    type: 'pdf-page',
                    fileId: f.id,
                    fileName: f.name,
                    page: pageNum,
                    sourceFile: f
                };
                if (includeResults && result && result.pages) {
                    vf.pageResult = result.pages[pageNum];
                }
                virtualFiles.push(vf);
            });
        } else {
            const result = job.perFileResults?.[f.id];
            const vf = {
                type: 'file',
                fileId: f.id,
                fileName: f.name
            };
            if (includeResults) {
                vf.fileResult = result;
            } else {
                vf.sourceFile = f;
            }
            virtualFiles.push(vf);
        }
    });
    return virtualFiles;
}

function getVirtualFileCount(job) {
    let count = 0;
    job.files.forEach(f => {
        const result = job.perFileResults?.[f.id];
        if (result && result.isPdf && result.pages) {
            count += Object.keys(result.pages).length;
        } else if (f.type === 'pdf') {
            // For both running/done AND pre-start:
            // ALWAYS respect user selection
            const countSel = parsePageSelection(f.pagesSel, f.pageCount || 1).length;
            count += countSel;
        } else {
            count += 1;
        }
    });
    return count;
}

const canvas = $('#canvas');
const glow = $('#dragGlow');
const centerHint = $('#centerHint');
const canvasFileInput = $('#canvasFileInput');

// Batch UI elements
const batchDock = $('#batchDock');
const batchModeToggle = $('#batchModeToggle');
const batchRunBtn = $('#batchRunBtn');
const batchDownloadBtn = $('#batchDownloadBtn');
const batchDeleteBtn = $('#batchDeleteBtn');

// Batch Event Listeners
batchModeToggle.addEventListener('change', (e) => toggleSelectionMode(e.target.checked));
batchRunBtn.addEventListener('click', batchRunOCR);
batchDownloadBtn.addEventListener('click', batchDownload);
batchDeleteBtn.addEventListener('click', batchDelete);

canvas.addEventListener('dragover', (e) => { e.preventDefault(); glow.classList.add('on'); });
canvas.addEventListener('dragleave', () => glow.classList.remove('on'));
canvas.addEventListener('drop', (e) => {
    e.preventDefault();
    glow.classList.remove('on');
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) createJobsFromDropped(files);
});
canvas.addEventListener('click', (e) => {
    if (e.target.closest('.jobCard')) return;
    if (e.target.closest('.modalOverlay')) return;
    canvasFileInput.click();
});
canvasFileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length) createJobsFromDropped(files);
    e.target.value = '';
});

/* ✅ 혼합 금지 정책:
   - input에 PDF + 이미지가 섞여 들어오면 자동 분리
   - PDF는 "PDF들 = 1 job" (묶음)
   - 이미지는 "이미지들 = 1 job" (묶음)
*/
async function createJobsFromDropped(fileObjs) {
    const pdfs = [];
    const imgs = [];
    const others = [];

    // Separate by type
    for (const file of fileObjs) {
        const ext = file.name.toLowerCase().split('.').pop();
        if (ext === 'pdf') {
            pdfs.push(file);
        } else if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) {
            imgs.push(file);
        } else {
            others.push(file);
        }
    }

    // Create jobs via API
    try {
        if (imgs.length) {
            const fd = new FormData();
            imgs.forEach(f => fd.append('files', f));
            fd.append('kind', 'img');
            fd.append('mode', 'text');
            fd.append('device', state.cudaSupported ? 'cuda' : 'cpu');

            const job = await apiCreateJob(fd);
            state.jobs.push(job);
            toast('작업 생성', `이미지 ${imgs.length}개 추가됨`);
        }

        if (pdfs.length) {
            const fd = new FormData();
            pdfs.forEach(f => fd.append('files', f));
            fd.append('kind', 'pdf');
            fd.append('mode', 'text');
            fd.append('device', state.cudaSupported ? 'cuda' : 'cpu');

            const job = await apiCreateJob(fd);
            state.jobs.push(job);
            toast('작업 생성', `PDF ${pdfs.length}개 추가됨`);
        }

        if (others.length) {
            toast('미지원', '확장자 미지원 파일은 무시됨.');
        }

        render();
    } catch (error) {
        console.error('Failed to create job:', error);
        toast('오류', '작업 생성 실패');
    }
}

// Removed createJob - now handled by API

/* ===== Queue helpers ===== */
function isQueued(jobId) { return state.queue.includes(jobId); }

function syncQueueBadges() {
    // queued jobs: status -> 대기열(n)
    state.queue.forEach((id, idx) => {
        const j = state.jobs.find(x => x.id === id);
        if (j && j.status !== 'OCR진행중' && j.status !== '완료') {
            j.status = `대기열(${idx + 1})`;
            j.progress = 0;
        }
    });
    render();
    if (state.modalJobId) renderModal();
}

async function deleteCard(jobId) {
    const idx = state.jobs.findIndex(j => j.id === jobId);
    if (idx === -1) return;

    const job = state.jobs[idx];
    if (!confirm(`"${job.name}" 카드를 삭제하시겠습니까?`)) return;

    try {
        // Delete from backend (removes from cards.json and deletes files)
        await apiDeleteJob(job.backendJobId || job.id);

        // Remove from frontend state
        state.jobs.splice(idx, 1);

        // Remove from queue if it's queued
        const qIdx = state.queue.indexOf(jobId);
        if (qIdx >= 0) state.queue.splice(qIdx, 1);

        toast('삭제 완료', `"${job.name}" 카드 삭제됨`);
        render();
    } catch (error) {
        console.error('Failed to delete card:', error);
        toast('삭제 실패', error.message);
    }
}
async function enqueueJob(jobId, { fromCanvas }) {
    const job = state.jobs.find(j => j.id === jobId);
    if (!job) return;

    if (job.files.length === 0) {
        toast('파일 없음', '작업에 파일이 없습니다.');
        return;
    }
    if (job.status === 'OCR진행중') {
        toast('이미 실행 중', '이미 OCR 진행 중입니다.');
        return;
    }
    if (job.status === '완료') {
        toast('완료됨', '이미 완료된 작업입니다.');
        return;
    }
    if (isQueued(jobId)) {
        toast('이미 대기열', '이미 큐에 들어가 있어.');
        return;
    }

    // Call API to enqueue
    try {
        await apiEnqueueJob(jobId);

        // Add to local queue
        state.queue.push(jobId);
        syncQueueBadges();
        toast('큐 추가', fromCanvas ? `캔버스에서 "${job.name}" 대기열 추가` : `작업 "${job.name}" 대기열 추가`);

    } catch (error) {
        console.error('Failed to enqueue job:', error);
        toast('오류', '작업 추가 실패');
    }
}

function processQueue() {
    // Backend now handles queue processing
    // This just updates UI state when jobs complete
    if (state.activeJobId) return;
    if (state.queue.length === 0) { render(); return; }

    const nextId = state.queue.shift();
    state.activeJobId = nextId;

    syncQueueBadges();
    render();
}

/* ===== Cards ===== */
function render() {
    const wrap = $('#cardsWrap');
    wrap.innerHTML = '';

    if (state.jobs.length === 0) centerHint.classList.remove('has-cards');
    else centerHint.classList.add('has-cards');

    state.jobs.forEach(job => {
        const div = document.createElement('div');
        div.className = 'jobCard';
        if (state.isSelectionMode) div.classList.add('selectionMode');
        if (state.selectedJobIds.has(job.id)) div.classList.add('selected');

        const isRunning = job.status === 'OCR진행중';
        const isQueuedState = job.status === '대기 중' && state.queue.includes(job.id);
        const canEnqueue = (job.status === '준비됨' || job.status === '완료') && !isQueuedState;

        const st = job.status;

        let miniProgress = '';
        if (isRunning || isQueuedState) {
            miniProgress = `<div class="miniProgress"><div class="miniBar" style="width:${job.progress}%"></div></div>`;
        } else if (st === '완료') {
            miniProgress = `<div class="miniProgress"><div class="miniBar" style="width:100%;background:var(--ok)"></div></div>`;
        }

        div.innerHTML = `
      <div class="cardCheckbox"></div>
      <div class="jobTitle">${escapeHtml(job.name)}</div>
      <div class="jobMeta">
        <div>${job.files.length}개 파일</div>
        <div class="pill" style="display:none; margin-top:6px">${st}</div>
      </div>
      
      <div class="jobFooter">
        <div class="jobStatusText" style="padding:0; border:none; background:transparent;">${escapeHtml(st)}</div>
      </div>
    `;

        div.addEventListener('click', (e) => {
            // Priority: Checkbox/Mode -> JobStartBox -> Modal
            if (state.isSelectionMode) {
                // In selection mode, clicking anywhere toggles selection
                // (except maybe the start button? No, disable start button action in selection mode for simplicity, or keep it?)
                // User requirement: "the cards now can be multi-selected."
                // Better to consume the click for selection.
                e.stopPropagation();
                toggleJobSelection(job.id);
                return;
            }

            openModal(job.id);
        });



        // Removed jobStartBox listener as visible element is gone

        wrap.appendChild(div);
    });

}

/* ===== Modal ===== */
const overlay = $('#modalOverlay');
$('#modalClose').addEventListener('click', () => closeModal());
overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });

function openModal(jobId) {
    state.modalJobId = jobId;
    state.modalPreviewIndex = 0;
    state.modalResultIndex = 0;
    overlay.classList.add('show');
    renderModal();
}
function closeModal() {
    overlay.classList.remove('show');
    state.modalJobId = null;
    hideRangePopover();
}
function getModalJob() {
    return state.jobs.find(j => j.id === state.modalJobId) || null;
}
function setToggle(el, on) { el.classList.toggle('on', !!on); }

function renderModal() {
    const job = getModalJob();
    if (!job) return;

    const pill = $('#jobNamePill');
    pill.textContent = job.name;
    pill.onclick = (e) => {
        if (job.status === 'OCR진행중') {
            toast('실행 중', '진행 중에는 이름을 바꿀 수 없어.');
            return;
        }

        const currentName = job.name;
        const input = document.createElement('input');
        input.type = 'text';
        input.value = currentName;
        input.className = 'inlineRenameInputPill';

        // Style specific to modal pill
        input.style.width = '300px';
        input.style.font = 'inherit';
        input.style.border = '1px solid var(--accent)';
        input.style.borderRadius = '4px';
        input.style.padding = '4px 8px';
        input.style.background = '#fff';
        input.style.color = 'inherit';

        pill.textContent = '';
        pill.appendChild(input);
        input.focus();

        const save = async () => {
            const newName = input.value.trim();
            if (newName && newName !== currentName) {
                try {
                    await apiUpdateJobName(job.backendJobId || job.id, newName);
                    job.name = newName;
                    toast('이름 변경', '작업 이름이 변경됨');
                } catch (error) {
                    console.error('Failed to update job name:', error);
                    toast('이름 변경 실패', error.message);
                }
            }
            // Restore text view (re-render modal title part only or full modal?)
            // renderModal re-binds onclick, so it's safe to call.
            // But we can just set textContent if we don't want full re-render flickering.
            // Actually renderModal() updates mostly everything. Let's call render() and renderModal().
            render();
            renderModal();
        };

        input.addEventListener('blur', save);
        input.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter') {
                input.blur();
            }
        });

        input.onclick = (ev) => ev.stopPropagation();
    };

    setToggle($('#toggleMode'), job.mode === 'img');
    setToggle($('#toggleDevice'), job.device === 'cpu');
    $('#deviceHint').textContent = state.cudaSupported ? 'CUDA 지원: ON (미지원이면 CPU로 고정)' : 'CUDA 지원: OFF → CPU 고정';

    const running = job.id === state.activeJobId && job.status === 'OCR진행중';
    const done = job.status === '완료';
    const queued = isQueued(job.id) || /^대기열\(\d+\)$/.test(job.status);

    // ✅ 모달에서도 "큐 추가"로 동작
    $('#startBtn').disabled = running || queued || job.files.length === 0;
    $('#startBtn').textContent = running ? 'OCR 진행중…' : (queued ? '대기열에 있음' : 'OCR 시작(큐 추가)');

    $('#modalBar').style.width = job.progress + '%';
    $('#modalLabel').textContent = Math.round(job.progress) + '%';
    $('#statusHint').textContent = job.status;

    $('#fileAddBtn').disabled = running;
    $('#fileRemoveBtn').disabled = running || (job.files.length === 0);

    $('#downloadBtn').disabled = !done;
    $('#downloadAllBtn').disabled = !done;

    renderPreview();
    renderResultEditor();
}

/* ===== Left preview navigation ===== */
$('#prevFile').addEventListener('click', () => navPreview(-1));
$('#nextFile').addEventListener('click', () => navPreview(+1));
function navPreview(delta) {
    const job = getModalJob();
    if (!job || job.files.length === 0) return;

    const virtualCount = getVirtualFileCount(job);
    state.modalPreviewIndex = (state.modalPreviewIndex + delta + virtualCount) % virtualCount;

    state.modalResultIndex = state.modalPreviewIndex;

    hideRangePopover();
    renderPreview();
    renderResultEditor();
}

/* ===== Right result navigation ===== */
$('#resPrev').addEventListener('click', () => navResult(-1));
$('#resNext').addEventListener('click', () => navResult(+1));
function navResult(delta) {
    const job = getModalJob();
    if (!job || job.files.length === 0) return;

    const virtualCount = getVirtualFileCount(job);
    state.modalResultIndex = (state.modalResultIndex + delta + virtualCount) % virtualCount;

    state.modalPreviewIndex = state.modalResultIndex;

    hideRangePopover();
    renderPreview();
    renderResultEditor();
}

/* ===== Modal file add/remove ===== */
const modalFileInput = $('#modalFileInput');
$('#fileAddBtn').addEventListener('click', () => {
    const job = getModalJob(); if (!job) return;
    if (job.status === 'OCR진행중') { toast('실행 중', '진행 중에는 파일을 추가할 수 없어.'); return; }
    modalFileInput.click();
});
modalFileInput.addEventListener('change', async (e) => {
    const job = getModalJob(); if (!job) return;
    const fileObjs = Array.from(e.target.files || []);
    if (!fileObjs.length) return;

    if (job.status === 'OCR진행중') {
        toast('실행 중', '진행 중에는 파일을 추가할 수 없어.');
        e.target.value = '';
        return;
    }

    // Separate by type
    const pdfs = fileObjs.filter(f => f.name.toLowerCase().endsWith('.pdf'));
    const imgs = fileObjs.filter(f => {
        const ext = f.name.toLowerCase().split('.').pop();
        return ['png', 'jpg', 'jpeg', 'webp'].includes(ext);
    });
    const others = fileObjs.filter(f => !pdfs.includes(f) && !imgs.includes(f));

    if (others.length) toast('미지원', `${others.length}개 파일 무시됨`);

    try {
        if (job.kind === 'img') {
            if (pdfs.length) toast('혼합 불가', '이미지 카드에는 PDF를 추가할 수 없어.');
            if (imgs.length) {
                // Upload to backend
                const result = await apiAddFilesToJob(job.backendJobId || job.id, imgs);

                // Update frontend state with backend response
                result.files.forEach(f => job.files.push(f));
                job.status = 'OCR진행가능';

                toast('파일 추가', `${imgs.length}개 추가됨`);
                state.modalPreviewIndex = job.files.length - 1;
                state.modalResultIndex = state.modalPreviewIndex;
                render();
                renderModal();
            }
        }

        if (job.kind === 'pdf') {
            if (imgs.length) toast('혼합 불가', 'PDF 카드에는 이미지를 추가할 수 없어.');
            if (pdfs.length) {
                // Upload to backend
                const result = await apiAddFilesToJob(job.backendJobId || job.id, pdfs);

                // Update frontend state with backend response
                result.files.forEach(f => job.files.push(f));
                job.status = 'OCR진행가능';

                toast('파일 추가', `${pdfs.length}개 추가됨`);
                state.modalPreviewIndex = job.files.length - 1;
                state.modalResultIndex = state.modalPreviewIndex;
                render();
                renderModal();
            }
        }
    } catch (error) {
        console.error('Failed to add files:', error);
        toast('추가 실패', error.message);
    }

    e.target.value = '';
});
$('#fileRemoveBtn').addEventListener('click', () => {
    const job = getModalJob(); if (!job) return;
    if (job.status === 'OCR진행중') { toast('실행 중', '진행 중에는 파일을 제거할 수 없어.'); return; }
    if (job.files.length === 0) return;

    const removed = job.files.splice(state.modalPreviewIndex, 1)[0];
    if (removed && job.perFileResults) delete job.perFileResults[removed.id];

    // Reset backend job ID so new file set gets uploaded
    delete job.backendJobId;

    toast('파일 제거', removed ? removed.name : '제거됨');

    if (job.files.length === 0) {
        job.status = '대기';
        job.progress = 0;
        job.perFileResults = {};
    } else if (job.status !== '완료') {
        job.status = 'OCR진행가능';
    }

    state.modalPreviewIndex = Math.min(state.modalPreviewIndex, job.files.length - 1);
    state.modalResultIndex = state.modalPreviewIndex;

    hideRangePopover();
    render();
    renderModal();
});

/* ===== PDF Range UI ===== */
const pdfRangeBar = $('#pdfRangeBar');
const rangeChip = $('#rangeChip');
const rangeValue = $('#rangeValue');
const rangePopover = $('#rangePopover');
const rangeInput = $('#rangeInput');

function showRangeBar(val) {
    pdfRangeBar.classList.add('on');
    rangeValue.textContent = val || 'all';
}
function hideRangeBar() {
    pdfRangeBar.classList.remove('on');
    hideRangePopover();
}
function showRangePopover(current) {
    rangePopover.classList.add('show');
    rangeInput.value = current || 'all';
    rangeInput.focus();
}
function hideRangePopover() { rangePopover.classList.remove('show'); }
function normalizeRange(v) {
    const t = (v || '').trim();
    return t ? t : 'all';
}

rangeChip.addEventListener('click', () => {
    const job = getModalJob(); if (!job) return;
    const f = job.files[state.modalPreviewIndex];
    if (!f || f.type !== 'pdf') return;
    if (job.status === 'OCR진행중') { toast('실행 중', '진행 중에는 범위를 바꿀 수 없어.'); return; }
    showRangePopover(f.pagesSel || 'all');
});
$('#rangeEditBtn').addEventListener('click', () => rangeChip.click());
$('#rangeApplyBtn').addEventListener('click', async () => {
    const job = getModalJob(); if (!job) return;
    const f = job.files[state.modalPreviewIndex];
    if (!f || f.type !== 'pdf') return;
    if (job.status === 'OCR진행중') { toast('실행 중', '진행 중에는 범위를 바꿀 수 없어.'); return; }

    const v = normalizeRange(rangeInput.value);

    try {
        // Update backend
        await apiUpdateFilePageSelection(job.backendJobId || job.id, f.id, v);

        // Update frontend
        f.pagesSel = v;
        showRangeBar(v);
        hideRangePopover();
        toast('범위 적용', `OCR 범위 = ${v}`);
    } catch (error) {
        console.error('Failed to update page selection:', error);
        toast('범위 적용 실패', error.message);
    }
});
$('#rangeCancelBtn').addEventListener('click', () => hideRangePopover());
rangeInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); $('#rangeApplyBtn').click(); }
    if (e.key === 'Escape') { e.preventDefault(); hideRangePopover(); }
});

/* ===== Preview render ===== */
function renderPreview() {
    const job = getModalJob();
    if (!job) return;

    const title = $('#previewTitle');
    const tagsContainer = $('#jobTitleTags');
    const content = $('#previewContent');

    // Helper to update title and tags
    const updateHeader = (name, tagHtml) => {
        if (title) title.textContent = name;
        if (tagsContainer) tagsContainer.innerHTML = tagHtml || '';
    };

    if (job.files.length === 0) {
        updateHeader('미리보기', '');
        content.innerHTML = `
      <div style="font-size:14px;font-weight:950;">미리보기</div>
      <div class="box">파일을 선택하면 여기 표시</div>
      <div style="font-size:12px; font-weight:900; color:var(--muted);">PDF는 placeholder로 표시</div>
    `;
        hideRangeBar();
        return;
    }

    // Create virtual file list using helper
    const virtualFiles = createVirtualFileList(job, false);
    const totalItems = virtualFiles.length;

    if (state.modalPreviewIndex >= totalItems) {
        state.modalPreviewIndex = Math.max(0, totalItems - 1);
    }

    const current = virtualFiles[state.modalPreviewIndex];
    if (!current) {
        hideRangeBar();
        return;
    }

    // Update both index displays (top and bottom)
    const bottomIdx = $('#previewIndexBottom');
    if (bottomIdx) {
        bottomIdx.textContent = `${state.modalPreviewIndex + 1} / ${totalItems}`;
    }

    if (current.type === 'pdf-page') {
        // --- PDF Page ---
        // Tag -> Top Header
        const tagHtml = `<span class="pill">PDF</span> <span style="font-size:12px; font-weight:800; color:var(--muted);">Page ${current.page}</span>`;
        updateHeader(current.fileName, tagHtml);

        // Use single page PDF endpoint for filtered view
        const pdfUrl = `http://localhost:8000/api/jobs/${job.id}/files/${encodeURIComponent(current.fileName)}/page/${current.page}#toolbar=0&navpanes=0&view=FitH`;

        content.innerHTML = `
      <embed src="${pdfUrl}" type="application/pdf" width="100%" style="flex:1; min-height:0; border:none;">
    `;
        showRangeBar(current.sourceFile.pagesSel || 'all');
    } else if (current.sourceFile.type === 'img') {
        // --- Image ---
        const tagHtml = `<span class="pill">IMG</span>`;
        updateHeader(current.fileName, tagHtml);

        // ...
        const imgUrl = `http://localhost:8000/api/jobs/${job.id}/files/${encodeURIComponent(current.fileName)}`;
        content.innerHTML = `
      <img src="${imgUrl}" style="max-width:100%; height:100%; object-fit:contain; border:none;" 
           onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
      <div class="box" style="display:none;">이미지 로드 실패</div>
    `;
        hideRangeBar();
    } else if (current.sourceFile.type === 'pdf') {
        // --- PDF File (Fallback/Raw) ---
        const tagHtml = `<span class="pill">PDF</span>`;
        updateHeader(current.fileName, tagHtml);

        const pdfUrl = `http://localhost:8000/api/jobs/${job.id}/files/${encodeURIComponent(current.fileName)}#toolbar=0&navpanes=0&view=FitH`;
        content.innerHTML = `
      <embed src="${pdfUrl}" type="application/pdf" width="100%" style="flex:1; min-height:0; border:none;">
    `;
        showRangeBar(current.sourceFile.pagesSel || 'all');
    } else {
        updateHeader(current.fileName, '');

        content.innerHTML = `
      <div style="font-size:14px;font-weight:950;">${escapeHtml(current.fileName)}</div>
      <div class="box">[미리보기 미지원]</div>
    `;
        hideRangeBar();
    }
}

/* ===== Result editor (per-file md) ===== */
function renderResultEditor() {
    const job = getModalJob();
    if (!job) return;

    const running = job.status === 'OCR진행중';
    const editor = $('#resultEditor');
    const indexDiv = $('#resIndex');
    const metaDiv = $('#resultMeta');
    const prevBtn = $('#resPrev');
    const nextBtn = $('#resNext');
    const applyBtn = $('#applyEditBtn');
    const resetBtn = $('#resetTextBtn');
    const toggleBtn = $('#toggleMdViewBtn');
    const downloadBtn = $('#downloadBtn');
    const downloadAllBtn = $('#downloadAllBtn');

    // Create virtual file list using helper
    const virtualFiles = createVirtualFileList(job, true);
    const totalItems = virtualFiles.length;
    const hasResults = virtualFiles.some(vf => vf.pageResult || vf.fileResult);

    // Enable buttons
    // Enable buttons
    // User Request: Disable Apply/Reset during streaming (Running)
    const isRunning = job.status === 'OCR진행중';

    applyBtn.disabled = !hasResults || isRunning;
    resetBtn.disabled = !hasResults || isRunning;

    // Toggle stays enabled if we have results (meaning streaming started)
    toggleBtn.disabled = !hasResults;

    downloadBtn.disabled = !hasResults || isRunning; // download usually wait for done
    downloadAllBtn.disabled = !hasResults || isRunning;

    // Ensure index is valid
    if (state.modalResultIndex >= totalItems) {
        state.modalResultIndex = Math.max(0, totalItems - 1);
    }

    indexDiv.textContent = `${state.modalResultIndex + 1} / ${totalItems}`;

    const current = virtualFiles[state.modalResultIndex];
    if (!current) {
        editor.value = '';
        editor.disabled = true;
        metaDiv.textContent = '—';
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        return;
    }

    prevBtn.disabled = state.modalResultIndex === 0;
    nextBtn.disabled = state.modalResultIndex >= totalItems - 1;

    if (current.type === 'pdf-page') {
        // PDF page item
        if (current.pageResult) {
            editor.value = current.pageResult.md || '';
            editor.disabled = false;
            metaDiv.textContent = `${current.fileName} - Page ${current.page} · ${current.pageResult.outName}`;
        } else {
            editor.value = running ? '처리 중...' : '대기 중...';
            editor.disabled = true;
            metaDiv.textContent = `${current.fileName} - Page ${current.page} (처리 대기 중)`;
        }
    } else {
        // Regular file item
        if (current.fileResult) {
            editor.value = current.fileResult.md || '';
            editor.disabled = false;
            metaDiv.textContent = `${current.fileResult.outName} · ${(current.fileResult.md || '').length}자`;
        } else {
            editor.value = running ?
                `처리 중...\n\n파일: ${current.fileName}\n상태: 대기 중` :
                'OCR 완료 후 결과가 표시됩니다.';
            editor.disabled = true;
            metaDiv.textContent = running ? '처리 대기 중...' : '—';
        }
    }

    // If in preview mode, update the preview with new content
    if (mdViewMode) {
        const preview = $('#resultPreview');
        const md = editor.value;
        const jobId = job ? (job.backendJobId || job.id) : null;
        preview.innerHTML = renderMarkdown(md, jobId);

        // Render math with KaTeX if available
        if (window.renderMathInElement) {
            try {
                renderMathInElement(preview, {
                    delimiters: [
                        { left: '$$', right: '$$', display: true },
                        { left: '$', right: '$', display: false },
                        { left: '\\[', right: '\\]', display: true },
                        { left: '\\(', right: '\\)', display: false }
                    ],
                    throwOnError: false
                });
            } catch (e) {
                console.warn('KaTeX rendering failed:', e);
            }
        }
    }
}

/* ===== Toggles ===== */
/* ===== Toggles ===== */
$('#toggleMode').addEventListener('click', async () => {
    const job = getModalJob(); if (!job) return;
    if (job.status === 'OCR진행중') { toast('실행 중', '진행 중에는 모드를 바꿀 수 없어.'); return; }

    const newMode = job.mode === 'img' ? 'text' : 'img';

    try {
        await apiUpdateJobMode(job.backendJobId || job.id, newMode);

        job.mode = newMode; // Update local state
        const on = job.mode === 'img';
        setToggle($('#toggleMode'), on);
        toast('모드 변경', job.mode === 'img' ? 'text+img' : 'text only');
        render();
        renderModal();
    } catch (error) {
        console.error('Failed to update job mode:', error);
        toast('변경 실패', error.message);
    }
});
$('#toggleDevice').addEventListener('click', async () => {
    const job = getModalJob(); if (!job) return;
    if (job.status === 'OCR진행중') { toast('실행 중', '진행 중에는 디바이스를 바꿀 수 없어.'); return; }

    if (!state.cudaSupported) {
        setToggle($('#toggleDevice'), true);
        job.device = 'cpu';
        toast('CUDA 미지원', 'CPU로 고정됨');
    } else {
        const newDevice = job.device === 'cuda' ? 'cpu' : 'cuda';

        try {
            await apiUpdateJobDevice(job.backendJobId || job.id, newDevice);

            job.device = newDevice; // Update local state
            const on = job.device === 'cpu'; // Toggle ON means CPU (as per original logic?) Wait, let's check original...
            // Original: setToggle($('#toggleDevice'), on); job.device = on ? 'cpu' : 'cuda';
            // So if ON then CPU. OFF then CUDA.
            // Let's stick to original UI logic: ON = CPU-only mode? or ON = CUDA?
            // Checking setup: setToggle($('#toggleDevice'), job.device === 'cpu'); -> So ON is CPU.

            setToggle($('#toggleDevice'), job.device === 'cpu');
            toast('디바이스 변경', job.device.toUpperCase());
            render();
            renderModal();
        } catch (error) {
            console.error('Failed to update job device:', error);
            toast('변경 실패', error.message);
        }
    }
});

/* ===== Start (enqueue) ===== */
$('#startBtn').addEventListener('click', () => {
    const job = getModalJob(); if (!job) return;
    enqueueJob(job.id, { fromCanvas: false });
});

// Mock OCR functions removed - backend handles via WebSocket

/* ===== Results edit/apply/reset/download ===== */
$('#applyEditBtn').addEventListener('click', async () => {
    const job = getModalJob(); if (!job) return;
    const f = job.files[state.modalResultIndex];
    const r = job.perFileResults[f.id];
    if (!r) return;

    const newContent = $('#resultEditor').value;

    try {
        await apiSaveEditedResult(job.backendJobId || job.id, r.outName, newContent);
        r.md = newContent; // Update local state
        toast('수정 적용', `${r.outName} 저장됨`);
    } catch (error) {
        console.error('Failed to save edited result:', error);
        toast('저장 실패', error.message);
    }
});
$('#resetTextBtn').addEventListener('click', () => {
    const job = getModalJob(); if (!job) return;
    const f = job.files[state.modalResultIndex];
    const r = job.perFileResults[f.id];
    if (!r) return;
    $('#resultEditor').value = r.originalMd;
    toast('되돌리기', '원본으로 되돌렸어.');
});

/* ===== Markdown view toggle ===== */
let mdViewMode = false; // false = editor, true = preview



$('#toggleMdViewBtn').addEventListener('click', () => {
    mdViewMode = !mdViewMode;
    const editor = $('#resultEditor');
    const preview = $('#resultPreview');
    const btn = $('#toggleMdViewBtn');

    if (mdViewMode) {
        // Show preview
        const job = getModalJob();
        // Use backendJobId if available (for completed jobs), otherwise id
        const jobId = job ? (job.backendJobId || job.id) : null;
        const md = editor.value;
        preview.innerHTML = renderMarkdown(md, jobId);
        editor.style.display = 'none';
        preview.style.display = 'block';
        btn.textContent = '✏️ 편집';

        // Render math with KaTeX if available
        if (window.renderMathInElement) {
            try {
                renderMathInElement(preview, {
                    delimiters: [
                        { left: '$$', right: '$$', display: true },
                        { left: '$', right: '$', display: false },
                        { left: '\\[', right: '\\]', display: true },
                        { left: '\\(', right: '\\)', display: false }
                    ],
                    throwOnError: false
                });
            } catch (e) {
                console.warn('KaTeX rendering failed:', e);
            }
        }
    } else {
        // Show editor
        editor.style.display = 'block';
        preview.style.display = 'none';
        btn.textContent = '👁 미리보기';
    }
});


$('#downloadBtn').addEventListener('click', () => {
    const job = getModalJob(); if (!job || job.status !== '완료') return;
    const f = job.files[state.modalResultIndex];
    const r = job.perFileResults[f.id];
    if (!r) return;

    // Download from backend
    apiDownloadResult(job.backendJobId || job.id, r.outName);
    toast('다운로드', `${r.outName} 다운로드 중...`);
});

$('#downloadAllBtn').addEventListener('click', () => {
    const job = getModalJob(); if (!job || job.status !== '완료') return;

    // Download ZIP from backend
    apiDownloadAllResults(job.backendJobId || job.id);
    apiDownloadAllResults(job.backendJobId || job.id);
    toast('전체 다운로드', '모든 .md + manifest.json 다운로드 중...');
});

$('#deleteJobBtn').addEventListener('click', async () => {
    const job = getModalJob(); if (!job) return;

    if (!confirm('정말 이 작업을 삭제하시겠습니까? 데이터와 결과 파일이 모두 삭제됩니다.')) return;

    try {
        await apiDeleteJob(job.backendJobId || job.id);

        // Remove from local state
        state.jobs = state.jobs.filter(j => j.id !== job.id);

        // Close details
        closeModal();
        render();
        toast('삭제 완료', '작업이 삭제되었습니다.');

    } catch (error) {
        console.error('Failed to delete job:', error);
        toast('삭제 실패', error.message);
    }
});
function downloadBlob(blob, filename) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
}

/* ===== Initialize ===== */
// Initialize API connection on page load
initAPI().then(() => {
    render();
});
/* ===== Live Streaming Handle ===== */
function handleOcrChunk(msg) {
    const job = state.jobs.find(j => j.id === msg.job_id);
    if (!job) return;

    // 1. Update State
    if (!job.perFileResults) job.perFileResults = {};

    // Initialize file result if missing
    if (!job.perFileResults[msg.file_id]) {
        job.perFileResults[msg.file_id] = {
            isPdf: !!msg.page,
            pages: {},
            md: '',
            images: [] // Placeholder
        };
    }

    const fileRes = job.perFileResults[msg.file_id];

    if (msg.page) {
        // PDF Page
        if (!fileRes.pages) fileRes.pages = {};
        if (!fileRes.pages[msg.page]) {
            fileRes.pages[msg.page] = {
                page: msg.page,
                md: '',
                images: []
            };
        }
        fileRes.pages[msg.page].md += msg.text;
    } else {
        // Single Image
        fileRes.md = (fileRes.md || '') + msg.text;
    }

    // 2. Update UI (Result Editor) if active
    if (state.modalJobId === msg.job_id) {
        // Check if we are viewing this specific file/page
        const virtualFiles = createVirtualFileList(job, true);
        const current = virtualFiles[state.modalResultIndex];

        if (current && current.fileId === msg.file_id) {
            const isMatch = (msg.page && current.page === msg.page) || (!msg.page && !current.page);

            if (isMatch) {
                const editor = $('#resultEditor');
                const toggle = $('#toggleMdViewBtn');
                const apply = $('#applyEditBtn');
                const reset = $('#resetTextBtn');

                // Unblock UI on first chunk (PARTIAL)
                if (editor.disabled) {
                    editor.value = '';
                    editor.disabled = false;
                    toggle.disabled = false;
                    // Keep Apply/Reset disabled during streaming
                    apply.disabled = true;
                    reset.disabled = true;
                }

                // Append text
                editor.value += msg.text;
                editor.scrollTop = editor.scrollHeight; // Auto-scroll

                // LIVE MARKDOWN UPDATE
                if (mdViewMode) {
                    const preview = $('#resultPreview');
                    const jobId = job ? (job.backendJobId || job.id) : null;
                    preview.innerHTML = renderMarkdown(editor.value, jobId);

                    // Render math with KaTeX if available
                    if (window.renderMathInElement) {
                        try {
                            renderMathInElement(preview, {
                                delimiters: [
                                    { left: '$$', right: '$$', display: true },
                                    { left: '$', right: '$', display: false },
                                    { left: '\\[', right: '\\]', display: true },
                                    { left: '\\(', right: '\\)', display: false }
                                ],
                                throwOnError: false
                            });
                        } catch (e) {
                            // Silent fail for math
                        }
                    }
                    preview.scrollTop = preview.scrollHeight; // Auto-scroll
                }

                // Update meta status if needed
                const metaDiv = $('#resultMeta');
                if (metaDiv.textContent.includes('대기 중') || metaDiv.textContent === '—') {
                    if (msg.page) {
                        metaDiv.textContent = `${current.fileName} - Page ${current.page} (작성 중...)`;
                    } else {
                        metaDiv.textContent = `${current.fileName} (작성 중...)`;
                    }
                }
            }
        }
    }
}
/* ===== Batch Operations ===== */
function downloadJobResults(job) {
    if (!job) return;
    apiDownloadAllResults(job.backendJobId || job.id);
    toast('다운로드', '다운로드 시작...');
}

function toggleSelectionMode(isModeOn) {
    state.isSelectionMode = isModeOn;
    if (!isModeOn) {
        state.selectedJobIds.clear();
        batchDock.classList.remove('active');
    } else {
        batchDock.classList.add('active');
    }
    render();
}

function toggleJobSelection(jobId) {
    if (state.selectedJobIds.has(jobId)) {
        state.selectedJobIds.delete(jobId);
    } else {
        state.selectedJobIds.add(jobId);
    }
    render();
}

async function batchRunOCR() {
    if (state.selectedJobIds.size === 0) return toast('오류', '선택된 작업이 없습니다.');
    let count = 0;
    let skipped = 0;

    // Convert to array to iterate
    const ids = Array.from(state.selectedJobIds);
    for (const id of ids) {
        const job = state.jobs.find(j => j.id === id);
        if (!job) continue;

        const isQueued = job.status === '대기 중' && state.queue.includes(id);
        const isRunning = job.status === 'OCR진행중';
        const isDone = job.status === '완료';

        // Filter: Skip if already queued, running, or done
        if (isQueued || isRunning || isDone) {
            skipped++;
            continue;
        }

        // Only run if Ready (or Failed which is implicit)
        await enqueueJob(id, { fromCanvas: true });
        count++;
        await new Promise(r => setTimeout(r, 50));
    }

    if (count > 0) {
        toast('배치 실행', `${count}개 작업이 큐에 추가됨` + (skipped > 0 ? ` (${skipped}개 스킵됨)` : ''));
    } else {
        toast('알림', `실행 가능한 작업이 없음 (${skipped}개 이미 실행/완료)`);
    }
}

async function batchDownload() {
    if (state.selectedJobIds.size === 0) return toast('오류', '선택된 작업이 없습니다.');

    // Filter for DONE jobs only
    const validIds = [];
    let skipped = 0;

    state.selectedJobIds.forEach(id => {
        const job = state.jobs.find(j => j.id === id);
        if (job && job.status === '완료') {
            validIds.push(id);
        } else {
            skipped++;
        }
    });

    if (validIds.length === 0) {
        return toast('오류', `다운로드할 완료된 작업이 없습니다. (${skipped}개 미완료)`);
    }

    if (skipped > 0) {
        toast('다운로드 시작', `${validIds.length}개 작업 다운로드 (${skipped}개 미완료 제외)`);
    } else {
        toast('다운로드 시작', `${validIds.length}개 작업 다운로드 중...`);
    }

    try {
        await apiBatchDownload(validIds);
    } catch (e) {
        console.error(e);
        toast('다운로드 실패', e.message);
    }
}

function batchDelete() {
    if (state.selectedJobIds.size === 0) return toast('오류', '선택된 작업이 없습니다.');
    if (!confirm(`선택한 ${state.selectedJobIds.size}개 작업을 삭제하시겠습니까?`)) return;

    const idsToDelete = Array.from(state.selectedJobIds);

    idsToDelete.forEach(id => {
        // Optimistically remove from frontend
        state.jobs = state.jobs.filter(j => j.id !== id);
        state.queue = state.queue.filter(qId => qId !== id);

        // Call backend (async, fire and forget)
        apiDeleteJob(id).catch(err => console.error("Batch delete fail", err));
    });

    state.selectedJobIds.clear();
    state.activeJobId = null;

    // Toggle off mode after delete
    batchModeToggle.checked = false;
    toggleSelectionMode(false);

    // UI update
    render();
    toast('삭제 완료', '선택한 작업이 삭제되었습니다.');
}
