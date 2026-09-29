import sqlite3
import unittest

import domain


class CRMDomainTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        domain.init(self.db)

    def test_import_skips_existing_email(self):
        result = domain.handle("POST", "/api/import", {
            "csv": "name,email,company,value,stage\nMegan Again,megan@example.com,Other,10,New\nFresh Lead,fresh@example.com,Fresh,25,New"
        }, self.db)
        self.assertEqual(result, {"imported": 1, "skipped": 1})

    def test_import_rejects_duplicate_email_inside_file(self):
        with self.assertRaises(ValueError):
            domain.handle("POST", "/api/import", {
                "csv": "name,email\nA,a@example.com\nB,a@example.com"
            }, self.db)

    def test_export_contains_expected_header(self):
        exported = domain.handle("GET", "/api/export", {}, self.db)["csv"]
        self.assertTrue(exported.startswith("name,email,company,value,stage,notes"))


if __name__ == "__main__":
    unittest.main()
