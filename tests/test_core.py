"""Non-destructive tests for WinToolKit core modules."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from modules import activity, cleanup, gpu_monitor, hardware, privacy, gaming


class HardwareTests(unittest.TestCase):
    def test_windows_11_build(self):
        with patch.object(hardware.platform, 'system', return_value='Windows'), patch.object(hardware.platform, 'version', return_value='10.0.22631'):
            self.assertEqual(hardware.windows_name(), 'Windows 11')

    def test_windows_10_build(self):
        with patch.object(hardware.platform, 'system', return_value='Windows'), patch.object(hardware.platform, 'version', return_value='10.0.19045'):
            self.assertEqual(hardware.windows_name(), 'Windows 10')


class GpuTests(unittest.TestCase):
    def test_no_nvidia_utility(self):
        with patch.object(gpu_monitor, '_adapter_names', return_value=['AMD Radeon RX 7900 XT']), patch.object(gpu_monitor.shutil, 'which', return_value=None):
            result = gpu_monitor.gpu_info()
        self.assertEqual(result['vendor'], 'AMD')
        self.assertEqual(result['utilization'], 'Unavailable')

    def test_nvidia_metrics(self):
        output = 'NVIDIA GeForce RTX 2080 SUPER, 7, 54, 2039, 8192, 1650, 7750, 54.88\n'
        with patch.object(gpu_monitor, '_adapter_names', return_value=['NVIDIA GeForce RTX 2080 SUPER']), patch.object(gpu_monitor.shutil, 'which', return_value='nvidia-smi'), patch.object(gpu_monitor.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=output)):
            result = gpu_monitor.gpu_info()
        self.assertEqual(result['utilization'], '7%')
        self.assertEqual(result['vram'], '2039 / 8192 MiB')
        self.assertEqual(result['power'], '54.88 W')

    def test_nvidia_command_failure(self):
        with patch.object(gpu_monitor, '_adapter_names', return_value=['NVIDIA GPU']), patch.object(gpu_monitor.shutil, 'which', return_value='nvidia-smi'), patch.object(gpu_monitor.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout='')):
            result = gpu_monitor.gpu_info()
        self.assertEqual(result['utilization'], 'Unavailable')


class PrivacyTests(unittest.TestCase):
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(privacy, 'SETTINGS', Path(temp) / 'WinToolKit' / 'settings.json'):
            self.assertFalse(privacy.load_privacy())
            privacy.save_privacy(True)
            self.assertTrue(privacy.load_privacy())
            privacy.save_privacy(False)
            self.assertFalse(privacy.load_privacy())

    def test_ip_masking(self):
        self.assertIn('[IP hidden]', privacy.redact('Host 192.168.1.25', True))
        self.assertEqual(privacy.redact('Host 192.168.1.25', False), 'Host 192.168.1.25')


class CleanupTests(unittest.TestCase):
    def test_only_old_regular_files(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            old = folder / 'old.tmp'
            recent = folder / 'recent.tmp'
            old.write_text('old')
            recent.write_text('new')
            past = time.time() - cleanup.MIN_AGE_SECONDS - 120
            os.utime(old, (past, past))
            found = {path.name for path, _ in cleanup.candidates(folder)}
            self.assertEqual(found, {'old.tmp'})

    def test_dry_run_does_not_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            target = folder / 'old.tmp'
            target.write_text('safe')
            past = time.time() - cleanup.MIN_AGE_SECONDS - 120
            os.utime(target, (past, past))
            with patch.object(cleanup, 'locations', return_value={'Test temporary files': folder}):
                result = cleanup.clean({'Test temporary files'}, dry_run=True)
            self.assertTrue(target.exists())
            self.assertEqual(result['Test temporary files'][0], 1)

    def test_actual_clean_only_in_isolated_test_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            old = folder / 'old.tmp'
            recent = folder / 'recent.tmp'
            old.write_text('old')
            recent.write_text('new')
            past = time.time() - cleanup.MIN_AGE_SECONDS - 120
            os.utime(old, (past, past))
            with patch.object(cleanup, 'locations', return_value={'Test temporary files': folder}):
                result = cleanup.clean({'Test temporary files'}, dry_run=False)
            self.assertFalse(old.exists())
            self.assertTrue(recent.exists())
            self.assertEqual(result['Test temporary files'][0], 1)


class GamingTests(unittest.TestCase):
    def test_rejects_invalid_power_plan_without_running_command(self):
        with patch.object(gaming.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                gaming.activate_power_plan('invalid-guid')
            run.assert_not_called()

    def test_valid_power_plan_uses_mocked_command(self):
        guid = '381b4222-f694-41f0-9685-ff5bb260df2e'
        with patch.object(gaming.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stderr='', stdout='')) as run:
            gaming.activate_power_plan(guid)
            self.assertEqual(run.call_args.args[0], ['powercfg', '/setactive', guid])


class ActivityTests(unittest.TestCase):
    def test_record_and_read(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(activity, 'LOG_PATH', Path(temp) / 'activity.log'):
            self.assertEqual(activity.read_recent(), 'No activity recorded yet.')
            activity.record('Automated test entry')
            self.assertIn('Automated test entry', activity.read_recent())


if __name__ == '__main__':
    unittest.main()
