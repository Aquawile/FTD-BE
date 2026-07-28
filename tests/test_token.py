import unittest
from datetime import timedelta

from app.auth.token import create_access_token, verify_token
from app.auth.config import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_EXPIRATION_MINUTES,
    JWT_ISSUER,
    JWT_TOKEN_VERSION,
)


class TestToken(unittest.TestCase):
    def test_create_access_token_returns_string(self):
        token = create_access_token({"sub": 1, "email": "test@example.com"})
        self.assertIsInstance(token, str)

    def test_create_access_token_contains_required_claims(self):
        token = create_access_token({"sub": 1, "email": "test@example.com"})
        payload = verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), "1")
        self.assertEqual(payload.get("email"), "test@example.com")
        self.assertEqual(payload.get("iss"), JWT_ISSUER)
        self.assertEqual(payload.get("aud"), JWT_AUDIENCE)
        self.assertEqual(payload.get("tv"), JWT_TOKEN_VERSION)
        self.assertIsNotNone(payload.get("exp"))
        self.assertIsNotNone(payload.get("iat"))

    def test_verify_token_valid_token(self):
        token = create_access_token({"sub": 1, "email": "test@example.com"})
        payload = verify_token(token)
        self.assertIsNotNone(payload)

    def test_verify_token_expired_token(self):
        token = create_access_token({"sub": 1}, expires_delta=timedelta(seconds=-1))
        payload = verify_token(token)
        self.assertIsNone(payload)

    def test_verify_token_wrong_secret(self):
        import jwt
        token = create_access_token({"sub": 1, "email": "test@example.com"})
        wrong_token = jwt.encode(
            {
                "sub": "1",
                "exp": 9999999999,
                "iat": 0,
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
                "tv": JWT_TOKEN_VERSION,
                "email": "test@example.com",
            },
            "wrong-secret-key",
            algorithm=JWT_ALGORITHM,
        )
        payload = verify_token(wrong_token)
        self.assertIsNone(payload)

    def test_verify_token_malformed_token(self):
        payload = verify_token("not.a.valid.token")
        self.assertIsNone(payload)

    def test_verify_token_wrong_token_version(self):
        import jwt
        from app.auth.config import JWT_SECRET_KEY
        wrong_tv_token = jwt.encode(
            {
                "sub": "1",
                "exp": 9999999999,
                "iat": 0,
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
                "tv": 999,
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )
        payload = verify_token(wrong_tv_token)
        self.assertIsNone(payload)

    def test_sub_is_string_in_payload(self):
        token = create_access_token({"sub": 42, "email": "user@test.com"})
        payload = verify_token(token)
        self.assertIsInstance(payload.get("sub"), str)
        self.assertEqual(payload.get("sub"), "42")


if __name__ == "__main__":
    unittest.main()