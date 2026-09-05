import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn

import extractor
import docx_generator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
SAMPLE_PDF_PATH = os.path.join(BASE_DIR, "sample_indent.pdf")
MANI_PDF_PATH = os.path.join(BASE_DIR, "mani.pdf")

os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(title="SAIL Material Management Module - Salem Steel Plant")

# Enable full CORS for public deployment access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def add_custom_headers(request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


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
    import platform, subprocess, shutil
    tess = shutil.which("tesseract")
    tess_ver = None
    if tess:
        try:
            r = subprocess.run([tess, "--version"], capture_output=True, text=True, timeout=3)
            tess_ver = r.stdout.splitlines()[0] if r.stdout else r.stderr.splitlines()[0]
        except Exception as e:
            tess_ver = str(e)
            
    return {
        "status": "ok",
        "is_docker": os.path.exists("/.dockerenv"),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "tesseract_path": tess,
        "tesseract_version": tess_ver
    }


@app.post("/api/analyze")
def analyze_pdf(file: UploadFile = File(...)):
    """
    Reads newly uploaded PDF from scratch.
    Synchronous def runs in FastAPI threadpool to prevent blocking the asyncio event loop.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    import traceback
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(file.file, tmp)

        # Extract freshly from the newly uploaded PDF
        extracted_text = extractor.extract_text_from_pdf(tmp_path, max_pages=10)
        
        # Parse into fixed structured proposal template
        proposal_data = extractor.parse_purchase_requisition(extracted_text, filename=file.filename)
        return proposal_data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass


@app.post("/api/load-sample")
def load_sample():
    """
    Loads sample document dynamically using the exact same parsing pipeline in threadpool.
    """
    target = SAMPLE_PDF_PATH if os.path.exists(SAMPLE_PDF_PATH) else MANI_PDF_PATH
    if os.path.exists(target):
        try:
            extracted_text = extractor.extract_text_from_pdf(target, max_pages=10)
            proposal_data = extractor.parse_purchase_requisition(extracted_text, filename=os.path.basename(target))
            return proposal_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sample loading failed: {str(e)}")
    else:
        raise HTTPException(status_code=404, detail="Sample PDF not found")


@app.post("/api/download-docx")
async def download_docx(data: dict):
    try:
        tmp_dir = tempfile.gettempdir()
        filename = "Purchase_Proposal_Note.docx"
        out_path = os.path.join(tmp_dir, filename)
        
        docx_generator.generate_purchase_proposal_docx(data, out_path)
        
        pr_raw = (
            data.get("indent_particulars", {})
            .get("purchase_requisition_no", "Proposal")
            .split()[0]
            .replace("/", "_")
            .replace("\\", "_")
        )
        download_name = f"{pr_raw}_Purchase_Proposal_Note.docx"
        
        return FileResponse(
            path=out_path,
            filename=download_name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Word doc generation failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
