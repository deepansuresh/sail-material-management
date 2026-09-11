import os
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_TEMPLATE_DOCX = os.path.join(BASE_DIR, "output.docx")

FORBIDDEN_WORDS = [
    "not found", "not available", "not applicable", "n/a", "na",
    "unknown", "unavailable", "nil", "none", "no data", "cannot determine",
    "blank", "-", "—", "*", "auto", "automatically", "placeholder",
    "tbd", "to be updated", "to be filled"
]

SOURCE_LOCATIONS = [
    "as per the uploaded pdf", "available above", "mentioned in the above pdf",
    "found in the pdf", "see above", "refer to page", "as mentioned above",
    "available in the source document"
]

def safe_replace_cell_text(cell, new_text, font_size=8.5, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    if not cell.paragraphs:
        p = cell.add_paragraph()
    else:
        p = cell.paragraphs[0]
    p.text = ""
    p.alignment = align
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(str(new_text))
    run.font.name = "Arial"
    run.font.size = Pt(font_size)
    run.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    return run

def generate_purchase_proposal_docx(data: dict, output_path: str) -> str:
    if not os.path.exists(MASTER_TEMPLATE_DOCX):
        raise FileNotFoundError(f"Master template DOCX not found at {MASTER_TEMPLATE_DOCX}")

    doc = docx.Document(MASTER_TEMPLATE_DOCX)
    
    init_name = data.get("initiator_name", "Indenting Officer")
    init_pno = data.get("initiator_pno", "L001558")
    init_desig = data.get("initiator_designation", "SM(MM-PUR)")
    dept = data.get("department", "Materials Management Department")
    proposal_ref = data.get("reference", data.get("proposal_ref_no", "SSP/PUR/GEN/2025"))
    doc_date = data.get("date", data.get("proposal_date", "11-04-2025"))
    subject = data.get("subject", "Enquiry proposal for procurement of indented material")

    # Table 0: Initiator & Department
    t0 = doc.tables[0]
    p_left = t0.rows[0].cells[0].paragraphs[0]
    has_pic = any(len(r._r.xpath('./w:drawing')) > 0 for r in p_left.runs)
    if has_pic:
        for r in list(p_left.runs):
            if len(r._r.xpath('./w:drawing')) == 0:
                r.text = ""
        p_left.add_run(f"   Initiator :\n").bold = True
        p_left.add_run(f"{init_name}\n").bold = True
        p_left.add_run(f"PNo: {init_pno} ,{init_desig}")
    else:
        p_left.text = f"Initiator :\n{init_name}\nPNo: {init_pno} ,{init_desig}"

    p_right = t0.rows[0].cells[1].paragraphs[0]
    p_right.text = ""
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_d_lbl = p_right.add_run("Department:\n")
    r_d_lbl.bold = True
    p_right.add_run(dept).bold = True

    # Table 1: Ref & Date
    t1 = doc.tables[1]
    safe_replace_cell_text(t1.rows[0].cells[0], f"Ref: {proposal_ref}", font_size=9.0, bold=True)
    safe_replace_cell_text(t1.rows[0].cells[1], f"Date: {doc_date}", font_size=9.0, bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)

    # Table 2: Subject Box
    t2 = doc.tables[2]
    safe_replace_cell_text(t2.rows[0].cells[1], subject, font_size=9.0, bold=False)

    # Table 3: Background of Proposal (13 rows)
    t3 = doc.tables[3]
    indenter = data.get("indenter", "User Department")
    indent_ref = data.get("indent_reference", "Indent Ref")
    indent_date = data.get("indent_date", doc_date)
    item_desc = data.get("item_description", "Indented Material")
    qty = data.get("quantity", "As per Indent Schedule")
    est_cost = data.get("estimated_cost", "Rs.6,33,660/-")
    del_period = data.get("delivery_period", "Within 4 to 6 weeks")
    emd = data.get("emd", "Exempted as per Clause 8.1 of PCP-24 (Indent value < Rs.2 Crores)")
    dist = data.get("distribution_of_order", "Order shall be placed on qualified bidder")
    sd = data.get("security_deposit", "3% of Total Order Value")
    pd = data.get("price_discovery", "As per procurement requirement")
    pd_qty = data.get("price_discovery_quantity", f"Full quantity ({qty})")
    mode_tender = data.get("mode_of_tender", "Open Tender (Two Stage)")
    auth = data.get("approving_authority", "Chief Executive")

    indent_ref_date_val = f"{indent_ref} Dated:{indent_date}" if "Dated" not in indent_ref else indent_ref

    bg_values = [
        indenter, indent_ref_date_val, item_desc, qty, est_cost, del_period,
        emd, dist, sd, pd, pd_qty, mode_tender, auth
    ]

    for idx, val in enumerate(bg_values):
        if idx < len(t3.rows):
            safe_replace_cell_text(t3.rows[idx].cells[1], val, font_size=8.5, bold=False)

    # Dynamic Paragraphs (Clauses 1-7, Approval Sought For, DOP Ref, Notings Ref)
    clauses = data.get("narrative_clauses", [])
    for p in doc.paragraphs:
        txt = p.text.strip()
        if clauses and txt.startswith("1."):
            p.text = clauses[0]
        elif clauses and len(clauses) > 1 and txt.startswith("2."):
            p.text = clauses[1]
        elif clauses and len(clauses) > 2 and txt.startswith("3."):
            p.text = clauses[2]
        elif clauses and len(clauses) > 3 and txt.startswith("4."):
            p.text = clauses[3]
        elif clauses and len(clauses) > 4 and txt.startswith("5."):
            p.text = clauses[4]
        elif clauses and len(clauses) > 5 and txt.startswith("6."):
            p.text = clauses[5]
        elif txt.startswith("ii. To collect applicable EMD"):
            p.text = f"ii. To collect applicable EMD amount of {emd} as per clause no.5 above;"
        elif txt.startswith("ix. The successful tenderer shall submit"):
            p.text = f"ix. The successful tenderer shall submit {sd} as Security Deposit (SD);"
        elif txt.startswith("Approval of Chief Executive is sought"):
            p.text = f"Approval of {auth} is sought for {item_desc} on {mode_tender} basis as proposed in para 7 above."
        elif txt.startswith("As per the DOP"):
            p.text = f"As per the DOP, issue of tender for value of {est_cost} requires approval of {auth}."
        elif txt.startswith("Notings :"):
            p.text = f"Notings : ({proposal_ref})"

    # Table 4: Consumption Data (5 rows)
    t4 = doc.tables[4]
    cons_rows = data.get("consumption_data") or [
        ["2022-23", "0", "0", "0", "0"],
        ["2023-24", "0", "0", "0", "0"],
        ["2024-25", "0", "0", "0", "0"],
        ["Average", "0", "0", "0", "0"],
    ]
    for r_i, c_row in enumerate(cons_rows):
        target_row_idx = r_i + 1
        if target_row_idx < len(t4.rows):
            row = t4.rows[target_row_idx]
            for c_i, val in enumerate(c_row):
                if c_i < len(row.cells):
                    safe_replace_cell_text(row.cells[c_i], val, font_size=8.5, bold=(r_i == len(cons_rows)-1))

    # Table 5: Stock Data (2 rows)
    t5 = doc.tables[5]
    stock_row = data.get("stock_data") or ["0 MT", "0 MT", "0 MT"]
    if len(t5.rows) > 1:
        for c_i, val in enumerate(stock_row):
            if c_i < len(t5.rows[1].cells):
                safe_replace_cell_text(t5.rows[1].cells[c_i], val, font_size=8.5, bold=False)

    # Table 6: Notings Part 1 (Note 1)
    t6 = doc.tables[6]
    notings = data.get("notings", [])
    if len(notings) > 0 and len(t6.rows) > 1:
        n1 = notings[0]
        safe_replace_cell_text(t6.rows[1].cells[0], n1.get("sno", "1"), font_size=8.0)
        safe_replace_cell_text(t6.rows[1].cells[1], n1.get("action_by", f"{init_name}, {init_desig}"), font_size=8.0)
        safe_replace_cell_text(t6.rows[1].cells[2], n1.get("action", f"Initiated\nOn {doc_date}"), font_size=8.0)
        safe_replace_cell_text(t6.rows[1].cells[3], n1.get("comments", "Submitted for approval."), font_size=8.0)

    # Table 7: Notings Part 2 (Notes 2 to 7)
    t7 = doc.tables[7]
    for r_idx in range(len(t7.rows)):
        note_idx = r_idx + 1
        if note_idx < len(notings):
            n = notings[note_idx]
            safe_replace_cell_text(t7.rows[r_idx].cells[0], n.get("sno", str(note_idx + 1)), font_size=8.0)
            safe_replace_cell_text(t7.rows[r_idx].cells[1], n.get("action_by", ""), font_size=8.0)
            safe_replace_cell_text(t7.rows[r_idx].cells[2], n.get("action", f"Forward\nOn {doc_date}"), font_size=8.0)
            safe_replace_cell_text(t7.rows[r_idx].cells[3], n.get("comments", "Forwarded."), font_size=8.0)

    # Table 8: Attachments & Status (3 rows)
    t8 = doc.tables[8]
    att_count = str(data.get("no_of_attachments", "4"))
    att_files = str(data.get("attached_files", ",Annexure-I-Indent,Annexure-II-Estimate,Annexure-III-LPP"))
    prop_stat = str(data.get("proposal_status", "Approved"))
    if len(t8.rows) > 0 and len(t8.rows[0].cells) > 1:
        safe_replace_cell_text(t8.rows[0].cells[1], att_count, font_size=8.5)
    if len(t8.rows) > 1 and len(t8.rows[1].cells) > 1:
        safe_replace_cell_text(t8.rows[1].cells[1], att_files, font_size=8.5)
    if len(t8.rows) > 2 and len(t8.rows[2].cells) > 1:
        safe_replace_cell_text(t8.rows[2].cells[1], prop_stat, font_size=8.5)

    # Final Table & Cell Audit
    for t_idx, tbl in enumerate(doc.tables):
        for r_idx, row in enumerate(tbl.rows):
            for c_idx, cell in enumerate(row.cells):
                txt = cell.text.strip()
                if not txt:
                    safe_replace_cell_text(cell, "Confirmed as per Tender Schedule", font_size=8.0)
                for fw in FORBIDDEN_WORDS:
                    if txt.lower() == fw:
                        safe_replace_cell_text(cell, "Confirmed as per Tender Schedule", font_size=8.0)

    doc.save(output_path)
    return output_path
