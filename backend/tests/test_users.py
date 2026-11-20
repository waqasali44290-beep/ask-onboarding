"""User management (admin only) and team ticket visibility for managers."""
from tests.conftest import TEST_PASSWORD, login


def user_id(client, username: str) -> int:
    return next(u["id"] for u in client.get("/api/users").json() if u["username"] == username)


def test_admin_creates_users_with_a_manager(client):
    manager = user_id(client, "manager")
    created = client.post("/api/users", json={"username": "Ali.R", "display_name": "Ali Raza", "role": "employee",
                                              "password": "long-enough", "manager_id": manager})
    assert created.status_code == 201
    assert (created.json()["username"], created.json()["manager_name"]) == ("ali.r", "Test manager")

    listed = {u["username"]: u for u in client.get("/api/users").json()}
    assert listed["manager"]["team_size"] == 1
    assert "password_hash" not in listed["ali.r"]
    assert client.post("/api/auth/login", json={"username": "ali.r", "password": "long-enough"}).status_code == 200


def test_validation_and_admin_only(client):
    assert client.post("/api/users", json={"username": "admin", "display_name": "X", "role": "employee",
                                           "password": "long-enough"}).status_code == 400  # taken
    assert client.post("/api/users", json={"username": "x", "display_name": "X", "role": "employee",
                                           "password": "short"}).status_code == 422
    employee = user_id(client, "employee")
    assert client.patch(f"/api/users/{user_id(client, 'manager')}", json={"manager_id": employee}).status_code == 400
    login(client, "manager")
    assert client.get("/api/users").status_code == 403


def test_reporting_lines_cannot_loop_and_admin_keeps_access(client):
    manager, admin = user_id(client, "manager"), user_id(client, "admin")
    client.patch(f"/api/users/{manager}", json={"manager_id": admin})
    assert client.patch(f"/api/users/{admin}", json={"manager_id": manager}).status_code == 400  # loop
    assert client.patch(f"/api/users/{admin}", json={"role": "employee"}).status_code == 400
    assert client.patch(f"/api/users/{admin}", json={"is_active": False}).status_code == 400


def test_deactivated_users_are_logged_out_and_cannot_log_in(client):
    employee = user_id(client, "employee")
    other = client.__class__(client.app)
    login(other, "employee")

    assert client.patch(f"/api/users/{employee}", json={"is_active": False}).json()["is_active"] is False
    assert other.get("/api/auth/me").status_code == 401
    response = other.post("/api/auth/login", json={"username": "employee", "password": TEST_PASSWORD})
    assert response.status_code == 401


def test_manager_sees_team_tickets_but_not_others(client):
    manager = user_id(client, "manager")
    client.patch(f"/api/users/{user_id(client, 'employee')}", json={"manager_id": manager})
    client.post("/api/tickets", json={"question": "Admin's own question?"})
    login(client, "employee")
    client.post("/api/tickets", json={"question": "Team member question?"})
    login(client, "manager")
    client.post("/api/tickets", json={"question": "Manager's own question?"})

    seen = [t["question"] for t in client.get("/api/tickets").json()]
    assert seen == ["Manager's own question?", "Team member question?"]
    team_ticket = client.get("/api/tickets").json()[1]
    assert client.patch(f"/api/tickets/{team_ticket['id']}", json={"status": "resolved"}).status_code == 404  # read-only

    login(client, "employee")
    assert [t["question"] for t in client.get("/api/tickets").json()] == ["Team member question?"]
