"""Operational and typed-value regressions on self-authored fictional files."""

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from localrag import KnowledgeStore, Metadata
from local_ops import copy_database, inspect_database


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "index.sqlite"
        self.store = KnowledgeStore(self.path)
        self.token = self.store.issue_identity("reader", "alpha", "viewer")
        source = self.root / "support.md"
        source.write_text("Support hours are 09:00 to 17:00.")
        self.meta = Metadata("alpha", "support", "Support", "support", 1, "2020-01-01")
        self.store.ingest(source, self.meta, rights_attested=True)

    def test_backup_restore_preserves_wal_and_revocation(self):
        db = sqlite3.connect(self.path)
        self.addCleanup(db.close)
        db.execute("PRAGMA journal_mode=WAL")
        self.store.revoke_identity("reader")
        backup = self.root / "backup.sqlite"
        receipt = copy_database(self.path, backup)
        self.assertTrue(receipt["contains_private_data"])
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        restored = self.root / "restored.sqlite"
        copy_database(backup, restored)
        with self.assertRaises(PermissionError):
            KnowledgeStore(restored).query(self.token, "Support hours?")
        self.assertEqual(inspect_database(restored)["counts"]["chunks"], 1)

    def test_backup_never_overwrites_existing_file_or_symlink(self):
        target = self.root / "existing"
        target.write_bytes(b"preserve")
        with self.assertRaises(FileExistsError):
            copy_database(self.path, target)
        link = self.root / "link"
        link.symlink_to(target)
        with self.assertRaises(FileExistsError):
            copy_database(self.path, link)
        self.assertEqual(target.read_bytes(), b"preserve")

    def test_wrong_database_is_not_restored(self):
        wrong = self.root / "wrong.sqlite"
        sqlite3.connect(wrong).close()
        target = self.root / "new.sqlite"
        with self.assertRaises(ValueError):
            copy_database(wrong, target)
        self.assertFalse(target.exists())

    def test_doctor_missing_db_does_not_create_it(self):
        missing = self.root / "missing.sqlite"
        result = subprocess.run(
            [sys.executable, "local_service.py", "--db", str(missing), "doctor"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(missing.exists())
        self.assertNotIn(self.token, result.stderr)

    def test_cli_backup_and_restore_receipts(self):
        backup = self.root / "cli-backup.sqlite"
        restored = self.root / "cli-restored.sqlite"
        for args in [
            ("--db", str(self.path), "backup", "--out", str(backup)),
            ("--db", str(restored), "restore", "--from-backup", str(backup)),
        ]:
            p = subprocess.run(
                [sys.executable, "local_service.py", *args],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["status"], "COPIED")
            self.assertNotIn(self.token, p.stdout)
        self.assertEqual(
            KnowledgeStore(restored).query(self.token, "What are the support hours?")[
                "status"
            ],
            "EXTRACTIVE",
        )


class ValueEvidenceTests(unittest.TestCase):
    def test_attributes_require_actual_values(self):
        cases = [
            (
                "phone",
                "The support phone number changes after every review.",
                "NO_ANSWER",
            ),
            (
                "phone",
                "The support phone number was updated on 2026-10-30 at 10:30.",
                "NO_ANSWER",
            ),
            ("phone", "The support phone number is +1 212 555 0100.", "EXTRACTIVE"),
            (
                "email",
                "The support email address will be announced later.",
                "NO_ANSWER",
            ),
            (
                "email",
                "The support email address is help@example.invalid.",
                "EXTRACTIVE",
            ),
        ]
        for field, text, expected in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                store = KnowledgeStore(root / "db")
                token = store.issue_identity("reader", "alpha", "viewer")
                path = root / "policy.md"
                path.write_text(text)
                store.ingest(
                    path,
                    Metadata("alpha", "policy", "Support", "support", 1, "2020-01-01"),
                    rights_attested=True,
                )
                q = (
                    "What are the support hours?"
                    if field == "hours"
                    else "What is the support "
                    + field
                    + (" number?" if field == "phone" else " address?")
                )
                result = store.query(token, q)
                self.assertEqual(result["status"], expected)
                if expected == "NO_ANSWER":
                    self.assertFalse(result["citations"])
                    self.assertIsNone(result["answer"])
