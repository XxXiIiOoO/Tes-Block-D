from __future__ import annotations

from tests.helpers import approve_registered_user_in_test_app


#Tut ya vynes test_local_domain_admin_style_email_is_accepted, chtoby ne razduvat ostalnoy kod.
def test_local_domain_admin_style_email_is_accepted(client):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "tester@blocktest.local",
            "username": "localtester",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201
    payload = register_response.json()
    assert payload["user"]["email"] == "tester@blocktest.local"
    approve_registered_user_in_test_app(payload["user"]["id"])

    login_response = client.post(
        "/auth/login",
        json={"email": "tester@blocktest.local", "password": "secret123"},
    )
    assert login_response.status_code == 200
