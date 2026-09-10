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

CONCATENATED_HEADER_PATTERNS = [
    "ParameterValue",
    "ParameterTender PriceAfter Negotiation",
    "Item sl. nos.AT ref. no.Previous purchase qty in nos./MTUnit rate incl. GST",
    "ParameterTender"
]

def safe_replace_cell_text(cell, new_text, font_size=9.0, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
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
    
    init_name = data.get("initiator_name", "SARAVANAN S")
    init_pno = data.get("initiator_pno", "L001558")
    init_desig = data.get("initiator_designation", "SM(MM-PUR)")
    dept = data.get("department", "HQ/MM PURCHASE/MM PURCHASE")
    proposal_ref = data.get("reference", data.get("proposal_ref_no", "SSP/SLM/MM PURCHASE/GEN/2025/214"))
    doc_date = data.get("date", data.get("proposal_date", "05-05-2025"))
    subject = data.get("subject", "Enquiry proposal for procurement of item")

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

    # Table 3: Background of Proposal
    t3 = doc.tables[3]
    indenter = data.get("indenter", "GM (SMS-O) MNT")
    indent_ref = data.get("indent_reference", "SMS/25/002")
    indent_date = data.get("indent_date", doc_date)
    item_desc = data.get("item_description", "Supply of MS Scrap Shredded")
    qty = data.get("quantity", "31,000 MT, Tolerance: +/- 25%")
    est_cost = data.get("estimated_cost", "Rs.1,32,27,32,800/-")
    del_period = data.get("delivery_period", "One month (staggered delivery)")
    emd = data.get("emd", "Rs.10,00,000/-")
    dist = data.get("distribution_of_order", "Order shall be placed on three parties")
    sd = data.get("security_deposit", "3% of Total Order Value")
    pd = data.get("price_discovery", "Monthly basis or as per SSP's production requirement")
    pd_qty = data.get("price_discovery_quantity", "4000 MT or as per SSP's production requirement")
    mode_tender = data.get("mode_of_tender", "Open Tender (Two Stage)")
    auth = data.get("approving_authority", "Chief Executive")

    indent_ref_date_val = f"{indent_ref} Dated:{indent_date}" if "Dated" not in indent_ref else indent_ref

    bg_values = [
        indenter, indent_ref_date_val, item_desc, qty, est_cost, del_period,
        emd, dist, sd, pd, pd_qty, mode_tender, auth
    ]

    for idx, val in enumerate(bg_values):
        align = WD_ALIGN_PARAGRAPH.RIGHT if idx in [4, 6] else WD_ALIGN_PARAGRAPH.LEFT
        safe_replace_cell_text(t3.rows[idx].cells[1], val, font_size=9.0, align=align)

    c1_text = f'1. Based on the Task Force Committee (TFC) recommendation, the above referred indent (Annexure I) was received from {indenter} for procurement of {qty} of "{item_desc}" on {mode_tender} basis at an estimated value of {est_cost} (Annexure II) with price discovery on {pd} with placement of order on {dist.lower() if "order" not in dist.lower() else dist}.'
    doc.paragraphs[2].text = c1_text

    c2_text = f'2. The estimate is based on LPP / budgetary estimate vide reference PO / indent enclosed as Annexure III. The last three years actual consumption enclosed as Annexure-IV is tabulated below'
    doc.paragraphs[3].text = c2_text

    t4 = doc.tables[4]
    cons_rows = data.get("consumption_data", [])
    if cons_rows and len(cons_rows) == 4:
        for r_idx, r_vals in enumerate(cons_rows, start=1):
            for c_idx, c_val in enumerate(r_vals):
                safe_replace_cell_text(t4.rows[r_idx].cells[c_idx], c_val, font_size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER if c_idx != 0 else WD_ALIGN_PARAGRAPH.LEFT)

    doc.paragraphs[4].text = f'3. The stock at site and pending supplies as on {indent_date} enclosed as Annexure-IV are tabulated below'

    t5 = doc.tables[5]
    stock_vals = data.get("stock_data", [])
    if stock_vals and len(stock_vals) == 3:
        for c_idx, s_val in enumerate(stock_vals):
            safe_replace_cell_text(t5.rows[1].cells[c_idx], s_val, font_size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER)

    c4_text = f'4. SMS Operation vide email dated:{indent_date} (copy enclosed) recommended to conduct price discovery for {pd_qty} towards first phase of price discovery through EPS. Since, the price discovery is on monthly basis for {pd_qty}, the eligibility criteria & EMD are fixed based on the monthly price discovery quantity of {pd_qty}.'
    doc.paragraphs[5].text = c4_text

    c5_text = f'5. As per the clause no.8.1 of PCP-24, EMD shall be taken in all procurement cases of Open Tenders with indent value Rs.2 Crores & above. Accordingly, applicable EMD amount of {emd} will be taken from the participating bidders. However, Micro & Small Enterprises (MSEs) / PSUs / Government Undertakings and Co-operative Societies / Start-ups as recognised by Department for Promotion of Industry and Internal Trade (DPIIT) will be exempted from submission of EMD as per extant Government policy.'
    doc.paragraphs[7].text = c5_text

    doc.paragraphs[8].text = '6. As per the extant guidelines of Government of India (GOI), purchase preference is applicable for MSE\'s as per PPP MSE\'s (Public Procurement Policy for MSE\'s) and for the Class I local suppliers as per PPP-MII policy (Public Procurement Policy - Make In India).'
    doc.paragraphs[9].text = '7. In view of the above, the following are proposed'

    sub_texts = [
        f"i. To issue an {mode_tender} enquiry through EPS;",
        f"ii. To collect applicable EMD amount of {emd} as per clause no.5 above;",
        f"iii. To reduce the procurement lead time, the tender opening date will be kept as 10 days from the date of issue of tender;",
        f"iv. LPP will be considered as estimate for subsequent RA's;",
        f"v. Techno-Commercial evaluation will be done for the first RA and the techno-commercially qualified suppliers will be considered as 'empanelled suppliers'. The offers of such techno-commercially qualified suppliers will be accepted for price discoveries, during the period of validity specified in the indent;",
        f"vi. Offers from new vendors will be techno-commercially evaluated offline. Upon successful techno-commercial evaluation, the new parties will be allowed to participate in the RA's along with the existing empanelled parties;",
        f"vii. In case of receipt of less than 'x+2' offers, the due date for tender submission will be extended suitably;",
        f'viii. Payment term will be "100% payment within 15 days from the date of acceptance supported by GARN/SRV and 3rd party certificate"',
        f"ix. The successful tenderer shall submit {sd} as Security Deposit (SD);",
    ]
    for p_offset, st in enumerate(sub_texts):
        doc.paragraphs[10 + p_offset].text = st

    doc.paragraphs[20].text = f"Approval of {auth} is sought for issue of {mode_tender} Enquiry as proposed above."
    doc.paragraphs[22].text = f"As per the DOP (Clause 1 of Page 24), issue of {mode_tender} enquiry for value above Rs.50 lakhs requires the approval of {auth}."
    doc.paragraphs[24].text = f"Notings : ({proposal_ref})"

    notings = data.get("notings", [])
    if notings:
        n0 = notings[0]
        safe_replace_cell_text(doc.tables[6].rows[1].cells[0], n0.get("sno", "1"), font_size=8.5)
        safe_replace_cell_text(doc.tables[6].rows[1].cells[1], n0.get("action_by", ""), font_size=8.5)
        safe_replace_cell_text(doc.tables[6].rows[1].cells[2], n0.get("action", ""), font_size=8.5)
        safe_replace_cell_text(doc.tables[6].rows[1].cells[3], n0.get("comments", ""), font_size=8.5)

        t7 = doc.tables[7]
        for r_idx, n_item in enumerate(notings[1:7]):
            if r_idx < len(t7.rows):
                safe_replace_cell_text(t7.rows[r_idx].cells[0], n_item.get("sno", str(r_idx + 2)), font_size=8.5)
                safe_replace_cell_text(t7.rows[r_idx].cells[1], n_item.get("action_by", ""), font_size=8.5)
                safe_replace_cell_text(t7.rows[r_idx].cells[2], n_item.get("action", ""), font_size=8.5)
                safe_replace_cell_text(t7.rows[r_idx].cells[3], n_item.get("comments", ""), font_size=8.5)

    t8 = doc.tables[8]
    no_att = data.get("no_of_attachments", "6")
    att_files = data.get("attached_files", ",Annexure-I-Indent,Annexure-II-Estimate,Annexure-III-LPP,Annexure-IV-3years-Consumption,SMSO-email,Work arrangement")
    status = data.get("proposal_status", "Approved")

    safe_replace_cell_text(t8.rows[0].cells[1], str(no_att), font_size=9.0)
    safe_replace_cell_text(t8.rows[1].cells[1], att_files, font_size=8.5)
    safe_replace_cell_text(t8.rows[2].cells[0], f"Proposal Status\n({proposal_ref})", font_size=9.0, bold=True)
    safe_replace_cell_text(t8.rows[2].cells[1], status, font_size=9.5, bold=True)

    doc.save(output_path)
    
    audit_doc = docx.Document(output_path)
    violations = []
    
    for t_idx, tbl in enumerate(audit_doc.tables):
        for r_idx, row in enumerate(tbl.rows):
            for c_idx, cell in enumerate(row.cells):
                txt = cell.text.strip()
                if not txt and (t_idx, r_idx, c_idx) not in [(4, 4, 1), (4, 4, 2), (4, 4, 3)]:
                    violations.append(f"Table {t_idx} Row {r_idx} Col {c_idx} is EMPTY!")
                for bad in CONCATENATED_HEADER_PATTERNS:
                    if bad in txt:
                        violations.append(f"Table {t_idx} Row {r_idx} Col {c_idx} CONCATENATED HEADER: {bad}")
                for fw in FORBIDDEN_WORDS:
                    if fw in ["-", "—", "*"]:
                        if txt == fw:
                            violations.append(f"Table {t_idx} Row {r_idx} Col {c_idx} PLACEHOLDER: {fw}")
                    elif fw == txt.lower():
                        violations.append(f"Table {t_idx} Row {r_idx} Col {c_idx} FORBIDDEN: {fw}")
                for sl in SOURCE_LOCATIONS:
                    if sl in txt.lower():
                        violations.append(f"Table {t_idx} Row {r_idx} Col {c_idx} SOURCE-LOCATION TEXT: {sl}")

    for p_idx, p in enumerate(audit_doc.paragraphs):
        p_txt = p.text.strip()
        for sl in SOURCE_LOCATIONS:
            if sl in p_txt.lower():
                violations.append(f"Paragraph {p_idx} contains SOURCE-LOCATION TEXT: {sl}")

    if violations:
        raise ValueError(f"Generated DOCX failed on-disk compliance audit with {len(violations)} violations:\n" + "\n".join(violations[:10]))

    return output_path
