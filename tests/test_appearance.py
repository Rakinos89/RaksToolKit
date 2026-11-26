import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from modules import appearance, privacy


class AccentSettingsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        settings = Path(tmp.name) / 'settings.json'
        p = patch.object(privacy, 'SETTINGS', settings)
        p.start()
        self.addCleanup(p.stop)
        self.settings = settings

    def test_default_and_invalid_color(self):
        self.assertEqual(appearance.load_accent(), 'Green')
        self.settings.write_text('{"accent_color":"Neon"}')
        self.assertEqual(appearance.load_accent(), 'Green')

    def test_save_and_load_accent(self):
        appearance.save_accent('Purple')
        self.assertEqual(appearance.load_accent(), 'Purple')

    def test_privacy_is_preserved_when_accent_changes(self):
        privacy.save_privacy(True)
        appearance.save_accent('Blue')
        self.assertTrue(privacy.load_privacy())
        self.assertEqual(appearance.load_accent(), 'Blue')

    def test_accent_is_preserved_when_privacy_changes(self):
        appearance.save_accent('Red')
        privacy.save_privacy(True)
        self.assertEqual(appearance.load_accent(), 'Red')
        self.assertTrue(json.loads(self.settings.read_text())['privacy_mode'])

    def test_reject_invalid_color(self):
        with self.assertRaises(ValueError):
            appearance.save_accent('Not a color')

    def test_corrupt_json_defaults(self):
        self.settings.write_text('invalid')
        self.assertEqual(appearance.load_accent(), 'Green')
