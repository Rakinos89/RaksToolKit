"""Tests for read-only network overview formatting."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import psutil
from modules.network_overview import normalize_network_info, get_network_overview


class NetworkOverviewTests(unittest.TestCase):
    def test_connected_adapter(self):
        raw = {'adapter': 'Ethernet', 'ipv4': '192.168.1.5',
               'gateway': '192.168.1.1', 'dns': ['1.1.1.1', '8.8.8.8']}
        stats = {'Ethernet': SimpleNamespace(isup=True, speed=1000)}
        addrs = {'Ethernet': [SimpleNamespace(family=psutil.AF_LINK, address='AA-BB-CC-DD-EE-FF')]}
        result = normalize_network_info(raw, stats, addrs)
        self.assertEqual(result['status'], 'Connected')
        self.assertEqual(result['speed'], '1000 Mbps')
        self.assertEqual(result['dns'], '1.1.1.1, 8.8.8.8')
        self.assertEqual(result['mac'], 'AA-BB-CC-DD-EE-FF')

    def test_disconnected_adapter(self):
        result = normalize_network_info({}, {}, {})
        self.assertEqual(result['status'], 'Disconnected')
        self.assertEqual(result['ipv4'], 'Not available')

    def test_single_dns_string(self):
        result = normalize_network_info({'adapter': 'Wi-Fi', 'dns': '9.9.9.9'}, {}, {})
        self.assertEqual(result['dns'], '9.9.9.9')

    @patch('modules.network_overview.subprocess.run')
    @patch('modules.network_overview.normalize_network_info')
    def test_powershell_json(self, normalize, run):
        run.return_value = SimpleNamespace(returncode=0, stdout='{"adapter":"Wi-Fi"}', stderr='')
        normalize.return_value = {'adapter': 'Wi-Fi'}
        self.assertEqual(get_network_overview(), {'adapter': 'Wi-Fi'})
        normalize.assert_called_once_with({'adapter': 'Wi-Fi'})

    @patch('modules.network_overview.subprocess.run')
    def test_invalid_json(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout='bad json', stderr='')
        with self.assertRaisesRegex(RuntimeError, 'parse'):
            get_network_overview()


if __name__ == '__main__':
    unittest.main()
