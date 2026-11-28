import json
import subprocess
import unittest
from unittest.mock import patch
from modules import disk_health


class DiskHealthTests(unittest.TestCase):
    def snapshot(self, payload):
        with patch.object(disk_health.sys, 'platform', 'win32'), patch.object(
            disk_health.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(payload), '')
        ):
            return disk_health.disk_health_snapshot()

    def test_multiple_disks(self):
        result = self.snapshot([{'model': 'NVMe', 'temperature_c': 52}, {'model': 'USB', 'temperature_c': 28}])
        self.assertEqual(result['status'], 'ok')
        self.assertEqual([d['temperature_c'] for d in result['disks']], [52, 28])

    def test_single_disk(self):
        self.assertEqual(len(self.snapshot({'model': 'SSD'})['disks']), 1)

    def test_missing_counters(self):
        disk = self.snapshot([{'model': 'SSD', 'reliability_status': 'permission_denied'}])['disks'][0]
        self.assertIsNone(disk['power_on_hours'])
        self.assertEqual(disk['reliability_status'], 'permission_denied')

    def test_zero_and_missing_distinct(self):
        disk = self.snapshot([{'wear_percent': 0, 'read_errors_total': 0, 'temperature_max_c': 0}])['disks'][0]
        self.assertEqual(disk['wear_percent'], 0)
        self.assertEqual(disk['read_errors_total'], 0)
        self.assertIsNone(disk['temperature_max_c'])
        self.assertIsNone(disk['write_errors_total'])

    def test_empty(self):
        self.assertEqual(self.snapshot([]), {'status': 'ok', 'disks': []})

    def test_invalid_response(self):
        self.assertEqual(self.snapshot([42])['status'], 'invalid_response')

    def test_timeout(self):
        with patch.object(disk_health.sys, 'platform', 'win32'), patch.object(disk_health.subprocess, 'run', side_effect=subprocess.TimeoutExpired('powershell', 30)):
            self.assertEqual(disk_health.disk_health_snapshot()['status'], 'timeout')

    def test_command_failure(self):
        with patch.object(disk_health.sys, 'platform', 'win32'), patch.object(disk_health.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'powershell')):
            self.assertEqual(disk_health.disk_health_snapshot()['status'], 'unavailable')

    def test_unsupported_platform(self):
        with patch.object(disk_health.sys, 'platform', 'linux'):
            self.assertEqual(disk_health.disk_health_snapshot()['status'], 'unsupported_platform')
