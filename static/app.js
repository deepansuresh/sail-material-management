// SAIL Material Management Module - Frontend Script
let currentProposalData = null;
let selectedFiles = [];
let analyzedDocuments = [];
let activeDocIndex = 0;

// Safe DOM text setter: sets innerText only if element exists; supports fallback IDs
function safeSetText(id, value, fallbackIds = []) {
    let el = document.getElementById(id);
    if (!el && fallbackIds && fallbackIds.length) {
        for (const fbId of fallbackIds) {
            el = document.getElementById(fbId);
            if (el) break;
        }
    }
    if (el) {
        el.innerText = (value !== undefined && value !== null) ? String(value) : '';
        return el;
    } else {
        return null;
    }
}

// Safe DOM HTML setter: sets innerHTML only if element exists; supports fallback IDs
function safeSetHtml(id, htmlContent, fallbackIds = []) {
    let el = document.getElementById(id);
    if (!el && fallbackIds && fallbackIds.length) {
        for (const fbId of fallbackIds) {
            el = document.getElementById(fbId);
            if (el) break;
        }
    }
    if (el) {
        el.innerHTML = (htmlContent !== undefined && htmlContent !== null) ? String(htmlContent) : '';
        return el;
    } else {
        return null;
    }
}

// HTML escape helper to prevent injection in dynamic table rows
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const selectBtn = document.getElementById('selectBtn');
    const sampleBtn = document.getElementById('sampleBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const clearFilesBtn = document.getElementById('clearFilesBtn');
    const newUploadBtn = document.getElementById('newUploadBtn');
    const downloadDocxBtn = document.getElementById('downloadDocxBtn');
    const printBtn = document.getElementById('printBtn');

    // 1. Select File button trigger
    if (selectBtn && fileInput) {
        selectBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
        selectBtn.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInput.click();
            }
        });
    }

    // 2. Drop zone click delegation (clicking empty drop area opens file picker)
    if (dropZone && fileInput) {
        dropZone.addEventListener('click', (e) => {
            if (e.target.closest('#sampleBtn') || 
                e.target.closest('#selectBtn') || 
                e.target.closest('#analyzeBtn') || 
                e.target.closest('#clearFilesBtn') ||
                e.target.closest('#addMoreBtn') ||
                e.target.closest('.btn-remove-file') ||
                e.target.closest('#selectedFileBox')) {
                return;
            }
            fileInput.click();
        });
    }

    // 3. File Input change handler (supports multiple files)
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                onFilesChosen(e.target.files);
            }
        });
    }

    // 4. Analyze button trigger
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (selectedFiles.length === 1) {
                handleFileUpload(selectedFiles[0]);
            } else if (selectedFiles.length > 1) {
                handleMultipleFileUpload(selectedFiles);
            } else if (fileInput && fileInput.files && fileInput.files.length > 0) {
                onFilesChosen(fileInput.files);
                if (selectedFiles.length === 1) {
                    handleFileUpload(selectedFiles[0]);
                } else if (selectedFiles.length > 1) {
                    handleMultipleFileUpload(selectedFiles);
                }
            } else {
                fileInput.click();
            }
        });
    }

    // 5. Clear button trigger
    if (clearFilesBtn) {
        clearFilesBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            selectedFiles = [];
            if (fileInput) fileInput.value = '';
            updateSelectedFilesUI();
            clearUploadError();
        });
    }

    // 6. Drag & drop handlers (supports multiple files)
    if (dropZone) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt ? dt.files : null;
            if (files && files.length > 0) {
                onFilesChosen(files);
            }
        });
    }

    // 7. Sample trigger
    if (sampleBtn) {
        sampleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            loadSampleRequisition();
        });
    }

    // 8. New Upload button
    if (newUploadBtn) {
        newUploadBtn.addEventListener('click', () => {
            currentProposalData = null;
            selectedFiles = [];
            analyzedDocuments = [];
            activeDocIndex = 0;

            const uploadCard = document.getElementById('uploadCard');
            const outputCard = document.getElementById('outputCard');
            const processingBox = document.getElementById('processingBox');
            const docSwitcherBar = document.getElementById('docSwitcherBar');

            if (outputCard) outputCard.style.display = 'none';
            if (uploadCard) uploadCard.style.display = 'flex';
            if (dropZone) dropZone.style.display = 'flex';
            if (processingBox) processingBox.style.display = 'none';
            if (docSwitcherBar) docSwitcherBar.style.display = 'none';
            if (fileInput) fileInput.value = '';

            updateSelectedFilesUI();
            clearUploadError();
        });
    }

    // 9. Download Word document
    if (downloadDocxBtn) {
        downloadDocxBtn.addEventListener('click', () => {
            if (!currentProposalData) return;
            downloadWordDocument(currentProposalData);
        });
    }

    // 10. Print / PDF action
    if (printBtn) {
        printBtn.addEventListener('click', () => {
            window.print();
        });
    }

    // 11. Navigation bar tab switching
    const navItems = document.querySelectorAll('.nav-item');
    if (navItems && navItems.length) {
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                navItems.forEach(n => n.classList.remove('active'));
                item.classList.add('active');
            });
        });
    }
});

// Helper: Handles file selection via file picker or drag & drop
function onFilesChosen(fileList) {
    if (!fileList || fileList.length === 0) return;

    let rejectedFiles = [];
    for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i];
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            rejectedFiles.push(`${file.name} (Not a PDF)`);
            continue;
        }
        if (file.size > 30 * 1024 * 1024) {
            rejectedFiles.push(`${file.name} (Exceeds 30 MB)`);
            continue;
        }
        const exists = selectedFiles.some(f => f.name === file.name && f.size === file.size);
        if (!exists) {
            selectedFiles.push(file);
        }
    }

    if (rejectedFiles.length > 0) {
        showUploadError(`Some files could not be added: ${rejectedFiles.join(', ')}`);
    } else {
        clearUploadError();
    }

    updateSelectedFilesUI();
}

// Helper: Updates the selected files list in the upload box
function updateSelectedFilesUI() {
    const selectedFileBox = document.getElementById('selectedFileBox');
    const selectedFileList = document.getElementById('selectedFileList');
    const uploadBtnGroup = document.getElementById('uploadBtnGroup');
    const dropHint = document.getElementById('dropHint');
    const selectedFilesCount = document.getElementById('selectedFilesCount');
    const selectedFilesTotalSize = document.getElementById('selectedFilesTotalSize');
    const analyzeBtnText = document.getElementById('analyzeBtnText');

    if (!selectedFileBox) return;

    if (selectedFiles.length === 0) {
        selectedFileBox.style.display = 'none';
        if (uploadBtnGroup) uploadBtnGroup.style.display = 'flex';
        if (dropHint) dropHint.style.display = 'block';
        return;
    }

    if (uploadBtnGroup) uploadBtnGroup.style.display = 'none';
    if (dropHint) dropHint.style.display = 'none';
    selectedFileBox.style.display = 'flex';

    let totalBytes = selectedFiles.reduce((acc, f) => acc + f.size, 0);
    const totalMB = (totalBytes / (1024 * 1024)).toFixed(2);

    if (selectedFilesCount) {
        selectedFilesCount.innerText = selectedFiles.length === 1 ? '1 file selected' : `${selectedFiles.length} files selected`;
    }
    if (selectedFilesTotalSize) {
        selectedFilesTotalSize.innerText = `(${totalMB} MB total)`;
    }
    if (analyzeBtnText) {
        analyzeBtnText.innerText = selectedFiles.length === 1 ? 'Analyze Proposal' : `Analyze All (${selectedFiles.length} Files)`;
    }

    if (selectedFileList) {
        selectedFileList.innerHTML = '';
        selectedFiles.forEach((f, idx) => {
            const fSizeMB = (f.size / (1024 * 1024)).toFixed(2);
            const item = document.createElement('div');
            item.className = 'selected-file-item';
            item.innerHTML = `
                <div class="file-item-left">
                    <div class="file-icon-badge">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                    </div>
                    <div class="file-details">
                        <div class="file-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</div>
                        <div class="file-size">${fSizeMB} MB</div>
                    </div>
                </div>
                <button type="button" class="btn-remove-file" data-index="${idx}" title="Remove this file">&times;</button>
            `;

            const removeBtn = item.querySelector('.btn-remove-file');
            if (removeBtn) {
                removeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    removeSelectedFile(idx);
                });
            }
            selectedFileList.appendChild(item);
        });
    }
}

function removeSelectedFile(index) {
    if (index >= 0 && index < selectedFiles.length) {
        selectedFiles.splice(index, 1);
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
        updateSelectedFilesUI();
    }
}

function uploadAndAnalyzeSingleFile(file) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/analyze', true);
        xhr.timeout = 180000;

        xhr.onload = () => {
            if (xhr.status === 200) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    resolve(data);
                } catch (e) {
                    reject(new Error('Invalid JSON response: ' + e.message));
                }
            } else {
                let msg = 'Server returned status ' + xhr.status;
                try {
                    const err = JSON.parse(xhr.responseText);
                    if (err.detail) msg = err.detail;
                } catch (_) {}
                reject(new Error(msg));
            }
        };

        xhr.onerror = () => reject(new Error('Network error during upload.'));
        xhr.ontimeout = () => reject(new Error('Request timed out after 3 minutes.'));

        xhr.send(formData);
    });
}

function handleFileUpload(file) {
    if (!file || !file.name) return;

    currentProposalData = null;
    clearUploadError();
    showProcessing('Preparing upload for ' + file.name + '...');
    updateSidebarActivity(file.name);

    const formData = new FormData();
    formData.append('file', file);

    const progressBar = document.getElementById('progressBar');
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/analyze', true);

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            const loadedMB = (e.loaded / (1024 * 1024)).toFixed(1);
            const totalMB = (e.total / (1024 * 1024)).toFixed(1);
            if (progressBar) progressBar.style.width = `${Math.min(percent, 90)}%`;
            if (percent < 100) {
                safeSetText('processStatus', `Uploading Document: ${percent}% (${loadedMB} MB / ${totalMB} MB)...`);
            } else {
                safeSetText('processStatus', 'Upload received. Extracting text & running OCR analysis...');
                if (progressBar) progressBar.style.width = '95%';
            }
        }
    };

    xhr.onload = () => {
        if (xhr.status === 200) {
            try {
                const data = JSON.parse(xhr.responseText);
                if (progressBar) progressBar.style.width = '100%';
                analyzedDocuments = [{ filename: file.name, data: data }];
                activeDocIndex = 0;
                const docSwitcherBar = document.getElementById('docSwitcherBar');
                if (docSwitcherBar) docSwitcherBar.style.display = 'none';
                renderProposal(data);
            } catch (err) {
                console.error('[Client Error] Error rendering proposal:', err);
                showUploadError('Failed to display document: ' + err.message);
            }
        } else {
            let detail = 'Server returned status ' + xhr.status;
            try {
                const errJson = JSON.parse(xhr.responseText);
                if (errJson.detail) detail = errJson.detail;
            } catch (e) {}
            console.error('[Server Error]', xhr.status, detail);
            showUploadError(detail);
        }
    };

    xhr.onerror = () => {
        console.error('[Network Error] XHR network connection error.');
        showUploadError('Network connection error while uploading to server. Please check your connection.');
    };

    xhr.ontimeout = () => {
        console.error('[Timeout Error] XHR request timed out.');
        showUploadError('Analysis request timed out after 3 minutes. Please try again.');
    };

    xhr.timeout = 180000;
    xhr.send(formData);
}

async function handleMultipleFileUpload(files) {
    if (!files || files.length === 0) return;

    currentProposalData = null;
    analyzedDocuments = [];
    clearUploadError();
    showProcessing(`Preparing to process ${files.length} documents...`);

    const progressBar = document.getElementById('progressBar');
    let failedFiles = [];

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileNum = i + 1;
        safeSetText('processStatus', `Analyzing file ${fileNum} of ${files.length}: ${file.name}...`);
        updateSidebarActivity(`${file.name} (${fileNum}/${files.length})`);
        
        const pct = Math.round((i / files.length) * 90) + 5;
        if (progressBar) progressBar.style.width = `${pct}%`;

        try {
            const data = await uploadAndAnalyzeSingleFile(file);
            analyzedDocuments.push({ filename: file.name, data: data });
        } catch (err) {
            console.error(`Error processing ${file.name}:`, err);
            failedFiles.push({ filename: file.name, error: err.message });
        }
    }

    if (progressBar) progressBar.style.width = '100%';

    if (analyzedDocuments.length === 0) {
        showUploadError(`All files failed to process. Errors: ${failedFiles.map(f => f.filename + ': ' + f.error).join('; ')}`);
        return;
    }

    renderMultipleProposals(analyzedDocuments, failedFiles);
}

function renderMultipleProposals(docs, failedFiles = []) {
    const docSwitcherBar = document.getElementById('docSwitcherBar');
    const docSwitcherTabs = document.getElementById('docSwitcherTabs');

    if (docs.length > 1) {
        if (docSwitcherBar) docSwitcherBar.style.display = 'flex';
        if (docSwitcherTabs) {
            docSwitcherTabs.innerHTML = '';
            docs.forEach((doc, idx) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'doc-tab' + (idx === 0 ? ' active' : '');
                btn.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    </svg>
                    <span>${escapeHtml(doc.filename)}</span>
                `;
                btn.addEventListener('click', () => switchActiveDocument(idx));
                docSwitcherTabs.appendChild(btn);
            });
        }
    } else {
        if (docSwitcherBar) docSwitcherBar.style.display = 'none';
    }

    activeDocIndex = 0;
    renderProposal(docs[0].data);
    updateSidebarActivity(docs[0].filename);

    if (failedFiles.length > 0) {
        const warnMsg = `Note: ${failedFiles.length} file(s) could not be parsed (${failedFiles.map(f => f.filename).join(', ')}). Displaying ${docs.length} successful proposal(s).`;
        showUploadError(warnMsg);
    }
}

function switchActiveDocument(index) {
    if (index < 0 || index >= analyzedDocuments.length) return;
    activeDocIndex = index;

    const tabs = document.querySelectorAll('.doc-tab');
    tabs.forEach((t, i) => {
        if (i === index) {
            t.classList.add('active');
        } else {
            t.classList.remove('active');
        }
    });

    const targetDoc = analyzedDocuments[index];
    renderProposal(targetDoc.data);
    updateSidebarActivity(targetDoc.filename);
}

function loadSampleRequisition() {
    currentProposalData = null;
    clearUploadError();
    showProcessing('Analyzing Sample SAIL Purchase Requisition...');
    updateSidebarActivity('sample_indent.pdf (SAIL Indent)');

    const progressBar = document.getElementById('progressBar');
    if (progressBar) progressBar.style.width = '50%';

    fetch('/api/load-sample', {
        headers: { 'ngrok-skip-browser-warning': 'true' }
    })
    .then(res => {
        if (!res.ok) throw new Error('Failed to load sample: ' + res.status);
        return res.json();
    })
    .then(data => {
        if (progressBar) progressBar.style.width = '100%';
        analyzedDocuments = [{ filename: 'sample_indent.pdf', data: data }];
        activeDocIndex = 0;
        const docSwitcherBar = document.getElementById('docSwitcherBar');
        if (docSwitcherBar) docSwitcherBar.style.display = 'none';
        renderProposal(data);
    })
    .catch(err => {
        console.error(err);
        showUploadError('Could not analyze sample requisition: ' + err.message);
    });
}

function showProcessing(statusText) {
    const dropZone = document.getElementById('dropZone');
    const processingBox = document.getElementById('processingBox');
    const processStatus = document.getElementById('processStatus');
    const progressBar = document.getElementById('progressBar');

    if (dropZone) dropZone.style.display = 'none';
    if (processingBox) processingBox.style.display = 'flex';
    if (processStatus) processStatus.innerText = statusText || 'Processing...';
    if (progressBar) progressBar.style.width = '10%';
}

function updateSidebarActivity(docName) {
    const docTimeEl = document.getElementById('docTime');
    const docNameEl = document.getElementById('docName');
    const docStatusEl = document.getElementById('docStatus');

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (docTimeEl) docTimeEl.innerText = timeStr;
    if (docNameEl) docNameEl.innerText = docName;
    if (docStatusEl) {
        docStatusEl.innerText = 'Analyzing';
        docStatusEl.className = 'activity-subtitle status-analyzing';
    }
}

function showUploadError(message) {
    const dropZone = document.getElementById('dropZone');
    const processingBox = document.getElementById('processingBox');
    if (processingBox) processingBox.style.display = 'none';
    if (dropZone) dropZone.style.display = 'flex';

    let errorBanner = document.getElementById('uploadErrorBanner');
    if (!errorBanner) {
        errorBanner = document.createElement('div');
        errorBanner.id = 'uploadErrorBanner';
        errorBanner.className = 'error-banner';
        const uploadCard = document.getElementById('uploadCard');
        if (uploadCard) uploadCard.insertBefore(errorBanner, uploadCard.firstChild);
    }
    if (errorBanner) {
        errorBanner.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>${escapeHtml(message)}</span>
        `;
        errorBanner.style.display = 'flex';
    }
}

function clearUploadError() {
    const errorBanner = document.getElementById('uploadErrorBanner');
    if (errorBanner) {
        errorBanner.style.display = 'none';
        errorBanner.innerHTML = '';
    }
}

function renderProposal(data) {
    if (data && data.data && typeof data.data === 'object' && !data.indent_particulars) {
        data = data.data;
    }

    if (!data || typeof data !== 'object') {
        console.error('[Render] Invalid data passed to renderProposal:', data);
        showUploadError('Invalid response received from server.');
        return;
    }

    currentProposalData = data;

    // Item Header
    safeSetText('docItemDesc', `Description of the item: ${data.item_description || ''}`);

    // Indent Particulars
    const ind = data.indent_particulars || {};
    safeSetText('valPRNo', ind.purchase_requisition_no || '');
    safeSetText('valIndentRefNo', ind.indent_reference_no || '');
    safeSetText('valIndentDate', ind.indent_date || '');
    safeSetText('valProposalDate', ind.proposal_date || '');
    safeSetText('valIndentRaisedBy', ind.indent_raised_by || '');
    safeSetText('valEstimate', ind.estimate || '');
    safeSetText('valBasisEstimate', ind.basis_of_estimate || '');
    safeSetText('valFirstTime', ind.first_time_procurement || '');
    safeSetText('valBudgetaryOffers', ind.budgetary_offers_count || '');

    // Previous Purchase Details
    const prev = data.previous_purchase_details || {};
    const prevBody = document.getElementById('prevTableBody');
    if (prevBody) {
        prevBody.innerHTML = '';
        (prev.items || []).forEach(itm => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${escapeHtml(itm.item_sl_no || '')}</td>
                <td>${escapeHtml(itm.at_ref_no || '')}</td>
                <td>${escapeHtml(itm.prev_qty || '')}</td>
                <td class="font-semibold">${escapeHtml(itm.unit_rate_incl_gst || '')}</td>
            `;
            prevBody.appendChild(tr);
        });
    }
    safeSetText('valPrevMode', prev.prev_mode_of_tender || '');

    // Indent Approval
    const ia = data.indent_approval || {};
    safeSetText('valApprovingAuth', ia.approving_authority || '');
    safeSetText('valApprovedDate', ia.indent_approved_date || '');
    safeSetText('valModeTender', ia.mode_of_tender || '');

    // Sanction Particulars
    const sp = data.sanction_particulars || {};
    safeSetText('valSupplierName', sp.supplier_name || '');
    safeSetText('valOrderValue', sp.order_value_incl_gst || '');
    safeSetText('valDevWrtEstimate', sp.deviation_wrt_estimate || '');

    // Negotiation Details
    const neg = data.negotiation_details || {};
    const negHeader = document.getElementById('negTableHeader');
    if (negHeader && neg.headers && neg.headers.length) {
        negHeader.innerHTML = neg.headers.map(h => `<th>${escapeHtml(h)}</th>`).join('');
    }
    const negBody = document.getElementById('negTableBody');
    if (negBody) {
        negBody.innerHTML = '';
        (neg.rows || []).forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="font-semibold">${escapeHtml(r[0] || '')}</td>
                <td>${escapeHtml(r[1] || '')}</td>
                <td>${escapeHtml(r[2] || '')}</td>
            `;
            negBody.appendChild(tr);
        });
    }

    // Narrative Clauses
    const narrativeList = document.getElementById('narrativeList');
    if (narrativeList) {
        narrativeList.innerHTML = '';
        (data.narrative_clauses || []).forEach(clause => {
            const li = document.createElement('li');
            li.innerText = String(clause || '').replace(/^\d+\.\s*/, '');
            narrativeList.appendChild(li);
        });
    }

    // Proposed Order Terms
    const pot = data.proposed_order_terms || {};
    safeSetText('termSupplier', pot.supplier_name || '');
    safeSetText('termItem', pot.item_description || '');
    safeSetText('termValNoGST', pot.total_order_value_without_gst || '');
    safeSetText('termValWithGST', pot.total_order_value_with_gst || '');
    safeSetText('termEstimate', pot.estimate || '');
    safeSetText('termDev', pot.percent_dev_wrt_estimate || '');

    const ct = pot.commercial_terms || {};
    safeSetText('termDelivery', ct.terms_of_delivery || '');
    safeSetText('termSchedule', ct.delivery_schedule || '');
    safeSetText('termPayment', ct.payment_terms || '');
    safeSetText('termValidity', ct.offer_validity || '');

    // Approval Section
    safeSetText('valApprovalSought', data.approval_sought_for || '', ['blockApprovalSought']);
    safeSetText('valApprovingDop', data.approving_authority_dop || '', ['blockApprovingDop']);
    safeSetText('valApprovalPath', data.suggested_approval_path || '', ['blockApprovalPath']);

    // Update Sidebar
    safeSetText('reportGeneratedText', 'Proposal Note Ready');
    const docStatusEl = document.getElementById('docStatus');
    if (docStatusEl) {
        docStatusEl.innerText = 'Completed';
        docStatusEl.className = 'activity-subtitle status-completed';
    }

    // Show output, hide upload
    const uploadCard = document.getElementById('uploadCard');
    if (uploadCard) uploadCard.style.display = 'none';

    const outputCard = document.getElementById('outputCard');
    if (outputCard) {
        outputCard.style.display = 'block';
        if (typeof outputCard.scrollIntoView === 'function') {
            outputCard.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

function downloadWordDocument(data) {
    if (!data) return;
    fetch('/api/download-docx', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) throw new Error('Download failed with status ' + response.status);
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        let refNo = (data.indent_particulars && data.indent_particulars.purchase_requisition_no) 
            ? data.indent_particulars.purchase_requisition_no.split(' ')[0] 
            : (data.indent_reference || 'Proposal');
        refNo = refNo.replace(/[\\/:*?"<>|]/g, '_');
        a.download = `${refNo}_Purchase_Proposal_Note.docx`;
        if (document.body) {
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            a.click();
        }
        window.URL.revokeObjectURL(url);
    })
    .catch(err => {
        console.error(err);
        alert('Could not download Word document: ' + err.message);
    });
}
