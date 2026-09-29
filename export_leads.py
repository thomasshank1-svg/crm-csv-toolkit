#!/usr/bin/env python3
"""Export CRM leads as CSV."""
import argparse
import os
import sqlite3
from pathlib import Path

import domain

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Export Pipeline leads.")
    parser.add_argument("--db", default=os.environ.get("DATABASE_PATH", str(ROOT / "data" / "app.db")))
    args = parser.parse_args()
    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    with db:
        domain.init(db)
        print(domain.export_csv(db), end="")


if __name__ == "__main__":
    main()
