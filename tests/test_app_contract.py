import unittest
from unittest.mock import patch

from app import app
from auth import routes as auth_routes


class AppContractTests(unittest.TestCase):
    def test_app_routes_do_not_duplicate_api_prefix(self):
        paths = {route.path for route in app.routes if hasattr(route, "path")}
        self.assertNotIn("/api/api/auth", paths)
        self.assertNotIn("/api/api/stocks", paths)
        self.assertIn("/api/auth/register", paths)
        self.assertIn("/api/stocks", paths)

    def test_register_creates_user_once(self):
        with patch.object(auth_routes.db, "get_user_by_username", return_value=None), \
             patch.object(auth_routes, "hash_password", return_value="hashed"), \
             patch.object(auth_routes.db, "create_user", return_value={"id": 1, "username": "newuser", "role": "user"}) as mock_create_user, \
             patch.object(auth_routes, "create_access_token", return_value="token"):
            response = auth_routes.register(
                auth_routes.RegisterRequest(
                    username="newuser",
                    email="newuser@example.com",
                    password="Password123!",
                )
            )

        self.assertEqual(mock_create_user.call_count, 1)
        self.assertEqual(response.access_token, "token")
        self.assertEqual(response.username, "newuser")


if __name__ == "__main__":
    unittest.main()
