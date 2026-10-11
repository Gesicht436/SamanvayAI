"""Unit tests for api.security: JWT tokens, Maker-Checker, and domain tags."""

import unittest

from fastapi import HTTPException

from api.security.jwt_auth import (
    AuthUser,
    create_access_token,
    decode_access_token,
    verify_maker_checker,
)


class TestAuth(unittest.TestCase):
    def test_create_and_decode_valid_token(self):
        token = create_access_token(
            sub="usr-101",
            org_id="OIL-1",
            role="MAKER",
            domains=["COMMON", "POWER"],
            display_name="Test Maker",
        )
        self.assertIsInstance(token, str)

        user = decode_access_token(token)
        self.assertIsInstance(user, AuthUser)
        self.assertEqual(user.sub, "usr-101")
        self.assertEqual(user.org_id, "OIL-1")
        self.assertEqual(user.role, "MAKER")
        self.assertIn("COMMON", user.domains)
        self.assertEqual(user.display_name, "Test Maker")

    def test_invalid_token_raises_401(self):
        with self.assertRaises(HTTPException) as ctx:
            decode_access_token("not-a-valid-jwt-token")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_TOKEN")

    def test_maker_checker_violation_raises_403(self):
        # Same user proposing and approving must fail
        with self.assertRaises(HTTPException) as ctx:
            verify_maker_checker(proposer_sub="usr-101", approver_sub="usr-101")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail["code"], "MAKER_CHECKER_VIOLATION")

    def test_maker_checker_distinct_passes(self):
        # Different users must succeed without exception
        try:
            verify_maker_checker(proposer_sub="usr-101", approver_sub="usr-102")
        except HTTPException:
            self.fail("verify_maker_checker raised HTTPException unexpectedly for distinct users.")


if __name__ == "__main__":
    unittest.main()
