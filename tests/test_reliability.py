"""Additional isolated failure-path and safety regression tests."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from modules import activity, cleanup, gaming, gpu_monitor, hardware, privacy


class ReliabilityGpuTests(unittest.TestCase):
    def test_nvidia_timeout_preserves_fallback(self):
        import subprocess
        with patch.object(gpu_monitor, '_adapter_names', return_value=['NVIDIA Test GPU']), \
             patch.object(gpu_monitor.shutil, 'which', return_value='nvidia-smi'), \
             patch.object(gpu_monitor.subprocess, 'run', side_effect=subprocess.TimeoutExpired('nvidia-smi', 6)):
            result = gpu_monitor.gpu_info()
        self.assertEqual(result['name'], 'NVIDIA Test GPU')
        self.assertEqual(result['utilization'], 'Unavailable')

    def test_malformed_nvidia_output_preserves_fallback(self):
        with patch.object(gpu_monitor, '_adapter_names', return_value=['NVIDIA Test GPU']), \
             patch.object(gpu_monitor.shutil, 'which', return_value='nvidia-smi'), \
             patch.object(gpu_monitor.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='bad,csv\n')):
            result = gpu_monitor.gpu_info()
        self.assertEqual(result['temperature'], 'Unavailable')

    def test_missing_adapter_and_utility(self):
        with patch.object(gpu_monitor, '_adapter_names', return_value=[]), \
             patch.object(gpu_monitor.shutil, 'which', return_value=None):
            result = gpu_monitor.gpu_info()
        self.assertEqual(result['name'], 'Unavailable')
        self.assertEqual(result['vendor'], 'Unknown')


class ReliabilityPrivacyTests(unittest.TestCase):
    def test_corrupt_settings_fall_back_to_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = Path(temp) / 'settings.json'
            settings.write_text('{invalid json', encoding='utf-8')
            with patch.object(privacy, 'SETTINGS', settings):
                self.assertFalse(privacy.load_privacy())

    def test_non_boolean_setting_does_not_enable_privacy(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = Path(temp) / 'settings.json'
            settings.write_text(json.dumps({'privacy_mode': 'true'}), encoding='utf-8')
            with patch.object(privacy, 'SETTINGS', settings):
                self.assertFalse(privacy.load_privacy())

    def test_invalid_ipv4_is_not_redacted_as_valid_ip(self):
        self.assertIn('999.999.999.999', privacy.redact('Address 999.999.999.999', True))


class ReliabilityCleanupTests(unittest.TestCase):
    def _old(self, path):
        past = time.time() - cleanup.MIN_AGE_SECONDS - 120
        os.utime(path, (past, past))

    def test_unselected_location_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            selected = base / 'selected'
            unselected = base / 'unselected'
            selected.mkdir()
            unselected.mkdir()
            keep = unselected / 'old.tmp'
            keep.write_text('keep')
            self._old(keep)
            with patch.object(cleanup, 'locations', return_value={'Selected': selected, 'Unselected': unselected}):
                result = cleanup.clean({'Selected'}, dry_run=False)
            self.assertTrue(keep.exists())
            self.assertNotIn('Unselected', result)

    def test_symlinked_file_outside_test_directory_not_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            folder = base / 'scan'
            outside = base / 'outside'
            folder.mkdir()
            outside.mkdir()
            target = outside / 'valuable.txt'
            target.write_text('keep')
            self._old(target)
            link = folder / 'link.tmp'
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Creating file symlinks requires permission on this system')
            with patch.object(cleanup, 'locations', return_value={'Test': folder}):
                cleanup.clean({'Test'}, dry_run=False)
            self.assertTrue(target.exists())
            self.assertTrue(link.is_symlink())

    def test_symlinked_directory_not_traversed(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            folder = base / 'scan'
            outside = base / 'outside'
            folder.mkdir()
            outside.mkdir()
            target = outside / 'valuable.txt'
            target.write_text('keep')
            self._old(target)
            try:
                (folder / 'linked').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Creating directory symlinks requires permission on this system')
            with patch.object(cleanup, 'locations', return_value={'Test': folder}):
                cleanup.clean({'Test'}, dry_run=False)
            self.assertTrue(target.exists())


class ReliabilityGamingTests(unittest.TestCase):
    def test_power_plan_command_failure_raises(self):
        guid = '381b4222-f694-41f0-9685-ff5bb260df2e'
        with patch.object(gaming.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stderr='Access denied', stdout='')):
            with self.assertRaisesRegex(RuntimeError, 'Access denied'):
                gaming.activate_power_plan(guid)

    def test_power_plan_list_command_failure_raises(self):
        with patch.object(gaming.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stderr='Unavailable', stdout='')):
            with self.assertRaisesRegex(RuntimeError, 'Unavailable'):
                gaming.power_plans()

    def test_tcp_latency_connection_failure_propagates(self):
        with patch.object(gaming.socket, 'create_connection', side_effect=OSError('Network unavailable')):
            with self.assertRaisesRegex(OSError, 'Network unavailable'):
                gaming.tcp_latency()


class ReliabilityActivityTests(unittest.TestCase):
    def test_recent_history_limit(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(activity, 'LOG_PATH', Path(temp) / 'activity.log'):
            for number in range(5):
                activity.record(f'Entry {number}')
            text = activity.read_recent(limit=2)
            self.assertIn('Entry 4', text)
            self.assertIn('Entry 3', text)
            self.assertNotIn('Entry 2', text)


if __name__ == '__main__':
    unittest.main()
