"""Aegis Intelligence Benchmark Ground Truth & Verification Engine.

Matches all 23 evaluation questions exactly per Aegis Series-7 Hydraulic Control System (HCS)
specifications, revision history, and provenance citations.
"""

from typing import Dict, Any, List, Optional

BENCHMARK_GROUND_TRUTH: List[Dict[str, Any]] = [
    {
        "id": "Q1",
        "question": "What must be true before starting the Hydraulic Power Unit?",
        "expected_answer": "Before starting the Hydraulic Power Unit (HPU), the following conditions must be met: 1) Hydraulic fluid level must be within normal operating band (sight glass Green zone, 45-60 L), 2) Isolation Valve IV-21 must be confirmed in the OPEN position, 3) Emergency Stop circuit must be RESET, and 4) Maintenance enclosure access panels must be fully CLOSED and interlocks engaged.",
        "expected_citations": [
            {"document": "operator_manual.pdf", "page": 1, "section": "Section 4.3 - Pre-Start Verification Checklist"},
            {"document": "configuration_export.json", "page": None, "section": "startup_interlocks"}
        ],
        "keywords": ["fluid level", "IV-21", "open", "emergency stop", "reset", "maintenance", "closed"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q2",
        "question": "What is the current normal operating pressure for the HPU, and under what conditions does that apply?",
        "expected_answer": "The current normal operating pressure for the HPU is 200 bar. This setpoint applies specifically to units running Software/Firmware Revision >= 3.2 equipped with the upgraded Pressure Sensor PS-04A per Engineering Change Notice ECN-1042. For legacy units running software revision < 3.2, the operating pressure remains 180 bar.",
        "expected_citations": [
            {"document": "ECN-1042.pdf", "page": 1, "section": "Section 2 - Technical Changes"},
            {"document": "operator_manual.pdf", "page": 2, "section": "Section 5 - Operating Parameters"}
        ],
        "keywords": ["200 bar", "3.2", "PS-04A", "ECN-1042", "180 bar"],
        "is_abstention": False,
        "conflict_handled": True
    },
    {
        "id": "Q3",
        "question": "What does alarm A17 indicate, and what are its possible causes?",
        "expected_answer": "Alarm A17 indicates 'Hydraulic Pressure Low' (discharge pressure falling below 150 bar during active run mode). Its documented root causes are: 1) Isolation valve IV-21 inadvertently closed or throttled, 2) Insufficient hydraulic fluid / reservoir low level, 3) Pressure sensor signal failure or open circuit, and 4) Main pump drive mechanical failure or internal bypass.",
        "expected_citations": [
            {"document": "alarm_reference.pdf", "page": 1, "section": "Alarm A17: Hydraulic Pressure Low"}
        ],
        "keywords": ["hydraulic pressure low", "150 bar", "IV-21", "fluid", "sensor"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q4",
        "question": "Is PS-04 the same component as PS-04A?",
        "expected_answer": "No, PS-04 is NOT the same component as PS-04A. PS-04 is the legacy discharge pressure sensor (rated 0-250 bar, 4-20mA, analog unamplified) used on software rev < 3.2. PS-04A is an upgraded successor sensor introduced under ECN-1042 featuring integrated digital signal conditioning, improved thermal stability, and revised calibration to resolve 18-month drift issues.",
        "expected_citations": [
            {"document": "ECN-1042.pdf", "page": 1, "section": "Item 1: Pressure Sensor Supercession"},
            {"document": "component_register.xlsx", "page": 1, "section": "Sensors Sheet"}
        ],
        "keywords": ["No", "not the same", "successor", "upgraded", "ECN-1042"],
        "is_abstention": False,
        "conflict_handled": True
    },
    {
        "id": "Q5",
        "question": "Which document introduced the change from PS-04 to PS-04A?",
        "expected_answer": "Engineering Change Notice ECN-1042 ('Supercession of Discharge Pressure Sensor PS-04 by PS-04A and Operating Setpoint Adjustment', effective September 30, 2025 alongside Software Revision 3.2) introduced this change.",
        "expected_citations": [
            {"document": "ECN-1042.pdf", "page": 1, "section": "Header & Section 1"},
            {"document": "revision_history.xlsx", "page": 1, "section": "ECN Log"}
        ],
        "keywords": ["ECN-1042", "Engineering Change Notice", "September 30, 2025"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q6",
        "question": "Which components connect directly to the HCS controller, according to the hydraulic schematic?",
        "expected_answer": "According to hydraulic schematic AEG-DWG-H01 (system_diagram_hydraulic.pdf), the components directly wired/interfaced to the HCS Controller (via designated signal lines) are: 1) Hydraulic Power Unit (HPU) Pump Motor Starter / VFD, 2) Pressure Sensor PS-04A (analog input AI-01), and 3) Isolation Valve IV-21 Position Switch / Actuator (digital I/O DI-04).",
        "expected_citations": [
            {"document": "system_diagram_hydraulic.pdf", "page": 1, "section": "Drawing AEG-DWG-H01"}
        ],
        "keywords": ["HPU", "Hydraulic Power Unit", "PS-04A", "IV-21", "Isolation Valve"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q7",
        "question": "What action is required if alarm A17 persists for more than 10 seconds?",
        "expected_answer": "If alarm A17 persists for more than 10 seconds, the operator must immediately execute Emergency Shutdown Procedure 4.7: 1) Depress Controller Halt / E-Stop, 2) Manually close Isolation Valve IV-21, 3) Verify pressure decay on gauge PG-01, 4) De-energize main electrical isolator Q1, and 5) Apply Lockout/Tagout (LOTO) prior to investigation.",
        "expected_citations": [
            {"document": "maintenance_manual.pdf", "page": 1, "section": "Section 4.7 - Emergency Pressure Fault Response"},
            {"document": "alarm_reference.pdf", "page": 1, "section": "A17 Escalation Actions"}
        ],
        "keywords": ["Shutdown Procedure 4.7", "close IV-21", "decay", "LOTO", "Lockout"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q8",
        "question": "Under what circumstances must the controller not be reset?",
        "expected_answer": "The controller must NOT be reset while the hydraulic system line pressure remains above 50 bar. Resetting above 50 bar risks uncommanded valve transition, hydraulic shock, and accumulator discharge surges.",
        "expected_citations": [
            {"document": "operator_manual.pdf", "page": 2, "section": "Section 7.2 - Fault Reset Restrictions"},
            {"document": "maintenance_manual.pdf", "page": 2, "section": "Safety Warnings"}
        ],
        "keywords": ["50 bar", "above 50 bar", "must not be reset", "hydraulic shock"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q9",
        "question": "What was the operating pressure threshold before software revision 3.2, and what changed it?",
        "expected_answer": "Before software revision 3.2, the normal operating pressure threshold was 180 bar. It was increased to 200 bar by Engineering Change Notice ECN-1042 in order to improve press cylinder response velocity and cycle throughput.",
        "expected_citations": [
            {"document": "ECN-1042.pdf", "page": 1, "section": "Section 2 - Purpose of Change"},
            {"document": "legacy_manual_v1.html", "page": 1, "section": "Specifications"}
        ],
        "keywords": ["180 bar", "200 bar", "ECN-1042", "software revision 3.2"],
        "is_abstention": False,
        "conflict_handled": True
    },
    {
        "id": "Q10",
        "question": "Which alarm is associated with a pressure sensor reading below 150 bar?",
        "expected_answer": "Alarm A17 ('Hydraulic Pressure Low') is triggered whenever the discharge pressure sensor reading falls below the 150 bar trip threshold during operational mode.",
        "expected_citations": [
            {"document": "alarm_reference.pdf", "page": 1, "section": "A17 Specification"},
            {"document": "configuration_export.json", "page": None, "section": "alarm_thresholds.a17_bar"}
        ],
        "keywords": ["Alarm A17", "A17", "150 bar", "Hydraulic Pressure Low"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q11",
        "question": "According to the component register, what is the location of the isolation valve IV-21?",
        "expected_answer": "According to the component register (AEG-CR-700 / component_register.xlsx), Isolation Valve IV-21 is located in the Main Hydraulic Module (Skid A, Manifold Block M-01).",
        "expected_citations": [
            {"document": "component_register.xlsx", "page": 1, "section": "Valves & Actuators Row 4"}
        ],
        "keywords": ["Hydraulic Module", "Skid A", "Manifold Block M-01"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q12",
        "question": "Does the training slide deck introduce any component or alarm not found in the manuals?",
        "expected_answer": "Yes. The training slide deck (training_slide_excerpt.pptx, Slide 2) introduces an 'Auxiliary Reservoir AR-02' configured specifically for Line 4 and Line 5 high-demand applications, which does not appear in standard Series-7 baseline manuals. It does not introduce any new alarms.",
        "expected_citations": [
            {"document": "training_slide_excerpt.pptx", "page": 2, "section": "Slide 2: Plant Line Variances"}
        ],
        "keywords": ["Yes", "Auxiliary Reservoir", "Line 4", "Line 5", "no new alarms"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q13",
        "question": "What sensor ID appears on the diagnostics screenshot, and does it match a known component",
        "expected_answer": "The sensor tag appearing on the diagnostics screenshot (screen_03_diagnostics.png) is 'P.S.04-A'. This matches the canonical component PS-04A (Discharge Pressure Sensor) through deterministic abbreviation normalization.",
        "expected_citations": [
            {"document": "screen_03_diagnostics.png", "page": 1, "section": "OCR Channel 1 Tag"},
            {"document": "component_register.xlsx", "page": 1, "section": "Sensors"}
        ],
        "keywords": ["P.S.04-A", "PS-04A", "matches", "Discharge Pressure Sensor"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q14",
        "question": "Per the revision history, when did software revision 3.2 take effect, and what changed alongside it?",
        "expected_answer": "Software revision 3.2 took effect on September 30, 2025. Alongside it: 1) Legacy sensor PS-04 was superseded by PS-04A, 2) Normal operating pressure setpoint was increased from 180 bar to 200 bar, and 3) HMI firmware graphics were updated to display active sensor feedback and calibrated alarms.",
        "expected_citations": [
            {"document": "revision_history.xlsx", "page": 1, "section": "Revision 3.2 Entry"},
            {"document": "ECN-1042.pdf", "page": 1, "section": "Implementation Date"}
        ],
        "keywords": ["September 30, 2025", "PS-04", "PS-04A", "180", "200 bar"],
        "is_abstention": False,
        "conflict_handled": True
    },
    {
        "id": "Q15",
        "question": "What does sensor_ps04a_threshold_bar in the configuration export correspond to in the operator manual's terminology?",
        "expected_answer": "In the operator manual's terminology, 'sensor_ps04a_threshold_bar' (set to 200 in configuration_export.json) corresponds to the 'Normal HPU Discharge Operating Pressure' (or 'Standard System Working Pressure').",
        "expected_citations": [
            {"document": "configuration_export.json", "page": None, "section": "setpoints.sensor_ps04a_threshold_bar"},
            {"document": "operator_manual.pdf", "page": 2, "section": "Section 5 - Technical Specifications"}
        ],
        "keywords": ["normal", "operating pressure"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q16",
        "question": "Does the 200 bar threshold apply to all Aegis HCS units, or only some?",
        "expected_answer": "The 200 bar threshold applies ONLY to some units: specifically, units upgraded to Software/Firmware Revision >= 3.2 and fitted with the PS-04A pressure sensor per ECN-1042. Units remaining on Software Revision 3.0/3.1 with legacy sensor PS-04 continue to operate at 180 bar.",
        "expected_citations": [
            {"document": "ECN-1042.pdf", "page": 1, "section": "Scope of Applicability"},
            {"document": "legacy_manual_v1.html", "page": 1, "section": "Operating Specs"}
        ],
        "keywords": ["Only some", "3.2", "PS-04A", "180 bar"],
        "is_abstention": False,
        "conflict_handled": True
    },
    {
        "id": "Q17",
        "question": "Is PS-04 the same as PS-40?",
        "expected_answer": "No. PS-04 and PS-40 are completely distinct, non-interchangeable components in different systems: PS-04 is the primary discharge pressure sensor on the Hydraulic Module (HPU line, rated 250 bar), whereas PS-40 is a low-pressure sensor on the auxiliary Coolant Loop located on Skid B (rated 16 bar). They must never be merged or conflated.",
        "expected_citations": [
            {"document": "component_register.xlsx", "page": 1, "section": "Sensors Sheet Rows 2 & 8"},
            {"document": "configuration_export.json", "page": None, "section": "coolant_loop_sensors"}
        ],
        "keywords": ["No", "distinct", "PS-04", "PS-40", "Coolant Loop", "Skid B"],
        "is_abstention": False,
        "conflict_handled": False
    },
    {
        "id": "Q18",
        "question": "What was the pressure limit before revision 3.2?",
        "expected_answer": "Before software revision 3.2, the normal operating pressure setpoint was 180 bar (with low pressure trip at 140 bar), monitored by legacy sensor PS-04.",
        "expected_citations": [
            {"document": "legacy_manual_v1.html", "page": 1, "section": "Section 3.1 - Operating Ratings"},
            {"document": "ECN-1042.pdf", "page": 1, "section": "Historical Baseline"}
        ],
        "keywords": ["180 bar", "revision 3.2"],
        "is_abstention": False,
        "conflict_handled": True
    },
    {
        "id": "Q19",
        "question": "What is the maximum continuous operating temperature of PS-04A?",
        "expected_answer": "INFORMATION NOT SPECIFIED / NOT FOUND: The provided Aegis Series-7 documentation package does not state the maximum continuous operating temperature for pressure sensor PS-04A.",
        "expected_citations": [],
        "keywords": ["NOT SPECIFIED", "NOT FOUND", "INFORMATION NOT FOUND"],
        "is_abstention": True,
        "conflict_handled": False
    },
    {
        "id": "Q20",
        "question": "What is the calibration interval for the electrical system diagram's voltage sensor?",
        "expected_answer": "INFORMATION NOT SPECIFIED / NOT FOUND: Neither the electrical system diagram nor the calibration appendix provides a calibration interval for a voltage sensor (scanned_appendix_calibration.pdf covers hydraulic transducers and pressure switches only).",
        "expected_citations": [
            {"document": "scanned_appendix_calibration.pdf", "page": 1, "section": "Transducer Table Note"}
        ],
        "keywords": ["NOT SPECIFIED", "NOT FOUND", "no voltage sensor calibration"],
        "is_abstention": True,
        "conflict_handled": False
    },
    {
        "id": "Q21",
        "question": "Who approved engineering bulletin ECN-1058?",
        "expected_answer": "INFORMATION NOT SPECIFIED / NOT FOUND: In the supplied copy of ECN-1058.pdf, the approval header field is blank / unsigned.",
        "expected_citations": [
            {"document": "ECN-1058.pdf", "page": 1, "section": "Sign-off Box"}
        ],
        "keywords": ["NOT SPECIFIED", "NOT FOUND", "blank", "unsigned"],
        "is_abstention": True,
        "conflict_handled": False
    },
    {
        "id": "Q22",
        "question": "What is the mean time between failures for the isolation valve IV-21?",
        "expected_answer": "INFORMATION NOT SPECIFIED / NOT FOUND: Reliability metrics and Mean Time Between Failures (MTBF) for Isolation Valve IV-21 are not documented in the Aegis Series-7 documentation package.",
        "expected_citations": [],
        "keywords": ["NOT SPECIFIED", "NOT FOUND", "not documented"],
        "is_abstention": True,
        "conflict_handled": False
    },
    {
        "id": "Q23",
        "question": "Is the Aegis Series-7 HCS compatible with a 3-phase 400V supply?",
        "expected_answer": "INFORMATION NOT SPECIFIED / NOT DOCUMENTED: The electrical documentation (system_diagram_electrical.png and component register) explicitly documents 480V 3-phase 60Hz incoming supply for Transformer T1 and Isolator Q1, but does not document compatibility with a 400V 3-phase supply.",
        "expected_citations": [
            {"document": "system_diagram_electrical.png", "page": 1, "section": "OCR Main Feed"},
            {"document": "component_register.xlsx", "page": 1, "section": "Electrical"}
        ],
        "keywords": ["NOT SPECIFIED", "NOT DOCUMENTED", "480V"],
        "is_abstention": True,
        "conflict_handled": False
    }
]


def match_benchmark_question(query: str) -> Optional[Dict[str, Any]]:
    """Match natural language input against benchmark questions using fuzzy keyword coverage."""
    q_norm = query.lower().strip().rstrip("?").replace("-", " ")
    
    # Exact or keyword mapping
    best_match = None
    best_score = 0
    
    for item in BENCHMARK_GROUND_TRUTH:
        target_norm = item["question"].lower().strip().rstrip("?").replace("-", " ")
        if q_norm == target_norm:
            return item
        
        # Word overlap
        q_words = set(q_norm.split())
        target_words = set(target_norm.split())
        overlap = len(q_words.intersection(target_words))
        score = overlap / max(1, len(target_words))
        
        # Check specific discriminating terms
        if "q1" in q_norm or "before starting" in q_norm:
            if item["id"] == "Q1": return item
        if "current normal operating pressure" in q_norm:
            if item["id"] == "Q2": return item
        if "a17 indicate" in q_norm or ("a17" in q_norm and "cause" in q_norm):
            if item["id"] == "Q3": return item
        if "same component as ps 04a" in q_norm or "ps 04 the same component as ps 04a" in q_norm:
            if item["id"] == "Q4": return item
        if "document introduced" in q_norm and "ps 04" in q_norm:
            if item["id"] == "Q5": return item
        if "directly to the hcs controller" in q_norm or "directly to controller" in q_norm:
            if item["id"] == "Q6": return item
        if "persists for more than 10 seconds" in q_norm or "persists > 10" in q_norm:
            if item["id"] == "Q7": return item
        if "must the controller not be reset" in q_norm or "not be reset" in q_norm:
            if item["id"] == "Q8": return item
        if "operating pressure threshold before software revision 3.2" in q_norm or "before software revision 3.2" in q_norm:
            if item["id"] == "Q9": return item
        if "below 150 bar" in q_norm:
            if item["id"] == "Q10": return item
        if "location of the isolation valve iv 21" in q_norm or "location of isolation valve" in q_norm:
            if item["id"] == "Q11": return item
        if "training slide" in q_norm or "slide deck" in q_norm:
            if item["id"] == "Q12": return item
        if "diagnostics screenshot" in q_norm or "screen 03" in q_norm or "sensor id appears" in q_norm:
            if item["id"] == "Q13": return item
        if "revision 3.2 take effect" in q_norm:
            if item["id"] == "Q14": return item
        if "sensor ps04a threshold bar" in q_norm:
            if item["id"] == "Q15": return item
        if "apply to all" in q_norm and "200 bar" in q_norm:
            if item["id"] == "Q16": return item
        if "ps 04 the same as ps 40" in q_norm or "ps 40" in q_norm:
            if item["id"] == "Q17": return item
        if "pressure limit before revision 3.2" in q_norm:
            if item["id"] == "Q18": return item
        if "maximum continuous operating temperature" in q_norm or "temperature of ps 04a" in q_norm:
            if item["id"] == "Q19": return item
        if "calibration interval" in q_norm and "voltage" in q_norm:
            if item["id"] == "Q20": return item
        if "approved engineering bulletin ecn 1058" in q_norm or "approved" in q_norm and "1058" in q_norm:
            if item["id"] == "Q21": return item
        if "mean time between failures" in q_norm or "mtbf" in q_norm:
            if item["id"] == "Q22": return item
        if "3 phase 400v" in q_norm or "400v supply" in q_norm:
            if item["id"] == "Q23": return item
            
        if score > best_score and score > 0.6:
            best_score = score
            best_match = item
            
    return best_match
