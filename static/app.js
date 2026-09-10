/**
 * SAIL Material Management Module - Salem Steel Plant
 * Frontend Application Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // State management
    let selectedFiles = [];
    let processedDocuments = {};
    let currentReviewDocId = null;
    let currentOcrDocId = null;
    let currentPreviewDocId = null;

    // DOM Elements
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const sampleFileBtn = document.getElementById('sampleFileBtn');
    const dropZone = document.getElementById('dropZone');
    const selectedFilesBox = document.getElementById('selectedFilesBox');
    const fileQueueTbody = document.getElementById('fileQueueTbody');
    const fileCountBadge = document.getElementById('fileCountBadge');
    const startAnalyzeBtn = document.getElementById('startAnalyzeBtn');
    const pipelineBox = document.getElementById('pipelineBox');
    const resultsContainer = document.getElementById('resultsContainer');
    const proposalCardsList = document.getElementById('proposalCardsList');
    const newAnalysisBtn = document.getElementById('newAnalysisBtn');

    // Modals
    const reviewModal = document.getElementById('reviewModal');
    const closeReviewModal = document.getElementById('closeReviewModal');
    const cancelReviewBtn = document.getElementById('cancelReviewBtn');
    const saveReviewBtn = document.getElementById('saveReviewBtn');
    const reviewDocMeta = document.getElementById('reviewDocMeta');
    const reviewFieldsTbody = document.getElementById('reviewFieldsTbody');

    const ocrModal = document.getElementById('ocrModal');
    const closeOcrModal = document.getElementById('closeOcrModal');
    const closeOcrBtn = document.getElementById('closeOcrBtn');
    const copyOcrBtn = document.getElementById('copyOcrBtn');
    const ocrDocMeta = document.getElementById('ocrDocMeta');
    const ocrPagesContainer = document.getElementById('ocrPagesContainer');
    const ocrSearchInput = document.getElementById('ocrSearchInput');

    const previewModal = document.getElementById('previewModal');
    const closePreviewModal = document.getElementById('closePreviewModal');
    const closePreviewBtn = document.getElementById('closePreviewBtn');
    const previewPaper = document.getElementById('previewPaper');
    const previewDownloadDocxBtn = document.getElementById('previewDownloadDocxBtn');
    const previewDownloadPdfBtn = document.getElementById('previewDownloadPdfBtn');

    // Tab Navigation
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            tabContents.forEach(tc => {
                if (tc.id === `tab-${targetTab}`) {
                    tc.style.display = 'block';
                } else {
                    tc.style.display = 'none';
                }
            });

            if (targetTab === 'dashboard') loadDashboardStats();
            if (targetTab === 'tracking') loadMaterialTracking();
            if (targetTab === 'reports') loadReports();
        });
    });

    // =========================================================================
    // File Upload & Drag-and-Drop Handlers
    // =========================================================================
    selectFileBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        handleFilesSelected(Array.from(e.target.files));
        fileInput.value = ''; // Reset
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFilesSelected(Array.from(e.dataTransfer.files));
        }
    });

    // Sample requisition loader
    sampleFileBtn.addEventListener('click', async () => {
        sampleFileBtn.disabled = true;
        sampleFileBtn.innerHTML = '<span>Loading Sample...</span>';
        try {
            // Fetch sample file from scratch directory or static
            const res = await fetch('/static/sample_indent.pdf').catch(() => null);
            let blob = null;
            if (res && res.ok) {
                blob = await res.blob();
            } else {
                // Fallback: create mock blob representing sample indent
                blob = new Blob(["%PDF-1.4 SAMPLE REQUISITION A612002 / SMS/25/002"], { type: "application/pdf" });
            }
            const sampleFile = new File([blob], "sample_indent_SMS_25_002.pdf", { type: "application/pdf" });
            handleFilesSelected([sampleFile]);
        } catch (err) {
            alert("Unable to load sample requisition: " + err.message);
        } finally {
            sampleFileBtn.disabled = false;
            sampleFileBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polygon points="10 8 16 12 10 16 10 8"></polygon>
                </svg>
                Load Sample Requisition
            `;
        }
    });

    function handleFilesSelected(files) {
        for (const file of files) {
            // Validate PDF
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                alert(`File "${file.name}" rejected. Only PDF documents are supported.`);
                continue;
            }
            // Validate 30 MB
            const sizeMB = file.size / (1024 * 1024);
            if (sizeMB > 30.0) {
                alert(`File "${file.name}" exceeds the 30 MB limit (${sizeMB.toFixed(1)} MB).`);
                continue;
            }
            // Avoid duplicates
            if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        }
        renderSelectedFilesTable();
    }

    function renderSelectedFilesTable() {
        if (selectedFiles.length === 0) {
            selectedFilesBox.style.display = 'none';
            return;
        }

        selectedFilesBox.style.display = 'block';
        fileCountBadge.textContent = `${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''}`;
        fileQueueTbody.innerHTML = '';

        selectedFiles.forEach((file, idx) => {
            const tr = document.createElement('tr');
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            tr.innerHTML = `
                <td>${idx + 1}</td>
                <td><strong>${escapeHtml(file.name)}</strong></td>
                <td>${sizeMB} MB</td>
                <td>PDF</td>
                <td><span class="badge-ready">Ready</span></td>
                <td>
                    <button class="btn-remove-file" data-index="${idx}" title="Remove file">
                        &times; Remove
                    </button>
                </td>
            `;
            fileQueueTbody.appendChild(tr);
        });

        // Add remove handlers
        document.querySelectorAll('.btn-remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.target.getAttribute('data-index'), 10);
                selectedFiles.splice(idx, 1);
                renderSelectedFilesTable();
            });
        });
    }

    // =========================================================================
    // Analysis Pipeline Execution
    // =========================================================================
    startAnalyzeBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) {
            alert('Please select at least one PDF file to analyze.');
            return;
        }

        startAnalyzeBtn.disabled = true;
        pipelineBox.style.display = 'block';

        const steps = ['upload', 'read', 'render', 'ocr', 'extract', 'validate', 'generate'];
        let currentStepIdx = 0;

        const updatePipelineUI = (title, sub, stepId) => {
            document.getElementById('currentStepTitle').textContent = title;
            document.getElementById('currentStepSub').textContent = sub;
            steps.forEach(s => {
                const el = document.getElementById(`step-${s}`);
                if (el) {
                    el.classList.remove('current');
                    if (steps.indexOf(s) < steps.indexOf(stepId)) {
                        el.classList.add('completed');
                    }
                }
            });
            const curEl = document.getElementById(`step-${stepId}`);
            if (curEl) curEl.classList.add('current');
        };

        try {
            updatePipelineUI("Uploading Documents...", "Sending files to Salem Steel Plant secure node", "upload");

            const formData = new FormData();
            if (selectedFiles.length === 1) {
                formData.append('file', selectedFiles[0]);
                setTimeout(() => updatePipelineUI("Reading PDF & Extracting Geometry...", "Parsing document page tree and streams", "read"), 800);
                setTimeout(() => updatePipelineUI("Converting Pages to High-Res Images...", "Preprocessing contrast & sharpness", "render"), 1800);
                setTimeout(() => updatePipelineUI("Running Multi-Pass OCR Engine...", "Extracting layout text and coordinates", "ocr"), 3000);
                setTimeout(() => updatePipelineUI("Extracting Procurement Fields...", "Mapping to 13 master template background fields", "extract"), 4500);
                setTimeout(() => updatePipelineUI("Validating Contextual Rules...", "Checking numbers, currency, and approving authorities", "validate"), 5500);

                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Analysis request failed');
                }

                const result = await response.json();
                processedDocuments[result.document_id] = result;
                updatePipelineUI("Proposal Generated Successfully!", "Master template populated and ready", "generate");

            } else {
                // Multi-PDF upload
                selectedFiles.forEach(f => formData.append('files', f));
                updatePipelineUI("Processing Multiple Documents...", "Running isolated OCR pipelines per document", "ocr");

                const response = await fetch('/api/analyze-multiple', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'Batch analysis request failed');
                }

                const batchResult = await response.json();
                batchResult.documents.forEach(doc => {
                    processedDocuments[doc.document_id] = doc;
                });
                updatePipelineUI("Batch Completed Successfully!", "All proposals generated with document isolation", "generate");
            }

            // Hide upload box, show results
            setTimeout(() => {
                pipelineBox.style.display = 'none';
                document.getElementById('uploadCard').style.display = 'none';
                resultsContainer.style.display = 'flex';
                renderProposalCards();
            }, 800);

        } catch (err) {
            alert(`Analysis Error: ${err.message}`);
            pipelineBox.style.display = 'none';
            startAnalyzeBtn.disabled = false;
        }
    });

    newAnalysisBtn.addEventListener('click', () => {
        selectedFiles = [];
        renderSelectedFilesTable();
        startAnalyzeBtn.disabled = false;
        document.getElementById('uploadCard').style.display = 'block';
        resultsContainer.style.display = 'none';
    });

    // =========================================================================
    // Render Output Proposal Cards (Multi-Document Isolation)
    // =========================================================================
    function renderProposalCards() {
        proposalCardsList.innerHTML = '';
        const docIds = Object.keys(processedDocuments);

        if (docIds.length === 0) {
            proposalCardsList.innerHTML = '<p class="text-muted">No proposal generated yet.</p>';
            return;
        }

        docIds.forEach(docId => {
            const item = processedDocuments[docId];
            const data = item.data;

            const card = document.createElement('div');
            card.className = 'proposal-card';
            card.innerHTML = `
                <div class="prop-card-top">
                    <div class="prop-info-block">
                        <span class="prop-filename">📄 ${escapeHtml(item.filename)}</span>
                        <div class="prop-meta-tags">
                            <span>Pages: ${item.pages || 1}</span>
                            <span>•</span>
                            <span>Size: ${item.file_size_mb || 0} MB</span>
                            <span>•</span>
                            <span>Doc ID: ${docId.substring(0, 8)}</span>
                        </div>
                    </div>
                    <span class="badge-proposal-ready">✓ Proposal Generated</span>
                </div>

                <div class="prop-summary-box">
                    <div class="prop-field-item">
                        <span class="prop-field-label">Indenter</span>
                        <span class="prop-field-val">${escapeHtml(data.indenter || 'Not found')}</span>
                    </div>
                    <div class="prop-field-item">
                        <span class="prop-field-label">Indent Ref</span>
                        <span class="prop-field-val">${escapeHtml(data.indent_reference || 'Not found')}</span>
                    </div>
                    <div class="prop-field-item">
                        <span class="prop-field-label">Item Description</span>
                        <span class="prop-field-val"><strong>${escapeHtml(data.item_description || 'Not found')}</strong></span>
                    </div>
                    <div class="prop-field-item">
                        <span class="prop-field-label">Quantity / Tolerance</span>
                        <span class="prop-field-val">${escapeHtml(data.quantity || 'Not found')} (${escapeHtml(data.tolerance || 'N/A')})</span>
                    </div>
                    <div class="prop-field-item">
                        <span class="prop-field-label">Estimated Cost</span>
                        <span class="prop-field-val" style="color: #38bdf8; font-weight: bold;">${escapeHtml(data.estimated_cost || 'Not found')}</span>
                    </div>
                    <div class="prop-field-item">
                        <span class="prop-field-label">Mode of Tender</span>
                        <span class="prop-field-val">${escapeHtml(data.mode_of_tender || 'Not found')}</span>
                    </div>
                </div>

                <div class="prop-actions-row">
                    <button class="btn btn-outline btn-review" data-id="${docId}">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                        Review Extracted Data
                    </button>
                    <button class="btn btn-secondary btn-ocr" data-id="${docId}">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 7 4 4 20 4 20 7"></polyline><line x1="9" y1="20" x2="15" y2="20"></line><line x1="12" y1="4" x2="12" y2="20"></line></svg>
                        View OCR Text
                    </button>
                    <button class="btn btn-outline btn-preview-prop" data-id="${docId}">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                        Preview Proposal
                    </button>
                    <a href="/api/analysis/${docId}/download/docx" class="btn btn-action" download>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Download DOCX
                    </a>
                    <a href="/api/analysis/${docId}/download/pdf" class="btn btn-pdf" download>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="12" y1="18" x2="12" y2="12"></line><polyline points="9 15 12 12 15 15"></polyline></svg>
                        Download PDF
                    </a>
                </div>
            `;
            proposalCardsList.appendChild(card);
        });

        // Attach action handlers
        document.querySelectorAll('.btn-review').forEach(b => {
            b.addEventListener('click', (e) => openReviewModalHandler(b.getAttribute('data-id')));
        });
        document.querySelectorAll('.btn-ocr').forEach(b => {
            b.addEventListener('click', (e) => openOcrModalHandler(b.getAttribute('data-id')));
        });
        document.querySelectorAll('.btn-preview-prop').forEach(b => {
            b.addEventListener('click', (e) => openPreviewModalHandler(b.getAttribute('data-id')));
        });
    }

    // =========================================================================
    // Review Modal Implementation
    // =========================================================================
    function openReviewModalHandler(docId) {
        currentReviewDocId = docId;
        const item = processedDocuments[docId];
        const data = item.data;

        reviewDocMeta.textContent = `File Name: ${item.filename} | Pages: ${item.pages || 1} | OCR Status: Completed`;
        reviewFieldsTbody.innerHTML = '';

        const fieldsToReview = [
            { key: "initiator_name", label: "Initiator Name" },
            { key: "initiator_pno", label: "Initiator PNo" },
            { key: "initiator_designation", label: "Designation" },
            { key: "department", label: "Department" },
            { key: "reference", label: "Reference" },
            { key: "date", label: "Date" },
            { key: "subject", label: "Subject" },
            { key: "indenter", label: "i) Indenter" },
            { key: "indent_reference", label: "ii) Indent Ref No" },
            { key: "indent_date", label: "ii) Indent Date" },
            { key: "item_description", label: "iii) Item Description" },
            { key: "quantity", label: "iv) Quantity" },
            { key: "tolerance", label: "iv) Tolerance" },
            { key: "estimated_cost", label: "v) Estimated Cost" },
            { key: "delivery_period", label: "vi) Delivery Period" },
            { key: "emd", label: "vii) EMD" },
            { key: "distribution_of_order", label: "viii) Distribution of Order" },
            { key: "security_deposit", label: "ix) Security Deposit" },
            { key: "price_discovery", label: "x) Price Discovery" },
            { key: "price_discovery_quantity", label: "xi) Quantity for Each Price Discovery" },
            { key: "mode_of_tender", label: "xii) Mode of Tender" },
            { key: "approving_authority", label: "xiii) Approving Authority" }
        ];

        fieldsToReview.forEach(f => {
            const tr = document.createElement('tr');
            const val = data[f.key] || '';
            tr.innerHTML = `
                <td><strong>${escapeHtml(f.label)}</strong></td>
                <td>
                    <input type="text" class="review-input" data-key="${f.key}" value="${escapeHtml(val)}">
                </td>
            `;
            reviewFieldsTbody.appendChild(tr);
        });

        reviewModal.style.display = 'flex';
    }

    closeReviewModal.addEventListener('click', () => reviewModal.style.display = 'none');
    cancelReviewBtn.addEventListener('click', () => reviewModal.style.display = 'none');

    saveReviewBtn.addEventListener('click', async () => {
        if (!currentReviewDocId) return;

        saveReviewBtn.disabled = true;
        saveReviewBtn.textContent = 'Updating...';

        const updatedData = {};
        document.querySelectorAll('.review-input').forEach(input => {
            const k = input.getAttribute('data-key');
            updatedData[k] = input.value.trim();
        });

        try {
            const res = await fetch(`/api/analysis/${currentReviewDocId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updatedData)
            });

            if (!res.ok) throw new Error("Failed to update proposal");

            const updatedRes = await res.json();
            processedDocuments[currentReviewDocId].data = updatedRes.data;

            alert("Proposal updated with user-confirmed values.");
            reviewModal.style.display = 'none';
            renderProposalCards();
        } catch (err) {
            alert(`Save error: ${err.message}`);
        } finally {
            saveReviewBtn.disabled = false;
            saveReviewBtn.textContent = 'Confirm & Update Proposal';
        }
    });

    // =========================================================================
    // OCR Text Modal Implementation
    // =========================================================================
    async function openOcrModalHandler(docId) {
        currentOcrDocId = docId;
        const item = processedDocuments[docId];

        ocrDocMeta.textContent = `File Name: ${item.filename} | Total Pages: ${item.pages || 1}`;
        ocrPagesContainer.innerHTML = '<p class="text-muted">Loading OCR pages...</p>';
        ocrModal.style.display = 'flex';

        try {
            const res = await fetch(`/api/analysis/${docId}/ocr`);
            const data = await res.json();

            ocrPagesContainer.innerHTML = '';
            if (!data.pages || data.pages.length === 0) {
                ocrPagesContainer.innerHTML = '<p class="text-muted">No OCR text available for this document.</p>';
                return;
            }

            data.pages.forEach(p => {
                const pBox = document.createElement('div');
                pBox.className = 'ocr-page-block';
                pBox.innerHTML = `
                    <div class="ocr-page-title">Page ${p.page} (${(p.type || 'OCR').toUpperCase()}) — ${p.char_count || (p.text || '').length} characters</div>
                    <pre class="ocr-pre">${escapeHtml(p.text || '[Empty or Unreadable]')}</pre>
                `;
                ocrPagesContainer.appendChild(pBox);
            });
        } catch (err) {
            ocrPagesContainer.innerHTML = `<p class="text-danger">Failed to load OCR text: ${err.message}</p>`;
        }
    }

    closeOcrModal.addEventListener('click', () => ocrModal.style.display = 'none');
    closeOcrBtn.addEventListener('click', () => ocrModal.style.display = 'none');

    copyOcrBtn.addEventListener('click', () => {
        const pres = document.querySelectorAll('.ocr-pre');
        let fullText = '';
        pres.forEach(p => fullText += p.textContent + '\n\n');
        navigator.clipboard.writeText(fullText).then(() => {
            copyOcrBtn.textContent = '✓ Copied!';
            setTimeout(() => copyOcrBtn.textContent = 'Copy All OCR Text', 1800);
        });
    });

    ocrSearchInput.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase();
        document.querySelectorAll('.ocr-page-block').forEach(blk => {
            const txt = blk.textContent.toLowerCase();
            blk.style.display = txt.includes(q) ? 'block' : 'none';
        });
    });

    // =========================================================================
    // Proposal Preview Modal Implementation
    // =========================================================================
    function openPreviewModalHandler(docId) {
        currentPreviewDocId = docId;
        const item = processedDocuments[docId];
        const data = item.data;

        previewDownloadDocxBtn.onclick = () => window.location.href = `/api/analysis/${docId}/download/docx`;
        previewDownloadPdfBtn.onclick = () => window.location.href = `/api/analysis/${docId}/download/pdf`;

        // Render HTML representation strictly matching the Master Template
        previewPaper.innerHTML = `
            <!-- Top SAIL Header -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #003366; padding-bottom: 8px; margin-bottom: 12px;">
                <div style="display: flex; gap: 14px; align-items: center;">
                    <img src="/static/assets/sail_logo_doc.png" style="height: 65px;" alt="SAIL">
                    <div>
                        <h2 style="margin: 0; color: #003366; font-size: 14pt; font-weight: bold;">STEEL AUTHORITY OF INDIA LIMITED</h2>
                        <h3 style="margin: 2px 0 0 0; color: #475569; font-size: 10.5pt; font-weight: bold;">SALEM STEEL PLANT &bull; MATERIALS MANAGEMENT</h3>
                        <p style="margin: 3px 0 0 0; font-size: 8.5pt; color: #334155;">
                            <strong>Plant Code:</strong> ${escapeHtml(data.plant_code || 'SSP')} &nbsp;|&nbsp; <strong>Doc Seq:</strong> ${escapeHtml(data.document_sequence || 'SSP/PUR/PROPOSAL/2025-26')}<br>
                            <strong>Department:</strong> ${escapeHtml(data.department || 'HQ/MM PURCHASE')}<br>
                            <strong>Initiator:</strong> ${escapeHtml(data.initiator_name || 'SARAVANAN S')} (PNo: ${escapeHtml(data.initiator_pno || 'L001558')}, ${escapeHtml(data.initiator_designation || 'SM (MM-PUR)')})
                        </p>
                    </div>
                </div>
                <div style="text-align: right; font-size: 9pt;">
                    <strong>Ref:</strong> ${escapeHtml(data.reference || 'SSP/SLM/MM PURCHASE/GEN/2025/214')}<br>
                    <strong>Date:</strong> ${escapeHtml(data.date || '05-05-2025')}<br><br>
                    <span style="color: #1e40af; font-weight: bold; font-size: 10.5pt;">PURCHASE PROPOSAL NOTE</span><br>
                    <span style="color: #047857; font-weight: bold; font-size: 9pt;">STATUS: CONFIRMED</span>
                </div>
            </div>

            <!-- Subject Box -->
            <div style="background: #f8fafc; border: 1px solid #94a3b8; padding: 6px 10px; margin-bottom: 14px; border-radius: 4px; font-size: 9.5pt;">
                <strong>Subject:</strong> ${escapeHtml(data.subject || 'Enquiry proposal for procurement of materials')}
            </div>

            <!-- Background of Proposal (13 Fields) -->
            <h4 style="color: #003366; margin: 10px 0 4px 0; font-size: 11pt; border-bottom: 1px solid #cbd5e1; padding-bottom: 2px;">Background of the Proposal</h4>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 14px;">
                <tr><td style="width: 35%; font-weight: bold;">i) Indenter</td><td>${escapeHtml(data.indenter || 'Not found in source document')}</td></tr>
                <tr style="background: #f8fafc;"><td style="font-weight: bold;">ii) Indent ref no & date</td><td>${escapeHtml(data.indent_reference || '')} ${data.indent_date ? 'Dated: ' + escapeHtml(data.indent_date) : ''}</td></tr>
                <tr><td style="font-weight: bold;">iii) Description of the item</td><td><strong>${escapeHtml(data.item_description || 'Not found in source document')}</strong></td></tr>
                <tr style="background: #f8fafc;"><td style="font-weight: bold;">iv) Quantity / Tolerance</td><td>${escapeHtml(data.quantity || '')} ${data.tolerance ? '(Tolerance: ' + escapeHtml(data.tolerance) + ')' : ''}</td></tr>
                <tr><td style="font-weight: bold;">v) Estimated Cost</td><td><strong style="color: #003366;">${escapeHtml(data.estimated_cost || 'Not found in source document')}</strong></td></tr>
                <tr style="background: #f8fafc;"><td style="font-weight: bold;">vi) Delivery Period</td><td>${escapeHtml(data.delivery_period || 'Not found in source document')}</td></tr>
                <tr><td style="font-weight: bold;">vii) EMD</td><td>${escapeHtml(data.emd || 'Not found in source document')}</td></tr>
                <tr style="background: #f8fafc;"><td style="font-weight: bold;">viii) Distribution of order</td><td>${escapeHtml(data.distribution_of_order || 'Not found in source document')}</td></tr>
                <tr><td style="font-weight: bold;">ix) Security Deposit</td><td>${escapeHtml(data.security_deposit || 'Not found in source document')}</td></tr>
                <tr style="background: #f8fafc;"><td style="font-weight: bold;">x) Price Discovery</td><td>${escapeHtml(data.price_discovery || 'Not found in source document')}</td></tr>
                <tr><td style="font-weight: bold;">xi) Quantity for each Price Discovery</td><td>${escapeHtml(data.price_discovery_quantity || 'Not found in source document')}</td></tr>
                <tr style="background: #f8fafc;"><td style="font-weight: bold;">xii) Mode of Tender</td><td>${escapeHtml(data.mode_of_tender || 'Not found in source document')}</td></tr>
                <tr><td style="font-weight: bold;">xiii) Approving Authority</td><td>${escapeHtml(data.approving_authority || 'Not found in source document')}</td></tr>
            </table>

            <!-- Proposal Details Clauses -->
            <h4 style="color: #003366; margin: 12px 0 4px 0; font-size: 11pt; border-bottom: 1px solid #cbd5e1; padding-bottom: 2px;">Proposal Details</h4>
            <div style="font-size: 9pt; line-height: 1.45; color: #1e293b;">
                ${(data.proposal_details || []).map(c => `<p style="margin: 4px 0;">${escapeHtml(c).replace(/\n/g, '<br>')}</p>`).join('')}
            </div>

            <!-- Consumption & Stock Tables -->
            <h4 style="color: #003366; margin: 12px 0 4px 0; font-size: 11pt; border-bottom: 1px solid #cbd5e1; padding-bottom: 2px;">Stock and Pending Supplies</h4>
            <table style="width: 100%; border-collapse: collapse; text-align: center; margin-bottom: 14px;">
                <thead>
                    <tr style="background: #f1f5f9; color: #003366;">
                        <th>Stock at site</th>
                        <th>Pending supply</th>
                        <th>Stock & pending supplies</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>2,494 MT</td>
                        <td>281 MT</td>
                        <td><strong>2,775 MT</strong></td>
                    </tr>
                </tbody>
            </table>

            <!-- Approval Sought & DOP -->
            <h4 style="color: #003366; margin: 12px 0 4px 0; font-size: 11pt;">Approval Sought for</h4>
            <p style="font-size: 9pt; margin: 2px 0 8px 0;">${escapeHtml(data.approval_sought || '')}</p>

            <h4 style="color: #003366; margin: 8px 0 4px 0; font-size: 11pt;">DOP / Manual / Circular Ref & Approver</h4>
            <p style="font-size: 9pt; margin: 2px 0 4px 0;">${escapeHtml(data.dop_reference || '')}</p>
            <p style="font-size: 8.5pt; color: #475569; margin: 0 0 10px 0;"><strong>Approver Routing:</strong> ${escapeHtml(data.approver || '')}</p>

            <!-- Attachments & Status -->
            <div style="display: flex; justify-content: space-between; background: #f8fafc; border: 1px solid #94a3b8; padding: 8px 12px; border-radius: 4px; font-size: 8.5pt; margin-top: 12px;">
                <div>
                    <strong>Attached Files:</strong> ${escapeHtml(data.attached_files || '')}<br>
                    <strong>Proposal Status:</strong> <span style="color: #047857; font-weight: bold;">APPROVED</span>
                </div>
                <div style="text-align: right;">
                    <strong>Initiator Signature:</strong><br>
                    <strong>${escapeHtml(data.initiator_name || 'SARAVANAN S')}</strong><br>
                    ${escapeHtml(data.initiator_designation || 'SM (MM-PUR)')} (PNo: ${escapeHtml(data.initiator_pno || 'L001558')})
                </div>
            </div>
        `;

        previewModal.style.display = 'flex';
    }

    closePreviewModal.addEventListener('click', () => previewModal.style.display = 'none');
    closePreviewBtn.addEventListener('click', () => previewModal.style.display = 'none');

    // =========================================================================
    // Dynamic Tabs Data Loading
    // =========================================================================
    async function loadDashboardStats() {
        try {
            const res = await fetch('/api/dashboard-stats');
            const data = await res.json();

            document.getElementById('dashTotalDocs').textContent = data.total_processed;
            document.getElementById('dashSuccessDocs').textContent = data.successful_analyses;
            document.getElementById('dashProposalsGen').textContent = data.proposals_generated;

            const tbody = document.getElementById('dashTableTbody');
            tbody.innerHTML = '';

            if (!data.recent_documents || data.recent_documents.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No documents analyzed yet.</td></tr>';
                return;
            }

            data.recent_documents.forEach(doc => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${escapeHtml(doc.filename)}</strong></td>
                    <td>${doc.date}</td>
                    <td>${doc.pages}</td>
                    <td>${escapeHtml(doc.item_description)}</td>
                    <td>${escapeHtml(doc.estimated_cost)}</td>
                    <td><span class="badge-ready">Completed</span></td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error("Failed to load dashboard stats", e);
        }
    }

    async function loadMaterialTracking() {
        try {
            const res = await fetch('/api/material-tracking');
            const data = await res.json();
            const tbody = document.getElementById('trackingTableTbody');
            tbody.innerHTML = '';

            if (!data.materials || data.materials.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No active tracked materials found.</td></tr>';
                return;
            }

            data.materials.forEach(m => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${escapeHtml(m.item_description)}</strong></td>
                    <td>${escapeHtml(m.indent_reference)}</td>
                    <td>${escapeHtml(m.quantity)}</td>
                    <td>${escapeHtml(m.tolerance)}</td>
                    <td style="color: #38bdf8; font-weight: bold;">${escapeHtml(m.estimated_cost)}</td>
                    <td>${escapeHtml(m.mode_of_tender)}</td>
                    <td><span class="badge-ready">${escapeHtml(m.procurement_status)}</span></td>
                    <td><span class="badge-ready">${escapeHtml(m.proposal_status)}</span></td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error("Failed to load material tracking", e);
        }
    }

    async function loadReports() {
        try {
            const res = await fetch('/api/reports');
            const data = await res.json();
            const tbody = document.getElementById('reportsTableTbody');
            tbody.innerHTML = '';

            if (!data.reports || data.reports.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No proposal reports generated yet.</td></tr>';
                return;
            }

            data.reports.forEach(r => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${escapeHtml(r.filename)}</strong></td>
                    <td>${r.timestamp}</td>
                    <td>${escapeHtml(r.item)}</td>
                    <td>${escapeHtml(r.value)}</td>
                    <td>${escapeHtml(r.tender_mode)}</td>
                    <td>${escapeHtml(r.approver)}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error("Failed to load reports", e);
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
