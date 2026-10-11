"""Route protection and allow-list audit test.
Verifies that every route on the FastAPI application has an auth dependency or an explicit allow-list entry.
"""

import unittest

from fastapi.testclient import TestClient

from api.main import app

# Explicit allow-list of public endpoints (Section 15, 21 Phase 1)
PUBLIC_ALLOW_LIST = {
    "/health",
    "/auth/demo-token",
    "/normalize",
    "/uom/convert",
    "/extract",
    "/extract/specs",
    "/extract/specs/{subcategory}",
    "/compare",
    "/tier",
    "/docs",
    "/docs/oauth2-redirect",
    "/openapi.json",
    "/redoc",
}


class TestRouteSecurity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_every_route_is_protected_or_allowed(self):
        """Audit every registered route on the FastAPI app."""
        for route in app.routes:
            path = getattr(route, "path", None)
            if not path:
                continue

            # Skip swagger and internal documentation routes
            if path in PUBLIC_ALLOW_LIST:
                continue

            # Attempt accessing without credentials
            methods = getattr(route, "methods", ["GET"])
            for method in methods:
                if method == "OPTIONS":
                    continue

                response = self.client.request(method, path)
                self.assertEqual(
                    response.status_code,
                    401,
                    f"Route '{method} {path}' is unauthenticated and NOT in PUBLIC_ALLOW_LIST!",
                )

    def test_public_routes_accessible_without_auth(self):
        """Verify public endpoints return 200 without token."""
        res_health = self.client.get("/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "OK")

        res_demo = self.client.post("/auth/demo-token", json={"sub": "test", "org_id": "OIL-1", "role": "MAKER"})
        self.assertEqual(res_demo.status_code, 200)
        self.assertIn("access_token", res_demo.json())

        # Test normalize endpoint
        res_norm = self.client.post("/normalize", json={"text": "GT VALVE 2INCH", "category": "VALVES"})
        self.assertEqual(res_norm.status_code, 200)
        self.assertEqual(res_norm.json()["clean_text"], "GATE VALVE 2INCH")

        # Test uom endpoint
        res_uom = self.client.post("/uom/convert", json={"qty": 10, "raw_uom": "KM"})
        self.assertEqual(res_uom.status_code, 200)
        self.assertEqual(res_uom.json()["canonical_qty"], 10000.0)

    def test_upload_requires_authentication(self):
        """Verify /ingest/upload rejects unauthenticated requests."""
        res = self.client.post("/ingest/upload", files={"file": ("test.csv", b"a,b\n1,2")})
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
