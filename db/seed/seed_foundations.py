"""Seed initial CPSE organizations and users across four major sectors.
Ensures organization neutrality (Section 1.3, 21 Phase 1).
"""

from api.database import SyncSessionLocal
from api.models import Organization, User

ORGANIZATIONS = [
    {
        "id": "OIL-1",
        "name": "Bharat Hydrocarbon & Refining Corporation (Synthetic CPSE)",
        "gstin": "07AAACB1234D1Z5",
        "headquarters": "New Delhi",
        "segment": ["COMMON", "REFINING", "UPSTREAM", "PETCHEM"],
        "profile": {
            "erp_target": "sap",
            "field_lengths": {"description": 40, "code": 18},
            "plants": [
                {"code": "PLANT-MATHURA", "city": "Mathura", "lat": 27.4924, "lon": 77.6737},
                {"code": "PLANT-GUWAHATI", "city": "Guwahati", "lat": 26.1445, "lon": 91.7362},
            ],
            "criticality_vocabulary": ["V", "E", "D"],
            "uom_aliases": {"NOS": "EA", "MTR": "M", "TONNE": "MT"},
        },
    },
    {
        "id": "POWER-1",
        "name": "National Power Generation Corporation (Synthetic CPSE)",
        "gstin": "06AAACN5678E1Z2",
        "headquarters": "New Delhi",
        "segment": ["POWER", "COMMON"],
        "profile": {
            "erp_target": "sap",
            "field_lengths": {"description": 40, "code": 18},
            "plants": [
                {"code": "PLANT-KORBA", "city": "Korba", "lat": 22.3595, "lon": 82.7501},
                {"code": "PLANT-RAMAGUNDAM", "city": "Ramagundam", "lat": 18.7645, "lon": 79.4754},
            ],
            "criticality_vocabulary": ["CRITICAL", "NORMAL", "LOW"],
            "uom_aliases": {"NUM": "EA", "METER": "M"},
        },
    },
    {
        "id": "STEEL-1",
        "name": "Steel Enterprise of India (Synthetic CPSE)",
        "gstin": "19AAACS9012F1Z9",
        "headquarters": "Kolkata",
        "segment": ["STEEL", "COMMON"],
        "profile": {
            "erp_target": "oracle",
            "field_lengths": {"description": 60, "code": 20},
            "plants": [
                {"code": "PLANT-BHILAI", "city": "Bhilai", "lat": 21.1938, "lon": 81.3509},
                {"code": "PLANT-ROURKELA", "city": "Rourkela", "lat": 22.2604, "lon": 84.8536},
            ],
            "criticality_vocabulary": ["HIGH", "MEDIUM", "LOW"],
            "uom_aliases": {"MT": "MT", "KG": "KG"},
        },
    },
    {
        "id": "MINE-1",
        "name": "Coal & Mineral Exploration CPSE (Synthetic CPSE)",
        "gstin": "20AAACC3456G1Z3",
        "headquarters": "Ranchi",
        "segment": ["MINING", "COMMON"],
        "profile": {
            "erp_target": "maximo",
            "field_lengths": {"description": 50, "code": 16},
            "plants": [
                {"code": "PLANT-DHANBAD", "city": "Dhanbad", "lat": 23.7957, "lon": 86.4304},
                {"code": "PLANT-RANCHI", "city": "Ranchi", "lat": 23.3441, "lon": 85.3096},
            ],
            "criticality_vocabulary": ["CATEGORY_A", "CATEGORY_B", "CATEGORY_C"],
            "uom_aliases": {"EA": "EA", "RL": "ROLL"},
        },
    },
]

USERS = [
    # OIL-1 Users
    {
        "subject": "usr-oil-maker-1",
        "org_id": "OIL-1",
        "display_name": "R. Sharma (Store Officer)",
        "role": "MAKER",
        "domains": ["COMMON"],
    },
    {
        "subject": "usr-oil-checker-1",
        "org_id": "OIL-1",
        "display_name": "A. Verma (Materials Manager)",
        "role": "CHECKER",
        "domains": ["COMMON", "REFINING"],
    },
    # POWER-1 Users
    {
        "subject": "usr-power-maker-1",
        "org_id": "POWER-1",
        "display_name": "S. Gupta (Procurement Exec)",
        "role": "MAKER",
        "domains": ["COMMON"],
    },
    {
        "subject": "usr-power-checker-1",
        "org_id": "POWER-1",
        "display_name": "V. Rao (Chief Engineer)",
        "role": "CHECKER",
        "domains": ["POWER", "COMMON"],
    },
    # STEEL-1 Users
    {
        "subject": "usr-steel-maker-1",
        "org_id": "STEEL-1",
        "display_name": "M. Banerjee (Store Incharge)",
        "role": "MAKER",
        "domains": ["COMMON"],
    },
    {
        "subject": "usr-steel-checker-1",
        "org_id": "STEEL-1",
        "display_name": "P. Sen (Refractories Head)",
        "role": "CHECKER",
        "domains": ["STEEL", "COMMON"],
    },
    # MINE-1 Users
    {
        "subject": "usr-mine-maker-1",
        "org_id": "MINE-1",
        "display_name": "K. Singh (Safety Engineer)",
        "role": "MAKER",
        "domains": ["COMMON"],
    },
    {
        "subject": "usr-mine-checker-1",
        "org_id": "MINE-1",
        "display_name": "B. Mahto (Colliery Manager)",
        "role": "CHECKER",
        "domains": ["MINING", "COMMON"],
    },
]


def seed_database():
    """Populate organizations and users idempotently."""
    session = SyncSessionLocal()
    try:
        # 1. Seed Organizations
        for org_data in ORGANIZATIONS:
            org = session.query(Organization).filter_by(id=org_data["id"]).first()
            if not org:
                org = Organization(**org_data)
                session.add(org)
            else:
                org.name = org_data["name"]
                org.segment = org_data["segment"]
                org.profile = org_data["profile"]
        session.commit()
        print(f"Successfully seeded {len(ORGANIZATIONS)} organizations.")

        # 2. Seed Users
        for user_data in USERS:
            user = session.query(User).filter_by(subject=user_data["subject"]).first()
            if not user:
                user = User(**user_data)
                session.add(user)
            else:
                user.display_name = user_data["display_name"]
                user.role = user_data["role"]
                user.domains = user_data["domains"]
        session.commit()
        print(f"Successfully seeded {len(USERS)} users.")
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
