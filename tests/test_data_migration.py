"""Regression tests for WinToolKit -> RaksToolKit AppData migration.

All test files are created in temporary directories; real AppData is untouched.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import activity, privacy


class ActivityMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.current = root / 'RaksToolKit' / 'activity.log'
        self.legacy = root / 'WinToolKit' / 'activity.log'
        patch_current = patch.object(activity, 'LOG_PATH', self.current)
        patch_legacy = patch.object(activity, 'LEGACY_LOG_PATH', self.legacy)
        patch_current.start()
        patch_legacy.start()
        self.addCleanup(patch_current.stop)
        self.addCleanup(patch_legacy.stop)

    def test_copies_existing_legacy_activity(self):
        self.legacy.parent.mkdir(parents=True)
        self.legacy.write_text('[old] First event\n[old] Second event\n', encoding='utf-8')
        self.assertIn('First event', activity.read_recent())
        self.assertEqual(self.current.read_bytes(), self.legacy.read_bytes())
        self.assertTrue(self.legacy.exists())

    def test_does_not_overwrite_existing_activity(self):
        self.legacy.parent.mkdir(parents=True)
        self.current.parent.mkdir(parents=True)
        self.legacy.write_text('Old entry\n', encoding='utf-8')
        self.current.write_text('New entry\n', encoding='utf-8')
        activity.migrate_activity()
        self.assertEqual(self.current.read_text(encoding='utf-8'), 'New entry\n')

    def test_repeated_migration_does_not_duplicate_entries(self):
        self.legacy.parent.mkdir(parents=True)
        self.legacy.write_text('Only once\n', encoding='utf-8')
        activity.migrate_activity()
        activity.migrate_activity()
        activity.read_recent()
        self.assertEqual(self.current.read_text(encoding='utf-8'), 'Only once\n')

    def test_missing_legacy_log_is_safe(self):
        activity.migrate_activity()
        self.assertFalse(self.current.exists())
        self.assertEqual(activity.read_recent(), 'No activity recorded yet.')


class SettingsMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.current = root / 'RaksToolKit' / 'settings.json'
        self.legacy = root / 'WinToolKit' / 'settings.json'
        patch_current = patch.object(privacy, 'SETTINGS', self.current)
        patch_legacy = patch.object(privacy, 'LEGACY_SETTINGS', self.legacy)
        patch_current.start()
        patch_legacy.start()
        self.addCleanup(patch_current.stop)
        self.addCleanup(patch_legacy.stop)

    def test_copies_existing_legacy_settings(self):
        self.legacy.parent.mkdir(parents=True)
        self.legacy.write_text('{"privacy_mode": true}', encoding='utf-8')
        self.assertTrue(privacy.load_privacy())
        self.assertEqual(self.current.read_bytes(), self.legacy.read_bytes())
        self.assertTrue(self.legacy.exists())

    def test_does_not_overwrite_existing_settings(self):
        self.legacy.parent.mkdir(parents=True)
        self.current.parent.mkdir(parents=True)
        self.legacy.write_text('{"privacy_mode": true}', encoding='utf-8')
        self.current.write_text('{"privacy_mode": false}', encoding='utf-8')
        privacy.migrate_settings()
        self.assertFalse(privacy.load_privacy())
        self.assertEqual(self.current.read_text(encoding='utf-8'), '{"privacy_mode": false}')

    def test_repeated_migration_preserves_newer_preference(self):
        self.legacy.parent.mkdir(parents=True)
        self.legacy.write_text('{"privacy_mode": true}', encoding='utf-8')
        privacy.migrate_settings()
        privacy.save_privacy(False)
        privacy.migrate_settings()
        self.assertFalse(privacy.load_privacy())
        self.assertIn('false', self.current.read_text(encoding='utf-8'))

    def test_missing_legacy_settings_is_safe(self):
        privacy.migrate_settings()
        self.assertFalse(self.current.exists())
        self.assertFalse(privacy.load_privacy())


if __name__ == '__main__':
    unittest.main()
