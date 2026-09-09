import os
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_TEMPLATE_DOCX = (
    os.path.join(BASE_DIR, "output.docx")
    if os.path.exists(os.path.join(BASE_DIR, "output.docx"))
    else os.path.join(BASE_DIR, "test_proposal.docx")
)

FORBIDDEN_WORDS = [
    "not found", "not available", "not applicable", "n/a", "na",
    "unknown", "nil", "none", "no data", "unavailable", "cannot determine",
    "blank", "-", "—", "*"
]

CONCATENATED_HEADER_PATTERNS = [
    "ParameterValue",
    "ParameterTender PriceAfter Negotiation",
    "Item sl. nos.AT ref. no.Previous purchase qty in nos./MTUnit rate incl. GST",
    "ParameterTender"
]

DISALLOWED_EXTRA_SECTIONS = [
    "Summary of Changes & Verification",
    "Verification Report",
    "Walkthrough",
    "Debug Information",
    "Developer Notes",
    "AI Explanation"
]


def generate_purchase_proposal_docx(data: dict, output_path: str) -> str:
    """
    Populates the IMMUTABLE MASTER TEMPLATE DOCX (output.docx / test_proposal.docx).
    Preserves all original tables, cells, widths, borders, styling, and page breaks.
    Never creates tables from scratch, never concatenates headers into 'ParameterValue'.
    Re-opens and programmatically validates the actual generated DOCX on disk:
    - EMPTY VALUE CELLS = 0
    - FORBIDDEN PLACEHOLDER OCCURRENCES = 0
    - CONCATENATED HEADER OCCURRENCES = 0
    - EXTRA SECTION OCCURRENCES = 0
    - ALL 9 NARRATIVE CLAUSES POPULATED
    """
    if not os.path.exists(MASTER_TEMPLATE_DOCX):
        raise FileNotFoundError(f"Master template DOCX not found at {MASTER_TEMPLATE_DOCX}")

    doc = docx.Document(MASTER_TEMPLATE_DOCX)
    
    # -------------------------------------------------------------
    # 1. Main Table (Table 0: Indent Particulars, Previous Purchase, Indent Approval, Sanction, Negotiation)
    # -------------------------------------------------------------
    t0 = doc.tables[0]
    
    # Row 0: Description of the item
    item_desc = str(data.get("item_description", "")).strip()
    t0.rows[0].cells[0].paragraphs[0].text = f"Description of the item: {item_desc}"
    
    ind = data.get("indent_particulars", {})
    prev = data.get("previous_purchase_details", {})
    ia = data.get("indent_approval", {})
    sp = data.get("sanction_particulars", {})
    pot = data.get("proposed_order_terms", {})
    ct = pot.get("commercial_terms", {})
    
    # Build complete key-to-value map for all two-column rows
    field_map = {
        "purchase requisition no.": ind.get("purchase_requisition_no", ""),
        "indent reference no.": ind.get("indent_reference_no", ""),
        "indent date": ind.get("indent_date", ""),
        "proposal date": ind.get("proposal_date", ""),
        "indent raised by": ind.get("indent_raised_by", ""),
        "estimate": ind.get("estimate", ""),
        "basis of estimate": ind.get("basis_of_estimate", ""),
        "first time procurement": ind.get("first_time_procurement", ""),
        "number of budgetary offers received": ind.get("budgetary_offers_count", ""),
        "previous purchase mode of tender": prev.get("prev_mode_of_tender", ""),
        "approving authority": ia.get("approving_authority", ""),
        "indent approved date": ia.get("indent_approved_date", ""),
        "mode of tender": ia.get("mode_of_tender", ""),
        "name of the supplier": sp.get("supplier_name", ""),
        "order value incl. gst": sp.get("order_value_incl_gst", ""),
        "deviation wrt estimate": sp.get("deviation_wrt_estimate", ""),
        "supplier name": pot.get("supplier_name", ""),
        "item description": pot.get("item_description", ""),
        "total order value without gst": pot.get("total_order_value_without_gst", ""),
        "total order value with gst": pot.get("total_order_value_with_gst", ""),
        "% dev wrt estimate": pot.get("percent_dev_wrt_estimate", ""),
        "terms of delivery": ct.get("terms_of_delivery", ""),
        "delivery schedule": ct.get("delivery_schedule", ""),
        "payment terms": ct.get("payment_terms", ""),
        "offer validity": ct.get("offer_validity", ""),
        "approval sought for": data.get("approval_sought_for", ""),
        "approving authority / dop / manual ref": data.get("approving_authority_dop", ""),
        "suggested approval path": data.get("suggested_approval_path", "")
    }
    
    # Update two-column key-value rows across all tables in the document
    for tbl in doc.tables:
        for row in tbl.rows:
            if len(row.cells) == 2:
                # Only update non-merged key-value cells
                if row.cells[0]._tc is not row.cells[1]._tc:
                    label = row.cells[0].text.strip().lower()
                    if label in field_map:
                        val = str(field_map[label]).strip()
                        row.cells[1].paragraphs[0].text = val
                    
    # Update Previous Purchase nested table (Row 13)
    prev_items = prev.get("items", [])
    if len(t0.rows) > 13 and len(t0.rows[13].cells[0].tables) > 0:
        prev_tbl = t0.rows[13].cells[0].tables[0]
        # Update row 1 in-place to preserve pristine cell formatting
        for idx, itm in enumerate(prev_items, start=1):
            if idx < len(prev_tbl.rows):
                prev_tbl.rows[idx].cells[0].paragraphs[0].text = str(itm.get("item_sl_no", "")).strip()
                prev_tbl.rows[idx].cells[1].paragraphs[0].text = str(itm.get("at_ref_no", "")).strip()
                prev_tbl.rows[idx].cells[2].paragraphs[0].text = str(itm.get("prev_qty", "")).strip()
                prev_tbl.rows[idx].cells[3].paragraphs[0].text = str(itm.get("unit_rate_incl_gst", "")).strip()
            else:
                nr = prev_tbl.add_row()
                nr.cells[0].paragraphs[0].text = str(itm.get("item_sl_no", "")).strip()
                nr.cells[1].paragraphs[0].text = str(itm.get("at_ref_no", "")).strip()
                nr.cells[2].paragraphs[0].text = str(itm.get("prev_qty", "")).strip()
                nr.cells[3].paragraphs[0].text = str(itm.get("unit_rate_incl_gst", "")).strip()
        # Remove any excess data rows beyond the items provided
        while len(prev_tbl.rows) > max(len(prev_items) + 1, 2):
            prev_tbl._tbl.remove(prev_tbl.rows[-1]._tr)

    # Update Negotiation nested table (Row 26)
    neg = data.get("negotiation_details", {})
    neg_rows = neg.get("rows", [])
    if len(t0.rows) > 26 and len(t0.rows[26].cells[0].tables) > 0:
        neg_tbl = t0.rows[26].cells[0].tables[0]
        for idx, r_data in enumerate(neg_rows, start=1):
            if idx < len(neg_tbl.rows):
                neg_tbl.rows[idx].cells[0].paragraphs[0].text = str(r_data[0]).strip()
                neg_tbl.rows[idx].cells[1].paragraphs[0].text = str(r_data[1]).strip()
                neg_tbl.rows[idx].cells[2].paragraphs[0].text = str(r_data[2]).strip()

    # -------------------------------------------------------------
    # 2. Narrative Clauses 1–9 (Paragraphs 4 to 12)
    # -------------------------------------------------------------
    clauses = data.get("narrative_clauses", [])
    clause_p_start = 4
    for idx, c in enumerate(clauses):
        p_idx = clause_p_start + idx
        if p_idx < len(doc.paragraphs):
            c_text = str(c).strip()
            prefix = f"{idx + 1}. " if not c_text.startswith(str(idx + 1)) else ""
            doc.paragraphs[p_idx].text = prefix + c_text

    # Save initial file to disk
    doc.save(output_path)

    # -------------------------------------------------------------
    # 3. Strict Post-Generation Disk Inspection & Validation
    # -------------------------------------------------------------
    validate_generated_docx(output_path)
    return output_path


def validate_generated_docx(docx_path: str):
    """
    Inspects the actual final generated DOCX from disk.
    Strictly verifies:
    - EMPTY VALUE CELLS = 0
    - FORBIDDEN PLACEHOLDER OCCURRENCES = 0
    - CONCATENATED HEADER OCCURRENCES = 0
    - EXTRA SECTION OCCURRENCES = 0
    - Narrative Clauses 1–9 present and non-empty
    - Previous Purchase & Negotiation tables complete
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Generated DOCX file not found at {docx_path}")

    saved_doc = docx.Document(docx_path)
    errors = []

    # 1. Extra Sections Check
    for p_idx, p in enumerate(saved_doc.paragraphs):
        p_txt = p.text.strip()
        for disallowed in DISALLOWED_EXTRA_SECTIONS:
            if disallowed.lower() in p_txt.lower():
                errors.append(f"Disallowed extra section '{disallowed}' found in Paragraph {p_idx}: '{p_txt}'")

    # 2. Narrative Clauses 1–9 Check
    clause_p_start = 4
    for c_num in range(1, 10):
        p_idx = clause_p_start + (c_num - 1)
        if p_idx >= len(saved_doc.paragraphs):
            errors.append(f"Narrative Clause {c_num} is missing from document paragraphs")
        else:
            c_txt = saved_doc.paragraphs[p_idx].text.strip()
            if not c_txt:
                errors.append(f"Narrative Clause {c_num} (Paragraph {p_idx}) is empty")
            for fb in FORBIDDEN_WORDS:
                if fb in ["-", "—", "*"]:
                    if c_txt == fb:
                        errors.append(f"Narrative Clause {c_num} consists solely of placeholder '{fb}'")
                elif re.search(r'\b' + re.escape(fb) + r'\b', c_txt, re.I):
                    errors.append(f"Narrative Clause {c_num} contains forbidden placeholder '{fb}'")

    # 3. Tables & Value Cells Check
    for t_idx, tbl in enumerate(saved_doc.tables):
        for r_idx, row in enumerate(tbl.rows):
            # Check for concatenated headers in every cell
            for c_idx, cell in enumerate(row.cells):
                txt = cell.text.strip()
                for bad_hdr in CONCATENATED_HEADER_PATTERNS:
                    if bad_hdr in txt:
                        errors.append(f"Concatenated header '{bad_hdr}' found in Table {t_idx} Row {r_idx} Col {c_idx}")
                for fb in FORBIDDEN_WORDS:
                    if fb in ["-", "—", "*"]:
                        if txt == fb:
                            errors.append(f"Forbidden placeholder '{fb}' found in Table {t_idx} Row {r_idx} Col {c_idx}")
                    elif re.search(r'\b' + re.escape(fb) + r'\b', txt, re.I):
                        if txt.lower() == fb or re.search(r'^(?:value|status)?\s*[:=\-]?\s*' + re.escape(fb) + r'\b', txt, re.I):
                            errors.append(f"Forbidden placeholder '{fb}' found in Table {t_idx} Row {r_idx} Col {c_idx}: '{txt}'")

            # Check 2-column key-value rows for empty values
            if len(row.cells) == 2:
                c0_txt = row.cells[0].text.strip()
                c1_txt = row.cells[1].text.strip()
                # Skip merged section header rows
                if row.cells[0]._tc is not row.cells[1]._tc and c0_txt.lower() != c1_txt.lower():
                    # Skip table header row
                    if c0_txt.lower() != "parameter":
                        if not c1_txt:
                            errors.append(f"Empty value cell for label '{c0_txt}' in Table {t_idx} Row {r_idx}")

    # 4. Nested Previous Purchase Table Check
    t0 = saved_doc.tables[0]
    if len(t0.rows) > 13 and len(t0.rows[13].cells[0].tables) > 0:
        prev_tbl = t0.rows[13].cells[0].tables[0]
        prev_hdr = [c.text.strip() for c in prev_tbl.rows[0].cells]
        if prev_hdr != ["Item sl. nos.", "AT ref. no.", "Previous purchase qty in nos./MT", "Unit rate incl. GST"]:
            errors.append(f"Previous Purchase Table header mismatch: {prev_hdr}")
        if len(prev_tbl.rows) < 2:
            errors.append("Previous Purchase Table has no data rows")
        for r_i, r in enumerate(prev_tbl.rows[1:], start=1):
            for c_i, c in enumerate(r.cells):
                if not c.text.strip():
                    errors.append(f"Empty cell in Previous Purchase Table Row {r_i} Col {c_i}")
                for fb in FORBIDDEN_WORDS:
                    if c.text.strip().lower() == fb:
                        errors.append(f"Forbidden placeholder '{fb}' in Previous Purchase Table Row {r_i} Col {c_i}")

    # 5. Nested Negotiation Table Check
    if len(t0.rows) > 26 and len(t0.rows[26].cells[0].tables) > 0:
        neg_tbl = t0.rows[26].cells[0].tables[0]
        neg_hdr = [c.text.strip() for c in neg_tbl.rows[0].cells]
        if neg_hdr != ["Parameter", "Tender Price", "After Negotiation"]:
            errors.append(f"Negotiation Table header mismatch: {neg_hdr}")
        if len(neg_tbl.rows) < 5:
            errors.append(f"Negotiation Table incomplete ({len(neg_tbl.rows)} rows < 5)")
        for r_i, r in enumerate(neg_tbl.rows[1:], start=1):
            for c_i, c in enumerate(r.cells):
                if not c.text.strip():
                    errors.append(f"Empty cell in Negotiation Table Row {r_i} Col {c_i}")
                for fb in FORBIDDEN_WORDS:
                    if c.text.strip().lower() == fb:
                        errors.append(f"Forbidden placeholder '{fb}' in Negotiation Table Row {r_i} Col {c_i}")

    if errors:
        try:
            os.remove(docx_path)
        except:
            pass
        raise ValueError(
            f"STRICT DOCX POST-GENERATION DISK VALIDATION FAILED ({len(errors)} violations):\n"
            + "\n".join(f"- {e}" for e in errors)
        )

    return True
