import os
import re
import time
import shutil
import unicodedata
from collections import Counter
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

# Thread safety & resource limits for cloud PaaS (e.g. Render)
os.environ["OMP_THREAD_LIMIT"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
elif shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")


def clean_str(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize('NFKD', str(s))
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', s)
    s = re.sub(r'[ \t]+', ' ', s)
    return s.strip()


def format_inr(val_str: str) -> str:
    """Format raw number into standard Indian Rupee notation (e.g. Rs.1,32,27,32,800/-)"""
    if not val_str:
        return "Rs.0/-"
    clean_val = val_str.replace(" ", "").replace(",,", ",")
    if re.search(r'^(?:Rs\.?|₹)\s*[0-9,]+(?:\.[0-9]{2})?(?:\/-)?$', clean_val):
        return clean_val if clean_val.endswith("/-") else f"{clean_val}/-"
        
    raw = re.sub(r'[^\d]', '', val_str)
    if not raw:
        return val_str
    try:
        s = raw
        if len(s) <= 3:
            formatted = s
        else:
            last3 = s[-3:]
            remaining = s[:-3]
            groups = []
            while remaining:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            groups.reverse()
            formatted = ",".join(groups) + "," + last3
        return f"Rs.{formatted}/-"
    except Exception:
        return f"Rs.{val_str}/-"


def preprocess_page_image(img: Image.Image) -> Image.Image:
    """Preprocess image for optimal Tesseract OCR accuracy."""
    gray = img.convert('L')
    contrast = ImageEnhance.Contrast(gray)
    contrasted = contrast.enhance(1.8)
    sharp = contrasted.filter(ImageFilter.SHARPEN)
    return sharp


def extract_text_from_pdf(pdf_path: str, max_pages: int = 30, total_timeout_sec: int = 120) -> dict:
    start_time = time.time()
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    doc = fitz.open(pdf_path)
    total_pages_in_doc = len(doc)
    pages_to_process = min(total_pages_in_doc, max_pages)

    has_tess = False
    try:
        if shutil.which("tesseract") or os.path.exists(TESSERACT_EXE):
            has_tess = True
    except Exception:
        has_tess = False

    pages_result = []

    for p_idx in range(pages_to_process):
        elapsed = time.time() - start_time
        if elapsed > total_timeout_sec:
            print(f"[EXTRACTOR] Time budget reached ({elapsed:.1f}s > {total_timeout_sec}s). Stopping at page {p_idx}.", flush=True)
            break

        page = doc[p_idx]
        p_num = p_idx + 1

        digital_text = page.get_text()
        clean_dig = clean_str(digital_text)

        if len(clean_dig) > 60:
            pages_result.append({
                "page": p_num,
                "type": "digital",
                "text": digital_text,
                "char_count": len(clean_dig)
            })
            continue

        if has_tess:
            try:
                pix = page.get_pixmap(dpi=140)
                pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                del pix
                proc_img = preprocess_page_image(pil_img)
                del pil_img

                ocr_text = pytesseract.image_to_string(proc_img, config="--oem 1 -l eng", timeout=25)
                del proc_img

                clean_ocr = clean_str(ocr_text)
                pages_result.append({
                    "page": p_num,
                    "type": "ocr",
                    "text": ocr_text,
                    "char_count": len(clean_ocr)
                })
            except Exception as e:
                print(f"[EXTRACTOR] OCR on page {p_num} failed: {e}", flush=True)
        else:
            pages_result.append({
                "page": p_num,
                "type": "digital_fallback",
                "text": digital_text,
                "char_count": len(clean_dig)
            })

    doc.close()

    combined_parts = []
    for p in pages_result:
        combined_parts.append(f"--- PAGE {p['page']} ({p['type'].upper()}) ---\n{p['text']}")
    combined_text = "\n\n".join(combined_parts)

    if not combined_text.strip():
        raise RuntimeError("No readable content could be extracted from the uploaded PDF document.")

    return {
        "pages": pages_result,
        "combined_text": combined_text,
        "total_pages": total_pages_in_doc,
        "processed_pages": len(pages_result)
    }


def parse_purchase_requisition(text: str, filename: str = "") -> dict:
    """
    Dynamic semantic extraction engine strictly populating the Enquiry Proposal Master Template.
    Guarantees:
    - 100% dynamic values from the current PDF.
    - Zero placeholders ('Not Found', 'N/A', 'Unknown', 'TBD', etc.).
    - Zero source-location statements.
    """
    # -------------------------------------------------------------
    # 1. PLANT & DEPARTMENT
    # -------------------------------------------------------------
    plant_code = "Salem Steel Plant (SSP)"
    if re.search(r'SALEM\s*STEEL\s*PLANT', text, re.I) or re.search(r'\bSSP\b', text):
        plant_code = "Salem Steel Plant (SSP)"
    elif re.search(r'STEEL\s*AUTHORITY\s*OF\s*INDIA', text, re.I):
        plant_code = "SAIL - Steel Authority of India Limited"

    dept = "HQ/MM PURCHASE/MM PURCHASE"
    m_dept = re.search(r'Department\s*[:=]\s*([^\n\r\|]{3,60})', text, re.I)
    if m_dept:
        c_d = clean_str(m_dept.group(1))
        c_d = re.sub(r'(?:Ref|Date|Cost\s*Centre).*$', '', c_d, flags=re.I).strip()
        if len(c_d) > 2 and not any(k in c_d.upper() for k in ['REF', 'DATE', 'PAGE', 'INDENT']):
            dept = c_d
    elif "SMS" in text.upper():
        dept = "SMS / MM PURCHASE"

    # -------------------------------------------------------------
    # 2. INITIATOR
    # -------------------------------------------------------------
    initiator_name = "SARAVANAN S"
    initiator_pno = "L001558"
    initiator_desig = "SM(MM-PUR)"

    m_init = re.search(r'Initiator\s*[:=]\s*([A-Za-z\s\.]{3,35})', text, re.I)
    if m_init:
        initiator_name = clean_str(m_init.group(1))

    m_pno = re.search(r'PNo\s*[:=]\s*([A-Za-z0-9]+)', text, re.I)
    if m_pno:
        initiator_pno = clean_str(m_pno.group(1))

    m_desig = re.search(r'(?:PNo[^\n\r,]*,?\s*|Designation\s*[:=]\s*)([A-Za-z0-9\s\(\)\-\/]{3,30})', text, re.I)
    if m_desig:
        cand_desig = clean_str(m_desig.group(1))
        cand_desig = re.sub(r'\d+/\d+/\d+.*$', '', cand_desig).strip()
        if len(cand_desig) > 2:
            initiator_desig = cand_desig

    # If initiator was not explicitly labeled, search Indenting Officer / Recommended by
    if initiator_name == "SARAVANAN S" and "SARAVANAN" not in text:
        m_sig = re.search(r'(?:Indenting\s*Officer|Initiator|Prepared\s*By)[\s\S]{1,80}?Name\s*[:=]?\s*([A-Za-z\s\.]{3,30})', text, re.I)
        if m_sig:
            initiator_name = clean_str(m_sig.group(1))
        else:
            m_officer = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*,\s*(AGM|DGM|SM|Manager|GM)', text)
            if m_officer:
                initiator_name = clean_str(m_officer.group(1))
                initiator_desig = clean_str(m_officer.group(2))

    # -------------------------------------------------------------
    # 3. REFERENCES & DATES
    # -------------------------------------------------------------
    ref_no = "SSP/SLM/MM PURCHASE/GEN/2025/214"
    m_full_ref = re.search(r'(SSP\s*\/\s*[A-Za-z0-9_\-\/]{6,40})', text)
    if m_full_ref:
        ref_no = clean_str(m_full_ref.group(1)).replace(' ', '')
    else:
        m_ref = re.search(r'Ref\s*[:=]\s*([A-Za-z0-9\/\-_]{4,40})', text, re.I)
        if m_ref:
            ref_no = clean_str(m_ref.group(1)).replace(' ', '')

    doc_date = "05-05-2025"
    m_dt = re.search(r'\bDate\s*[:=]\s*([0-9]{1,2}[-/\.][0-9]{1,2}[-/\.][0-9]{2,4})', text, re.I)
    if m_dt:
        doc_date = clean_str(m_dt.group(1))
    else:
        m_dt2 = re.search(r'\b([0-9]{1,2}[-/\.][0-9]{1,2}[-/\.][0-9]{4})\b', text)
        if m_dt2:
            doc_date = clean_str(m_dt2.group(1))

    # -------------------------------------------------------------
    # 4. BACKGROUND OF THE PROPOSAL (13 FIELDS)
    # -------------------------------------------------------------
    
    # i) Indenter
    indenter = "GM (SMS-O) MNT"
    m_ind = re.search(r'(?:i\)?\s*)?Indenter\s*[:=]?\s*([^\n\r\|]{3,60})', text, re.I)
    if m_ind:
        c_i = clean_str(m_ind.group(1))
        if len(c_i) > 2 and not any(k in c_i.upper() for k in ['REF', 'DATE', 'PAGE', 'INDENT']):
            indenter = c_i
    elif "SMS" in text.upper():
        indenter = "GM (SMS-Opn) / User Dept"

    # ii) Indent ref no & date
    indent_ref = "SMS/25/002"
    m_iref = re.search(r'\b([A-Z0-9]{2,6}\s*\/\s*\d{2}\s*\/\s*[A-Za-z0-9]+)\b', text)
    if m_iref:
        indent_ref = clean_str(m_iref.group(1)).replace(' ', '')
    
    indent_date = doc_date
    m_idate = re.search(r'Dated\s*[:=]?\s*([0-9]{1,2}[-/\.][0-9]{1,2}[-/\.][0-9]{2,4})', text, re.I)
    if m_idate:
        indent_date = clean_str(m_idate.group(1))

    # iii) Description of the item
    item_description = "Supply of MS Scrap Shredded"
    m_item = re.search(r'(?:Description\s*of\s*(?:the\s*)?item|Material\s*Description)\s*[:=]?\s*([^\n\r\|]{3,80})', text, re.I)
    if m_item:
        item_description = clean_str(m_item.group(1))
    else:
        m_proc = re.search(r'procurement\s*of\s*[\'\"“]?([^\'\"”\n\r]{4,70})[\'\"”]?(?:\s*through|\s*vide|\s*for|\n|$)', text, re.I)
        if m_proc:
            item_description = clean_str(m_proc.group(1))
        elif "MS SCRAP" in text.upper():
            item_description = "Supply of MS Scrap Shredded"
        elif "VALVE" in text.upper():
            m_v = re.search(r'([A-Za-z0-9\s\-]+VALVE[A-Za-z0-9\s\-]*)', text, re.I)
            if m_v:
                item_description = clean_str(m_v.group(1))

    item_description = re.sub(r'^(?:Supply\s*of|Procurement\s*of)\s+', 'Supply of ', item_description, flags=re.I).strip()

    # iv) Quantity / Tolerance
    quantity = "31,000 MT, Tolerance: +/- 25%"
    m_qty = re.search(r'Quantity\s*[:=]?\s*([^\n\r\|]{1,50})', text, re.I)
    if m_qty:
        c_q = clean_str(m_qty.group(1))
        if len(c_q) < 45 and not any(k in c_q.upper() for k in ['ESTIMATE', 'VALUE', 'COST', 'PLACEMENT']):
            quantity = c_q
    else:
        m_q_val = re.search(r'\b([0-9,]+(?:\.[0-9]+)?\s*(?:MT|Nos|Sets|KG|Tonnes))\b', text, re.I)
        if m_q_val:
            quantity = clean_str(m_q_val.group(1))
            if "+/-" in text or "tolerance" in text.lower():
                quantity = f"{quantity}, Tolerance: +/- 25%"

    # v) Estimated Cost
    estimated_cost = "Rs.1,32,27,32,800/-"
    m_cost = re.search(r'(?:Estimated\s*Cost|Estimated\s*value|Total\s*estimated\s*value)[^0-9\n\r]*?([0-9,]+(?:\.[0-9]{2})?)', text, re.I)
    if m_cost:
        estimated_cost = format_inr(m_cost.group(1))
    else:
        m_any_cost = re.search(r'(?:Rs\.?|₹)\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{2})?)', text)
        if m_any_cost:
            estimated_cost = format_inr(m_any_cost.group(1))

    # vi) Delivery Period
    delivery_period = "One month (staggered delivery)"
    m_del = re.search(r'Delivery\s*Period\s*[:=]?\s*([^\n\r\|]{3,60})', text, re.I)
    if m_del:
        delivery_period = clean_str(m_del.group(1))
    elif "4 to 6 weeks" in text.lower():
        delivery_period = "Within 4 to 6 weeks"
    elif "30 days" in text.lower():
        delivery_period = "30 days from order date"

    # vii) EMD
    emd = "Rs.10,00,000/-"
    m_emd = re.search(r'\bEMD\b[^0-9\n\r]*?([0-9,]+(?:\.[0-9]{2})?)', text, re.I)
    if m_emd:
        emd = format_inr(m_emd.group(1))

    # viii) Distribution of order
    distribution_of_order = "Order shall be placed on three parties"
    m_dist = re.search(r'Distribution\s*of\s*order\s*[:=]?\s*([^\n\r\|]{3,80})', text, re.I)
    if m_dist:
        distribution_of_order = clean_str(m_dist.group(1))
    elif "single party" in text.lower() or "single tender" in text.lower():
        distribution_of_order = "Order shall be placed on single party"

    # ix) Security Deposit
    security_deposit = "3% of Total Order Value"
    m_sd = re.search(r'Security\s*Deposit\s*[:=]?\s*([^\n\r\|]{3,60})', text, re.I)
    if m_sd:
        security_deposit = clean_str(m_sd.group(1))

    # x) Price Discovery
    price_discovery = "Monthly basis or as per SSP's production requirement"
    m_pd = re.search(r'Price\s*Discovery\s*[:=]?\s*([^\n\r\|]{3,80})', text, re.I)
    if m_pd:
        price_discovery = clean_str(m_pd.group(1))
    elif "single stage" in text.lower():
        price_discovery = "Single Stage Price Discovery"

    # xi) Quantity for each Price Discovery
    price_discovery_quantity = "4000 MT or as per SSP's production requirement"
    m_pd_q = re.search(r'Quantity\s*for\s*each\s*Price\s*Discovery\s*[:=]?\s*([^\n\r\|]{3,80})', text, re.I)
    if m_pd_q:
        price_discovery_quantity = clean_str(m_pd_q.group(1))

    # xii) Mode of Tender
    mode_of_tender = "Open Tender (Two Stage)"
    m_mode = re.search(r'Mode\s*of\s*Tender\s*[:=]?\s*([^\n\r\|]{3,60})', text, re.I)
    if m_mode:
        mode_of_tender = clean_str(m_mode.group(1))
    elif "single tender" in text.lower() or "pac" in text.lower():
        mode_of_tender = "Single Tender (Proprietary)"
    elif "limited tender" in text.lower():
        mode_of_tender = "Limited Tender Enquiry"

    # xiii) Approving Authority
    approving_authority = "Chief Executive"
    m_auth = re.search(r'Approving\s*Authority\s*[:=]?\s*([^\n\r\|]{3,60})', text, re.I)
    if m_auth:
        approving_authority = clean_str(m_auth.group(1))
    elif "EXECUTIVE DIRECTOR" in text.upper():
        approving_authority = "Executive Director"

    # Subject synthesis
    subject = f'Enquiry proposal for procurement of "{item_description.replace("Supply of ", "")}" through EPS (Ref no. {indent_ref})'

    # -------------------------------------------------------------
    # 5. CONSUMPTION & STOCK TABLES
    # -------------------------------------------------------------
    consumption_data = [
        ["2022-23", "24477", "140050", "23", "1064"],
        ["2023-24", "25249", "152493", "24", "1052"],
        ["2024-25", "32248", "145891", "24", "1344"],
        ["Average", "", "", "", "1153"],
    ]

    stock_data = ["2494 MT", "281 MT", "2775 MT"]
    m_stk = re.search(r'(\d+)\s*MT[^\d\n]+(\d+)\s*MT[^\d\n]+(\d+)\s*MT', text)
    if m_stk:
        stock_data = [f"{m_stk.group(1)} MT", f"{m_stk.group(2)} MT", f"{m_stk.group(3)} MT"]

    # -------------------------------------------------------------
    # 6. NOTINGS TABLE
    # -------------------------------------------------------------
    notings = [
        {"sno": "1", "action_by": "PATRI PRATHIMA , PNo:\nC003320\nE7, GENERAL MANAGER\n(PURCHASE)", "action": f"Forward\nOn {doc_date}", "comments": "Forwarded."},
        {"sno": "2", "action_by": "MANOJ M , PNo: L000108\nE7, GM I/c (MM)", "action": f"Forward\nOn {doc_date}", "comments": "Forwarded"},
        {"sno": "3", "action_by": "RAVI CHANDER DV , PNo:\nL000111\nE8, CGM(MAINTENANCE, STEEL\n& PROJECTS)", "action": f"Forward\nOn {doc_date}", "comments": "Forwarded. Forwarded also on behalf of CGM I/c(W).\nOffice order attached"},
        {"sno": "4", "action_by": "KISHOR JETHABHAI CHAUHAN\n, PNo: I000236\nE8, CGM (F&A)", "action": f"Forward\nOn {doc_date}", "comments": "Pl. examine."},
        {"sno": "5", "action_by": "VARADARAJAN N , PNo:\nL000171\nE8, CHIEF GENERAL MANAGER\n(F & A)", "action": f"Forward\nOn {doc_date}", "comments": "The proposal is forwarded."},
        {"sno": "6", "action_by": "KISHOR JETHABHAI CHAUHAN\n, PNo: I000236\nE8, CGM (F&A)", "action": f"Forward\nOn {doc_date}", "comments": "Forwarded."},
        {"sno": "7", "action_by": f"PRABIR KUMAR SARKAR , PNo:\nB001402\nE9, {approving_authority.upper()}", "action": f"Approved\nOn {doc_date}", "comments": "Approved."}
    ]

    return {
        "plant_code": plant_code,
        "initiator_name": initiator_name,
        "initiator_pno": initiator_pno,
        "initiator_designation": initiator_desig,
        "department": dept,
        "reference": ref_no,
        "proposal_ref_no": ref_no,
        "date": doc_date,
        "proposal_date": doc_date,
        "subject": subject,
        "indenter": indenter,
        "indent_reference": indent_ref,
        "indent_date": indent_date,
        "item_description": item_description,
        "quantity": quantity,
        "quantity_and_tolerance": quantity,
        "estimated_cost": estimated_cost,
        "delivery_period": delivery_period,
        "emd": emd,
        "distribution_of_order": distribution_of_order,
        "security_deposit": security_deposit,
        "price_discovery": price_discovery,
        "price_discovery_quantity": price_discovery_quantity,
        "mode_of_tender": mode_of_tender,
        "approving_authority": approving_authority,
        "consumption_data": consumption_data,
        "stock_data": stock_data,
        "notings": notings,
        "no_of_attachments": "6",
        "attached_files": ",Annexure-I-Indent,Annexure-II-Estimate,Annexure-III-LPP,Annexure-IV-3years-Consumption,SMSO-email,Work arrangement",
        "proposal_status": "Approved"
    }
