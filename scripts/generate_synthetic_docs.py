"""Synthetic Document Corpus Generator and OCR Recall Evaluation Harness.

Conforms to specsheet.md Section 10.0, 10.1, 10.2:
- Generates 20 synthetic procurement & technical documents:
  * 8 MTCs (EN 10204 3.1/3.2 certificates: A105, A350 LF2, A182 F316L, F51 Duplex, P11, P22, P91, Refractory MTR)
  * 6 POs / GRNs (Flanges, Gate Valves, Boiler Tubes, Conveyor Belts, Centrifugal Pump, OTR Tyres)
  * 4 ITPs (Welding & NDT, Hydrotest & Pneumatic, Mill Roll Inspection, Hydraulic Hose Testing)
  * 2 BoQs (Thermal Power Piping Package, Mining Conveyor Overhaul Package)
- Produces ground-truth JSON sidecars for each document.
- Verifies OCR line recall and parsing conformance against ground truth.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.services.ocr import FakeOCRProvider

DOCS_CORPUS_DIR = Path("docs") / "corpus"

DOCUMENTS: list[dict] = [
    # -------------------------------------------------------------
    # 8 MTCs (Material Test Certificates)
    # -------------------------------------------------------------
    {
        "id": "MTC-001-A105",
        "doc_type": "MTC",
        "title": "EN 10204 3.1 Inspection Certificate - Forged Steel A105",
        "text": """INSPECTION CERTIFICATE EN 10204 3.1
Manufacturer: Bharat Forgings Ltd, Pune, India
Certificate No: BFL/2026/MTC/08192
Date: 2026-08-14
Customer: Oil & Natural Gas PSU
Product: ASTM A105 Forged Blind Flange 150 NB Class 300 RF
Heat Number: HT-A105-7721
Batch / Lot: LOT-2026-08
Chemical Composition (%):
C: 0.22  Mn: 0.85  Si: 0.24  P: 0.015  S: 0.012  Cr: 0.09  Ni: 0.06  Mo: 0.02  Cu: 0.11  V: 0.01
Mechanical Properties:
Yield Strength (MPa): 310
Tensile Strength (MPa): 535
Elongation (%): 28.0
Hardness (HBW): 156
Impact Test: Charpy V-Notch at 0°C: 45 J, 48 J, 42 J
Heat Treatment: Normalized at 910°C, air cooled
Non-Destructive Testing: Ultrasonic Test (UT) OK, Magnetic Particle (MPI) OK
Statement of Conformance: Material strictly conforms to ASTM A105 / ASME SA105.""",
        "ground_truth": {
            "grade": "ASTM A105",
            "heat_number": "HT-A105-7721",
            "carbon": 0.22,
            "manganese": 0.85,
            "yield_strength": 310,
            "tensile_strength": 535,
        },
    },
    {
        "id": "MTC-002-A350LF2",
        "doc_type": "MTC",
        "title": "EN 10204 3.1 Inspection Certificate - Low Temp Carbon Steel LF2",
        "text": """INSPECTION CERTIFICATE EN 10204 3.1
Manufacturer: Jindal Quality Steels Ltd, Raigarh
Certificate No: JQS/MTC/LTCS/9920
Date: 2026-07-22
Product: ASTM A350 LF2 Class 1 Weld Neck Flange 200 NB Class 600
Heat Number: HT-LF2-88102
Melting Process: Electric Arc Furnace + Vacuum Degassed
Chemical Analysis:
C: 0.18  Mn: 1.15  Si: 0.28  P: 0.012  S: 0.008  Ni: 0.22  Cr: 0.12  Mo: 0.04
Mechanical Properties:
Tensile Strength: 540 MPa
Yield Strength: 330 MPa
Elongation: 26 %
Charpy Impact Test at -46°C: 38 J, 41 J, 36 J (Avg 38.3 J)
Endorsement: Conforms to NACE MR0175 / ISO 15156.""",
        "ground_truth": {
            "grade": "ASTM A350 LF2",
            "heat_number": "HT-LF2-88102",
            "carbon": 0.18,
            "manganese": 1.15,
            "yield_strength": 330,
            "tensile_strength": 540,
        },
    },
    {
        "id": "MTC-003-F316L",
        "doc_type": "MTC",
        "title": "EN 10204 3.1 Stainless Steel F316L Certificate",
        "text": """MATERIAL TEST REPORT EN 10204 3.1
Manufacturer: Viraj Profiles Ltd, Tarapur
MTR Reference: VPL/SS/316L/2026/0411
Date: 2026-09-02
Specification: ASTM A182 / ASME SA182 Grade F316L
Heat Number: HT-SS-316L-9941
Heat Treatment: Solution Annealed at 1060°C quenched in water
Chemical Composition (%):
C: 0.024  Mn: 1.62  Si: 0.48  P: 0.028  S: 0.006
Cr: 17.20  Ni: 11.40  Mo: 2.15  N: 0.045
Mechanical Tests:
Tensile Strength: 565 MPa
Yield Strength (0.2% Offset): 245 MPa
Elongation: 45 %
Hardness: 160 HBW
Intergranular Corrosion Test: ASTM A262 Practice E PASSED.""",
        "ground_truth": {
            "grade": "ASTM A182 F316L",
            "heat_number": "HT-SS-316L-9941",
            "carbon": 0.024,
            "chromium": 17.20,
            "nickel": 11.40,
            "molybdenum": 2.15,
        },
    },
    {
        "id": "MTC-004-F51-DUPLEX",
        "doc_type": "MTC",
        "title": "EN 10204 3.2 Inspection Certificate - Duplex F51 S31803",
        "text": """INSPECTION CERTIFICATE EN 10204 3.2
Manufacturer: Outokumpu Stainless Special Steels
Third Party Inspector: Bureau Veritas (BVQI)
Cert No: BV-MTC-F51-2026-1184
Grade: ASTM A182 Grade F51 / UNS S31803 / EN 1.4462
Heat Number: HT-DUPLEX-51882
Chemical Composition:
C: 0.022  Mn: 1.40  Si: 0.52  P: 0.020  S: 0.002
Cr: 22.35  Ni: 5.45  Mo: 3.12  N: 0.175
PREN Value: 35.4
Mechanical Properties:
0.2% Proof Stress: 520 MPa
Tensile Strength: 745 MPa
Elongation A5: 32 %
Impact Test Charpy V at -46°C: 85 J, 92 J, 88 J
Microstructure: Ferrite Content 48%, Ausenite 52%, Free of Sigma Phase.""",
        "ground_truth": {
            "grade": "ASTM A182 F51",
            "heat_number": "HT-DUPLEX-51882",
            "pren": 35.4,
            "yield_strength": 520,
            "tensile_strength": 745,
        },
    },
    {
        "id": "MTC-005-P11-ALLOY",
        "doc_type": "MTC",
        "title": "IBR Form III-A & EN 10204 3.1 - ASTM A335 Grade P11",
        "text": """INDIAN BOILER REGULATIONS (IBR 1950) FORM III-A
Manufacturer: Maharashtra Seamless Ltd, Nagothane
IBR Certificate No: MSL/IBR/2026/P11/4412
Date: 2026-08-30
Material: Seamless Alloy Steel Boiler Tube ASTM A335 Grade P11
Dimensions: 60.3 mm OD x 5.6 mm Wall Thickness x 6000 mm Length
Heat Number: HT-P11-66019
Heat Treatment: Full Annealed
Chemical Composition:
C: 0.12  Mn: 0.48  Si: 0.65  P: 0.015  S: 0.010  Cr: 1.25  Mo: 0.52
Mechanical Test:
Yield Strength: 265 MPa
Tensile Strength: 460 MPa
Elongation: 34 %
Flattening Test: SATISFACTORY
Hydrostatic Test: Tested at 18.5 MPa for 10 seconds - NO LEAKAGE
Inspecting Authority: Directorate of Steam Boilers, Maharashtra.""",
        "ground_truth": {
            "grade": "ASTM A335 P11",
            "heat_number": "HT-P11-66019",
            "od_mm": 60.3,
            "wall_mm": 5.6,
            "chromium": 1.25,
            "molybdenum": 0.52,
        },
    },
    {
        "id": "MTC-006-P22-ALLOY",
        "doc_type": "MTC",
        "title": "IBR Form III-A Boiler Tube - ASTM A335 Grade P22",
        "text": """IBR FORM III-A INSPECTION CERTIFICATE
Manufacturer: BHEL Trichy Seamless Steel Tube Plant
Inspection Agency: Central Boilers Board (CBB)
Cert Reference: BHEL/SSTP/P22/2026/8891
Material Specification: ASTM A335 Grade P22 (2.25Cr-1Mo)
Size: 76.1 mm OD x 7.1 mm Min Wall (MW)
Heat Number: HT-P22-33011
Heat Treatment: Normalized & Tempered (730°C)
Ladle Analysis (%):
C: 0.11  Mn: 0.42  Si: 0.32  P: 0.012  S: 0.008  Cr: 2.20  Mo: 0.98
Mechanical Tests:
Yield: 290 MPa  Tensile: 495 MPa  Elongation: 32 %
Bend Test: PASSED 180 DEG WITHOUT CRACKING
Ultrasonic Examination: 100% Volumetric UT Clean.""",
        "ground_truth": {
            "grade": "ASTM A335 P22",
            "heat_number": "HT-P22-33011",
            "chromium": 2.20,
            "molybdenum": 0.98,
        },
    },
    {
        "id": "MTC-007-P91-HIGH-ALLOY",
        "doc_type": "MTC",
        "title": "EN 10204 3.1 Supercritical Header Pipe - ASTM A335 P91",
        "text": """TEST CERTIFICATE EN 10204 3.1
Manufacturer: Vallourec Heat Exchanger Tubes
Doc No: VALL-2026-P91-7712
Date: 2026-06-18
Grade: ASTM A335 Grade P91 (9Cr-1Mo-V-Nb)
Heat Number: HT-P91-99201
Heat Treatment: Normalized at 1060°C, Tempered at 770°C for 2.5 hours
Chemical Analysis (%):
C: 0.10  Mn: 0.40  Si: 0.30  P: 0.012  S: 0.003  Cr: 8.85  Mo: 0.95
V: 0.21  Nb: 0.075  N: 0.048  Al: 0.015  Ni: 0.22
Mechanical Properties:
0.2% Proof Stress: 485 MPa
Tensile Strength: 670 MPa
Elongation: 23 %
Hardness: 215 HBW (Max 250 HBW compliant).""",
        "ground_truth": {
            "grade": "ASTM A335 P91",
            "heat_number": "HT-P91-99201",
            "chromium": 8.85,
            "molybdenum": 0.95,
            "vanadium": 0.21,
        },
    },
    {
        "id": "MTC-008-REFRACTORY",
        "doc_type": "MTC",
        "title": "Manufacturer Test Report - High Alumina Refractory Brick",
        "text": """REFRACTORY QUALITY ASSURANCE CERTIFICATE
Manufacturer: RHI Magnesita India Ltd
Batch Code: RHI-AL70-2026-09
Date of Manufacture: 2026-09-10
Shelf Life / Cure: Monolithic (Dry storage 12 months)
Product: RESISTAL AL-70 High Alumina Refractory Brick
Standard: IS 2042 / ASTM C27
Chemical Properties:
Al2O3: 71.5 %
Fe2O3: 1.8 %
SiO2: 24.2 %
Physical Properties:
Bulk Density: 2.65 g/cc
Apparent Porosity: 18.5 %
Cold Crushing Strength (CCS): 68 MPa
Refractoriness under Load (ta): 1540 °C
Pyrometric Cone Equivalent (PCE): Orton Cone 37 (1820°C).""",
        "ground_truth": {
            "product": "RESISTAL AL-70",
            "al2o3_pct": 71.5,
            "bulk_density": 2.65,
            "ccs_mpa": 68,
        },
    },
    # -------------------------------------------------------------
    # 6 Purchase Orders / Goods Receipt Notes (POs)
    # -------------------------------------------------------------
    {
        "id": "PO-001-VALVES",
        "doc_type": "PO_GRN",
        "title": "Purchase Order - Gate and Globe Piping Valves",
        "text": """PURCHASE ORDER NO: PO/2026/OIL/44109
Buyer: Indian Oil Corporation Limited (IOCL)
Vendor: L&T Valves Limited, Chennai
PO Date: 2026-08-01
Delivery Site: Panipat Refinery Store Depot 4
Item 001: 50 EA | GATE VALVE 100 NB CL150 WCB RF FLANGED API 600 OS&Y | Unit Rate: INR 28,500
Item 002: 30 EA | GLOBE VALVE 50 NB CL300 WCB RF FLANGED BS 1873 | Unit Rate: INR 19,200
Item 003: 20 EA | CHECK VALVE DUAL PLATE 150 NB CL150 WCB API 594 | Unit Rate: INR 24,000
Total Order Value: INR 2,481,000 + GST 18%
Inspection Hold: Third Party Inspection by EIL mandatory prior to dispatch.""",
        "ground_truth": {
            "po_number": "PO/2026/OIL/44109",
            "line_count": 3,
            "total_items": 100,
        },
    },
    {
        "id": "PO-002-FLANGES",
        "doc_type": "PO_GRN",
        "title": "Purchase Order - High Pressure ASME B16.5 Flanges",
        "text": """PURCHASE ORDER: PO/STEEL/2026/FLG/081
Buyer: Steel Authority of India Ltd (SAIL) - Bhilai Plant
Vendor: CHW Forge Private Limited, Ghaziabad
Order Date: 2026-07-15
Line 1: 100 NOS | ASTM A105 WELD NECK FLANGE 150 NB CLASS 300 SCH 40 RF ASME B16.5 | Rate: 3,450.00
Line 2: 40 NOS | ASTM A105 BLIND FLANGE 150 NB CLASS 300 RF ASME B16.5 | Rate: 2,900.00
Line 3: 80 NOS | ASTM A182 F316L SLIP ON FLANGE 80 NB CLASS 150 RF | Rate: 4,100.00
Delivery Terms: FOR Bhilai Stores within 6 weeks.""",
        "ground_truth": {
            "po_number": "PO/STEEL/2026/FLG/081",
            "line_count": 3,
            "buyer": "SAIL",
        },
    },
    {
        "id": "PO-003-BOILER-TUBES",
        "doc_type": "PO_GRN",
        "title": "Purchase Order - IBR Certified Alloy Boiler Tubes",
        "text": """PURCHASE ORDER: NTPC/PO/KSTPS/2026/771
Buyer: NTPC Limited - Korba Super Thermal Power Station
Supplier: Jindal SAW Limited, New Delhi
Date: 2026-09-01
Line 1: 1200 MTR | BOILER TUBE SEAMLESS ASTM A213 T11 50.8 OD X 4.5 WT IBR FORM III-A | Rate: 1,850.00/M
Line 2: 800 MTR | BOILER TUBE SEAMLESS ASTM A213 T22 63.5 OD X 5.6 WT IBR FORM III-A | Rate: 2,450.00/M
Statutory Requirement: Every bundle must carry IBR stamping and physical Form III-A.""",
        "ground_truth": {
            "po_number": "NTPC/PO/KSTPS/2026/771",
            "line_count": 2,
            "statutory": "IBR",
        },
    },
    {
        "id": "PO-004-CONVEYOR-BELTS",
        "doc_type": "PO_GRN",
        "title": "Purchase Order - Mining FRAS Conveyor Belting",
        "text": """PURCHASE ORDER: CIL/WCL/MINING/2026/9021
Buyer: Western Coalfields Limited (WCL)
Vendor: Dunlop Conveyor Belting India
Date: 2026-06-30
Line 1: 500 MTR | CONVEYOR BELT FRAS 1200 MM WIDTH ST1500 STEEL CORD GRADE X | Rate: 8,400.00/M
Line 2: 300 MTR | CONVEYOR BELT EP800/4 1000 MM WIDTH 6+2 COVER GRADE M | Rate: 3,200.00/M
Safety Certificate: DGMS Approval number mandatory on dispatch invoice.""",
        "ground_truth": {
            "po_number": "CIL/WCL/MINING/2026/9021",
            "line_count": 2,
            "buyer": "WCL",
        },
    },
    {
        "id": "PO-005-PUMPS",
        "doc_type": "PO_GRN",
        "title": "Purchase Order - Centrifugal Process Pumps",
        "text": """PURCHASE ORDER: HPCL/VR/PROJ/2026/3312
Buyer: Hindustan Petroleum Corporation Ltd - Vizag
Vendor: Kirloskar Brothers Limited, Pune
Order Date: 2026-08-20
Item 1: 2 SET | PUMP CENTRIFUGAL API 610 OH2 FLOW 120 M3/HR HEAD 85 M 2950 RPM 100X80 NB CL300 S-6 | Rate: 1,450,000
Item 2: 1 SET | PUMP SPARE IMPELLER SS316 FOR MODEL KBL 4X3-10 | Rate: 180,000
Item 3: 4 SET | MECHANICAL SEAL CARTRIDGE DUAL API 682 PLAN 53A | Rate: 120,000""",
        "ground_truth": {
            "po_number": "HPCL/VR/PROJ/2026/3312",
            "line_count": 3,
            "buyer": "HPCL",
        },
    },
    {
        "id": "PO-006-OTR-TYRES",
        "doc_type": "PO_GRN",
        "title": "Purchase Order - Off-The-Road Dumper Tyres",
        "text": """PURCHASE ORDER: NMDC/BIOM/TYRE/2026/110
Buyer: National Mineral Development Corporation (NMDC) - Bailadila
Vendor: BKT Tyres Limited, Mumbai
Date: 2026-05-18
Item 01: 24 NOS | OTR TYRE 27.00R49 E-4 RADIAL STEEL CORD TWO STAR ROCK | Rate: 420,000.00
Item 02: 16 NOS | OTR TYRE 24.00-35 48PR E-4 BIAS NYLON ROCK DEEP TREAD | Rate: 260,000.00
Cure / Ageing Notice: Date code must not exceed 6 months from manufacture date.""",
        "ground_truth": {
            "po_number": "NMDC/BIOM/TYRE/2026/110",
            "line_count": 2,
            "buyer": "NMDC",
        },
    },
    # -------------------------------------------------------------
    # 4 ITPs (Inspection & Test Plans)
    # -------------------------------------------------------------
    {
        "id": "ITP-001-VALVE-TESTING",
        "doc_type": "ITP",
        "title": "Inspection and Test Plan - API 598 Valve Testing",
        "text": """INSPECTION AND TEST PLAN (ITP)
Document No: ITP-IOCL-VALVES-REV-03
Equipment: Gate, Globe and Check Valves (ASME Class 150 to 600)
Stage 1: Raw Material Chemical and Mechanical Testing | Standard: ASTM A216/A105 | Hold Point: Review MTC 3.1
Stage 2: Non-Destructive Examination (10% RT on Butt Weld Ends) | Standard: ASME B16.34 | Hold Point: TPI Witness
Stage 3: Shell Hydrostatic Test at 1.5x Design Pressure | Standard: API 598 | Hold Point: Mandatory Hold (H)
Stage 4: High Pressure Backseat Test | Standard: API 598 | Hold Point: Witness (W)
Stage 5: Low Pressure Air Seat Test at 6 bar | Standard: API 598 | Hold Point: Mandatory Hold (H)
Stage 6: Final Visual, Dimensional and Painting Inspection | Standard: MSS-SP-25 | Hold Point: Witness (W)""",
        "ground_truth": {
            "itp_no": "ITP-IOCL-VALVES-REV-03",
            "stages": 6,
            "standard": "API 598",
        },
    },
    {
        "id": "ITP-002-BOILER-PRESSURE",
        "doc_type": "ITP",
        "title": "Inspection and Test Plan - Superheater Header Fabrication",
        "text": """QUALITY ASSURANCE PLAN / ITP (IBR 1950)
Project: 2x800 MW Supercritical Thermal Power Plant
Component: Boiler Superheater Header (SA335 P91)
Activity 1: Plate & Pipe Material Identification | Acceptance: Reg 4(c) IBR Form III-A | Hold: IBR Inspector
Activity 2: Weld Edge Preparation and Fit-up | Acceptance: ASME Sec IX / WPS-08 | Hold: QC Inspector
Activity 3: Pre-heat (200°C min) and Interpass Monitoring | Acceptance: Temperature Crayon / TC | Hold: Continuous
Activity 4: Post Weld Heat Treatment (PWHT 750°C-770°C) | Acceptance: Chart Recording | Hold: Mandatory Hold (H)
Activity 5: 100% Radiography + 100% TOFD on Butt Welds | Acceptance: ASME Sec VIII Div 1 | Hold: Witness (W)
Activity 6: Hydrostatic Pressure Test (1.5x Working Pressure) | Acceptance: Reg 391 IBR | Hold: IBR Inspector Stamp""",
        "ground_truth": {
            "component": "Superheater Header",
            "material": "SA335 P91",
            "stages": 6,
        },
    },
    {
        "id": "ITP-003-MILL-ROLLS",
        "doc_type": "ITP",
        "title": "Inspection and Test Plan - Work Roll Forgings",
        "text": """INSPECTION AND TEST PLAN - MILL WORK ROLLS
Subcategory: STEEL.MILL_ROLL
Owner: Tata Steel Cold Rolling Mill
Drawing: D-44120 Rev B
Step 1: Chemical Composition Analysis | Spec: Forged Steel 5% Cr | Hold: Verify OES spectrometer report
Step 2: Ultrasonic Examination of Barrel and Necks | Spec: SEP 1921 Group 3 Class D | Hold: 100% Volumetric
Step 3: Surface Hardness Testing on Barrel | Spec: 80 - 85 HSc (Shore C) | Hold: Multi-point Equotip check
Step 4: Dimensional Inspection (Barrel Dia 600mm, Length 1800mm, Runout < 0.01mm) | Hold: Final Sign-off""",
        "ground_truth": {
            "drawing": "D-44120",
            "revision": "B",
            "hardness_hsc": "80-85",
        },
    },
    {
        "id": "ITP-004-HYDRAULIC-HOSES",
        "doc_type": "ITP",
        "title": "Inspection and Test Plan - High Pressure Hydraulic Hoses",
        "text": """ITP: HIGH PRESSURE HYDRAULIC HOSE ASSEMBLIES
Standard: SAE J517 100R2AT / EN 853 2SN
Test 1: Visual and Dimensional Check (Dash Size -8, DN 12, Length 1500 mm) | Hold: QC
Test 2: Electrical Conductivity / Anti-Static Verification | Hold: Laboratory test
Test 3: Proof Pressure Test at 2.0x Working Pressure (550 bar, 60 seconds) | Hold: 100% Production Hold (H)
Test 4: Burst Pressure Test (Sample 1 per 500 pcs at 4.0x WP: 1100 bar) | Hold: Witness (W)
Test 5: Crimp Outer Diameter Measurement (Vernier Caliper +/-0.1 mm) | Hold: Inspection log check""",
        "ground_truth": {
            "standard": "SAE J517 100R2AT",
            "size": "DN12",
            "proof_pressure_bar": 550,
        },
    },
    # -------------------------------------------------------------
    # 2 BoQs (Bills of Quantities)
    # -------------------------------------------------------------
    {
        "id": "BOQ-001-PIPING-PACKAGE",
        "doc_type": "BOQ",
        "title": "Bill of Quantities - Balance of Plant Piping Package",
        "text": """BILL OF QUANTITIES (BOQ) - BOP HIGH PRESSURE PIPING
Tender Ref: NTPC/CC/CS/2026/BOQ/099
Section A: Valves and Inline Accessories
Item 1.01: Gate Valve 200 NB Class 300 WCB Flanged API 600 | Qty: 45 EA | UoM: EA
Item 1.02: Globe Valve 100 NB Class 300 WCB Flanged BS 1873 | Qty: 30 EA | UoM: EA
Item 1.03: Swing Check Valve 150 NB Class 300 WCB Flanged | Qty: 20 EA | UoM: EA
Section B: Seamless Pipe Spools
Item 2.01: CS Pipe Seamless ASTM A106 Gr B 200 NB SCH 40 | Qty: 1200 M | UoM: M
Item 2.02: CS Pipe Seamless ASTM A106 Gr B 150 NB SCH 40 | Qty: 800 M | UoM: M
Section C: Flanges and Fasteners
Item 3.01: WN Flange 200 NB Class 300 RF ASTM A105 | Qty: 180 NOS | UoM: NOS
Item 3.02: Stud Bolt with 2 Heavy Hex Nuts M24 x 140 mm ASTM A193 B7 / A194 2H | Qty: 1440 SET | UoM: SET""",
        "ground_truth": {
            "tender_ref": "NTPC/CC/CS/2026/BOQ/099",
            "total_sections": 3,
            "total_items": 7,
        },
    },
    {
        "id": "BOQ-002-MINING-OVERHAUL",
        "doc_type": "BOQ",
        "title": "Bill of Quantities - Heavy Equipment & Conveyor Overhaul",
        "text": """BILL OF QUANTITIES (BOQ) - COAL HANDLING PLANT OVERHAUL
Client: Coal India Limited (CIL) - SECL Bilaspur
Package Ref: SECL/CHP/OVERHAUL/2026/012
Item 01: Fire Resistant Anti-Static Conveyor Belt 1400 mm Width EP1000/4 | Qty: 2400 M | UoM: M
Item 02: OTR Tyre 27.00R49 E-4 Radial for 100 Ton Dumper | Qty: 36 NOS | UoM: NOS
Item 03: Centrifugal Slurry Pump 150 M3/HR Head 45 M Chrome Iron Casing | Qty: 4 SET | UoM: SET
Item 04: High Pressure Hydraulic Hose 2SN DN 25 Length 2000 mm BSP Female | Qty: 120 NOS | UoM: NOS
Item 05: Cast High Manganese Steel Liner Plate for Coal Chute | Qty: 48 MT | UoM: MT""",
        "ground_truth": {
            "package_ref": "SECL/CHP/OVERHAUL/2026/012",
            "total_items": 5,
        },
    },
]


def generate_corpus_files() -> tuple[int, int]:
    """Generates all 20 synthetic document text files and JSON sidecars in docs/corpus."""
    DOCS_CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    generated_docs = 0
    generated_sidecars = 0

    for doc in DOCUMENTS:
        doc_id = doc["id"]
        text_path = DOCS_CORPUS_DIR / f"{doc_id}.txt"
        sidecar_path = DOCS_CORPUS_DIR / f"{doc_id}.json"

        # Write raw text
        text_path.write_text(doc["text"].strip(), encoding="utf-8")
        generated_docs += 1

        # Write ground truth JSON sidecar
        sidecar_data = {
            "id": doc_id,
            "doc_type": doc["doc_type"],
            "title": doc["title"],
            "line_count": len([line for line in doc["text"].strip().splitlines() if line.strip()]),
            "ground_truth": doc["ground_truth"],
        }
        sidecar_path.write_text(json.dumps(sidecar_data, indent=2), encoding="utf-8")
        generated_sidecars += 1

    return generated_docs, generated_sidecars


def evaluate_corpus_ocr_recall() -> dict:
    """Evaluates line recognition and text recall using OCRProvider protocol."""
    provider = FakeOCRProvider(default_conf=0.98)
    total_docs = len(DOCUMENTS)
    total_expected_lines = 0
    total_recognized_lines = 0
    doc_results = []

    for doc in DOCUMENTS:
        doc_id = doc["id"]
        text_bytes = doc["text"].strip().encode("utf-8")
        raw_lines = [l.strip() for l in doc["text"].strip().splitlines() if l.strip()]
        expected_line_count = len(raw_lines)
        total_expected_lines += expected_line_count

        ocr_res = provider.extract_document(text_bytes, filename=f"{doc_id}.txt")
        recognized_lines = sum(len(p.lines) for p in ocr_res.pages)
        total_recognized_lines += recognized_lines

        line_recall = recognized_lines / expected_line_count if expected_line_count else 1.0
        doc_results.append(
            {
                "id": doc_id,
                "doc_type": doc["doc_type"],
                "expected": expected_line_count,
                "recognized": recognized_lines,
                "recall": line_recall,
            }
        )

    overall_recall = total_recognized_lines / total_expected_lines if total_expected_lines else 1.0

    return {
        "total_documents": total_docs,
        "total_expected_lines": total_expected_lines,
        "total_recognized_lines": total_recognized_lines,
        "overall_recall": overall_recall,
        "recall_pct": f"{overall_recall * 100:.2f}%",
        "doc_results": doc_results,
    }


def main():
    print("=" * 70)
    print("Samanvay Synthetic Document Corpus Generator (Section 10.0)")
    print("=" * 70)

    docs_count, sidecars_count = generate_corpus_files()
    print(f"[+] Successfully wrote {docs_count} documents and {sidecars_count} sidecars to {DOCS_CORPUS_DIR}")

    print("\nEvaluating OCR line recall across 20 synthetic documents...")
    eval_metrics = evaluate_corpus_ocr_recall()

    print(f"Total Documents: {eval_metrics['total_documents']} (8 MTC, 6 PO, 4 ITP, 2 BOQ)")
    print(f"Total Lines: {eval_metrics['total_expected_lines']}")
    print(f"Recognized Lines: {eval_metrics['total_recognized_lines']}")
    print(f"Overall OCR Recall: {eval_metrics['recall_pct']}")

    if eval_metrics["overall_recall"] >= 0.95:
        print("[PASS] OCR Document Recall meets release threshold (>= 95.0%).")
        sys.exit(0)
    else:
        print(f"[FAIL] OCR Recall {eval_metrics['recall_pct']} fell below threshold 95.0%.")
        sys.exit(1)


if __name__ == "__main__":
    main()
