import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

DATASET_DIR = r"c:\Users\adhil\OneDrive\Desktop\sybil\aegis-knowledge-system\data\aegis-dataset"
os.makedirs(DATASET_DIR, exist_ok=True)

def style_header(row, fill_color="2B6CB0"):
    header_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for cell in row:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

def auto_fit_columns(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

def create_component_specifications():
    wb = openpyxl.Workbook()
    # Sheet 1: Components
    ws1 = wb.active
    ws1.title = "Components"
    
    headers1 = ["Component_ID", "Component_Name", "Description", "Subsystem", "Material", "Weight_kg"]
    ws1.append(headers1)
    
    rows1 = [
        ["PA-7100", "Primary Actuator", "Main hydraulic ram for flight control surface actuation", "Flight Control", "Titanium Ti-6Al-4V", 12.4],
        ["SV-4200", "Servo Valve (Rev A)", "Electrohydraulic servo valve for primary actuator control", "Flight Control", "Stainless Steel 17-4PH", 2.1],
        ["HX-3300", "Heat Exchanger", "Fuel-cooled hydraulic heat exchanger", "Thermal Management", "Aluminum 6061-T6", 8.7],
        ["FLT-2100", "Main Filter Assembly", "10-micron filtration unit with bypass indicator", "Filtration", "Stainless Steel 316L", 3.2],
        ["PMP-5000", "Primary Hydraulic Pump", "Engine-driven variable displacement pump", "Power Generation", "Inconel 718", 15.6],
        ["ACC-1800", "Hydraulic Accumulator", "Bladder-type precharged accumulator", "Energy Storage", "Steel AISI 4340", 6.3],
        ["RES-0900", "Hydraulic Reservoir", "Pressurized bootstrap reservoir with level sensing", "Fluid Storage", "Aluminum 2024-T3", 4.8],
        ["PRV-6600", "Pressure Relief Valve", "System overpressure protection valve", "Safety", "Stainless Steel 440C", 1.4]
    ]
    for r in rows1:
        ws1.append(r)
    style_header(ws1[1])
    auto_fit_columns(ws1)

    # Sheet 2: Operating Parameters
    ws2 = wb.create_sheet(title="Operating Parameters")
    headers2 = ["Component_ID", "Parameter", "Value", "Unit", "Min_Value", "Max_Value", "Test_Condition"]
    ws2.append(headers2)
    
    rows2 = [
        ["PA-7100", "Operating Pressure", 3000, "PSI", 2800, 3200, "Normal flight"],
        ["PA-7100", "Max Pressure", 3750, "PSI", "-", 3750, "Proof pressure"],
        ["PA-7100", "Operating Temperature", "-", "°C", -40, 85, "Full range"],
        ["SV-4200", "Flow Rate", 15, "GPM", 0.5, 18, "Nominal"],
        ["SV-4200", "Response Time", 8, "ms", "-", 12, "Step input"],
        ["HX-3300", "Heat Rejection", 12, "kW", 8, 15, "Max continuous"],
        ["PMP-5000", "Displacement", 28.5, "cc/rev", "-", "-", "Nominal"],
        ["PMP-5000", "Max Speed", 4200, "RPM", 800, 4200, "Full range"],
        ["ACC-1800", "Precharge Pressure", 1500, "PSI", 1450, 1550, "At 20°C"],
        ["FLT-2100", "Filtration Rating", 10, "micron", "-", "-", "Absolute"],
        ["FLT-2100", "Bypass Pressure", 75, "PSI", 70, 80, "Differential"]
    ]
    for r in rows2:
        ws2.append(r)
    style_header(ws2[1])
    auto_fit_columns(ws2)

    # Sheet 3: Maintenance Schedule
    ws3 = wb.create_sheet(title="Maintenance Schedule")
    headers3 = ["Component_ID", "Interval_Hours", "Task", "Procedure_Ref"]
    ws3.append(headers3)
    
    rows3 = [
        ["PA-7100", 2000, "Seal inspection", "MP-7100-01"],
        ["SV-4200", 1000, "Flow test and null adjustment", "MP-4200-01"],
        ["HX-3300", 3000, "Core inspection and cleaning", "MP-3300-01"],
        ["FLT-2100", 500, "Element replacement", "MP-2100-01"],
        ["PMP-5000", 2500, "Wear plate inspection", "MP-5000-01"]
    ]
    for r in rows3:
        ws3.append(r)
    style_header(ws3[1])
    auto_fit_columns(ws3)

    target_path = os.path.join(DATASET_DIR, "component_specifications.xlsx")
    wb.save(target_path)
    print(f"Saved: {target_path}")

def create_quality_inspection_report():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inspection Results"

    headers = ["Date", "Inspector", "Aircraft_SN", "Component_ID", "Component_Name", "Test_Type", "Measured_Value", "Unit", "Spec_Min", "Spec_Max", "Result"]
    ws.append(headers)

    rows = [
        ["2024-01-15", "R. Chen", "S7-1035", "PA-7100", "Primary Actuator", "Pressure Test", 3010, "PSI", 2800, 3200, "PASS"],
        ["2024-01-15", "R. Chen", "S7-1035", "SV-4200", "Servo Valve", "Response Time", 7.8, "ms", 0, 12, "PASS"],
        ["2024-01-15", "R. Chen", "S7-1035", "SV-4200", "Servo Valve", "Flow Rate", 14.8, "GPM", 0.5, 18, "PASS"],
        ["2024-02-20", "A. Williams", "S7-1038", "PA-7100", "Primary Actuator", "Pressure Test", 2950, "PSI", 2800, 3200, "PASS"],
        ["2024-02-20", "A. Williams", "S7-1038", "SV-4200", "Servo Valve", "Response Time", 9.5, "ms", 0, 12, "PASS"],
        ["2024-02-20", "A. Williams", "S7-1038", "FLT-2100", "Filter Assembly", "Bypass Pressure", 73, "PSI", 70, 80, "PASS"],
        ["2024-03-10", "R. Chen", "S7-1042", "PA-7100", "Primary Actuator", "Pressure Test", 3190, "PSI", 3000, 3400, "PASS"],
        ["2024-03-10", "R. Chen", "S7-1042", "SV-4200A", "Servo Valve A", "Response Time", 5.8, "ms", 0, 8, "PASS"],
        ["2024-03-10", "R. Chen", "S7-1042", "SV-4200A", "Servo Valve A", "Flow Rate", 17.5, "GPM", 12, 20, "PASS"],
        ["2024-04-05", "A. Williams", "S7-1045", "PMP-5000", "Primary Pump", "Displacement", 28.3, "cc/rev", 27, 30, "PASS"],
        ["2024-04-05", "A. Williams", "S7-1045", "ACC-1800", "Accumulator", "Precharge", 1590, "PSI", 1550, 1650, "PASS"],
        ["2024-04-05", "A. Williams", "S7-1045", "HX-3300", "Heat Exchanger", "Heat Rejection", 11.8, "kW", 8, 15, "PASS"]
    ]

    for r in rows:
        ws.append(r)
    style_header(ws[1], fill_color="2C5282")
    auto_fit_columns(ws)

    target_path = os.path.join(DATASET_DIR, "quality_inspection_report.xlsx")
    wb.save(target_path)
    print(f"Saved: {target_path}")

if __name__ == "__main__":
    create_component_specifications()
    create_quality_inspection_report()
    print("XLSX creation complete.")
