import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_TEMPLATE_DOCX = os.path.join(BASE_DIR, "test_proposal.docx")

FORBIDDEN_WORDS = [
    "not found", "not available", "not applicable", "n/a", "na",
    "unknown", "nil", "none", "no data", "unavailable", "cannot determine",
    "-", "—", "*"
]

def generate_purchase_proposal_docx(data: dict, output_path: str):
    """
    Populates the IMMUTABLE MASTER TEMPLATE DOCX (test_proposal.docx).
    Preserves all original tables, cells, widths, borders, styling, and page breaks.
    Never creates tables from scratch, never concatenates headers into 'ParameterValue'.
    Validates that every single value cell contains real source-supported data.
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
                label = row.cells[0].text.strip().lower()
                if label in field_map:
                    val = str(field_map[label]).strip()
                    row.cells[1].paragraphs[0].text = val
                    
    # Update Previous Purchase nested table (Row 13)
    prev_items = prev.get("items", [])
    if len(t0.rows) > 13 and len(t0.rows[13].cells[0].tables) > 0:
        prev_tbl = t0.rows[13].cells[0].tables[0]
        # Preserve header row (row 0), remove any extra old data rows
        while len(prev_tbl.rows) > 1:
            tr = prev_tbl.rows[-1]._tr
            prev_tbl._tbl.remove(tr)
            
        for itm in prev_items:
            nr = prev_tbl.add_row()
            nr.cells[0].paragraphs[0].text = str(itm.get("item_sl_no", "")).strip()
            nr.cells[1].paragraphs[0].text = str(itm.get("at_ref_no", "")).strip()
            nr.cells[2].paragraphs[0].text = str(itm.get("prev_qty", "")).strip()
            nr.cells[3].paragraphs[0].text = str(itm.get("unit_rate_incl_gst", "")).strip()

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

    # -------------------------------------------------------------
    # 3. Strict Programmatic Validation Before Saving
    # -------------------------------------------------------------
    validation_errors = []
    
    # Verify Table Headers are separate
    for t_idx, tbl in enumerate(doc.tables):
        for r_idx, row in enumerate(tbl.rows):
            # Check for header concatenation in single cells
            for c_idx, cell in enumerate(row.cells):
                txt = cell.text.strip()
                if "ParameterValue" in txt:
                    validation_errors.append(f"Concatenated ParameterValue found in Table {t_idx} Row {r_idx} Col {c_idx}")
                if "ParameterTender" in txt:
                    validation_errors.append(f"Concatenated ParameterTender found in Table {t_idx} Row {r_idx} Col {c_idx}")
                for bad in FORBIDDEN_WORDS:
                    if txt.lower() == bad:
                        validation_errors.append(f"Forbidden placeholder '{bad}' found in Table {t_idx} Row {r_idx} Col {c_idx}")
            
            # Check for empty value cells in 2-column key-value rows
            if len(row.cells) == 2:
                c0_txt = row.cells[0].text.strip().lower()
                c1_txt = row.cells[1].text.strip()
                # Skip section headers (where both cells are merged or header rows)
                if c0_txt != c1_txt.lower() and c0_txt not in ["parameter", "description of the item"]:
                    if not c1_txt:
                        validation_errors.append(f"Empty value cell for label '{row.cells[0].text.strip()}' in Table {t_idx} Row {r_idx}")

    # Verify nested previous purchase table
    if len(t0.rows) > 13 and len(t0.rows[13].cells[0].tables) > 0:
        prev_tbl = t0.rows[13].cells[0].tables[0]
        prev_hdr = [c.text.strip() for c in prev_tbl.rows[0].cells]
        if prev_hdr != ["Item sl. nos.", "AT ref. no.", "Previous purchase qty in nos./MT", "Unit rate incl. GST"]:
            validation_errors.append(f"Previous Purchase Table header mismatch: {prev_hdr}")
        for r_i, r in enumerate(prev_tbl.rows[1:], start=1):
            for c_i, c in enumerate(r.cells):
                if not c.text.strip():
                    validation_errors.append(f"Empty cell in Previous Purchase Table Row {r_i} Col {c_i}")

    # Verify nested negotiation table
    if len(t0.rows) > 26 and len(t0.rows[26].cells[0].tables) > 0:
        neg_tbl = t0.rows[26].cells[0].tables[0]
        neg_hdr = [c.text.strip() for c in neg_tbl.rows[0].cells]
        if neg_hdr != ["Parameter", "Tender Price", "After Negotiation"]:
            validation_errors.append(f"Negotiation Table header mismatch: {neg_hdr}")
        for r_i, r in enumerate(neg_tbl.rows[1:], start=1):
            for c_i, c in enumerate(r.cells):
                if not c.text.strip():
                    validation_errors.append(f"Empty cell in Negotiation Table Row {r_i} Col {c_i}")

    if validation_errors:
        raise ValueError(f"DOCX Generation Validation Failed:\n" + "\n".join(f"- {e}" for e in validation_errors))

    doc.save(output_path)
    return output_path
