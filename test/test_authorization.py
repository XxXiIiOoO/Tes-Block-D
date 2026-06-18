from __future__ import annotations


#Tut proveryayu polnyy auth-flow: registraciya, login, me, refresh.
def test_authorization_flow(client):
    register_response = client.post(
        "/auth/register",
        json={
            "email": "auth-flow@example.com",
            "username": "auth_flow_user",
            "password": "StrongPass123!",
        },
    )
    assert register_response.status_code == 201
    verify_response = client.post(
        "/auth/verify-email",
        json={"token": register_response.json()["verification_token"]},
    )
    assert verify_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={"email": "auth-flow@example.com", "password": "StrongPass123!"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()

    access_token = login_payload["access_token"]
    refresh_token = login_payload["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_payload = me_response.json()
    assert me_payload["email"] == "auth-flow@example.com"
    assert me_payload["email_verified"] is True
    assert me_payload["role"] == "worker"

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["user"]["email"] == "auth-flow@example.com"
