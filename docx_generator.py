import os
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "static", "assets")
LOGO_DOC_PATH = os.path.join(ASSETS_DIR, "sail_logo_doc.png")
LOGO_TRANS_PATH = os.path.join(ASSETS_DIR, "sail_logo_transparent.png")
LOGO_CROP_PATH = os.path.join(ASSETS_DIR, "sail_logo.png")


def set_cell_background(cell, hex_color):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=60, bottom=60, left=100, right=100):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_table_borders(table, color="CCCCCC", sz="4", val="single"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)


def clean_text(s):
    if s is None:
        return "Not found in source document"
    s = str(s).strip()
    if not s or s.lower() in ["none", "null", "n/a", "na", "nil"]:
        return "Not found in source document"
    return s


def generate_purchase_proposal_docx(data: dict, output_path: str) -> str:
    """
    Generates an official Word document matching the Master Procurement Template
    with the SAIL logo, exact 13 Background fields, Proposal clauses, and tables.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = docx.Document()

    # Set 0.5 inch margins all around
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    primary_blue = RGBColor(0, 51, 102)     # #003366
    accent_blue = RGBColor(30, 64, 175)     # #1e40af
    dark_gray = RGBColor(30, 41, 59)        # #1e293b
    muted_gray = RGBColor(71, 85, 105)      # #475569

    best_logo = LOGO_DOC_PATH if os.path.exists(LOGO_DOC_PATH) else (
        LOGO_TRANS_PATH if os.path.exists(LOGO_TRANS_PATH) else LOGO_CROP_PATH
    )

    plant_code = clean_text(data.get("plant_code", "SSP - Salem Steel Plant"))
    doc_seq = clean_text(data.get("document_sequence", "SSP/PUR/PROPOSAL/2025-26"))
    initiator_name = clean_text(data.get("initiator_name", "SARAVANAN S"))
    initiator_pno = clean_text(data.get("initiator_pno", "L001558"))
    initiator_desig = clean_text(data.get("initiator_designation", "SM (MM-PUR)"))
    dept = clean_text(data.get("department", "HQ/MM PURCHASE/MM PURCHASE"))
    ref_no = clean_text(data.get("reference", "SSP/SLM/MM PURCHASE/GEN/2025/214"))
    doc_date = clean_text(data.get("date", "05-05-2025"))
    subject = clean_text(data.get("subject", "Enquiry proposal for procurement of MS Scrap Shredded through EPS"))

    # -------------------------------------------------------------
    # 1. HEADER WITH SAIL LOGO & METADATA TABLE
    # -------------------------------------------------------------
    header_table = doc.add_table(rows=1, cols=3)
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(header_table, color="FFFFFF", sz="0", val="none")
    header_table.rows[0].cells[0].width = Inches(1.0)
    header_table.rows[0].cells[1].width = Inches(4.2)
    header_table.rows[0].cells[2].width = Inches(2.3)

    # Logo cell
    cell_logo = header_table.rows[0].cells[0]
    p_logo = cell_logo.paragraphs[0]
    p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.exists(best_logo):
        try:
            p_logo.add_run().add_picture(best_logo, width=Inches(0.85))
        except Exception:
            pass

    # Title cell
    cell_title = header_table.rows[0].cells[1]
    p1 = cell_title.paragraphs[0]
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(2)
    r1 = p1.add_run("STEEL AUTHORITY OF INDIA LIMITED\n")
    r1.font.name = "Calibri"
    r1.font.size = Pt(11)
    r1.font.bold = True
    r1.font.color.rgb = primary_blue

    r2 = p1.add_run("SALEM STEEL PLANT • MATERIALS MANAGEMENT MODULE\n")
    r2.font.name = "Calibri"
    r2.font.size = Pt(9)
    r2.font.bold = True
    r2.font.color.rgb = muted_gray

    r3 = p1.add_run(f"Plant Code: {plant_code}   |   Doc Seq: {doc_seq}\nDepartment: {dept}\nInitiator: {initiator_name}  (PNo: {initiator_pno}, {initiator_desig})")
    r3.font.name = "Calibri"
    r3.font.size = Pt(8.5)
    r3.font.color.rgb = dark_gray

    # Meta cell
    cell_meta = header_table.rows[0].cells[2]
    p_meta = cell_meta.paragraphs[0]
    p_meta.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_meta.paragraph_format.space_before = Pt(0)
    p_meta.paragraph_format.space_after = Pt(2)
    rm1 = p_meta.add_run(f"Ref: {ref_no}\nDate: {doc_date}\n\n")
    rm1.font.name = "Calibri"
    rm1.font.size = Pt(8.5)
    rm1.font.color.rgb = dark_gray

    rm2 = p_meta.add_run("PURCHASE PROPOSAL NOTE\n")
    rm2.font.name = "Calibri"
    rm2.font.size = Pt(9.5)
    rm2.font.bold = True
    rm2.font.color.rgb = accent_blue

    rm3 = p_meta.add_run("STATUS: CONFIRMED")
    rm3.font.name = "Calibri"
    rm3.font.size = Pt(8.5)
    rm3.font.bold = True
    rm3.font.color.rgb = RGBColor(4, 120, 87)

    # Divider line
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(4)
    p_div.paragraph_format.space_after = Pt(4)
    r_line = p_div.add_run("―" * 68)
    r_line.font.name = "Calibri"
    r_line.font.size = Pt(9)
    r_line.font.color.rgb = primary_blue

    # Subject Box
    subj_table = doc.add_table(rows=1, cols=2)
    subj_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(subj_table, color="94A3B8", sz="4", val="single")
    subj_table.rows[0].cells[0].width = Inches(0.9)
    subj_table.rows[0].cells[1].width = Inches(6.6)
    set_cell_background(subj_table.rows[0].cells[0], "F1F5F9")
    set_cell_background(subj_table.rows[0].cells[1], "F8FAFC")

    ps0 = subj_table.rows[0].cells[0].paragraphs[0]
    rs0 = ps0.add_run("Subject:")
    rs0.font.name = "Calibri"
    rs0.font.size = Pt(9)
    rs0.font.bold = True
    rs0.font.color.rgb = primary_blue

    ps1 = subj_table.rows[0].cells[1].paragraphs[0]
    rs1 = ps1.add_run(subject)
    rs1.font.name = "Calibri"
    rs1.font.size = Pt(9)
    rs1.font.color.rgb = dark_gray

    # -------------------------------------------------------------
    # 2. BACKGROUND OF THE PROPOSAL (Strict 13 Fields)
    # -------------------------------------------------------------
    p_h2 = doc.add_paragraph()
    p_h2.paragraph_format.space_before = Pt(8)
    p_h2.paragraph_format.space_after = Pt(4)
    rh2 = p_h2.add_run("Background of the Proposal")
    rh2.font.name = "Calibri"
    rh2.font.size = Pt(10)
    rh2.font.bold = True
    rh2.font.color.rgb = primary_blue

    bg_fields = [
        ("i) Indenter", clean_text(data.get("indenter", "GM (SMS-O) MNT"))),
        ("ii) Indent ref no & date", clean_text(data.get("indent_reference", "SMS/25/002") + (" Dated: " + str(data.get("indent_date", "")) if data.get("indent_date") else ""))),
        ("iii) Description of the item", clean_text(data.get("item_description", "MS SCRAP - SHREDDED"))),
        ("iv) Quantity / Tolerance", clean_text(f"{data.get('quantity', '')} {data.get('tolerance', '')}".strip() or "31,000 MT, Tolerance: +/- 25%")),
        ("v) Estimated Cost", clean_text(data.get("estimated_cost", "Rs.1,32,27,32,800/-"))),
        ("vi) Delivery Period", clean_text(data.get("delivery_period", "One month (staggered delivery)"))),
        ("vii) EMD", clean_text(data.get("emd", "Rs.10,00,000/-"))),
        ("viii) Distribution of order", clean_text(data.get("distribution_of_order", "Order shall be placed on three parties"))),
        ("ix) Security Deposit", clean_text(data.get("security_deposit", "3% of Total Order Value"))),
        ("x) Price Discovery", clean_text(data.get("price_discovery", "Monthly basis or as per SSP's production requirement"))),
        ("xi) Quantity for each Price Discovery", clean_text(data.get("price_discovery_quantity", "4000 MT or as per SSP's production requirement"))),
        ("xii) Mode of Tender", clean_text(data.get("mode_of_tender", "Open Tender (Two Stage) through EPS"))),
        ("xiii) Approving Authority", clean_text(data.get("approving_authority", "Chief Executive")))
    ]

    bg_table = doc.add_table(rows=len(bg_fields), cols=2)
    bg_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(bg_table, color="CBD5E1", sz="4", val="single")
    for idx, (label, val) in enumerate(bg_fields):
        row = bg_table.rows[idx]
        row.cells[0].width = Inches(2.6)
        row.cells[1].width = Inches(4.9)
        set_cell_margins(row.cells[0], top=35, bottom=35, left=60, right=60)
        set_cell_margins(row.cells[1], top=35, bottom=35, left=60, right=60)
        if idx % 2 == 1:
            set_cell_background(row.cells[0], "F8FAFC")
            set_cell_background(row.cells[1], "F8FAFC")

        p_lbl = row.cells[0].paragraphs[0]
        p_lbl.paragraph_format.space_before = Pt(0)
        p_lbl.paragraph_format.space_after = Pt(0)
        rlbl = p_lbl.add_run(label)
        rlbl.font.name = "Calibri"
        rlbl.font.size = Pt(8.5)
        rlbl.font.bold = True
        rlbl.font.color.rgb = primary_blue

        p_val = row.cells[1].paragraphs[0]
        p_val.paragraph_format.space_before = Pt(0)
        p_val.paragraph_format.space_after = Pt(0)
        rval = p_val.add_run(val)
        rval.font.name = "Calibri"
        rval.font.size = Pt(8.5)
        rval.font.color.rgb = dark_gray

    # -------------------------------------------------------------
    # 3. PROPOSAL DETAILS (Numbered Clauses)
    # -------------------------------------------------------------
    p_h3 = doc.add_paragraph()
    p_h3.paragraph_format.space_before = Pt(8)
    p_h3.paragraph_format.space_after = Pt(4)
    rh3 = p_h3.add_run("Proposal Details")
    rh3.font.name = "Calibri"
    rh3.font.size = Pt(10)
    rh3.font.bold = True
    rh3.font.color.rgb = primary_blue

    proposal_details = data.get("proposal_details", [])
    if not proposal_details or not isinstance(proposal_details, list) or len(proposal_details) == 0:
        ind_no = clean_text(data.get("indent_reference", "above referred indent"))
        ind_dept = clean_text(data.get("department", "the user department"))
        item_d = clean_text(data.get("item_description", "the indented item"))
        qty_tol = clean_text(f"{data.get('quantity', '')} (Tolerance: {data.get('tolerance', '')})")
        est_c = clean_text(data.get("estimated_cost", ""))
        tender_m = clean_text(data.get("mode_of_tender", "Open Tender basis"))
        dist_ord = clean_text(data.get("distribution_of_order", "multiple parties"))
        emd_amt = clean_text(data.get("emd", "applicable EMD"))
        sd_amt = clean_text(data.get("security_deposit", "3% of Total Order Value"))

        proposal_details = [
            f"1. Based on the indent recommendations, the above referred indent ({ind_no}) was received from {ind_dept} for procurement of {qty_tol} of \"{item_d}\" on {tender_m} at an estimated value of {est_c} with order distribution as {dist_ord}.",
            f"2. The estimate is framed based on Last Purchase Price (LPP) / realistic market budgetary estimates in compliance with standard Salem Steel Plant Purchase Policy guidelines.",
            f"3. The stock position at site and pending supplies have been reviewed to ensure continuity of operations without inventory stockout or unnecessary overstocking.",
            f"4. The procurement schedule and phased discovery quantities are formulated based on production requirement to optimize procurement lead time and cash flow.",
            f"5. As per the clause no.8.1 of PCP-24, EMD shall be taken in all procurement cases of Open Tenders with indent value Rs.2 Crores & above. Accordingly, {emd_amt} will be taken from participating bidders. Micro & Small Enterprises (MSEs) / PSUs / Start-ups will be exempted as per extant Government policy.",
            f"6. As per extant guidelines of Government of India (GOI), purchase preference is applicable for MSEs as per PPP-MSE policy and for Class I local suppliers as per PPP-MII policy (Public Procurement Policy - Make In India).",
            f"7. In view of the above, the following are proposed:\n"
            f"   i. To issue {tender_m};\n"
            f"   ii. To collect {emd_amt} as per clause no.5 above;\n"
            f"   iii. To keep tender opening date as 10 to 15 days from issue date to minimize procurement lead time;\n"
            f"   iv. Techno-commercial evaluation will be completed strictly as per tender qualification criteria;\n"
            f"   v. Payment term will be 100% payment within 15 days from date of acceptance supported by GARN/SRV and inspection certificate;\n"
            f"   vi. The successful tenderer shall submit {sd_amt} as Security Deposit (SD)."
        ]

    for clause in proposal_details:
        p_c = doc.add_paragraph()
        p_c.paragraph_format.space_before = Pt(1)
        p_c.paragraph_format.space_after = Pt(3)
        rc = p_c.add_run(clause)
        rc.font.name = "Calibri"
        rc.font.size = Pt(8.5)
        rc.font.color.rgb = dark_gray

    # -------------------------------------------------------------
    # 4. CONSUMPTION DETAILS TABLE
    # -------------------------------------------------------------
    p_h4 = doc.add_paragraph()
    p_h4.paragraph_format.space_before = Pt(8)
    p_h4.paragraph_format.space_after = Pt(2)
    rh4 = p_h4.add_run("Consumption Details")
    rh4.font.name = "Calibri"
    rh4.font.size = Pt(10)
    rh4.font.bold = True
    rh4.font.color.rgb = primary_blue

    cons_headers = [
        "Financial Year",
        f"Consumption of {data.get('item_description', 'Item')[:25]} (MT)",
        "Slab Production (MT)",
        "No. of Converters",
        "Specific Consumption (MT/Converter)"
    ]
    cons_table = doc.add_table(rows=1, cols=5)
    cons_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(cons_table, color="94A3B8", sz="4", val="single")
    for c_idx, h_text in enumerate(cons_headers):
        cell = cons_table.rows[0].cells[c_idx]
        set_cell_background(cell, "F1F5F9")
        set_cell_margins(cell, top=40, bottom=40, left=50, right=50)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.font.name = "Calibri"
        r.font.size = Pt(8)
        r.font.bold = True
        r.font.color.rgb = primary_blue

    default_cons_rows = [
        ["2022-23", "24,477", "1,40,050", "23", "1,064"],
        ["2023-24", "25,249", "1,52,493", "24", "1,052"],
        ["2024-25", "32,248", "1,45,891", "24", "1,344"],
        ["Average", "-", "-", "-", "1,153"]
    ]
    for row_data in default_cons_rows:
        row = cons_table.add_row()
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            set_cell_margins(cell, top=30, bottom=30, left=50, right=50)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(8)
            if row_data[0] == "Average":
                r.font.bold = True
                set_cell_background(cell, "F8FAFC")

    # -------------------------------------------------------------
    # 5. STOCK AND PENDING SUPPLIES TABLE
    # -------------------------------------------------------------
    p_h5 = doc.add_paragraph()
    p_h5.paragraph_format.space_before = Pt(8)
    p_h5.paragraph_format.space_after = Pt(2)
    rh5 = p_h5.add_run("Stock and Pending Supplies")
    rh5.font.name = "Calibri"
    rh5.font.size = Pt(10)
    rh5.font.bold = True
    rh5.font.color.rgb = primary_blue

    stock_table = doc.add_table(rows=2, cols=3)
    stock_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(stock_table, color="94A3B8", sz="4", val="single")
    for c_idx, h_text in enumerate(["Stock at site", "Pending supply", "Stock & pending supplies"]):
        cell = stock_table.rows[0].cells[c_idx]
        set_cell_background(cell, "F1F5F9")
        set_cell_margins(cell, top=40, bottom=40, left=50, right=50)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.font.name = "Calibri"
        r.font.size = Pt(8.5)
        r.font.bold = True
        r.font.color.rgb = primary_blue

    stock_vals = ["2,494 MT", "281 MT", "2,775 MT"]
    for c_idx, val in enumerate(stock_vals):
        cell = stock_table.rows[1].cells[c_idx]
        set_cell_margins(cell, top=35, bottom=35, left=50, right=50)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(val)
        r.font.name = "Calibri"
        r.font.size = Pt(8.5)
        if c_idx == 2:
            r.font.bold = True

    # -------------------------------------------------------------
    # 6. APPROVAL SOUGHT FOR & DOP REFERENCE
    # -------------------------------------------------------------
    p_h6 = doc.add_paragraph()
    p_h6.paragraph_format.space_before = Pt(8)
    p_h6.paragraph_format.space_after = Pt(2)
    rh6 = p_h6.add_run("Approval Sought for")
    rh6.font.name = "Calibri"
    rh6.font.size = Pt(10)
    rh6.font.bold = True
    rh6.font.color.rgb = primary_blue

    p_as = doc.add_paragraph()
    p_as.paragraph_format.space_before = Pt(1)
    p_as.paragraph_format.space_after = Pt(4)
    ras = p_as.add_run(clean_text(data.get("approval_sought", f"Approval of {data.get('approving_authority', 'Competent Authority')} is sought for issue of {data.get('mode_of_tender', 'Open Tender Enquiry')} as proposed above.")))
    ras.font.name = "Calibri"
    ras.font.size = Pt(8.5)

    p_h7 = doc.add_paragraph()
    p_h7.paragraph_format.space_before = Pt(6)
    p_h7.paragraph_format.space_after = Pt(2)
    rh7 = p_h7.add_run("DOP / Manual / Circular Ref & Approver")
    rh7.font.name = "Calibri"
    rh7.font.size = Pt(10)
    rh7.font.bold = True
    rh7.font.color.rgb = primary_blue

    p_dop = doc.add_paragraph()
    p_dop.paragraph_format.space_before = Pt(1)
    p_dop.paragraph_format.space_after = Pt(2)
    rdop = p_dop.add_run(clean_text(data.get("dop_reference", "As per the Delegation of Powers (DOP), issue of Open Tender enquiry for the sanctioned indent value requires approval of the Competent Authority.")))
    rdop.font.name = "Calibri"
    rdop.font.size = Pt(8.5)

    p_app = doc.add_paragraph()
    p_app.paragraph_format.space_before = Pt(0)
    p_app.paragraph_format.space_after = Pt(4)
    rapp = p_app.add_run(f"Designated Approver Routing: {data.get('approver', 'SM (MM-P) / GM (MM-P) / GM I/c (MM) / CGM (Maint, Steel & Projects) / CGM I/c (W) / CGM (F&A) / ED')}")
    rapp.font.name = "Calibri"
    rapp.font.size = Pt(8)
    rapp.font.bold = True
    rapp.font.color.rgb = muted_gray

    # -------------------------------------------------------------
    # 7. NOTINGS TABLE
    # -------------------------------------------------------------
    p_h8 = doc.add_paragraph()
    p_h8.paragraph_format.space_before = Pt(6)
    p_h8.paragraph_format.space_after = Pt(2)
    rh8 = p_h8.add_run(f"Notings : ({ref_no})")
    rh8.font.name = "Calibri"
    rh8.font.size = Pt(10)
    rh8.font.bold = True
    rh8.font.color.rgb = primary_blue

    notings_table = doc.add_table(rows=1, cols=4)
    notings_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(notings_table, color="94A3B8", sz="4", val="single")
    for c_idx, h_text in enumerate(["SNo", "Action By", "Action", "Comments"]):
        cell = notings_table.rows[0].cells[c_idx]
        set_cell_background(cell, "F1F5F9")
        set_cell_margins(cell, top=35, bottom=35, left=50, right=50)
        p = cell.paragraphs[0]
        r = p.add_run(h_text)
        r.font.name = "Calibri"
        r.font.size = Pt(8)
        r.font.bold = True
        r.font.color.rgb = primary_blue

    default_notings = [
        ("1", "PATRI PRATHIMA, PNo: C003320\nGENERAL MANAGER (PURCHASE)", "Forward\n05-05-2025", "Forwarded."),
        ("2", "MANOJ M, PNo: L000108\nGM I/c (MM)", "Forward\n06-05-2025", "Forwarded."),
        ("3", "RAVI CHANDER DV, PNo: L000111\nCGM (MAINTENANCE, STEEL & PROJECTS)", "Forward\n06-05-2025", "Forwarded. Also on behalf of CGM I/c(W)."),
        ("4", "KISHOR JETHABHAI CHAUHAN, PNo: I000236\nCGM (F&A)", "Forward\n06-05-2025", "Examined. Concurred."),
        ("5", "PRABIR KUMAR SARKAR, PNo: B001402\nEXECUTIVE DIRECTOR", "Approved\n08-05-2025", "Approved as proposed.")
    ]
    for n_data in default_notings:
        row = notings_table.add_row()
        for c_idx, val in enumerate(n_data):
            cell = row.cells[c_idx]
            set_cell_margins(cell, top=30, bottom=30, left=50, right=50)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.name = "Calibri"
            r.font.size = Pt(8)

    # -------------------------------------------------------------
    # 8. ATTACHMENTS & SIGNATURE
    # -------------------------------------------------------------
    att_count = str(data.get("attachment_count", len(data.get("attachments", [])) or "6"))
    att_files = clean_text(data.get("attached_files", "Annexure-I-Indent, Annexure-II-Estimate, Annexure-III-LPP, Annexure-IV-3years-Consumption, Indenter-email, DOP-reference"))
    prop_stat = clean_text(data.get("proposal_status", "APPROVED"))

    sign_table = doc.add_table(rows=1, cols=2)
    sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(sign_table, color="94A3B8", sz="4", val="single")
    sign_table.rows[0].cells[0].width = Inches(4.7)
    sign_table.rows[0].cells[1].width = Inches(2.8)
    set_cell_background(sign_table.rows[0].cells[0], "F1F5F9")
    set_cell_background(sign_table.rows[0].cells[1], "F1F5F9")

    psign0 = sign_table.rows[0].cells[0].paragraphs[0]
    rsign0 = psign0.add_run(f"No. of attachments: {att_count}\nAttached Files: {att_files}\nProposal Status: {prop_stat}")
    rsign0.font.name = "Calibri"
    rsign0.font.size = Pt(8)
    rsign0.font.bold = True

    psign1 = sign_table.rows[0].cells[1].paragraphs[0]
    rsign1 = psign1.add_run(f"Initiator Signature:\n\n{initiator_name}\n{initiator_desig}\nPNo: {initiator_pno}")
    rsign1.font.name = "Calibri"
    rsign1.font.size = Pt(8.5)
    rsign1.font.bold = True

    doc.save(output_path)
    print(f"[DOCX_GENERATOR] Successfully created official proposal DOCX at: {output_path}", flush=True)
    return output_path
