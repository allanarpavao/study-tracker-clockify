import app as app_module

def test_get_goals_for_month_returns_monthly_when_exists(db):
    db.execute(" INSERT INTO monthly_goals (year_month, daily_hours, weekly_hours, monthly_hours) VALUES (?, ?, ?, ?)",
               ("2026-01", 4.0, 26.0, 100.0))
    db.commit()
    monthly_goals = app_module.get_goals_for_month(db, "2026-01")
    assert monthly_goals["daily_hours"] == 4.0
    assert monthly_goals["weekly_hours"] == 26.0
    assert monthly_goals["monthly_hours"] == 100.0


def test_get_goals_for_month_falls_back_to_default(db):
    monthly_goals_without_personalization = app_module.get_goals_for_month(db, "2026-02")
    assert monthly_goals_without_personalization["daily_hours"] == 3.0
    assert monthly_goals_without_personalization["weekly_hours"] == 20.0
    assert monthly_goals_without_personalization["monthly_hours"] == 80.0

def test_get_project_filter_empty_returns_no_restriction(db):
    sql_fragment, params = app_module.get_project_filter(db)
    assert sql_fragment == ""
    assert params == []

def test_get_project_filter_returns_only_included(db):
    db.execute(
        "INSERT INTO project_filters (project, included) VALUES (?, ?)",
        ("Project A", 1)
    )
    db.execute(
        "INSERT INTO project_filters (project, included) VALUES (?, ?)",
        ("Project B", 0)
    )
    db.execute(
        "INSERT INTO project_filters (project, included) VALUES (?, ?)",
        ("Project C", 1)
    )
    sql_fragment, params = app_module.get_project_filter(db)
    assert sql_fragment == " AND project IN (?,?)"
    assert set(params) == {"Project A", "Project C"} #order not important
    # assert params == ["Project A", "Project C"]
