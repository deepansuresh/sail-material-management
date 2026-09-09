// SAIL Material Management Module - Frontend Script
let currentProposalData = null;

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
    const processingBox = document.getElementById('processingBox');
    const uploadCard = document.getElementById('uploadCard');
    const outputCard = document.getElementById('outputCard');
    const newUploadBtn = document.getElementById('newUploadBtn');
    const downloadDocxBtn = document.getElementById('downloadDocxBtn');
    const printBtn = document.getElementById('printBtn');

    // Select File trigger
    if (selectBtn && fileInput) {
        selectBtn.addEventListener('click', () => fileInput.click());
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
            }
        });
    }

    // Drag & drop
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
                handleFileUpload(files[0]);
            }
        });
    }

    // Sample trigger
    if (sampleBtn) {
        sampleBtn.addEventListener('click', () => {
            loadSampleRequisition();
        });
    }

    // Actions
    if (newUploadBtn) {
        newUploadBtn.addEventListener('click', () => {
            currentProposalData = null;
            if (outputCard) outputCard.style.display = 'none';
            if (uploadCard) uploadCard.style.display = 'flex';
            if (dropZone) dropZone.style.display = 'flex';
            if (processingBox) processingBox.style.display = 'none';
            if (fileInput) fileInput.value = '';
        });
    }

    if (downloadDocxBtn) {
        downloadDocxBtn.addEventListener('click', () => {
            if (!currentProposalData) return;
            downloadWordDocument(currentProposalData);
        });
    }

    if (printBtn) {
        printBtn.addEventListener('click', () => {
            window.print();
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

    xhr.timeout = 180000; // 3 minutes timeout
    xhr.send(formData);
}

function loadSampleRequisition() {
    currentProposalData = null;
    clearUploadError();
    showProcessing('Analyzing Sample SAIL Purchase Requisition...');
    updateSidebarActivity('sample_indent.pdf (SAIL Indent)');

    const progressBar = document.getElementById('progressBar');
    if (progressBar) progressBar.style.width = '50%';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/load-sample', true);

    xhr.onload = () => {
        if (xhr.status === 200) {
            try {
                const data = JSON.parse(xhr.responseText);
                if (progressBar) progressBar.style.width = '100%';
                renderProposal(data);
            } catch (err) {
                console.error('[Client Error] Error rendering sample:', err);
                showUploadError('Failed to display sample data: ' + err.message);
            }
        } else {
            let detail = 'Server returned status ' + xhr.status;
            try {
                const errJson = JSON.parse(xhr.responseText);
                if (errJson.detail) detail = errJson.detail;
            } catch (e) {}
            showUploadError('Error loading sample: ' + detail);
        }
    };

    xhr.onerror = () => {
        showUploadError('Network error loading sample requisition.');
    };

    xhr.timeout = 90000;
    xhr.send();
}

function showProcessing(statusText) {
    const dropZone = document.getElementById('dropZone');
    if (dropZone) dropZone.style.display = 'none';

    const processingBox = document.getElementById('processingBox');
    if (processingBox) processingBox.style.display = 'flex';

    safeSetText('processStatus', statusText);
}

function resetUploadUI() {
    const dropZone = document.getElementById('dropZone');
    if (dropZone) dropZone.style.display = 'flex';

    const processingBox = document.getElementById('processingBox');
    if (processingBox) processingBox.style.display = 'none';
}

function updateSidebarActivity(filename) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    safeSetText('recentUploadText', `${filename} (${timeStr})`);
    safeSetText('reportGeneratedText', 'Processing document...');
}

function showUploadError(errorMessage) {
    resetUploadUI();

    let errorBanner = document.getElementById('uploadErrorBanner');
    if (!errorBanner) {
        errorBanner = document.createElement('div');
        errorBanner.id = 'uploadErrorBanner';
        errorBanner.style.cssText = 'background:#FEF2F2;border:1px solid #F87171;color:#991B1B;padding:12px 16px;border-radius:8px;margin:16px 0;width:100%;font-size:14px;display:flex;align-items:center;gap:10px;line-height:1.4;';
        const dropZone = document.getElementById('dropZone');
        if (dropZone && dropZone.parentNode) {
            dropZone.parentNode.insertBefore(errorBanner, dropZone);
        }
    }
    if (errorBanner) {
        errorBanner.innerHTML = `<strong>Analysis Error:</strong> <span>${escapeHtml(errorMessage)}</span>`;
        errorBanner.style.display = 'flex';
    }

    safeSetText('reportGeneratedText', 'Analysis Failed');
}

function clearUploadError() {
    const errorBanner = document.getElementById('uploadErrorBanner');
    if (errorBanner) {
        errorBanner.style.display = 'none';
        errorBanner.innerHTML = '';
    }
}

function renderProposal(data) {
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
            // Clean leading numbers if duplicate
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

    // Approval Section (supports both new val* and legacy block* IDs)
    safeSetText('valApprovalSought', data.approval_sought_for || '', ['blockApprovalSought']);
    safeSetText('valApprovingDop', data.approving_authority_dop || '', ['blockApprovingDop']);
    safeSetText('valApprovalPath', data.suggested_approval_path || '', ['blockApprovalPath']);

    // Update Sidebar
    safeSetText('reportGeneratedText', 'Proposal Note Ready');

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
            : 'Proposal';
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
