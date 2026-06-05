import app as app_module


def test_init_db_creates_all_tables(db):
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    table_names = {row["name"] for row in rows}
    expected = {"sessions", "goals", "monthly_goals", "project_filters"}
    assert expected.issubset(table_names)


def test_init_db_inserts_default_goals(db):
    goals = db.execute("SELECT * FROM goals WHERE id = 1").fetchone()
    assert goals is not None
    assert goals["daily_hours"] == 3.0
    assert goals["weekly_hours"] == 20.0
    assert goals["monthly_hours"] == 80.0


def test_init_db_is_idempotent(db):
    """Running init_db multiple times should not create duplicate entries."""
    app_module.init_db()
    count = db.execute("SELECT COUNT(*) AS c FROM goals").fetchone()["c"]
    assert count == 1