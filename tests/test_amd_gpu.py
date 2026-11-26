"""Hardware-independent tests for the AMD ADLX GPU metrics adapter."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from modules import amd_gpu


class AMDGPUHelpersTests(unittest.TestCase):
    def test_quantity_formats_values(self):
        self.assertEqual(amd_gpu._quantity(42.5, '%'), '42.5%')
        self.assertEqual(amd_gpu._quantity(1750, 'MHz'), '1750 MHz')
        self.assertEqual(amd_gpu._quantity(None, 'W'), 'Unavailable')
        self.assertEqual(amd_gpu._quantity(True, 'W'), 'Unavailable')
        self.assertEqual(amd_gpu._quantity('not a number', 'W'), 'Unavailable')

    def test_select_gpu_prefers_discrete(self):
        integrated = Mock()
        integrated.Type.return_value = 1
        discrete = Mock()
        discrete.Type.return_value = 2
        self.assertIs(amd_gpu._select_gpu([integrated, discrete], 2), discrete)
        self.assertIs(amd_gpu._select_gpu([integrated], 2), integrated)
        self.assertIsNone(amd_gpu._select_gpu([], 2))

    def test_vram_rejects_invalid_total(self):
        gpu = Mock()
        gpu.TotalVRAM.return_value = 0
        metrics = Mock()
        metrics.GPUVRAM.return_value = 100
        self.assertEqual(amd_gpu._vram(gpu, metrics, None), 'Unavailable')

    def test_power_falls_back_to_board_power(self):
        metrics = Mock()
        metrics.GPUPower.return_value = None
        metrics.GPUTotalBoardPower.return_value = 120
        self.assertEqual(amd_gpu._power(metrics, None), '120 W')

    def test_unsupported_metric_is_not_read(self):
        support = Mock()
        support.IsSupportedGPUUsage.return_value = False
        info = {'utilization': 'Unavailable'}
        metrics = Mock()
        gpu = Mock()
        amd_gpu._apply_metrics(info, gpu, metrics, support)
        self.assertEqual(info['utilization'], 'Unavailable')
        metrics.GPUUsage.assert_not_called()


class AMDGPUReadTests(unittest.TestCase):
    def make_adlx(self, *, init_ok=True, gpus=None, monitoring=None):
        helper = Mock()
        helper.Initialize.return_value = 0 if init_ok else 99
        system = Mock()
        system.GetGPUs.return_value = [] if gpus is None else gpus
        system.GetPerformanceMonitoringServices.return_value = monitoring
        helper.GetSystemServices.return_value = system
        adlx = SimpleNamespace(
            ADLXHelper=Mock(return_value=helper),
            ADLX_RESULT=SimpleNamespace(ADLX_OK=0, ADLX_ALREADY_INITIALIZED=1),
            ADLX_GPU_TYPE=SimpleNamespace(GPUTYPE_DISCRETE=2),
        )
        return adlx, helper, system

    def test_missing_dependency_returns_none(self):
        with patch.object(amd_gpu, '_import_adlx', side_effect=ImportError):
            self.assertIsNone(amd_gpu.read_amd_metrics())

    def test_initialization_failure_terminates(self):
        adlx, helper, _ = self.make_adlx(init_ok=False)
        with patch.object(amd_gpu, '_import_adlx', return_value=adlx):
            self.assertIsNone(amd_gpu.read_amd_metrics())
        helper.Terminate.assert_called_once()

    def test_no_gpu_returns_none_and_terminates(self):
        adlx, helper, _ = self.make_adlx()
        with patch.object(amd_gpu, '_import_adlx', return_value=adlx):
            self.assertIsNone(amd_gpu.read_amd_metrics())
        helper.Terminate.assert_called_once()

    def test_gpu_without_monitoring_returns_name_and_unavailable_metrics(self):
        gpu = Mock()
        gpu.Type.return_value = 2
        gpu.Name.return_value = 'AMD Radeon Test GPU'
        adlx, helper, _ = self.make_adlx(gpus=[gpu], monitoring=None)
        with patch.object(amd_gpu, '_import_adlx', return_value=adlx):
            result = amd_gpu.read_amd_metrics()
        self.assertEqual(result['vendor'], 'AMD')
        self.assertEqual(result['name'], 'AMD Radeon Test GPU')
        self.assertEqual(result['temperature'], 'Unavailable')
        helper.Terminate.assert_called_once()

    def test_metrics_are_normalized(self):
        gpu = Mock()
        gpu.Type.return_value = 2
        gpu.Name.return_value = 'AMD Radeon Test GPU'
        gpu.TotalVRAM.return_value = 8192
        metrics = Mock()
        metrics.GPUUsage.return_value = 37
        metrics.GPUTemperature.return_value = 58
        metrics.GPUVRAM.return_value = 2048
        metrics.GPUClockSpeed.return_value = 2100
        metrics.GPUVRAMClockSpeed.return_value = 1750
        metrics.GPUPower.return_value = 125
        monitoring = Mock()
        monitoring.GetSupportedGPUMetrics.return_value = None
        monitoring.GetCurrentGPUMetrics.return_value = metrics
        adlx, helper, _ = self.make_adlx(gpus=[gpu], monitoring=monitoring)
        with patch.object(amd_gpu, '_import_adlx', return_value=adlx):
            result = amd_gpu.read_amd_metrics()
        self.assertEqual(result['utilization'], '37%')
        self.assertEqual(result['vram'], '2048 / 8192 MiB')
        self.assertEqual(result['core_clock'], '2100 MHz')
        self.assertEqual(result['power'], '125 W')
        self.assertIn('58', result['temperature'])
        helper.Terminate.assert_called_once()

    def test_monitoring_exception_still_terminates(self):
        gpu = Mock()
        gpu.Type.return_value = 2
        gpu.Name.return_value = 'AMD Radeon Test GPU'
        monitoring = Mock()
        monitoring.GetSupportedGPUMetrics.side_effect = RuntimeError('driver error')
        monitoring.GetCurrentGPUMetrics.side_effect = RuntimeError('driver error')
        adlx, helper, _ = self.make_adlx(gpus=[gpu], monitoring=monitoring)
        with patch.object(amd_gpu, '_import_adlx', return_value=adlx):
            result = amd_gpu.read_amd_metrics()
        self.assertEqual(result['name'], 'AMD Radeon Test GPU')
        self.assertEqual(result['utilization'], 'Unavailable')
        helper.Terminate.assert_called_once()


if __name__ == '__main__':
    unittest.main()
