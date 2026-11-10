from decimal import Decimal
from tests.conftest import make_auth_headers
from app.models.cash_register import CashRegister
from app.models.fund_transfer import FundTransfer


def test_fund_transfer_workflow(client, db, seed_data):
    agent = seed_data["agent"]
    director = seed_data["director"]
    agent_headers = make_auth_headers(agent)
    dir_headers = make_auth_headers(director)

    # Agent initiates transfer of 10,000 DA to director
    res_create = client.post(
        "/api/v1/fund-transfers",
        headers=agent_headers,
        json={
            "to_user_id": director.id,
            "branch_id": seed_data["branch1"].id,
            "amount": 10000.00,
            "reason": "Recettes de la journée",
        },
    )
    assert res_create.status_code == 200
    transfer_data = res_create.json()
    transfer_id = transfer_data["id"]
    assert transfer_data["status"] == "pending"

    # Director confirms receipt
    res_confirm = client.post(
        f"/api/v1/fund-transfers/{transfer_id}/confirm",
        headers=dir_headers,
    )
    assert res_confirm.status_code == 200
    assert res_confirm.json()["status"] == "confirmed"

    # Verify immutability: cancelling confirmed transfer is rejected (400)
    res_cancel = client.post(
        f"/api/v1/fund-transfers/{transfer_id}/cancel",
        headers=dir_headers,
    )
    assert res_cancel.status_code == 400


def test_fund_transfer_contested(client, db, seed_data):
    agent = seed_data["agent"]
    director = seed_data["director"]
    agent_headers = make_auth_headers(agent)
    dir_headers = make_auth_headers(director)

    res_create = client.post(
        "/api/v1/fund-transfers",
        headers=agent_headers,
        json={
            "to_user_id": director.id,
            "branch_id": seed_data["branch1"].id,
            "amount": 5000.00,
            "reason": "Recettes partielles",
        },
    )
    t_id = res_create.json()["id"]

    # Director contests
    res_contest = client.post(
        f"/api/v1/fund-transfers/{t_id}/contest",
        headers=dir_headers,
        json={"reason": "Montant incomplet dans l'enveloppe"},
    )
    assert res_contest.status_code == 200
    assert res_contest.json()["status"] == "contested"

