import jwt

from tests.conftest import SECRET, auth, make_token


def test_valid_nest_shaped_token_accepted(client):
    r = client.get("/ai/v1/datasets", headers=auth())
    assert r.status_code == 200 and r.json() == []


def test_sub_claim_accepted_instead_of_id(client):
    assert client.get("/ai/v1/datasets", headers=auth(use_sub=True)).status_code == 200


def test_missing_token_401(client):
    r = client.get("/ai/v1/datasets")
    assert r.status_code == 401
    assert r.json()["success"] is False and r.json()["code"] == "NOT_AUTHENTICATED"


def test_wrong_secret_401(client):
    assert client.get("/ai/v1/datasets", headers=auth(secret="other")).status_code == 401


def test_expired_401(client):
    r = client.get("/ai/v1/datasets", headers=auth(exp_in=-10))
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


def test_tampered_401(client):
    tok = make_token()
    head, body, sig = tok.split(".")
    bad = f"{head}.{body[:-2]}xx.{sig}"
    assert client.get("/ai/v1/datasets", headers=auth(bad)).status_code == 401


def test_missing_email_401(client):
    assert client.get("/ai/v1/datasets", headers=auth(email=None)).status_code == 401


def test_missing_exp_401(client):
    tok = jwt.encode({"id": "u1", "email": "a@b.c"}, SECRET, algorithm="HS256")
    assert client.get("/ai/v1/datasets", headers=auth(tok)).status_code == 401


def test_alg_none_rejected(client):
    tok = jwt.encode({"id": "u1", "email": "a@b.c", "exp": 9999999999}, None, algorithm="none")
    assert client.get("/ai/v1/datasets", headers=auth(tok)).status_code == 401


def test_health_needs_no_auth_and_survives_dependencies_down(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["db"] == "up" and body["qdrant"] == "down" and body["ollama"] == "down"
