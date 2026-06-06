

def test_get_goals_default(client):
    response = client.get("/api/goals")
    data = response.get_json()
    assert data["daily_hours"] == 3.0
    assert data["monthly_hours"] == 80.0
    assert data["weekly_hours"] == 20.0
    assert response.status_code == 200

def test_get_goals_for_month_fallback(client):
    response = client.get("/api/goals?month=2025-03")
    data = response.get_json()
    assert data["daily_hours"] == 3.0
    assert data["monthly_hours"] == 80.0
    assert data["weekly_hours"] == 20.0
    assert response.status_code == 200


def test_put_goals_default_updates_global(client, db):
    """Test that PUT /api/goals with no month updates the global goals. (else)"""
    response = client.put("/api/goals", json={
        "daily_hours": 5.0,
        "weekly_hours": 27.0,
        "monthly_hours": 90.0
    })
    inserted = db.execute("SELECT * FROM goals WHERE id = 1").fetchone()
    assert inserted["daily_hours"] == 5.0
    assert inserted["weekly_hours"] == 27.0
    assert inserted["monthly_hours"] == 90.0
    assert response.status_code == 200


def test_put_goals_for_month_creates_row(client, db):
    response = client.put("/api/goals?month=2026-01", json={
        "daily_hours": 2.0,
        "weekly_hours": 18.0,
        "monthly_hours": 40.0
    })
    inserted = db.execute(
        "SELECT * FROM monthly_goals WHERE year_month = '2026-01'"
    ).fetchone()

    assert inserted is not None
    assert inserted["daily_hours"] == 2.0
    assert inserted["weekly_hours"] == 18.0
    assert inserted["monthly_hours"] == 40.0
    assert response.status_code == 200

def test_put_goals_for_month_updates_existing(client, db):
    client.put("/api/goals?month=2026-01", json={
        "daily_hours": 4.0,
        "weekly_hours": 26.0,
        "monthly_hours": 100.0,
    })
    response = client.put("/api/goals?month=2026-01", json={
        "daily_hours": 6.0,
        "weekly_hours": 35.0,
        "monthly_hours": 140.0,
    })

    inserted = db.execute(
        "SELECT * FROM monthly_goals WHERE year_month = '2026-01'"
    ).fetchone()
    
    count = db.execute(
        "SELECT COUNT(*) AS c FROM monthly_goals WHERE year_month = ?", ("2026-01",)
    ).fetchone()["c"]

    assert count == 1
    assert inserted is not None
    assert inserted["daily_hours"] == 6.0
    assert inserted["weekly_hours"] == 35.0
    assert inserted["monthly_hours"] == 140.0
    assert response.status_code == 200


def test_put_goals_for_month_does_not_affect_other_months(client, db):
    client.put("/api/goals?month=2026-01", json={
        "daily_hours": 4.0,
        "weekly_hours": 26.0,
        "monthly_hours": 100.0,
    })
    client.put("/api/goals?month=2026-02", json={
        "daily_hours": 5.0,
        "weekly_hours": 28.0,
        "monthly_hours": 102.0,
    })
    
    # change january to make sure it doesn't affect february
    client.put("/api/goals?month=2026-01", json={
        "daily_hours": 6.0,
        "weekly_hours": 35.0,
        "monthly_hours": 140.0,
    })
    inserted = db.execute(
        "SELECT * FROM monthly_goals"
    ).fetchall()

    january = db.execute(
        "SELECT * FROM monthly_goals WHERE year_month = ?", ("2026-01",)
    ).fetchone()
    february = db.execute(
        "SELECT * FROM monthly_goals WHERE year_month = ?", ("2026-02",)
    ).fetchone()

    assert len(inserted) == 2
    assert january["daily_hours"] == 6.0
    assert january["weekly_hours"] == 35.0
    assert january["monthly_hours"] == 140.0

    assert february["daily_hours"] == 5.0
    assert february["weekly_hours"] == 28.0
    assert february["monthly_hours"] == 102.0