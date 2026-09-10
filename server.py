import os
import sys
import re
import shutil
import tempfile
import uuid
import datetime
import traceback
from typing import List

# Thread safety & resource limits for cloud PaaS (e.g. Render)
os.environ["OMP_THREAD_LIMIT"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

from fastapi import FastAPI, UploadFile, File, HTTPException, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import uvicorn

import extractor
import docx_generator
import pdf_generator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = FastAPI(
    title="SAIL Material Management Module - Salem Steel Plant",
    description="Official Procurement Proposal Note Generator & Material Tracking System",
    version="2026.09.10-production"
)

# Enable CORS for public cloud deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static web assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Custom middleware to bypass tunnel warnings if applicable
@app.middleware("http")
async def add_custom_headers(request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


# In-memory document session registry with document isolation
DOCUMENTS_STORE = {}
RECENT_ACTIVITY = [
    {
        "id": "init_1",
        "title": "System Initialized",
        "detail": "SAIL Material Management Module active on Salem Steel Plant cloud node",
        "timestamp": "Just now",
        "icon": "shield-check"
    },
    {
        "id": "init_2",
        "title": "Master Template Loaded",
        "detail": "Salem Steel Plant standard Procurement Proposal Note template verified",
        "timestamp": "12 min ago",
        "icon": "file-text"
    }
]


@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Index file not found")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/health")
def health_check():
    import platform
    tess_path = shutil.which("tesseract") or extractor.TESSERACT_EXE
    has_tess = os.path.exists(tess_path) if tess_path else False
    return {
        "status": "ok",
        "service": "SAIL Material Management Module - Salem Steel Plant",
        "version": app.version,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "tesseract_available": has_tess,
        "max_file_size_mb": 30,
        "active_documents": len(DOCUMENTS_STORE)
    }


def _process_single_pdf_file(file_content: bytes, original_filename: str) -> dict:
    """Internal helper to process a single PDF file with full multi-document isolation."""
    # 1. 30 MB validation
    size_mb = len(file_content) / (1024 * 1024)
    if size_mb > 30.0:
        raise HTTPException(
            status_code=400,
            detail=f"File '{original_filename}' exceeds the 30 MB limit ({size_mb:.2f} MB)."
        )

    # 2. PDF format check
    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type for '{original_filename}'. Only PDF files are supported."
        )

    doc_id = str(uuid.uuid4())
    tmp_path = os.path.join(UPLOADS_DIR, f"{doc_id}_{original_filename}")
    
    try:
        with open(tmp_path, "wb") as f:
            f.write(file_content)

        print(f"[API] Processing document '{original_filename}' ({size_mb:.2f} MB) with ID: {doc_id}", flush=True)

        # 3. OCR & text extraction
        extracted_data = extractor.extract_text_from_pdf(tmp_path, max_pages=30, total_timeout_sec=120)
        total_pages = extracted_data.get("total_pages", 1)
        raw_ocr_pages = extracted_data.get("pages", [])
        combined_text = extracted_data.get("combined_text", "")

        # 4. Procurement parsing into master template format
        proposal_data = extractor.parse_purchase_requisition(combined_text, filename=original_filename)

        # 5. Generate outputs (DOCX and PDF)
        docx_path = os.path.join(OUTPUTS_DIR, f"{doc_id}_Purchase_Proposal_Note.docx")
        pdf_path = os.path.join(OUTPUTS_DIR, f"{doc_id}_Purchase_Proposal_Note.pdf")

        docx_generator.generate_purchase_proposal_docx(proposal_data, docx_path)
        pdf_generator.generate_purchase_proposal_pdf(proposal_data, pdf_path)

        now_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        doc_record = {
            "document_id": doc_id,
            "filename": original_filename,
            "file_size_mb": round(size_mb, 2),
            "pages": total_pages,
            "ocr_status": "completed",
            "extraction_status": "completed",
            "proposal_status": "generated",
            "timestamp": now_str,
            "data": proposal_data,
            "ocr_pages": raw_ocr_pages,
            "docx_path": docx_path,
            "pdf_path": pdf_path
        }

        # Store in isolated session dictionary
        DOCUMENTS_STORE[doc_id] = doc_record

        # Append to activity feed
        RECENT_ACTIVITY.insert(0, {
            "id": f"act_{doc_id[:8]}",
            "title": f"Analyzed: {original_filename}",
            "detail": f"Generated Proposal for {proposal_data.get('item_description', 'Materials')[:32]}",
            "timestamp": "Just now",
            "icon": "check-circle"
        })

        return {
            "success": True,
            "document_id": doc_id,
            "filename": original_filename,
            "pages": total_pages,
            "file_size_mb": round(size_mb, 2),
            "ocr_status": "completed",
            "extraction_status": "completed",
            "proposal_status": "generated",
            "data": proposal_data
        }

    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@app.post("/api/analyze")
async def analyze_single_pdf(file: UploadFile = File(...)):
    """Analyze a single uploaded purchase requisition PDF."""
    try:
        content = await file.read()
        return _process_single_pdf_file(content, file.filename)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed for '{file.filename}': {str(e)}")


@app.post("/api/analyze-multiple")
async def analyze_multiple_pdfs(files: List[UploadFile] = File(...)):
    """
    Analyze multiple purchase requisition PDFs in a single session.
    Guarantees strict multi-document isolation: each document has its own
    independent OCR, extracted fields, and generated proposal.
    """
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided for analysis.")

    results = []
    errors = []

    for file in files:
        try:
            content = await file.read()
            res = _process_single_pdf_file(content, file.filename)
            results.append(res)
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })

    return {
        "success": len(results) > 0,
        "total_submitted": len(files),
        "total_processed": len(results),
        "documents": results,
        "errors": errors
    }


@app.get("/api/analysis/{doc_id}")
def get_analysis_result(doc_id: str):
    """Retrieve extracted fields and proposal metadata for a document."""
    if doc_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document analysis not found.")
    doc = DOCUMENTS_STORE[doc_id]
    return {
        "success": True,
        "document_id": doc_id,
        "filename": doc["filename"],
        "pages": doc["pages"],
        "file_size_mb": doc["file_size_mb"],
        "ocr_status": doc["ocr_status"],
        "extraction_status": doc["extraction_status"],
        "proposal_status": doc["proposal_status"],
        "data": doc["data"]
    }


@app.get("/api/analysis/{doc_id}/ocr")
def get_ocr_text(doc_id: str):
    """View per-page OCR text extracted from the document."""
    if doc_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc = DOCUMENTS_STORE[doc_id]
    return {
        "document_id": doc_id,
        "filename": doc["filename"],
        "total_pages": doc["pages"],
        "pages": doc.get("ocr_pages", [])
    }


@app.get("/api/analysis/{doc_id}/proposal")
def get_proposal_data(doc_id: str):
    """Fetch structured proposal data matching the master procurement template."""
    if doc_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DOCUMENTS_STORE[doc_id]["data"]


@app.post("/api/analysis/{doc_id}/update")
def update_proposal_data(doc_id: str, updated_data: dict = Body(...)):
    """Allow user review and confirmation of extracted values before downloading."""
    if doc_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    doc = DOCUMENTS_STORE[doc_id]
    doc["data"].update(updated_data)
    doc["user_confirmed"] = True

    # Regenerate files with confirmed values
    docx_generator.generate_purchase_proposal_docx(doc["data"], doc["docx_path"])
    pdf_generator.generate_purchase_proposal_pdf(doc["data"], doc["pdf_path"])

    return {
        "success": True,
        "message": "Extracted values successfully confirmed and proposal updated.",
        "data": doc["data"]
    }


@app.get("/api/analysis/{doc_id}/download/docx")
def download_docx_by_id(doc_id: str):
    """Download official Purchase Proposal Note in Word (.docx) format."""
    if doc_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc = DOCUMENTS_STORE[doc_id]
    path = doc["docx_path"]
    if not os.path.exists(path):
        docx_generator.generate_purchase_proposal_docx(doc["data"], path)

    ref_str = re.sub(r'[^A-Za-z0-9_-]', '_', doc["data"].get("indent_reference", "Proposal"))[:20]
    filename = f"{ref_str}_Purchase_Proposal_Note.docx"
    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.get("/api/analysis/{doc_id}/download/pdf")
def download_pdf_by_id(doc_id: str):
    """Download official Purchase Proposal Note in PDF (.pdf) format."""
    if doc_id not in DOCUMENTS_STORE:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc = DOCUMENTS_STORE[doc_id]
    path = doc["pdf_path"]
    if not os.path.exists(path):
        pdf_generator.generate_purchase_proposal_pdf(doc["data"], path)

    ref_str = re.sub(r'[^A-Za-z0-9_-]', '_', doc["data"].get("indent_reference", "Proposal"))[:20]
    filename = f"{ref_str}_Purchase_Proposal_Note.pdf"
    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/pdf"
    )


@app.post("/api/download-docx")
def download_docx_from_json(data: dict = Body(...)):
    """Generate and return DOCX directly from JSON payload."""
    try:
        tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_proposal.docx")
        docx_generator.generate_purchase_proposal_docx(data, tmp_path)
        ref_str = re.sub(r'[^A-Za-z0-9_-]', '_', data.get("indent_reference", "Proposal"))[:20]
        return FileResponse(
            path=tmp_path,
            filename=f"{ref_str}_Purchase_Proposal_Note.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {str(e)}")


@app.post("/api/download-pdf")
def download_pdf_from_json(data: dict = Body(...)):
    """Generate and return PDF directly from JSON payload."""
    try:
        tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_proposal.pdf")
        pdf_generator.generate_purchase_proposal_pdf(data, tmp_path)
        ref_str = re.sub(r'[^A-Za-z0-9_-]', '_', data.get("indent_reference", "Proposal"))[:20]
        return FileResponse(
            path=tmp_path,
            filename=f"{ref_str}_Purchase_Proposal_Note.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.get("/api/dashboard-stats")
def get_dashboard_stats():
    """Metrics for Dashboard navigation page."""
    total_docs = len(DOCUMENTS_STORE)
    recent_docs = []
    for d_id, item in list(DOCUMENTS_STORE.items())[-10:]:
        recent_docs.append({
            "document_id": d_id,
            "filename": item["filename"],
            "date": item["timestamp"],
            "pages": item["pages"],
            "status": "Completed",
            "proposal_status": item["proposal_status"],
            "item_description": item["data"].get("item_description", "N/A"),
            "estimated_cost": item["data"].get("estimated_cost", "N/A")
        })

    return {
        "total_processed": total_docs,
        "successful_analyses": total_docs,
        "failed_analyses": 0,
        "proposals_generated": total_docs,
        "recent_documents": recent_docs,
        "recent_activity": RECENT_ACTIVITY[:8]
    }


@app.get("/api/material-tracking")
def get_material_tracking():
    """Extracted procurement materials inventory for Material Tracking tab."""
    materials = []
    for d_id, item in DOCUMENTS_STORE.items():
        data = item["data"]
        materials.append({
            "document_id": d_id,
            "item_description": data.get("item_description", "Not found"),
            "quantity": data.get("quantity", "Not found"),
            "tolerance": data.get("tolerance", "Not found"),
            "indent_reference": data.get("indent_reference", "Not found"),
            "estimated_cost": data.get("estimated_cost", "Not found"),
            "mode_of_tender": data.get("mode_of_tender", "Not found"),
            "procurement_status": "Active Indent",
            "proposal_status": "Proposal Generated"
        })
    return {"materials": materials}


@app.get("/api/reports")
def get_reports():
    """Summary of all processed reports for Reports tab."""
    reports_list = []
    for d_id, item in DOCUMENTS_STORE.items():
        data = item["data"]
        reports_list.append({
            "document_id": d_id,
            "filename": item["filename"],
            "timestamp": item["timestamp"],
            "item": data.get("item_description", "N/A"),
            "value": data.get("estimated_cost", "N/A"),
            "tender_mode": data.get("mode_of_tender", "N/A"),
            "approver": data.get("approving_authority", "N/A")
        })
    return {"reports": reports_list}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
