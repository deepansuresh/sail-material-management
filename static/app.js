// SAIL Material Management Module - Frontend Script
let currentProposalData = null;
let selectedFile = null;

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
        console.warn(`[DOM] Element with id '${id}' not found in current DOM.`);
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
        console.warn(`[DOM] Element with id '${id}' not found in current DOM.`);
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
    const changeFileBtn = document.getElementById('changeFileBtn');
    const selectedFileBox = document.getElementById('selectedFileBox');
    const selectedFileName = document.getElementById('selectedFileName');
    const selectedFileSize = document.getElementById('selectedFileSize');
    const uploadBtnGroup = document.getElementById('uploadBtnGroup');
    const dropHint = document.getElementById('dropHint');
    const processingBox = document.getElementById('processingBox');
    const uploadCard = document.getElementById('uploadCard');
    const outputCard = document.getElementById('outputCard');
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
                e.target.closest('#changeFileBtn') ||
                e.target.closest('#selectedFileBox')) {
                return;
            }
            fileInput.click();
        });
    }

    // 3. File Input change handler
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                onFileChosen(e.target.files[0]);
            }
        });
    }

    // Helper: when a file is selected (via picker or drag-and-drop)
    function onFileChosen(file) {
        if (!file || !file.name) return;

        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showUploadError('Please select a valid PDF document.');
            return;
        }

        if (file.size > 30 * 1024 * 1024) {
            showUploadError('File size exceeds maximum limit of 30 MB.');
            return;
        }

        clearUploadError();
        selectedFile = file;

        // Display selected file info & Analyze button
        if (selectedFileName) selectedFileName.innerText = file.name;
        if (selectedFileSize) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            selectedFileSize.innerText = `(${sizeMB} MB)`;
        }

        if (selectedFileBox) selectedFileBox.style.display = 'flex';
        if (uploadBtnGroup) uploadBtnGroup.style.display = 'none';
        if (dropHint) dropHint.style.display = 'none';
    }

    // 4. Analyze button trigger
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (selectedFile) {
                handleFileUpload(selectedFile);
            } else if (fileInput && fileInput.files && fileInput.files[0]) {
                handleFileUpload(fileInput.files[0]);
            } else {
                fileInput.click();
            }
        });
    }

    // 5. Change File button trigger
    if (changeFileBtn && fileInput) {
        changeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            selectedFile = null;
            fileInput.value = '';
            if (selectedFileBox) selectedFileBox.style.display = 'none';
            if (uploadBtnGroup) uploadBtnGroup.style.display = 'flex';
            if (dropHint) dropHint.style.display = 'block';
            fileInput.click();
        });
    }

    // 6. Drag & drop handlers
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
            if (files && files[0]) {
                onFileChosen(files[0]);
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
            selectedFile = null;
            if (outputCard) outputCard.style.display = 'none';
            if (uploadCard) uploadCard.style.display = 'flex';
            if (dropZone) dropZone.style.display = 'flex';
            if (processingBox) processingBox.style.display = 'none';
            if (selectedFileBox) selectedFileBox.style.display = 'none';
            if (uploadBtnGroup) uploadBtnGroup.style.display = 'flex';
            if (dropHint) dropHint.style.display = 'block';
            if (fileInput) fileInput.value = '';
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

function handleFileUpload(file) {
    if (!file || !file.name) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showUploadError('Please select a valid PDF document.');
        return;
    }

    if (file.size > 30 * 1024 * 1024) {
        showUploadError('File size exceeds maximum limit of 30 MB.');
        return;
    }

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
