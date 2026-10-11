"""Subcategory Classifier Service.

Classifies material item descriptions into registered domain subcategories using:
1. Category hint validation.
2. Rule-based regex and keyword patterns across all 21 standard/deep subcategories.
3. Centroid/token-similarity fallback.
4. Ambiguity and low-confidence gating flagging CATEGORY_UNCERTAIN (Invariant S3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from api.core.trigram import similarity as trigram_similarity


@dataclass
class ClassificationResult:
    """Subcategory classification output."""

    subcategory: str | None
    major_category: str | None
    confidence: float
    flags: list[str] = field(default_factory=list)

    @property
    def is_uncertain(self) -> bool:
        """True if category classification is low confidence or uncertain."""
        return "CATEGORY_UNCERTAIN" in self.flags or self.subcategory is None


# Registry of known subcategories to major categories
SUBCATEGORY_MAP: dict[str, str] = {
    # Common
    "VALVES.GATE": "VALVES",
    "PIPES.PIPE": "PIPES",
    "FLANGES.FLANGE": "FLANGES",
    "CABLES.POWER": "CABLES",
    "MOTORS.EX": "MOTORS",
    "STEEL.STRUCTURAL": "STEEL",
    "STEEL.REBAR": "STEEL",
    "BEARINGS.BEARING": "BEARINGS",
    "FASTENERS.STUD_BOLT": "FASTENERS",
    "INSTRUMENTS.TRANSMITTER": "INSTRUMENTS",
    # Power
    "POWER.TRANSFORMER": "POWER",
    "POWER.BREAKER": "POWER",
    "POWER.BOILER_TUBE": "POWER",
    # Steel
    "STEEL.REFRACTORY": "STEEL",
    "STEEL.CONVEYOR_BELT": "STEEL",
    "STEEL.MILL_ROLL": "STEEL",
    # Mining
    "MINING.OTR_TYRE": "MINING",
    "MINING.WIRE_ROPE": "MINING",
    # Heavy Engineering
    "HEAVY.PUMP_CENTRIFUGAL": "HEAVY",
    "HEAVY.HYDRAULIC_HOSE": "HEAVY",
    "HEAVY.MADE_TO_DRAWING": "HEAVY",
}

# Rule-based patterns with weights and negative context guards
RULES: list[dict] = [
    {
        "subcategory": "HEAVY.MADE_TO_DRAWING",
        "patterns": [
            re.compile(
                r"\b(?:MADE\s+TO\s+DRAWING|AS\s+PER\s+DRG|DRAWING\s+NO|DRG\s+NO|FABRICATED\s+AS\s+PER\s+DRG)\b",
                re.IGNORECASE,
            ),
        ],
        "weight": 0.98,
    },
    {
        "subcategory": "STEEL.REFRACTORY",
        "patterns": [
            re.compile(
                r"\b(?:REFRACTORY|FIRECLAY|MAG-CARBON|MAGNESIA-CARBON|CASTABLE|RAMMING\s+MASS|GUNNING\s+MIX)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:AL2O3\s*\d+%|MGO\s*\d+%|REFRACTORY\s+BRICK)\b", re.IGNORECASE),
        ],
        "weight": 0.96,
    },
    {
        "subcategory": "MINING.OTR_TYRE",
        "patterns": [
            re.compile(r"\b(?:OTR\s+TYRE|OTR\s+TIRE|HAUL\s+TRUCK\s+TYRE|LOADER\s+TYRE)\b", re.IGNORECASE),
            re.compile(r"\b\d{2}\.\d{2}R\d{2}\b", re.IGNORECASE),  # 27.00R49
        ],
        "weight": 0.97,
    },
    {
        "subcategory": "STEEL.CONVEYOR_BELT",
        "patterns": [
            re.compile(r"\b(?:CONVEYOR\s+BELT|CONVEYOR\s+BELTING)\b", re.IGNORECASE),
            re.compile(r"\b(?:EP\s*\d+/\d+|ST\s*\d{3,4})\b.*\b(?:BELT|BELTING)\b", re.IGNORECASE),
        ],
        "weight": 0.96,
    },
    {
        "subcategory": "STEEL.MILL_ROLL",
        "patterns": [
            re.compile(
                r"\b(?:MILL\s+ROLL|WORK\s+ROLL|BACKUP\s+ROLL|EDGER\s+ROLL|ROLLING\s+MILL\s+ROLL)\b", re.IGNORECASE
            ),
        ],
        "weight": 0.96,
    },
    {
        "subcategory": "MINING.WIRE_ROPE",
        "patterns": [
            re.compile(r"\b(?:WIRE\s+ROPE|STEEL\s+WIRE\s+ROPE|HOIST\s+ROPE|WINDER\s+ROPE)\b", re.IGNORECASE),
            re.compile(r"\b6X(?:36|19|37)\b.*\b(?:IWRC|FC)\b", re.IGNORECASE),
        ],
        "weight": 0.96,
    },
    {
        "subcategory": "HEAVY.HYDRAULIC_HOSE",
        "patterns": [
            re.compile(r"\b(?:HYDRAULIC\s+HOSE|HOSE\s+ASSEMBLY|HOSE\s+ASSY)\b", re.IGNORECASE),
            re.compile(r"\b(?:100R[12]AT|100R12|2SN|4SP|4SH)\b", re.IGNORECASE),
        ],
        "weight": 0.96,
    },
    {
        "subcategory": "POWER.BOILER_TUBE",
        "patterns": [
            re.compile(r"\b(?:BOILER\s+TUBE|SUPERHEATER\s+TUBE|ECONOMISER\s+TUBE|REHEATER\s+TUBE)\b", re.IGNORECASE),
            re.compile(r"\b(?:SA213|A213|SA192|A192)\s*[- ]?(?:T11|T22|T91|T92|A1)\b", re.IGNORECASE),
        ],
        "weight": 0.96,
    },
    {
        "subcategory": "POWER.TRANSFORMER",
        "patterns": [
            re.compile(r"\b(?:POWER\s+TRANSFORMER|DISTRIBUTION\s+TRANSFORMER|TRANSFORMER|XMER)\b", re.IGNORECASE),
            re.compile(r"\b(?:ONAN|ONAF|OFAF)\b.*\b(?:KVA|MVA)\b", re.IGNORECASE),
        ],
        "weight": 0.95,
    },
    {
        "subcategory": "POWER.BREAKER",
        "patterns": [
            re.compile(
                r"\b(?:CIRCUIT\s+BREAKER|VACUUM\s+CIRCUIT\s+BREAKER|VCB|SF6\s+BREAKER|ACB|MCCB)\b", re.IGNORECASE
            ),
        ],
        "weight": 0.95,
    },
    {
        "subcategory": "HEAVY.PUMP_CENTRIFUGAL",
        "patterns": [
            re.compile(
                r"\b(?:CENTRIFUGAL\s+PUMP|BOILER\s+FEED\s+PUMP|PROCESS\s+PUMP|API\s*610\s+PUMP)\b", re.IGNORECASE
            ),
            re.compile(r"\bAPI\s*610\b", re.IGNORECASE),
        ],
        "weight": 0.95,
    },
    {
        "subcategory": "VALVES.GATE",
        "patterns": [
            re.compile(r"\b(?:GATE\s+VALVE|VLV\s+GT|VALVE\s+GATE|GATE\s+VLV)\b", re.IGNORECASE),
            re.compile(r"\b(?:API\s*600|API\s*602|API\s*603)\b", re.IGNORECASE),
        ],
        "weight": 0.95,
    },
    {
        "subcategory": "FLANGES.FLANGE",
        "patterns": [
            re.compile(
                r"\b(?:WNRF|SORF|BLRF|SW\s+FLG|SLIP-ON\s+FLANGE|WELD\s+NECK\s+FLANGE|BLIND\s+FLANGE|FLANGE)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:ASME\s*B16\.5|B16\.47)\b", re.IGNORECASE),
        ],
        "weight": 0.94,
    },
    {
        "subcategory": "PIPES.PIPE",
        "patterns": [
            re.compile(
                r"\b(?:SMLS\s+PIPE|ERW\s+PIPE|SEAMLESS\s+PIPE|STEEL\s+PIPE|LINE\s+PIPE|ASTM\s+A106|A53|API\s*5L)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\bPIPE\b", re.IGNORECASE),
        ],
        "negatives": [re.compile(r"\b(?:BOILER\s+TUBE|HOSE|TYRE)\b", re.IGNORECASE)],
        "weight": 0.92,
    },
    {
        "subcategory": "CABLES.POWER",
        "patterns": [
            re.compile(
                r"\b(?:POWER\s+CABLE|XLPE\s+CABLE|PVC\s+CABLE|ARMOURED\s+CABLE|CONTROL\s+CABLE)\b", re.IGNORECASE
            ),
            re.compile(r"\b\d+(?:\.5)?C\s*[X*]\s*\d+(?:\.\d+)?\b", re.IGNORECASE),  # 4C X 16
        ],
        "negatives": [re.compile(r"\b(?:WIRE\s+ROPE)\b", re.IGNORECASE)],
        "weight": 0.94,
    },
    {
        "subcategory": "MOTORS.EX",
        "patterns": [
            re.compile(
                r"\b(?:INDUCTION\s+MOTOR|IND\s+MOT|ELECTRIC\s+MOTOR|SQUIRREL\s+CAGE\s+MOTOR|FLAMEPROOF\s+MOTOR)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:TEFC|FLAMEPROOF|EXPLOSION\s+PROOF)\b.*\b(?:MOTOR|KW|HP)\b", re.IGNORECASE),
        ],
        "weight": 0.94,
    },
    {
        "subcategory": "STEEL.REBAR",
        "patterns": [
            re.compile(r"\b(?:TMT\s+BAR|REBAR|CRS\s+BAR|FE\s*500D|FE\s*550D|IS\s*1786)\b", re.IGNORECASE),
        ],
        "weight": 0.95,
    },
    {
        "subcategory": "STEEL.STRUCTURAL",
        "patterns": [
            re.compile(r"\b(?:ISMB|ISMC|ISJB|ISLB|ISWB|ISA|ISNT)\s*\d+\b", re.IGNORECASE),
            re.compile(r"\b(?:STRUCTURAL\s+STEEL|E250A|E250BR|E350|IS\s*2062)\b", re.IGNORECASE),
        ],
        "weight": 0.95,
    },
    {
        "subcategory": "BEARINGS.BEARING",
        "patterns": [
            re.compile(
                r"\b(?:BALL\s+BEARING|ROLLER\s+BEARING|TAPER\s+ROLLER\s+BEARING|SPHERICAL\s+ROLLER\s+BEARING)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:BEARING\s+(?:6[0-9]{3}|7[0-9]{3}|2[0-9]{4}|NU\s*[0-9]{3}))\b", re.IGNORECASE),
            re.compile(r"\b(?:6[0-9]{3}|7[0-9]{3}|2[0-9]{4})\s*(?:2RS|2Z|ZZ|C3|C4)\b", re.IGNORECASE),
        ],
        "weight": 0.95,
    },
    {
        "subcategory": "FASTENERS.STUD_BOLT",
        "patterns": [
            re.compile(r"\b(?:STUD\s+BOLT|HEX\s+BOLT|HEX\s+NUT|FASTENER)\b", re.IGNORECASE),
            re.compile(r"\b(?:A193\s+B7|A194\s+2H|GRADE\s+8\.8|GRADE\s+10\.9)\b", re.IGNORECASE),
            re.compile(r"\b(?:STUD\s+M\d+|BOLT\s+M\d+)\b", re.IGNORECASE),
        ],
        "weight": 0.94,
    },
    {
        "subcategory": "INSTRUMENTS.TRANSMITTER",
        "patterns": [
            re.compile(
                r"\b(?:PRESSURE\s+TRANSMITTER|TEMPERATURE\s+TRANSMITTER|LEVEL\s+TRANSMITTER|DIFF(?:ERENTIAL)?\s+PRESSURE\s+TRANSMITTER|FLOW\s+TRANSMITTER)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:4-20MA|HART\s+PROTOCOL|TRANSMITTER)\b", re.IGNORECASE),
        ],
        "weight": 0.94,
    },
]

# Precomputed centroid keywords per subcategory for similarity fallback
CENTROID_KEYWORDS: dict[str, list[str]] = {
    "VALVES.GATE": ["valve", "gate", "api600", "flanged", "trim", "bonnet", "wedge"],
    "PIPES.PIPE": ["pipe", "seamless", "smls", "erw", "carbon", "steel", "astm", "a106"],
    "FLANGES.FLANGE": ["flange", "wnrf", "sorf", "blrf", "asme", "b16.5", "raised", "face"],
    "CABLES.POWER": ["cable", "power", "xlpe", "pvc", "armoured", "conductor", "copper", "aluminium", "core"],
    "MOTORS.EX": ["motor", "induction", "flameproof", "ex", "tefc", "squirrel", "cage", "frame", "pole"],
    "STEEL.STRUCTURAL": ["steel", "structural", "beam", "channel", "angle", "ismb", "ismc", "isa", "e250"],
    "STEEL.REBAR": ["rebar", "tmt", "bar", "crs", "fe500d", "fe550d", "diameter", "reinforcement"],
    "BEARINGS.BEARING": ["bearing", "ball", "roller", "clearance", "skf", "fag", "seal", "shield"],
    "FASTENERS.STUD_BOLT": ["stud", "bolt", "nut", "fastener", "b7", "2h", "thread", "metric"],
    "INSTRUMENTS.TRANSMITTER": ["transmitter", "instrument", "pressure", "temperature", "level", "hart", "4-20ma"],
    "POWER.TRANSFORMER": ["transformer", "xmer", "power", "distribution", "kva", "mva", "dyn11", "onan"],
    "POWER.BREAKER": ["breaker", "circuit", "vcb", "sf6", "acb", "mccb", "breaking", "capacity"],
    "POWER.BOILER_TUBE": ["boiler", "tube", "superheater", "sa213", "t22", "t91", "ibr"],
    "STEEL.REFRACTORY": ["refractory", "brick", "castable", "magnesia", "carbon", "alumina", "mortar"],
    "STEEL.CONVEYOR_BELT": ["conveyor", "belt", "belting", "ep", "carcass", "ply", "fras", "width"],
    "STEEL.MILL_ROLL": ["roll", "mill", "work", "backup", "barrel", "drawing", "rolling"],
    "MINING.OTR_TYRE": ["tyre", "tire", "otr", "haul", "truck", "loader", "radial", "tread"],
    "MINING.WIRE_ROPE": ["rope", "wire", "steel", "iwrc", "hoist", "winder", "mining", "lay"],
    "HEAVY.PUMP_CENTRIFUGAL": ["pump", "centrifugal", "api610", "head", "flow", "impeller", "casing"],
    "HEAVY.HYDRAULIC_HOSE": ["hose", "hydraulic", "assembly", "2sn", "100r2at", "pressure", "fitting"],
    "HEAVY.MADE_TO_DRAWING": ["drawing", "part", "fabricated", "drg", "revision", "owner", "machined"],
}


def classify_subcategory(text: str, category_hint: str | None = None) -> ClassificationResult:
    """Classifies a material description into a canonical subcategory.

    Args:
        text: Raw or normalized material text description.
        category_hint: Optional category or subcategory hint.

    Returns:
        ClassificationResult with subcategory, confidence, and flags.
    """
    if not text or not text.strip():
        return ClassificationResult(
            subcategory=None,
            major_category=None,
            confidence=0.0,
            flags=["CATEGORY_UNCERTAIN"],
        )

    clean = text.strip()

    # 1. Direct validation if category_hint is a full canonical subcategory
    if category_hint:
        hint_upper = category_hint.strip().upper()
        if hint_upper in SUBCATEGORY_MAP:
            return ClassificationResult(
                subcategory=hint_upper,
                major_category=SUBCATEGORY_MAP[hint_upper],
                confidence=0.98,
                flags=[],
            )
        # Check if hint is a major category
        matching_major = [sub for sub, major in SUBCATEGORY_MAP.items() if major == hint_upper]
        if len(matching_major) == 1:
            return ClassificationResult(
                subcategory=matching_major[0],
                major_category=hint_upper,
                confidence=0.92,
                flags=[],
            )

    # 2. Rule-based regex pattern matching
    matched_rules: list[tuple[str, float]] = []
    for rule in RULES:
        sub = rule["subcategory"]
        patterns = rule["patterns"]
        negatives = rule.get("negatives", [])

        # Check negative context guards
        if any(neg.search(clean) for neg in negatives):
            continue

        for pat in patterns:
            if pat.search(clean):
                matched_rules.append((sub, rule["weight"]))
                break

    if matched_rules:
        # Find best rule match
        # If all matches point to the same subcategory, return high confidence
        sub_counts: dict[str, float] = {}
        for sub, weight in matched_rules:
            sub_counts[sub] = max(sub_counts.get(sub, 0.0), weight)

        # Filter by category_hint if hint provided
        if category_hint:
            hint_upper = category_hint.strip().upper()
            filtered = {
                s: w for s, w in sub_counts.items() if SUBCATEGORY_MAP[s] == hint_upper or s.startswith(hint_upper)
            }
            if filtered:
                sub_counts = filtered

        # If exactly one subcategory matched or highest has distinct lead
        sorted_subs = sorted(sub_counts.items(), key=lambda x: x[1], reverse=True)
        best_sub, best_conf = sorted_subs[0]

        # Conflict check if multiple different subcategories matched with high confidence
        if len(sorted_subs) > 1:
            second_sub, second_conf = sorted_subs[1]
            if second_conf >= 0.95 and best_conf >= 0.95 and best_sub != second_sub:
                # Ambiguous collision between distinct families
                return ClassificationResult(
                    subcategory=best_sub,
                    major_category=SUBCATEGORY_MAP.get(best_sub),
                    confidence=0.65,
                    flags=["CATEGORY_UNCERTAIN"],
                )

        return ClassificationResult(
            subcategory=best_sub,
            major_category=SUBCATEGORY_MAP.get(best_sub),
            confidence=best_conf,
            flags=[],
        )

    # 3. Fallback: Centroid / token overlap and trigram similarity
    lower_tokens = set(re.findall(r"[a-z0-9]+", clean.lower()))
    best_fallback_sub: str | None = None
    best_fallback_score: float = 0.0

    for sub, keywords in CENTROID_KEYWORDS.items():
        if category_hint:
            hint_upper = category_hint.strip().upper()
            if SUBCATEGORY_MAP.get(sub) != hint_upper and not sub.startswith(hint_upper):
                continue

        keyword_set = set(keywords)
        overlap = len(lower_tokens & keyword_set)
        jaccard = overlap / len(lower_tokens | keyword_set) if (lower_tokens | keyword_set) else 0.0
        tri_sim = trigram_similarity(clean.lower(), " ".join(keywords))
        combined = 0.6 * jaccard + 0.4 * tri_sim

        if combined > best_fallback_score:
            best_fallback_score = combined
            best_fallback_sub = sub

    if best_fallback_sub and best_fallback_score >= 0.15:
        confidence = min(0.85, 0.50 + best_fallback_score)
        return ClassificationResult(
            subcategory=best_fallback_sub,
            major_category=SUBCATEGORY_MAP.get(best_fallback_sub),
            confidence=confidence,
            flags=[],
        )

    # 4. Low confidence / uncertain fallback
    return ClassificationResult(
        subcategory=None,
        major_category=None,
        confidence=0.0,
        flags=["CATEGORY_UNCERTAIN"],
    )
