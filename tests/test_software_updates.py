"""Tests for winget command selection and streaming."""
import unittest
from unittest.mock import patch

from modules import software_updates


class FakeProcess:
    stdout = iter(['Update found\n', '\n', 'Done\n'])

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def wait(self):
        return 0


class SoftwareUpdatesTests(unittest.TestCase):
    @patch('modules.software_updates.subprocess.Popen')
    @patch('modules.software_updates.shutil.which', return_value=r'C:\winget.exe')
    def test_check_is_read_only(self, _, popen):
        popen.return_value = FakeProcess()
        lines = []
        self.assertEqual(software_updates.check_updates(lines.append), 0)
        self.assertEqual(popen.call_args.args[0], [r'C:\winget.exe', 'upgrade', '--disable-interactivity'])
        self.assertEqual(lines, ['Update found', 'Done'])

    @patch('modules.software_updates.subprocess.Popen')
    @patch('modules.software_updates.shutil.which', return_value=r'C:\winget.exe')
    def test_upgrade_all_command(self, _, popen):
        popen.return_value = FakeProcess()
        self.assertEqual(software_updates.upgrade_all(lambda _: None), 0)
        self.assertEqual(popen.call_args.args[0], [r'C:\winget.exe', 'upgrade', '--all'])

    @patch('modules.software_updates.shutil.which', return_value=None)
    def test_missing_winget(self, _):
        with self.assertRaises(FileNotFoundError):
            software_updates.upgrade_all(lambda _: None)


if __name__ == '__main__':
    unittest.main()
