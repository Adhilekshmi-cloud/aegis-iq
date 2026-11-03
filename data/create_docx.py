import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DATASET_DIR = r"c:\Users\adhil\OneDrive\Desktop\sybil\aegis-knowledge-system\data\aegis-dataset"
os.makedirs(DATASET_DIR, exist_ok=True)

def create_ecn_docx():
    doc = Document()

    # Page setup - 1 inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Header title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("AEGIS AEROSPACE SYSTEMS")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(12)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

    h1 = doc.add_heading("ENGINEERING CHANGE NOTICE", level=1)
    h1.paragraph_format.space_after = Pt(12)
    for run in h1.runs:
        run.font.name = "Arial"
        run.font.size = Pt(18)
        run.font.color.rgb = RGBColor(0x2B, 0x6C, 0xB0)

    # Metadata Table
    table = doc.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    metadata = [
        ("ECN Number:", "ECN-2847", "Date:", "2024-06-01"),
        ("System Designation:", "Aegis Series-7 Hydraulic Control System", "Effective Applicability:", "Revision B, S/N 1042 and subsequent"),
        ("Originator:", "J. Martinez, Chief Hydraulic Engineer", "Department:", "Hydraulic Flight Controls Engineering"),
        ("Status:", "APPROVED FOR IMPLEMENTATION", "Priority Level:", "MANDATORY FLIGHT SAFETY RETROFIT")
    ]

    for row_idx, data in enumerate(metadata):
        row = table.rows[row_idx]
        cell_0 = row.cells[0]
        cell_1 = row.cells[1]
        
        cell_0.text = f"{data[0]} {data[1]}"
        cell_1.text = f"{data[2]} {data[3]}"

        for cell in (cell_0, cell_1):
            shading = parse_xml(r'<w:shd {} w:fill="F0F4F8"/>'.format(nsdecls('w')))
            cell._tc.get_or_add_tcPr().append(shading)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.space_before = Pt(2)
                for r in p.runs:
                    r.font.name = "Calibri"
                    r.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Section 1
    h2 = doc.add_heading("1. Change Description & Detailed Rationale", level=2)
    for run in h2.runs:
        run.font.name = "Arial"
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0x2C, 0x52, 0x82)

    # Item 1: Servo Valve Upgrade
    p = doc.add_paragraph()
    r = p.add_run("1.1 Item 1: Servo Valve Upgrade (SV-4200 → SV-4200A)")
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(11)

    bullets1 = [
        ("Part Number Supercession: ", "Replace SV-4200 with SV-4200A across all Series-7 installations."),
        ("Part Number Change: ", "SV-4200 \u2192 SV-4200A"),
        ("Flow Rate Specification: ", "Revised to 18 GPM nominal (increased from previous 15 GPM standard)."),
        ("Response Time Performance: ", "Step input response time improved to 6 ms (reduced from 8 ms baseline; legacy valves in field exhibited up to 10-12 ms latency)."),
        ("Engineering Rationale: ", "Field operational reports (ref DR-2024-0147) and aerodynamic flutter trials indicated that the legacy SV-4200 response time was marginal during high-alpha rapid maneuvering regimes, causing momentary control surface lag.")
    ]
    for prefix, body in bullets1:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(2)
        pr = bp.add_run(prefix)
        pr.bold = True
        pr.font.name = "Calibri"
        br = bp.add_run(body)
        br.font.name = "Calibri"

    # Item 2: Operating Pressure Revision
    p2 = doc.add_paragraph()
    p2.paragraph_format.space_before = Pt(6)
    r2 = p2.add_run("1.2 Item 2: Operating Pressure Envelope Revision")
    r2.bold = True
    r2.font.name = "Calibri"
    r2.font.size = Pt(11)

    bullets2 = [
        ("System Nominal Pressure: ", "Nominal operating pressure revised to 3200 PSI (Previous Rev A specification: 3000 PSI). Steady-state tolerance 3100\u20133350 PSI."),
        ("Proof Pressure Standard: ", "Proof pressure revised to 4000 PSI (Previous specification: 3750 PSI)."),
        ("Burst Pressure Margin: ", "Burst pressure revised to 4800 PSI (Previous specification: 4500 PSI)."),
        ("Engineering Rationale: ", "Enhanced primary flight actuator authority and surface holding stiffness required for the expanded high-dynamic-pressure flight envelope.")
    ]
    for prefix, body in bullets2:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(2)
        pr = bp.add_run(prefix)
        pr.bold = True
        pr.font.name = "Calibri"
        br = bp.add_run(body)
        br.font.name = "Calibri"

    # Item 3: Accumulator Precharge Update
    p3 = doc.add_paragraph()
    p3.paragraph_format.space_before = Pt(6)
    r3 = p3.add_run("1.3 Item 3: Hydraulic Accumulator Precharge Adjustment")
    r3.bold = True
    r3.font.name = "Calibri"
    r3.font.size = Pt(11)

    bullets3 = [
        ("Previous Precharge: ", "1500 PSI at 20\u00b0C ambient (ACC-1800)."),
        ("New Precharge Specification: ", "1600 PSI at 20\u00b0C ambient (ACC-1800 Rev B calibration)."),
        ("Engineering Rationale: ", "Higher operating system pressure (3200 PSI) necessitates adjusted precharge pressure ratio to maintain optimum pulsation damping volume and emergency reserve delivery.")
    ]
    for prefix, body in bullets3:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(2)
        pr = bp.add_run(prefix)
        pr.bold = True
        pr.font.name = "Calibri"
        br = bp.add_run(body)
        br.font.name = "Calibri"

    # Section 2: Affected Documents
    h2_docs = doc.add_heading("2. Affected Technical Documentation", level=2)
    for run in h2_docs.runs:
        run.font.name = "Arial"
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0x2C, 0x52, 0x82)

    aff_p = doc.add_paragraph("The following technical manuals and specifications are impacted by this Engineering Change Notice and are scheduled for concurrent update:")
    for doc_name, doc_id in [
        ("Operator Manual", "OM-S7-001"),
        ("Maintenance Guide", "MG-S7-001"),
        ("Component Specifications", "CS-S7-001")
    ]:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(2)
        r_name = bp.add_run(f"{doc_name} ")
        r_name.bold = True
        r_id = bp.add_run(f"(Document Reference: {doc_id})")

    # Section 3: Approvals
    h2_app = doc.add_heading("3. Verification & Engineering Approvals", level=2)
    for run in h2_app.runs:
        run.font.name = "Arial"
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(0x2C, 0x52, 0x82)

    app_table = doc.add_table(rows=4, cols=4)
    app_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    app_headers = ["Role / Authority", "Signee Name", "Date", "Status"]
    hdr_row = app_table.rows[0]
    for i, title in enumerate(app_headers):
        hdr_row.cells[i].text = title
        shd = parse_xml(r'<w:shd {} w:fill="2B6CB0"/>'.format(nsdecls('w')))
        hdr_row.cells[i]._tc.get_or_add_tcPr().append(shd)
        for p in hdr_row.cells[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    app_data = [
        ("Engineering Authority", "J. Martinez, Chief Hydraulic Engineer", "2024-05-28", "APPROVED"),
        ("Quality Assurance", "R. Chen, Quality Assurance Manager", "2024-05-30", "APPROVED"),
        ("Configuration Management", "A. Patel, CM Lead", "2024-06-01", "RELEASED")
    ]
    for r_idx, d in enumerate(app_data):
        row = app_table.rows[r_idx + 1]
        for c_idx, val in enumerate(d):
            row.cells[c_idx].text = val
            for p in row.cells[c_idx].paragraphs:
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.space_before = Pt(2)
                for r in p.runs:
                    r.font.name = "Calibri"
                    r.font.size = Pt(9.5)

    target_path = os.path.join(DATASET_DIR, "engineering_change_notice_ECN_2847.docx")
    doc.save(target_path)
    print(f"Saved: {target_path}")

if __name__ == "__main__":
    create_ecn_docx()
