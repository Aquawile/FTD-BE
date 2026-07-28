import unittest

from app.auth.hasher import hash_password, verify_password


class TestHasher(unittest.TestCase):
    def test_hash_password_produces_bcrypt_hash(self):
        result = hash_password("testpass123")
        self.assertTrue(result.startswith("$2b$"))

    def test_verify_password_correct(self):
        h = hash_password("testpass123")
        self.assertTrue(verify_password("testpass123", h))

    def test_verify_password_incorrect(self):
        h = hash_password("testpass123")
        self.assertFalse(verify_password("wrongpass", h))

    def test_hash_password_unique_salt(self):
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        self.assertNotEqual(h1, h2)

    def test_verify_password_returns_false_for_wrong_hash(self):
        self.assertFalse(verify_password("testpass123", "$2b$12$invalidhashnotavalidbcrypthash"))


if __name__ == "__main__":
    unittest.main()