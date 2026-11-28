import unittest
from types import SimpleNamespace
from unittest.mock import patch
from modules import hardware_monitor as monitor


class HardwareMonitorTests(unittest.TestCase):
    @patch.object(monitor, 'windows_name', return_value='Windows 11')
    @patch.object(monitor, 'cpu_name', return_value='Test CPU')
    @patch.object(monitor.psutil, 'cpu_count', side_effect=[4, 8])
    @patch.object(monitor.psutil, 'cpu_percent', return_value=25.0)
    @patch.object(monitor.psutil, 'cpu_freq', return_value=SimpleNamespace(current=3200))
    @patch.object(monitor.psutil, 'virtual_memory', return_value=SimpleNamespace(total=16000, available=8000, percent=50))
    def test_system_snapshot(self, *mocks):
        data = monitor.system_snapshot()
        self.assertEqual(data['cpu_name'], 'Test CPU')
        self.assertEqual(data['physical_cores'], 4)
        self.assertEqual(data['logical_cores'], 8)
        self.assertEqual(data['cpu_percent'], 25)
        self.assertEqual(data['cpu_frequency_mhz'], 3200)
        self.assertEqual(data['memory_available_bytes'], 8000)

    @patch.object(monitor.psutil, 'cpu_freq', return_value=None)
    @patch.object(monitor.psutil, 'virtual_memory', side_effect=OSError)
    def test_missing_readings(self, *mocks):
        data = monitor.system_snapshot()
        self.assertIsNone(data['cpu_frequency_mhz'])
        self.assertIsNone(data['memory_total_bytes'])

    @patch.object(monitor.psutil, 'disk_partitions', return_value=[SimpleNamespace(device='C:', mountpoint='C:/', fstype='NTFS')])
    @patch.object(monitor.psutil, 'disk_usage', return_value=SimpleNamespace(total=100, free=40, used=60, percent=60))
    def test_volume_snapshot(self, *mocks):
        self.assertEqual(monitor.volume_snapshot()[0]['free_bytes'], 40)

    @patch.object(monitor.psutil, 'disk_partitions', return_value=[SimpleNamespace(device='D:', mountpoint='D:/', fstype='NTFS')])
    @patch.object(monitor.psutil, 'disk_usage', side_effect=PermissionError)
    def test_inaccessible_volume(self, *mocks):
        self.assertIsNone(monitor.volume_snapshot()[0]['percent'])

    @patch.object(monitor.psutil, 'disk_partitions', side_effect=OSError)
    def test_enumeration_failure(self, *mocks):
        self.assertEqual(monitor.volume_snapshot(), [])

    def test_invalid_numbers(self):
        for value in (None, True, -1, float('nan'), float('inf'), '10'):
            self.assertIsNone(monitor._number(value))
        self.assertEqual(monitor._number(0), 0)
