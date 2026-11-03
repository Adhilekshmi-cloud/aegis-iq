import os
import sys
import subprocess

DATASET_DIR = r"c:\Users\adhil\OneDrive\Desktop\sybil\aegis-knowledge-system\data\aegis-dataset"
os.makedirs(DATASET_DIR, exist_ok=True)
target_path = os.path.join(DATASET_DIR, "training_presentation.pptx")

try:
    import pptx
except ImportError:
    print("Installing python-pptx...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-pptx"])
        import pptx
    except Exception as e:
        print(f"Pip install failed: {e}")
        pptx = None

if pptx:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    prs = Presentation()
    # 16:9 widescreen layout
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6] # blank

    def add_header(slide, title_text):
        tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(0.8))
        tf = tx_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.name = "Arial"
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

    # Slide 1: Title slide
    title_slide_layout = prs.slide_layouts[0]
    slide1 = prs.slides.add_slide(title_slide_layout)
    title = slide1.shapes.title
    subtitle = slide1.placeholders[1]
    title.text = "Aegis Series-7 Hydraulic Control System - Maintenance Training"
    subtitle.text = "Revision B - Updated June 2024"

    # Slide 2: System Overview
    slide2 = prs.slides.add_slide(blank_layout)
    add_header(slide2, "System Overview")
    tx_box = slide2.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.5))
    tf = tx_box.text_frame
    tf.word_wrap = True

    bullets2 = [
        "Dual-redundant 3000 PSI hydraulic flight control system with automated cross-channel failover",
        "Uses MIL-PRF-83282 synthetic polyol ester fluid (fire-resistant, non-corrosive)",
        "Operating temperature range: -40°C to +85°C continuous thermal envelope",
        "Channel L and Channel R independent power loops provide fail-operational surface control",
        "Engine-driven variable displacement pumps maintain continuous delivery across all flight profiles"
    ]
    for i, b in enumerate(bullets2):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "• " + b
        p.font.name = "Calibri"
        p.font.size = Pt(20)
        p.space_after = Pt(16)

    # Slide 3: Key Components Table
    slide3 = prs.slides.add_slide(blank_layout)
    add_header(slide3, "Key Components")
    rows, cols = 7, 3
    left, top, width, height = Inches(1.0), Inches(1.6), Inches(11.3), Inches(4.8)
    table_shape = slide3.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    table.columns[0].width = Inches(3.5)
    table.columns[1].width = Inches(2.2)
    table.columns[2].width = Inches(5.6)

    headers3 = ["Component", "Component ID", "Function / Application"]
    for c_idx, h in enumerate(headers3):
        cell = table.cell(0, c_idx)
        cell.text = h
        p = cell.text_frame.paragraphs[0]
        p.font.bold = True
        p.font.size = Pt(16)
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(0x2B, 0x6C, 0xB0)

    comp_data = [
        ("Primary Actuator", "PA-7100", "Flight surface actuation (main hydraulic ram)"),
        ("Servo Valve", "SV-4200A", "Actuator flow control (upgraded 18 GPM, 6 ms fast response)"),
        ("Heat Exchanger", "HX-3300", "Thermal management & fuel-fluid heat rejection (12 kW)"),
        ("Filter Assembly", "FLT-2100", "Fluid filtration (10-micron absolute with 75 PSI delta-P bypass)"),
        ("Hydraulic Pump", "PMP-5000", "Pressure generation (engine-driven, 28.5 cc/rev displacement)"),
        ("Accumulator", "ACC-1800", "Energy storage & pulsation damping (nitrogen precharged)")
    ]
    for r_idx, (c, cid, fn) in enumerate(comp_data):
        for c_idx, val in enumerate([c, cid, fn]):
            cell = table.cell(r_idx + 1, c_idx)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(14)
            p.font.name = "Calibri"

    # Slide 4: Maintenance Intervals Table
    slide4 = prs.slides.add_slide(blank_layout)
    add_header(slide4, "Maintenance Intervals")
    rows4, cols4 = 6, 4
    left4, top4, width4, height4 = Inches(1.0), Inches(1.6), Inches(11.3), Inches(4.5)
    table_shape4 = slide4.shapes.add_table(rows4, cols4, left4, top4, width4, height4)
    table4 = table_shape4.table
    table4.columns[0].width = Inches(2.5)
    table4.columns[1].width = Inches(2.3)
    table4.columns[2].width = Inches(4.0)
    table4.columns[3].width = Inches(2.5)

    headers4 = ["Component ID", "Interval (Hours)", "Scheduled Task", "Procedure Reference"]
    for c_idx, h in enumerate(headers4):
        cell = table4.cell(0, c_idx)
        cell.text = h
        p = cell.text_frame.paragraphs[0]
        p.font.bold = True
        p.font.size = Pt(16)
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(0x2B, 0x6C, 0xB0)

    maint_data = [
        ("PA-7100", "2000 hrs", "Seal inspection and leakage rate check", "MP-7100-01"),
        ("SV-4200", "1000 hrs", "Flow test and null adjustment", "MP-4200-01"),
        ("HX-3300", "3000 hrs", "Core inspection and ultrasonic cleaning", "MP-3300-01"),
        ("FLT-2100", "500 hrs", "Filter element replacement (P/N FE-2100-10A)", "MP-2100-01"),
        ("PMP-5000", "2500 hrs", "Wear plate inspection and case drain check", "MP-5000-01")
    ]
    for r_idx, row in enumerate(maint_data):
        for c_idx, val in enumerate(row):
            cell = table4.cell(r_idx + 1, c_idx)
            cell.text = val
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(14)
            p.font.name = "Calibri"

    # Slide 5: Common Issues and Troubleshooting
    slide5 = prs.slides.add_slide(blank_layout)
    add_header(slide5, "Common Issues and Troubleshooting")
    tx_box5 = slide5.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.5))
    tf5 = tx_box5.text_frame
    tf5.word_wrap = True

    troubleshoot = [
        "Servo valve response degradation: Field reports show legacy SV-4200 valves exhibiting ~10ms latency. Schedule upgrade to SV-4200A per ECN-2847.",
        "Filter bypass indication at cold start: Transient pop-up indication normal below -10°C due to cold fluid viscosity. Reset button after warmup; replace element if pop recurs.",
        "Accumulator precharge loss: Check precharge pressure every 500 hours. Recharge with dry nitrogen to specification (1500 PSI for Rev A, 1600 PSI for Rev B / S/N 1042+).",
        "Heat exchanger thermal soak: Ground operations in high ambient conditions (>35°C) can cause temperature readings near 95°C. In-flight airflow and fuel flow restore 65°C baseline."
    ]
    for i, t in enumerate(troubleshoot):
        p = tf5.paragraphs[0] if i == 0 else tf5.add_paragraph()
        p.text = "• " + t
        p.font.name = "Calibri"
        p.font.size = Pt(18)
        p.space_after = Pt(14)

    # Slide 6: Safety Notes
    slide6 = prs.slides.add_slide(blank_layout)
    add_header(slide6, "Safety Notes & Maintenance Precautions")
    tx_box6 = slide6.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.5))
    tf6 = tx_box6.text_frame
    tf6.word_wrap = True

    safety_notes = [
        "HIGH PRESSURE HAZARD: System operates at HIGH PRESSURE - 3000 PSI minimum PPE required (full eye protection, face shield, and rated gloves).",
        "Always depressurize before maintenance: Discharge accumulator energy storage and verify reservoir depressurization valve is open before breaking line fittings.",
        "Approved fluid standard: Use only approved fluid MIL-PRF-83282 polyol ester synthetic base. NEVER service with MIL-H-5606.",
        "High surface temperatures: Hydraulic lines and heat exchanger surfaces may exceed 90°C following flight operations. Allow cooling period before touch inspection."
    ]
    for i, s in enumerate(safety_notes):
        p = tf6.paragraphs[0] if i == 0 else tf6.add_paragraph()
        p.text = "• " + s
        p.font.name = "Calibri"
        p.font.size = Pt(18)
        p.space_after = Pt(16)

    prs.save(target_path)
    print(f"Saved PPTX using python-pptx: {target_path}")

else:
    print("python-pptx could not be loaded. Please ensure python-pptx is installed.")
    sys.exit(1)
