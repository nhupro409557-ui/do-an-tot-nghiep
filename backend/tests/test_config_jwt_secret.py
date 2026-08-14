import os
import unittest
from unittest.mock import patch

from app.config import Settings


class JwtSecretConfigurationTest(unittest.TestCase):
    def test_missing_jwt_secret_is_stable_across_serverless_instances(self) -> None:
        environment = {
            "DATABASE_URL": "postgresql+asyncpg://user:strong-password@db.example.com/app",
        }

        with patch.dict(os.environ, environment, clear=True):
            first = Settings(_env_file=None).jwt_secret_key
            second = Settings(_env_file=None).jwt_secret_key

        self.assertEqual(first, second)
        self.assertNotEqual(first, environment["DATABASE_URL"])

    def test_explicit_jwt_secret_remains_authoritative(self) -> None:
        environment = {
            "DATABASE_URL": "postgresql+asyncpg://user:strong-password@db.example.com/app",
            "JWT_SECRET_KEY": "configured-production-secret",
        }

        with patch.dict(os.environ, environment, clear=True):
            configured = Settings(_env_file=None).jwt_secret_key

        self.assertEqual(configured, environment["JWT_SECRET_KEY"])


if __name__ == "__main__":
    unittest.main()
