import app as app_module
import io

def test_import_no_file_returns_error(client):
    """Test that importing without a file returns an error."""
    response = client.post("/api/import", data={})
    assert response.get_json()["error"] == "Nenhum arquivo enviado"
    assert response.status_code == 400

def test_import_inserts_valid_records(client, db):
    """Test that valid CSV records are inserted into the database."""

    csv_content = (
    "Start Date,Project,Task,Description,Start Time,End Time,Duration (decimal)\n"
    "21/05/2026,Estudos,AWS Academy,Módulo 1,09:04:22,09:59:43,0.92\n")

    csv_bytes = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
    "/api/import",
    data={"file": (csv_bytes, "test.csv")},
    content_type="multipart/form-data",
    )

    data = response.get_json()
    row = db.execute("SELECT * FROM sessions").fetchone()

    assert row["date"] == "2026-05-21"
    assert row["project"] == "Estudos"
    assert row["duration_hours"] == 0.92
    assert data["inserted"] == 1
    assert data["skipped"] == 0

def test_import_skips_duplicates_same_file(client, db):
    """Test that duplicate records are skipped during import."""

    csv_content = (
    "Start Date,Project,Task,Description,Start Time,End Time,Duration (decimal)\n"
    "21/05/2026,Estudos,AWS Academy,Módulo 1,09:04:22,09:59:43,0.92\n"
    "21/05/2026,Estudos,AWS Academy,Módulo 1,09:04:22,09:59:43,0.92\n")

    csv_bytes = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
    "/api/import",
    data={"file": (csv_bytes, "test.csv")},
    content_type="multipart/form-data",
    )
    data = response.get_json()
    count = db.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
    
    assert data["inserted"] == 1
    assert data["skipped"] == 1
    assert count == 1

def test_import_skips_duplicates_two_files(client, db):
    """Test that duplicate records are skipped during import with different files."""

    csv_content = (
    "Start Date,Project,Task,Description,Start Time,End Time,Duration (decimal)\n"
    "21/05/2026,Estudos,AWS Academy,Módulo 1,09:04:22,09:59:43,0.92\n")

    csv_bytes_1 = io.BytesIO(csv_content.encode("utf-8"))
    response_1 = client.post(
        "/api/import",
        data={"file": (csv_bytes_1, "test.csv")},
        content_type="multipart/form-data")

    csv_bytes_2 = io.BytesIO(csv_content.encode("utf-8"))
    response_2 = client.post(
        "/api/import",
        data={"file": (csv_bytes_2, "test.csv")},
        content_type="multipart/form-data")

    data = response_2.get_json()
    count = db.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
    
    assert data["inserted"] == 0
    assert data["skipped"] == 1
    assert count == 1

def test_import_ignores_rows_without_date(client, db):
    csv_content = (
    "Start Date,Project,Task,Description,Start Time,End Time,Duration (decimal)\n"
    "21/05/2026,Estudos,AWS Academy,Módulo 2,10:00:00,11:00:00,1.0\n"
    ",Leitura,Clean Code,Capítulo 1,09:04:22,09:59:43,0.92\n"
    "22/05/2026,Voluntariado,RioEcoPets, Redes Sociais,10:00:00,11:00:00,1.0\n")

    csv_bytes = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
    "/api/import",
    data={"file": (csv_bytes, "test.csv")},
    content_type="multipart/form-data",
    )
    registers = db.execute(
        "SELECT project FROM sessions"
    ).fetchall()
    project_names = [r["project"] for r in registers]

    assert len(registers) == 2
    assert "Estudos" in project_names
    assert "Voluntariado" in project_names
    assert "Leitura" not in project_names


def test_import_registers_new_projects(client, db):
    csv_content = (
    "Start Date,Project,Task,Description,Start Time,End Time,Duration (decimal)\n"
    "21/05/2026,Estudos,AWS Academy,Módulo 1,09:04:22,09:59:43,0.92\n")

    csv_bytes = io.BytesIO(csv_content.encode("utf-8"))

    response = client.post(
    "/api/import",
    data={"file": (csv_bytes, "test.csv")},
    content_type="multipart/form-data",
    )
    registered = db.execute(
        "SELECT project, included FROM project_filters"
    ).fetchone()

    assert registered["project"] == "Estudos"
    assert registered["included"] == 1

#TODO: add test that check if project is duplicated in project_filters and not added again