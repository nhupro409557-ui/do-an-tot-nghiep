import unittest
from unittest.mock import patch

from fastapi import Response

from app.api.routers.auth_utils import clear_refresh_cookie, set_refresh_cookie


class RefreshCookieConfigurationTest(unittest.TestCase):
    def test_https_frontend_uses_cross_site_secure_cookie(self) -> None:
        response = Response()

        with patch(
            "app.api.routers.auth_utils.settings.frontend_url",
            "https://do-an-tot-nghiep-rho.vercel.app",
        ):
            set_refresh_cookie(response, "refresh-token")

        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("secure", cookie)
        self.assertIn("samesite=none", cookie)
        self.assertIn("path=/api/auth", cookie)

    def test_http_local_frontend_keeps_development_cookie_compatible(self) -> None:
        response = Response()

        with patch(
            "app.api.routers.auth_utils.settings.frontend_url",
            "http://localhost:3000",
        ):
            set_refresh_cookie(response, "refresh-token")

        cookie = response.headers["set-cookie"].lower()
        self.assertNotIn("secure", cookie)
        self.assertIn("samesite=lax", cookie)

    def test_cookie_deletion_matches_https_cookie_attributes(self) -> None:
        response = Response()

        with patch(
            "app.api.routers.auth_utils.settings.frontend_url",
            "https://do-an-tot-nghiep-rho.vercel.app",
        ):
            clear_refresh_cookie(response)

        cookie = response.headers["set-cookie"].lower()
        self.assertIn("secure", cookie)
        self.assertIn("samesite=none", cookie)
        self.assertIn("path=/api/auth", cookie)


if __name__ == "__main__":
    unittest.main()
