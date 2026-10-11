"""Command-line utility to generate a signed demo JWT token.
Run via `uv run python scripts/demo_token.py`.
"""

import argparse

from api.security.jwt_auth import create_access_token


def main():
    parser = argparse.ArgumentParser(description="Generate demo HS256 JWT token for Samanvay.")
    parser.add_argument("--sub", default="usr-oil-maker-1", help="User subject identifier")
    parser.add_argument("--org", default="OIL-1", help="Tenant organization ID")
    parser.add_argument("--role", default="MAKER", help="User role (MAKER, CHECKER, ADMIN, etc.)")
    parser.add_argument("--domains", nargs="*", default=["COMMON"], help="Domain tags (e.g. COMMON POWER STEEL)")
    parser.add_argument("--name", default="R. Sharma", help="Display name")

    args = parser.parse_args()
    token = create_access_token(
        sub=args.sub,
        org_id=args.org,
        role=args.role,
        domains=args.domains,
        display_name=args.name,
    )

    print("=== Samanvay Demo Access Token ===")
    print(f"Subject : {args.sub}")
    print(f"Org ID  : {args.org}")
    print(f"Role    : {args.role}")
    print(f"Domains : {args.domains}")
    print("\nToken:\n" + token)
    print('\nUse with curl:\ncurl -H "Authorization: Bearer ' + token + '" http://localhost:8000/audit/verify')


if __name__ == "__main__":
    main()
