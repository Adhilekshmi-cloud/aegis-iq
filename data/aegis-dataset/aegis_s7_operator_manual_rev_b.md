# Aegis Series-7 Hydraulic Control System - Operator Manual

**Document ID:** OM-S7-001  
**Revision:** Rev B  
**Publication Date:** 2024-03-15  
**Approved By:** Aegis Flight Dynamics & Controls Engineering Group  
**Distribution:** Flight Operations, Ground Support, and Base Maintenance Personnel  

---

## 1. System Description

The Aegis Series-7 Hydraulic Control System is a centralized, high-performance, 3000 PSI class dual-redundant power actuation architecture engineered specifically for multi-axis primary flight control and high-rate maneuvering. The system supplies continuous hydraulic authority to all aerodynamic primary control surfaces, including ailerons, elevators, and rudder, as well as secondary utility actuation circuits.

### 1.1 Dual-Redundant Architecture
The system architecture incorporates two entirely independent and symmetrical hydraulic power channels designated as Channel L (Left) and Channel R (Right). Each channel operates independently with dedicated pressure generation, fluid reservoir storage, filtration, thermal conditioning, and accumulator energy storage. 

Under standard operating conditions, both Channel L and Channel R share actuator duty loads symmetrically. A dual-coil electrohydraulic servo valve (SV-4200) interfaces directly with the primary actuator ram (PA-7100), metering flow from both circuits. Cross-channel check valves and high-speed isolation shutoff valves ensure that pressure anomalies, hydraulic line severance, or complete fluid loss in one channel will not propagate to or compromise the companion channel. Automatic failover occurs seamlessly within 15 milliseconds, maintaining full aerodynamic surface stiffness.

### 1.2 Hydraulic Fluid
The Series-7 system is standardized exclusively on synthetic hydrocarbon polyol ester fluid conforming to specification **MIL-PRF-83282**. 
- Fluid Type: MIL-PRF-83282 Polyol Ester Synthetic Base
- Operational Temperature Range: -40°C to 204°C
- Flash Point: > 205°C
- Strict prohibition: Never mix with mineral-based MIL-H-5606 fluid. Mixing leads to seal elastomer deterioration and catastrophic valve seizure.

---

## 2. Operating Parameters

The following parameters govern normal flight and ground operations for the Aegis Series-7 hydraulic system. All cockpit flight instrument indications and ground maintenance test sets are calibrated to these limits.

| Parameter | Nominal Value | Minimum Limit | Maximum Limit | Units | Operational Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| System Operating Pressure | 3000 | 2800 | 3200 | PSI | Normal flight operating range |
| Proof Pressure Rating | 3750 | — | 3750 | PSI | Structural proof factor 1.25x |
| Burst Pressure Rating | 4500 | — | 4500 | PSI | Safety margin 1.50x |
| Fluid Operating Temperature | 65 | -40 | 85 | °C | Normal continuous operation |
| Fluid Peak Temperature | — | — | 105 | °C | Transient maximum (max 10 min) |
| System Total Flow Rate | 30.0 | 1.0 | 36.0 | GPM | Combined Channel L + R output |
| Servo Valve Flow Rate (SV-4200) | 15.0 | 0.5 | 18.0 | GPM | Per servo valve assembly |
| Servo Valve Response Time | 8 | — | 12 | ms | Step command null to full stroke |
| Pump Operating Speed | 3200 | 800 | 4200 | RPM | Engine accessory pad speed |
| Pump Displacement | 28.5 | 27.0 | 30.0 | cc/rev | Variable displacement pump |
| Accumulator Precharge | 1500 | 1450 | 1550 | PSI | Nitrogen at 20°C ambient |
| Filter Differential Pressure | 15 | 0 | 75 | PSI | Delta-P across element |
| Filter Bypass Activation | 75 | 70 | 80 | PSI | Mechanical pop-up indicator |
| Reservoir Fluid Volume | 4.8 | 3.6 | 5.2 | Liters | Pressurized bootstrap chamber |

---

## 3. Normal Operating Procedures

### 3.1 Pre-Flight Hydraulic Inspection
1. **Fluid Level Verification:** Inspect bootstrap reservoir sight glass (RES-0900) on both channels. Ensure level indicator resides in the green operational band (minimum 3.8 L indicated cold).
2. **Filter Bypass Indicator Check:** Inspect the mechanical differential indicator on the main filter assemblies (FLT-2100). Verify the red pop-up button is fully depressed and flush with the housing.
   - *Note:* In cold ambient conditions below -10°C, high fluid viscosity may cause transient indicator pop during pump start. If ambient is below -10°C and indicator is popped prior to warmup, reset button once engine achieves idle temperature. If it pops after warmup, replace element.
3. **Accumulator Precharge Verification:** Confirm nitrogen precharge gauge on ACC-1800 reads 1500 ± 50 PSI at ambient temperature (~20°C).
4. **General Leak Check:** Visually inspect line fittings, servo valve manifolds, and primary actuator cylinder rod packings for fluid weepage. Allowable leakage is zero drops per minute at actuator dynamic seals.

### 3.2 System Startup and Ground Warmup
1. Engage Engine Starter / Ground Auxiliary Power.
2. Advance power levers to idle. Confirm PMP-5000 rotation initiates fluid circulation.
3. Monitor cockpit HMI panel (`PRESS-SYS` display):
   - Channel L and Channel R pressure must build to at least 2800 PSI within 4.0 seconds of engine stabilization.
   - Verify nominal operating pressure settles between 2900 and 3100 PSI (3000 PSI nominal).
4. Exercise flight controls: Cycle primary flight control stick through full pitch, roll, and yaw deflections. Verify smooth displacement without hesitation or acoustic shudder.
5. Check servo valve latency: Actuator response should be instantaneous with no stick catch or rate limiting.

### 3.3 In-Flight Monitoring
During all flight regimes, primary flight computers continuously poll hydraulic sensory nodes:
- Maintain monitoring of `PRESS-SYS` (nominal 3000 PSI).
- Monitor `TEMP-HYD` via HMI thermal page (`HX-MAIN`). Temperature should stabilize between 55°C and 75°C.
- If continuous high-energy maneuvering induces fluid temperature rise exceeding 85°C, fuel-cooled heat exchanger (HX-3300) modulates fuel bypass to boost heat rejection up to rated 12 kW capacity.

---

## 4. Emergency & Abnormal Procedures

### 4.1 Low System Pressure (Channel Depressurization)
**Indication:** Master Warning LIGHT, audible chime, HMI alert `HYD L PRESS LOW` or `HYD R PRESS LOW` (< 2400 PSI).

1. Identify degraded channel via cockpit HMI pressure display (`PRESS-SYS`).
2. Verify isolation valve closure: The automated flight control system will execute automated channel isolation.
3. Confirm companion channel pressure remains stable between 2800 and 3100 PSI.
4. Primary actuator (PA-7100) automatically shifts to single-channel authority mode. Flight control capability is fully preserved without reduction in aerodynamic limit authority.
5. Avoid aggressive simultaneous multi-axis high-rate inputs to prevent peak flow starvation.
6. Land at nearest suitable airfield.

### 4.2 Hydraulic Fluid Overtemperature
**Indication:** Master Caution LIGHT, HMI alert `HYD TEMP HIGH` (> 95°C).

1. Inspect thermal display page `HX-MAIN`.
2. Check engine fuel feed temperature to confirm adequate heat sink capacity in fuel line heat exchanger HX-3300.
3. Reduce sustained maneuvering loads and aerodynamic surface dithering.
4. If temperature continues climbing above 105°C:
   - Isolate secondary utility actuation circuits.
   - Monitor reservoir level for boil-off or foaming.
   - Declare operational urgency and commence descent to lower ambient thermal altitudes.

### 4.3 Total Hydraulic Dual-Channel Failure
**Indication:** Dual warning lights `HYD L FAIL` and `HYD R FAIL`, system pressure < 1200 PSI on both channels.

1. Immediately activate Emergency Actuator Ram Air Turbine (RAT) deployment switch.
2. Accumulator ACC-1800 provides up to 12 seconds of stored hydraulic energy at 1500 PSI precharge for initial attitude recovery.
3. Transition aircraft to alternate pitch trim and rudder manual reversion.
4. Prepare for emergency forced landing or controlled evacuation per flight operations directives.

---

## 5. Component Technical Reference

The following table details the primary Line Replaceable Units (LRUs) that constitute the Aegis Series-7 hydraulic ecosystem:

### 5.1 Primary Actuator (PA-7100)
- **Part Number:** PA-7100
- **Alternative Naming:** Main Hydraulic Ram (common field designation)
- **HMI Identifier:** `ACT-PRI`
- **Subsystem:** Flight Control
- **Material:** Forged Titanium Ti-6Al-4V cylinder barrel and chrome-plated piston shaft
- **Weight:** 12.4 kg
- **Design Pressure:** 3000 PSI nominal (proof 3750 PSI, burst 4500 PSI)
- **Stroke / Displacement:** 142 mm dual-acting balanced cylinder
- **Operating Temperature:** -40°C to +85°C

### 5.2 Electrohydraulic Servo Valve (SV-4200)
- **Part Number:** SV-4200 (Revision A standard build)
- **HMI Identifier:** `SRV-V1`
- **Subsystem:** Flight Control
- **Material:** Stainless Steel 17-4PH housing and sleeve
- **Weight:** 2.1 kg
- **Rated Flow Rate:** 15.0 GPM at 1000 PSI drop across valve
- **Step Response Time:** 8 ms nominal (12 ms maximum allowable)
- **Coil Resistance:** 100 Ohms dual parallel redundant coils

### 5.3 Primary Hydraulic Pump (PMP-5000)
- **Part Number:** PMP-5000
- **HMI Identifier:** `PMP-1`
- **Subsystem:** Power Generation
- **Material:** Inconel 718 rotating cylinder block and valve plate
- **Weight:** 15.6 kg
- **Displacement:** 28.5 cc/rev variable axial piston
- **Speed Envelope:** 800 RPM idle to 4200 RPM maximum continuous

### 5.4 Hydraulic Energy Accumulator (ACC-1800)
- **Part Number:** ACC-1800
- **HMI Identifier:** `ACC-1`
- **Subsystem:** Energy Storage & Pulsation Damping
- **Material:** High-strength Alloy Steel AISI 4340
- **Weight:** 6.3 kg
- **Precharge Gas:** Dry Nitrogen, 1500 PSI at 20°C ambient

### 5.5 Main Filter Assembly (FLT-2100)
- **Part Number:** FLT-2100 (Element P/N: FE-2100-10A)
- **HMI Identifier:** `FLT-PRI`
- **Subsystem:** Fluid Filtration & Conditioning
- **Material:** Stainless Steel 316L housing
- **Weight:** 3.2 kg
- **Rating:** 10-micron absolute microglass media
- **Bypass Relief Setting:** 75 PSI differential pressure

### 5.6 Fuel-Cooled Heat Exchanger (HX-3300)
- **Part Number:** HX-3300
- **HMI Identifier:** `HX-MAIN`
- **Subsystem:** Thermal Management
- **Material:** Aluminum 6061-T6 plate-fin counter-flow matrix
- **Weight:** 8.7 kg
- **Heat Rejection Capacity:** 12.0 kW continuous at rated fuel and fluid mass flows

### 5.7 Hydraulic Reservoir Assembly (RES-0900)
- **Part Number:** RES-0900
- **HMI Identifier:** `RES-1`
- **Subsystem:** Fluid Storage
- **Material:** Aluminum 2024-T3
- **Weight:** 4.8 kg
- **Usable Fluid Capacity:** 4.8 Liters bootstrap pressurized

### 5.8 System Pressure Relief Valve (PRV-6600)
- **Part Number:** PRV-6600
- **HMI Identifier:** `PRV-SYS`
- **Subsystem:** System Safety & Overpressure Protection
- **Material:** Stainless Steel 440C hardened seat
- **Weight:** 1.4 kg
- **Cracking Pressure:** 3650 PSI; Full Flow Relief: 3850 PSI
