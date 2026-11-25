"""Regression tests for UI worker failure reporting and task-state recovery.

These tests do not open a window or execute Windows repair commands.
"""
import queue
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main


class UiRecoveryTests(unittest.TestCase):
    def make_app(self, *events):
        app = SimpleNamespace(
            events=queue.Queue(),
            running_task='SFC Scan',
            power_plan_refresh_busy=False,
            gaming_busy=False,
            current_page='Dashboard',
            append_log=Mock(),
            set_maintenance_status=Mock(),
            set_power_plan_status=Mock(),
            update_task_buttons=Mock(),
            update_power_plan_buttons=Mock(),
            after=Mock(),
            process_events=lambda: None,
        )
        for event in events:
            app.events.put(event)
        return app

    def test_successful_maintenance_releases_task(self):
        app = self.make_app(('done', 'SFC Scan', 0))
        main.WinToolKit.process_events(app)
        self.assertIsNone(app.running_task)
        self.assertIn('completed successfully', app.set_maintenance_status.call_args.args[0])
        app.update_task_buttons.assert_called_once()

    def test_failed_maintenance_releases_task(self):
        app = self.make_app(('done', 'SFC Scan', 1))
        main.WinToolKit.process_events(app)
        self.assertIsNone(app.running_task)
        self.assertIn('failed', app.set_maintenance_status.call_args.args[0])
        app.update_task_buttons.assert_called_once()

    def test_exception_releases_task_and_reports_error(self):
        app = self.make_app(('error', 'SFC Scan', 'Access denied'))
        main.WinToolKit.process_events(app)
        self.assertIsNone(app.running_task)
        self.assertIn('failed', app.set_maintenance_status.call_args.args[0])
        app.append_log.assert_called_once()
        app.update_task_buttons.assert_called_once()

    def test_power_plan_exception_releases_task_and_reports_error(self):
        app = self.make_app(('error', 'Change power plan', 'Access denied'))
        app.running_task = 'Change power plan'
        main.WinToolKit.process_events(app)
        self.assertIsNone(app.running_task)
        self.assertIn('Access denied', app.set_power_plan_status.call_args.args[0])
        app.update_power_plan_buttons.assert_called_once()

    def test_power_plan_refresh_failure_releases_refresh_lock(self):
        app = self.make_app(('gaming_error', 'Power plans: timeout'))
        app.power_plan_refresh_busy = True
        main.WinToolKit.process_events(app)
        self.assertFalse(app.power_plan_refresh_busy)
        self.assertIn('timeout', app.set_power_plan_status.call_args.args[0])
        app.update_power_plan_buttons.assert_called_once()

    def test_power_plan_worker_exception_is_queued(self):
        app = self.make_app()
        with patch.object(main, 'power_plans', side_effect=RuntimeError('powercfg unavailable')):
            main.WinToolKit.power_plan_worker(app)
        self.assertEqual(app.events.get_nowait(), ('gaming_error', 'Power plans: powercfg unavailable'))

    def test_power_plan_apply_exception_is_queued(self):
        app = self.make_app()
        with patch.object(main, 'activate_power_plan', side_effect=RuntimeError('Access denied')):
            main.WinToolKit.power_plan_worker_apply(app, 'test-guid')
        self.assertEqual(app.events.get_nowait(), ('error', 'Change power plan', 'Access denied'))


if __name__ == '__main__':
    unittest.main()
