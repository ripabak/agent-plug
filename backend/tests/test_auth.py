"""Unit + API tests for authentication."""
import uuid

from app.auth import create_access_token, decode_access_token, hash_password, verify_password


def _email() -> str:
    return f"{uuid.uuid4().hex}@example.com"


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        hashed = hash_password("s3cret!")
        assert hashed != "s3cret!"
        assert verify_password("s3cret!", hashed)

    def test_wrong_password_rejected(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_hashes_are_salted(self):
        assert hash_password("same") != hash_password("same")


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token(42)
        assert decode_access_token(token) == 42

    def test_decode_garbage_returns_none(self):
        assert decode_access_token("not-a-jwt") is None


class TestAuthAPI:
    def test_register_and_me(self, client):
        email = _email()
        res = client.post(
            "/api/auth/register",
            json={"email": email, "display_name": "New", "password": "secret123"},
        )
        assert res.status_code == 201
        body = res.json()
        assert body["access_token"]
        assert body["user"]["email"] == email

        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == email

    def test_register_duplicate_email(self, client, auth_headers):
        _, email = auth_headers
        res = client.post(
            "/api/auth/register",
            json={"email": email, "display_name": "Dup", "password": "secret123"},
        )
        assert res.status_code == 400

    def test_register_short_password_rejected(self, client):
        res = client.post(
            "/api/auth/register",
            json={"email": _email(), "display_name": "X", "password": "123"},
        )
        assert res.status_code == 422

    def test_login_success(self, client, auth_headers):
        _, email = auth_headers
        res = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
        assert res.status_code == 200
        assert res.json()["access_token"]

    def test_login_wrong_password(self, client, auth_headers):
        _, email = auth_headers
        res = client.post("/api/auth/login", json={"email": email, "password": "wrong"})
        assert res.status_code == 401

    def test_me_without_token(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_with_invalid_token(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
        assert res.status_code == 401
