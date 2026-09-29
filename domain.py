"""CRM lead tracker plus CSV import/export helpers."""
from datetime import datetime, timezone
import csv
import io
import re

STAGES = ["New", "Contacted", "Proposal", "Won", "Lost"]


def init(db):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS leads(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            company TEXT NOT NULL,
            value_cents INTEGER NOT NULL DEFAULT 0 CHECK(value_cents >= 0),
            stage TEXT NOT NULL DEFAULT 'New',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        """
    )
    if not db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]:
        now = datetime.now(timezone.utc).isoformat()
        db.executemany(
            "INSERT INTO leads(name,email,company,value_cents,stage,notes,created_at) VALUES(?,?,?,?,?,?,?)",
            [
                ("Megan Parker", "megan@example.com", "Northwind Studio", 350000, "Proposal", "Asked for ecommerce launch plan.", now),
                ("Jordan Lee", "jordan@example.com", "Urban Clinic", 180000, "Contacted", "Needs appointment booking flow.", now),
                ("Sara Chen", "sara@example.com", "Blue Finch", 520000, "New", "Imported from referral list.", now),
            ],
        )


def valid_email(value):
    email = str(value or "").strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Each lead needs a valid email.")
    return email


def money_to_cents(value):
    text = str(value or "0").strip().replace("$", "").replace(",", "")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", text):
        raise ValueError("Lead value must be a positive dollar amount.")
    dollars, _, cents = text.partition(".")
    return int(dollars) * 100 + int((cents + "00")[:2])


def row_to_lead(row):
    name = str(row.get("name", "")).strip()
    company = str(row.get("company", "")).strip() or "Independent"
    stage = str(row.get("stage", "New")).strip() or "New"
    notes = str(row.get("notes", "")).strip()
    if not 2 <= len(name) <= 80:
        raise ValueError("Each lead needs a name between 2 and 80 characters.")
    if stage not in STAGES:
        raise ValueError(f"Stage must be one of: {', '.join(STAGES)}.")
    return {
        "name": name,
        "email": valid_email(row.get("email")),
        "company": company[:120],
        "value_cents": money_to_cents(row.get("value", row.get("value_cents", 0))),
        "stage": stage,
        "notes": notes[:1000],
    }


def leads(db):
    return [dict(row) for row in db.execute("SELECT * FROM leads ORDER BY id DESC")]


def import_csv(db, text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Paste CSV data first.")
    if len(text.encode()) > 65536:
        raise ValueError("CSV must be smaller than 64 KB.")
    reader = csv.DictReader(io.StringIO(text))
    required = {"name", "email"}
    if not reader.fieldnames or not required.issubset({field.strip().lower() for field in reader.fieldnames}):
        raise ValueError("CSV needs at least name and email columns.")
    normalized = []
    seen = set()
    for index, raw in enumerate(reader, start=2):
        row = {str(key).strip().lower(): value for key, value in raw.items() if key is not None}
        lead = row_to_lead(row)
        if lead["email"] in seen:
            raise ValueError(f"Duplicate email inside CSV on row {index}.")
        seen.add(lead["email"])
        normalized.append(lead)
    if not normalized:
        raise ValueError("CSV did not contain any leads.")
    now = datetime.now(timezone.utc).isoformat()
    imported = skipped = 0
    for lead in normalized:
        try:
            db.execute(
                "INSERT INTO leads(name,email,company,value_cents,stage,notes,created_at) VALUES(?,?,?,?,?,?,?)",
                (lead["name"], lead["email"], lead["company"], lead["value_cents"], lead["stage"], lead["notes"], now),
            )
            imported += 1
        except Exception:
            skipped += 1
    return {"imported": imported, "skipped": skipped}


def export_csv(db):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "email", "company", "value", "stage", "notes"])
    for lead in reversed(leads(db)):
        writer.writerow([
            lead["name"],
            lead["email"],
            lead["company"],
            f"{lead['value_cents'] / 100:.2f}",
            lead["stage"],
            lead["notes"],
        ])
    return output.getvalue()


def handle(method, path, data, db):
    if method == "GET" and path == "/api/state":
        all_leads = leads(db)
        totals = {stage: 0 for stage in STAGES}
        for lead in all_leads:
            totals[lead["stage"]] += lead["value_cents"]
        return {"stages": STAGES, "leads": all_leads, "totals": totals}

    if method == "GET" and path == "/api/export":
        return {"csv": export_csv(db)}

    if method == "POST" and path == "/api/leads":
        lead = row_to_lead(data)
        row = db.execute(
            "INSERT INTO leads(name,email,company,value_cents,stage,notes,created_at) VALUES(?,?,?,?,?,?,?)",
            (lead["name"], lead["email"], lead["company"], lead["value_cents"], lead["stage"], lead["notes"], datetime.now(timezone.utc).isoformat()),
        )
        return {"id": row.lastrowid}

    if method == "POST" and path == "/api/import":
        return import_csv(db, data.get("csv", ""))

    if method == "POST" and path == "/api/stage":
        stage = str(data.get("stage", "")).strip()
        if stage not in STAGES:
            raise ValueError("Choose a listed stage.")
        row = db.execute("UPDATE leads SET stage=? WHERE id=?", (stage, data.get("id")))
        if not row.rowcount:
            raise LookupError()
        return {"ok": True}

    raise LookupError()
