#!/usr/bin/env python3
"""Import a CSV file into the local CRM database."""
import argparse
import os
import sqlite3
from pathlib import Path

import domain

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Import leads into Pipeline.")
    parser.add_argument("csv_file", help="CSV with name,email,company,value,stage,notes columns")
    parser.add_argument("--db", default=os.environ.get("DATABASE_PATH", str(ROOT / "data" / "app.db")))
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    with db:
        domain.init(db)
        result = domain.import_csv(db, Path(args.csv_file).read_text())
    print(f"{result['imported']} imported, {result['skipped']} skipped")


if __name__ == "__main__":
    main()
