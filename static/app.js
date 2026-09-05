// SAIL Material Management Module - Frontend Script
let currentProposalData = null;

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
    selectBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Drag & drop
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
        const files = dt.files;
        if (files && files[0]) {
            handleFileUpload(files[0]);
        }
    });

    // Sample trigger
    sampleBtn.addEventListener('click', () => {
        loadSampleRequisition();
    });

    // Actions
    newUploadBtn.addEventListener('click', () => {
        currentProposalData = null;
        outputCard.style.display = 'none';
        uploadCard.style.display = 'flex';
        dropZone.style.display = 'flex';
        processingBox.style.display = 'none';
        fileInput.value = '';
    });

    downloadDocxBtn.addEventListener('click', () => {
        if (!currentProposalData) return;
        downloadWordDocument(currentProposalData);
    });

    printBtn.addEventListener('click', () => {
        window.print();
    });
});

function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Please select a valid PDF document.');
        return;
    }

    if (file.size > 30 * 1024 * 1024) {
        alert('File size exceeds maximum limit of 30 MB.');
        return;
    }

    currentProposalData = null;
    showProcessing('Uploading & Scanning ' + file.name + '...');
    updateSidebarActivity(file.name);

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/analyze', {
        method: 'POST',
        headers: {
            'ngrok-skip-browser-warning': 'true'
        },
        body: formData
    })
    .then(res => {
        if (!res.ok) throw new Error('Failed to analyze document.');
        return res.json();
    })
    .then(data => {
        renderProposal(data);
    })
    .catch(err => {
        console.error(err);
        alert('Error processing file: ' + err.message);
        resetUploadUI();
    });
}

function loadSampleRequisition() {
    currentProposalData = null;
    showProcessing('Analyzing Uploaded SAIL Purchase Requisition (SMS/25/002 / A612002)...');
    updateSidebarActivity('media_1788530530901.pdf (SAIL PR A612002)');

    fetch('/api/load-sample', {
        method: 'POST',
        headers: {
            'ngrok-skip-browser-warning': 'true'
        }
    })
    .then(res => {
        if (!res.ok) throw new Error('Failed to load sample requisition.');
        return res.json();
    })
    .then(data => {
        renderProposal(data);
    })
    .catch(err => {
        console.error(err);
        alert('Error loading sample: ' + err.message);
        resetUploadUI();
    });
}

function showProcessing(statusText) {
    document.getElementById('dropZone').style.display = 'none';
    document.getElementById('processingBox').style.display = 'flex';
    document.getElementById('processStatus').innerText = statusText;
}

function resetUploadUI() {
    document.getElementById('dropZone').style.display = 'flex';
    document.getElementById('processingBox').style.display = 'none';
}

function updateSidebarActivity(filename) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    document.getElementById('recentUploadText').innerText = `${filename} (${timeStr})`;
    document.getElementById('reportGeneratedText').innerText = 'Processing document...';
}

function renderProposal(data) {
    currentProposalData = data;

    // Item Header
    document.getElementById('docItemDesc').innerText = `Description of the item: ${data.item_description}`;

    // Indent Particulars
    const ind = data.indent_particulars || {};
    document.getElementById('valPRNo').innerText = ind.purchase_requisition_no || '-';
    document.getElementById('valIndentDate').innerText = ind.indent_date || '-';
    document.getElementById('valIndentRaisedBy').innerText = ind.indent_raised_by || '-';
    document.getElementById('valEstimate').innerText = ind.estimate || '-';
    document.getElementById('valBasisEstimate').innerText = ind.basis_of_estimate || '-';
    document.getElementById('valFirstTime').innerText = ind.first_time_procurement || '-';
    document.getElementById('valBudgetaryOffers').innerText = ind.budgetary_offers_count || '-';

    // Previous Purchase Details
    const prev = data.previous_purchase_details || {};
    const prevBody = document.getElementById('prevTableBody');
    prevBody.innerHTML = '';
    (prev.items || []).forEach(itm => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${itm.item_sl_no || ''}</td>
            <td>${itm.at_ref_no || ''}</td>
            <td>${itm.prev_qty || ''}</td>
            <td class="font-semibold">${itm.unit_rate_incl_gst || ''}</td>
        `;
        prevBody.appendChild(tr);
    });
    document.getElementById('valPrevMode').innerText = prev.prev_mode_of_tender || '-';

    // Indent Approval
    const ia = data.indent_approval || {};
    document.getElementById('valApprovingAuth').innerText = ia.approving_authority || '-';
    document.getElementById('valApprovedDate').innerText = ia.indent_approved_date || '-';
    document.getElementById('valModeTender').innerText = ia.mode_of_tender || '-';

    // Sanction Particulars
    const sp = data.sanction_particulars || {};
    document.getElementById('valSupplierName').innerText = sp.supplier_name || '-';
    document.getElementById('valOrderValue').innerText = sp.order_value_incl_gst || '-';
    document.getElementById('valDevWrtEstimate').innerText = sp.deviation_wrt_estimate || '-';

    // Negotiation Details
    const neg = data.negotiation_details || {};
    const negHeader = document.getElementById('negTableHeader');
    if (neg.headers && neg.headers.length) {
        negHeader.innerHTML = neg.headers.map(h => `<th>${h}</th>`).join('');
    }
    const negBody = document.getElementById('negTableBody');
    negBody.innerHTML = '';
    (neg.rows || []).forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="font-semibold">${r[0] || ''}</td>
            <td>${r[1] || ''}</td>
            <td>${r[2] || ''}</td>
        `;
        negBody.appendChild(tr);
    });

    // Narrative Clauses
    const narrativeList = document.getElementById('narrativeList');
    narrativeList.innerHTML = '';
    (data.narrative_clauses || []).forEach(clause => {
        const li = document.createElement('li');
        // Clean leading numbers if duplicate
        li.innerText = clause.replace(/^\d+\.\s*/, '');
        narrativeList.appendChild(li);
    });

    // Proposed Order Terms
    const pot = data.proposed_order_terms || {};
    document.getElementById('termSupplier').innerText = pot.supplier_name || '-';
    document.getElementById('termItem').innerText = pot.item_description || '-';
    document.getElementById('termValNoGST').innerText = pot.total_order_value_without_gst || '-';
    document.getElementById('termValWithGST').innerText = pot.total_order_value_with_gst || '-';
    document.getElementById('termEstimate').innerText = pot.estimate || '-';
    document.getElementById('termDev').innerText = pot.percent_dev_wrt_estimate || '-';

    const ct = pot.commercial_terms || {};
    document.getElementById('termDelivery').innerText = ct.terms_of_delivery || '-';
    document.getElementById('termSchedule').innerText = ct.delivery_schedule || '-';
    document.getElementById('termPayment').innerText = ct.payment_terms || '-';
    document.getElementById('termValidity').innerText = ct.offer_validity || '-';

    // Approval Blocks
    document.getElementById('blockApprovalSought').innerText = data.approval_sought_for || '-';
    document.getElementById('blockApprovingDop').innerText = data.approving_authority_dop || '-';
    document.getElementById('blockApprovalPath').innerText = data.suggested_approval_path || '-';

    // Update Sidebar
    document.getElementById('reportGeneratedText').innerText = 'Proposal Note Ready';

    // Show output, hide upload
    document.getElementById('uploadCard').style.display = 'none';
    document.getElementById('outputCard').style.display = 'block';

    // Smooth scroll to top of card
    document.getElementById('outputCard').scrollIntoView({ behavior: 'smooth' });
}

function downloadWordDocument(data) {
    fetch('/api/download-docx', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) throw new Error('Download failed.');
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        const refNo = (data.indent_particulars && data.indent_particulars.purchase_requisition_no) 
            ? data.indent_particulars.purchase_requisition_no.split(' ')[0] 
            : 'Proposal';
        a.download = `${refNo}_Purchase_Proposal_Note.docx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    })
    .catch(err => {
        console.error(err);
        alert('Could not download Word document: ' + err.message);
    });
}
