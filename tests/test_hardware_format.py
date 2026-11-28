import unittest
from modules.hardware_format import (format_bytes, format_frequency, format_percent,
                                     format_count, format_text, format_system, format_volume)


class HardwareFormatTests(unittest.TestCase):
    def test_bytes(self):
        for value, expected in [(0, '0 B'), (1023, '1023 B'), (1024, '1.00 KiB'),
                                (1024**3, '1.00 GiB'), (1024**4, '1.00 TiB')]:
            self.assertEqual(format_bytes(value), expected)

    def test_frequency(self):
        self.assertEqual(format_frequency(3600), '3.60 GHz')
        self.assertEqual(format_frequency(800), '800 MHz')
        self.assertEqual(format_frequency(0), '0 MHz')

    def test_percent(self):
        for value, expected in [(0, '0.0%'), (39.6, '39.6%'), (100, '100.0%'), (101, 'N/A')]:
            self.assertEqual(format_percent(value), expected)

    def test_invalid_numbers(self):
        for formatter in (format_bytes, format_frequency, format_percent, format_count):
            for value in (None, True, -1, float('nan'), float('inf'), '42'):
                with self.subTest(formatter=formatter, value=value):
                    self.assertEqual(formatter(value), 'N/A')

    def test_count(self):
        self.assertEqual(format_count(8), '8')
        self.assertEqual(format_count(8.5), 'N/A')

    def test_text(self):
        self.assertEqual(format_text(' NTFS '), 'NTFS')
        self.assertEqual(format_text(' '), 'N/A')
        self.assertEqual(format_text(None), 'N/A')

    def test_system(self):
        raw = {'cpu_frequency_mhz': 3600, 'memory_total_bytes': 1024**3}
        result = format_system(raw)
        self.assertEqual(result['cpu_frequency_mhz'], '3.60 GHz')
        self.assertEqual(result['memory_total_bytes'], '1.00 GiB')
        self.assertEqual(result['cpu_name'], 'N/A')
        self.assertEqual(raw, {'cpu_frequency_mhz': 3600, 'memory_total_bytes': 1024**3})

    def test_volume(self):
        result = format_volume({'device': 'C:', 'percent': 0, 'free_bytes': 1024})
        self.assertEqual(result['device'], 'C:')
        self.assertEqual(result['percent'], '0.0%')
        self.assertEqual(result['free_bytes'], '1.00 KiB')
        self.assertEqual(result['total_bytes'], 'N/A')
