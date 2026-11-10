from tests.conftest import make_auth_headers
from app.core.security import create_access_token


def test_dg_can_access_any_branch(client, seed_data):
    headers = make_auth_headers(seed_data["dg"])
    response = client.get("/api/v1/students?branch_id=2", headers=headers)
    assert response.status_code == 200


def test_director_blocked_from_another_branch(client, seed_data):
    # Director of branch 1 requests branch 2
    headers = make_auth_headers(seed_data["director"])
    response = client.get(f"/api/v1/students?branch_id={seed_data['branch2'].id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


def test_inter_branch_grant_allows_access(client, seed_data):
    # Create grant for branch 2
    token_with_grant = create_access_token(
        subject=str(seed_data["director"].id),
        role=seed_data["director"].role,
        branch_id=seed_data["branch1"].id,
        extra_claims={"granted_branches": [seed_data["branch2"].id]},
    )
    headers = {"Authorization": f"Bearer {token_with_grant}"}
    response = client.get(f"/api/v1/students?branch_id={seed_data['branch2'].id}", headers=headers)
    assert response.status_code == 200

