"""RaksToolKit: Windows dashboard, maintenance and gaming tools."""
import os
import platform
import queue
import sys
from pathlib import Path
import subprocess
import threading
from datetime import datetime
from tkinter import TclError, messagebox

import customtkinter as ctk
import psutil

from modules.activity import LOG_PATH, read_recent, record
from modules.privacy import load_privacy, save_privacy, redact
from modules.hardware import cpu_name, windows_name
from modules.gaming import gpu_info, game_processes, power_plans, activate_power_plan, tcp_latency
from modules.cleanup import locations, scan, clean
from modules.network import flush_dns
from modules.software_updates import check_updates
from modules.system import REPAIR_COMMANDS, is_admin, relaunch_as_admin

VERSION = '1.1.0-dev'
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('green')


def resource_path(relative_path):
    """Find bundled resources in PyInstaller and local development."""
    base_path = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return base_path / relative_path


class RaksToolKit(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f'RaksToolKit v{VERSION}')
        icon_path = resource_path(Path('assets') / 'icons' / 'rakstoolkit.ico')
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except (OSError, TclError):
                pass  # Keep the application usable if Windows rejects the icon.
        self.geometry('1120x760')
        self.minsize(900, 600)
        self.admin = is_admin()
        self.privacy_mode = load_privacy()
        self.events = queue.Queue()
        self.running_task = None
        self.current_page = 'Dashboard'
        self.current_tab = 'System Repair'
        self.cleanup_selection = {}
        self.cleanup_scan = None
        self.maintenance_log = ['Ready to run maintenance tasks.']
        self.maintenance_state = ('Ready for maintenance tasks.', 'gray70')
        self.task_buttons = []
        self.gaming_busy = False
        self.gaming_plans = {}
        self.power_plan_status = ('Power plan: Ready.', 'gray70')
        self.power_plan_refresh_busy = False
        self.power_plan_buttons = []
        self.last_gaming_refresh = 0
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=205, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky='nsew')
        self.sidebar.grid_propagate(False)
        ctk.CTkLabel(self.sidebar, text='RaksToolKit', font=('Segoe UI', 25, 'bold')).pack(pady=(28, 4))
        ctk.CTkLabel(self.sidebar, text=f'v{VERSION}  •  ' + ('Administrator' if self.admin else 'Standard user'),
                     text_color='#70c080' if self.admin else '#e0b66a').pack(pady=(0, 28))
        for name in ('Dashboard', 'Maintenance', 'Gaming', 'Network', 'Settings', 'Activity'):
            ctk.CTkButton(self.sidebar, text=name, height=39,
                          command=lambda n=name: self.show_page(n)).pack(fill='x', padx=16, pady=5)

        self.content = ctk.CTkFrame(self)
        self.content.grid(row=0, column=1, padx=15, pady=15, sticky='nsew')
        self.show_page('Dashboard')
        self.after(1000, self.refresh_stats)
        self.after(2000, self.refresh_gaming_live)
        self.after(100, self.process_events)

    def show_page(self, page):
        self.current_page = page
        for widget in self.content.winfo_children():
            widget.destroy()
        self.task_buttons = []
        ctk.CTkLabel(self.content, text=page, font=('Segoe UI', 28, 'bold')).pack(pady=(18, 12))
        if page == 'Dashboard':
            self.build_dashboard()
            self.update_dashboard()
        elif page == 'Maintenance':
            self.build_maintenance()
        elif page == 'Gaming':
            self.build_gaming()
        elif page == 'Activity':
            self.build_activity()
        elif page == 'Settings':
            self.build_settings()
        else:
            ctk.CTkLabel(self.content, text=f'{page} tools coming in a future release.').pack(pady=25)

    def display_text(self, value):
        return redact(value, self.privacy_mode)

    def build_settings(self):
        ctk.CTkLabel(self.content, text='Privacy & Preferences', font=('Segoe UI',19,'bold')).pack(pady=(8,15))
        switch=ctk.CTkSwitch(self.content,text='Privacy Mode',command=self.change_privacy_mode)
        switch.pack(pady=12)
        self.privacy_switch=switch
        if self.privacy_mode: switch.select()
        ctk.CTkLabel(self.content,text='Hide the computer name, Windows username, and IPv4 addresses in displayed information.',wraplength=600).pack(pady=8)
        ctk.CTkLabel(self.content,text='This does not erase existing logs, hide other applications, or guarantee that every identifier is masked.',wraplength=600,text_color='gray70').pack(pady=8)
        ctk.CTkLabel(self.content,text=f'RaksToolKit version {VERSION}').pack(pady=12)
        ctk.CTkLabel(self.content,text=self.display_text(f'Activity log: {LOG_PATH}'),wraplength=650).pack(pady=12)

    def change_privacy_mode(self):
        enabled=bool(self.privacy_switch.get())
        try: save_privacy(enabled)
        except OSError as exc:
            messagebox.showerror('Could not save setting',str(exc))
            if self.privacy_mode: self.privacy_switch.select()
            else: self.privacy_switch.deselect()
            return
        self.privacy_mode=enabled
        self.show_page('Settings')

    def build_gaming(self):
        """Scrollable gaming dashboard with asynchronous GPU sampling."""
        scroll = ctk.CTkScrollableFrame(self.content, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=12, pady=(0, 10))
        ctk.CTkLabel(scroll, text='Gaming & Performance',
                     font=('Segoe UI', 19, 'bold')).pack(pady=(0, 5))
        self.gpu_label = ctk.CTkLabel(scroll, text='Detecting GPU...',
                                      font=('Segoe UI', 15, 'bold'), wraplength=690)
        self.gpu_label.pack(pady=(0, 5))
        self.gaming_status = ctk.CTkLabel(scroll, text='Live GPU updates every 2 seconds',
                                          text_color='gray70')
        self.gaming_status.pack(pady=(0, 12))

        metrics = ctk.CTkFrame(scroll, fg_color='transparent')
        metrics.pack(fill='x', padx=12)
        metrics.grid_columnconfigure((0, 1), weight=1, uniform='gpu')
        self.gpu_metric_values = {}
        self.gpu_metric_bars = {}
        specs = [('utilization', 'GPU Load'), ('temperature', 'Temperature'),
                 ('vram', 'VRAM Usage'), ('power', 'Power Draw')]
        for index, (key, heading) in enumerate(specs):
            card = ctk.CTkFrame(metrics, corner_radius=12)
            card.grid(row=index // 2, column=index % 2, padx=7, pady=7, sticky='nsew')
            ctk.CTkLabel(card, text=heading, text_color='gray75').pack(pady=(12, 2))
            value = ctk.CTkLabel(card, text='Checking...', font=('Segoe UI', 20, 'bold'))
            value.pack(pady=(0, 8))
            self.gpu_metric_values[key] = value
            if key in ('utilization', 'vram'):
                bar = ctk.CTkProgressBar(card)
                bar.pack(fill='x', padx=18, pady=(0, 14))
                bar.set(0)
                self.gpu_metric_bars[key] = bar
            else:
                ctk.CTkLabel(card, text='').pack(pady=(0, 8))

        clocks = ctk.CTkFrame(scroll)
        clocks.pack(fill='x', padx=19, pady=(8, 12))
        self.gpu_core_clock_label = ctk.CTkLabel(clocks, text='Core clock: Checking...')
        self.gpu_core_clock_label.pack(side='left', expand=True, padx=8, pady=10)
        self.gpu_memory_clock_label = ctk.CTkLabel(clocks, text='Memory clock: Checking...')
        self.gpu_memory_clock_label.pack(side='left', expand=True, padx=8, pady=10)

        ctk.CTkLabel(scroll, text='Gaming Utilities',
                     font=('Segoe UI', 17, 'bold')).pack(pady=(8, 6))
        self.games_label = ctk.CTkLabel(scroll, text='Known running games: Checking...', wraplength=690)
        self.games_label.pack(pady=5)
        self.latency_label = ctk.CTkLabel(scroll, text='TCP latency: Not tested')
        self.latency_label.pack(pady=5)
        actions = ctk.CTkFrame(scroll, fg_color='transparent')
        actions.pack(pady=5)
        ctk.CTkButton(actions, text='Test TCP Latency',
                      command=self.start_latency_test).pack(side='left', padx=5)
        ctk.CTkButton(actions, text='Refresh Now',
                      command=self.start_gaming_refresh).pack(side='left', padx=5)
        ctk.CTkLabel(scroll, text='Windows Power Plan',
                     font=('Segoe UI', 16, 'bold')).pack(pady=(14, 6))
        self.power_plan_menu = ctk.CTkOptionMenu(scroll, values=['Loading...'], width=300)
        self.power_plan_menu.pack(pady=4)
        apply_button = ctk.CTkButton(scroll, text='Apply Selected Power Plan',
                                     command=self.request_power_plan)
        apply_button.pack(pady=4)
        refresh_button = ctk.CTkButton(scroll, text='Refresh Power Plans',
                                       command=self.start_power_plan_refresh)
        refresh_button.pack(pady=4)
        self.power_plan_buttons = [apply_button, refresh_button]
        self.power_plan_status_label = ctk.CTkLabel(
            scroll, text=self.power_plan_status[0], text_color=self.power_plan_status[1])
        self.power_plan_status_label.pack(pady=(4, 8))
        self.update_power_plan_buttons()
        ctk.CTkLabel(scroll,
                     text='GPU metrics use NVIDIA nvidia-smi when available. Other vendors may show '
                          'unavailable metrics. TCP latency is not in-game ping.',
                     wraplength=690, text_color='gray70').pack(padx=25, pady=(14, 20))
        self.start_gaming_refresh()
        self.start_power_plan_refresh()

    @staticmethod
    def _gpu_fraction(value):
        try:
            return max(0.0, min(1.0, float(value.rstrip('%')) / 100))
        except (ValueError, AttributeError):
            return 0.0

    def update_gpu_cards(self, gpu):
        self.gpu_label.configure(text=self.display_text(gpu['name']))
        for key in ('utilization', 'temperature', 'vram', 'power'):
            self.gpu_metric_values[key].configure(text=self.display_text(gpu.get(key, 'Unavailable')))
        self.gpu_metric_bars['utilization'].set(self._gpu_fraction(gpu['utilization']))
        try:
            used, total = gpu['vram'].split(' / ')
            total = total.split()[0]
            fraction = float(used) / float(total)
        except (ValueError, ZeroDivisionError, AttributeError):
            fraction = 0.0
        self.gpu_metric_bars['vram'].set(max(0.0, min(1.0, fraction)))
        self.gpu_core_clock_label.configure(text=f"Core clock: {gpu['core_clock']}")
        self.gpu_memory_clock_label.configure(text=f"Memory clock: {gpu['memory_clock']}")

    def start_gaming_refresh(self):
        if self.gaming_busy:
            return
        self.gaming_busy = True
        if self.current_page == 'Gaming':
            self.gaming_status.configure(text='Refreshing GPU and running games...')
        threading.Thread(target=self.gaming_worker, daemon=True).start()

    def gaming_worker(self):
        try:
            self.events.put(('gaming_data', gpu_info(), game_processes()))
        except Exception as exc:
            self.events.put(('gaming_error', str(exc)))

    def start_latency_test(self):
        if self.current_page == 'Gaming':
            self.latency_label.configure(text='TCP latency: Testing...')
        threading.Thread(target=self.latency_worker, daemon=True).start()

    def latency_worker(self):
        try:
            self.events.put(('latency', f'{tcp_latency()} ms (TCP connection)'))
        except OSError as exc:
            self.events.put(('latency', f'Unavailable: {exc}'))

    def set_power_plan_status(self, message, color='gray70'):
        self.power_plan_status = (message, color)
        if self.current_page == 'Gaming':
            self.power_plan_status_label.configure(text=message, text_color=color)

    def update_power_plan_buttons(self):
        if self.current_page == 'Gaming':
            disabled = bool(self.running_task or self.power_plan_refresh_busy)
            for button in self.power_plan_buttons:
                button.configure(state='disabled' if disabled else 'normal')

    def start_power_plan_refresh(self):
        if self.power_plan_refresh_busy or self.running_task:
            return
        self.power_plan_refresh_busy = True
        self.set_power_plan_status('Power plan: Refreshing...', '#e0b45d')
        self.update_power_plan_buttons()
        threading.Thread(target=self.power_plan_worker, daemon=True).start()

    def power_plan_worker(self):
        try:
            self.events.put(('power_plans', power_plans()))
        except Exception as exc:
            self.events.put(('gaming_error', f'Power plans: {exc}'))

    def request_power_plan(self):
        if self.running_task:
            messagebox.showwarning('Task running', 'Wait for the maintenance task to finish.')
            return
        choice = self.power_plan_menu.get()
        guid = self.gaming_plans.get(choice)
        if not guid:
            messagebox.showinfo('No plan selected', 'Refresh and select an available power plan.')
            return
        if not messagebox.askyesno('Change Windows power plan',
                                   f'Activate {choice}? This changes your Windows power settings.'):
            return
        self.running_task = 'Change power plan'
        self.set_power_plan_status(f'Power plan: Applying {choice}...', '#e0b45d')
        self.update_power_plan_buttons()
        self.append_log(f'--- Activating power plan: {choice} ---')
        threading.Thread(target=self.power_plan_worker_apply, args=(guid,), daemon=True).start()

    def power_plan_worker_apply(self, guid):
        try:
            activate_power_plan(guid)
            self.events.put(('power_applied',))
        except Exception as exc:
            self.events.put(('error', 'Change power plan', str(exc)))

    def build_dashboard(self):
        ctk.CTkLabel(self.content, text='Live System Overview', font=('Segoe UI', 18, 'bold')).pack(pady=(0, 12))
        cards = ctk.CTkFrame(self.content, fg_color='transparent')
        cards.pack(fill='x', padx=25)
        self.stats = {}
        for title in ('CPU', 'RAM', 'C: Drive'):
            card = ctk.CTkFrame(cards)
            card.pack(side='left', expand=True, fill='both', padx=6)
            ctk.CTkLabel(card, text=title, font=('Segoe UI', 16, 'bold')).pack(pady=(18, 5))
            label = ctk.CTkLabel(card, text='Loading...', font=('Segoe UI', 22))
            label.pack(pady=5)
            bar = ctk.CTkProgressBar(card)
            bar.pack(fill='x', padx=16, pady=(8, 20))
            self.stats[title] = (label, bar)
        info = ctk.CTkFrame(self.content)
        info.pack(fill='x', padx=30, pady=25)
        details = [
            ('Operating system', windows_name()),
            ('Processor', cpu_name()),
            ('CPU cores', f'{psutil.cpu_count(logical=False) or "?"} physical / {psutil.cpu_count() or "?"} logical'),
            ('Total memory', f'{psutil.virtual_memory().total / (1024**3):.1f} GiB'),
            ('Computer', platform.node()),
        ]
        for title, value in details:
            row = ctk.CTkFrame(info, fg_color='transparent')
            row.pack(fill='x', padx=18, pady=5)
            ctk.CTkLabel(row, text=title + ':', width=160, anchor='w').pack(side='left')
            ctk.CTkLabel(row, text=self.display_text(value), anchor='w', wraplength=490).pack(side='left', fill='x', expand=True)

    def update_dashboard(self):
        if self.current_page != 'Dashboard':
            return
        values = {'CPU': psutil.cpu_percent(interval=None),
                  'RAM': psutil.virtual_memory().percent,
                  'C: Drive': psutil.disk_usage('C:\\').percent}
        for name, value in values.items():
            label, bar = self.stats[name]
            label.configure(text=f'{value:.1f}%')
            bar.set(value / 100)

    def refresh_gaming_live(self):
        """Poll only while the Gaming page is visible; never overlap workers."""
        if self.current_page == 'Gaming' and not self.gaming_busy:
            self.start_gaming_refresh()
        self.after(2000, self.refresh_gaming_live)

    def refresh_stats(self):
        if self.current_page == 'Dashboard':
            self.update_dashboard()
        self.after(1000, self.refresh_stats)

    def build_maintenance(self):
        if self.admin:
            ctk.CTkLabel(self.content, text='Running as Administrator', text_color='#70c080').pack(pady=(0, 10))
        else:
            ctk.CTkButton(self.content, text='Restart as Administrator',
                          command=self.request_elevation).pack(pady=(0, 10))
        tabs = ctk.CTkSegmentedButton(self.content,
                                     values=['System Repair', 'Smart Cleanup', 'Network', 'Software Updates'],
                                     command=self.show_maintenance_tab)
        tabs.pack(padx=15, pady=(0, 10))
        self.tab_content = ctk.CTkFrame(self.content, fg_color='transparent')
        self.tab_content.pack(fill='x', padx=15, pady=5)
        self.maintenance_status = ctk.CTkLabel(self.content, text=self.maintenance_state[0],
                                               text_color=self.maintenance_state[1])
        self.maintenance_status.pack(pady=(4, 0))
        self.maintenance_output = ctk.CTkTextbox(self.content, height=220)
        self.maintenance_output.pack(fill='both', expand=True, padx=20, pady=(8, 20))
        self.maintenance_output.insert('end', self.display_text('\n'.join(self.maintenance_log)) + '\n')
        self.maintenance_output.configure(state='disabled')
        self.maintenance_output.see('end')
        tabs.set(self.current_tab)
        self.show_maintenance_tab(self.current_tab)

    def show_maintenance_tab(self, tab):
        self.current_tab = tab
        for widget in self.tab_content.winfo_children():
            widget.destroy()
        self.task_buttons = []
        if tab == 'System Repair':
            ctk.CTkLabel(self.tab_content, text='Windows Component & File Repair',
                         font=('Segoe UI', 17, 'bold')).pack(pady=10)
            for task in ('DISM RestoreHealth', 'SFC Scan'):
                button = ctk.CTkButton(self.tab_content, text=task, width=200, height=36,
                                       command=lambda t=task: self.start_task(t))
                button.pack(pady=6)
                self.task_buttons.append(button)
        elif tab == 'Software Updates':
            ctk.CTkLabel(self.tab_content, text='Available Application Updates',
                         font=('Segoe UI', 17, 'bold')).pack(pady=10)
            ctk.CTkLabel(self.tab_content, text='Read-only check using winget. No software will be installed.').pack(pady=(0, 8))
            button = ctk.CTkButton(self.tab_content, text='Check for Updates', width=200, height=36,
                                   command=self.start_update_check)
            button.pack(pady=6)
            self.task_buttons.append(button)
        elif tab == 'Network':
            ctk.CTkLabel(self.tab_content, text='DNS Resolver Maintenance',
                         font=('Segoe UI', 17, 'bold')).pack(pady=10)
            button = ctk.CTkButton(self.tab_content, text='Flush DNS Cache', width=200,
                                   command=lambda: self.start_task('Flush DNS Cache'))
            button.pack(pady=10)
            self.task_buttons.append(button)
        else:
            ctk.CTkLabel(self.tab_content, text='Temporary files older than 24 hours',
                         font=('Segoe UI', 17, 'bold')).pack(pady=8)
            self.cleanup_selection = {}
            for name in locations():
                var = ctk.BooleanVar(value=name == 'User temporary files')
                self.cleanup_selection[name] = var
                ctk.CTkCheckBox(self.tab_content, text=name, variable=var).pack(anchor='w', padx=30, pady=3)
            controls = ctk.CTkFrame(self.tab_content, fg_color='transparent')
            controls.pack(pady=12)
            for label, mode in (('Scan', 'scan'), ('Dry Run', 'dry'), ('Clean Selected', 'clean')):
                button = ctk.CTkButton(controls, text=label, width=130,
                                       command=lambda m=mode: self.start_cleanup(m))
                button.pack(side='left', padx=5)
                self.task_buttons.append(button)
        self.update_task_buttons()

    def update_task_buttons(self):
        for button in self.task_buttons:
            button.configure(state='disabled' if self.running_task else 'normal')

    def set_maintenance_status(self, message, color='gray70'):
        """Remember status even when the Maintenance page is not visible."""
        self.maintenance_state = (message, color)
        if self.current_page == 'Maintenance':
            self.maintenance_status.configure(text=message, text_color=color)

    def append_log(self, line):
        self.maintenance_log.append(line)
        if len(self.maintenance_log) > 1500:
            self.maintenance_log = self.maintenance_log[-1500:]
        try:
            record(line)
        except OSError:
            pass  # Logging failure must not interrupt maintenance.
        if self.current_page == 'Maintenance':
            self.maintenance_output.configure(state='normal')
            self.maintenance_output.insert('end', self.display_text(line) + '\n')
            self.maintenance_output.see('end')
            self.maintenance_output.configure(state='disabled')

    def build_activity(self):
        ctk.CTkLabel(self.content, text='Saved activity history',
                     font=('Segoe UI', 17, 'bold')).pack(pady=8)
        ctk.CTkButton(self.content, text='Refresh History', command=self.refresh_activity).pack(pady=5)
        self.activity_status = ctk.CTkLabel(self.content, text='Loading history...', text_color='gray70')
        self.activity_status.pack(pady=(0, 2))
        self.activity_output = ctk.CTkTextbox(self.content)
        self.activity_output.pack(fill='both', expand=True, padx=20, pady=15)
        self.refresh_activity()

    def refresh_activity(self):
        try:
            content = read_recent()
            status = f'History refreshed at {datetime.now():%H:%M:%S} | {len(content.splitlines())} displayed lines'
        except OSError as exc:
            content = f'Unable to read log: {exc}'
            status = 'History refresh failed'
        self.activity_status.configure(text=status)
        self.activity_output.configure(state='normal')
        self.activity_output.delete('1.0', 'end')
        self.activity_output.insert('end', self.display_text(content))
        self.activity_output.see('end')
        self.activity_output.configure(state='disabled')

    def request_elevation(self):
        if self.running_task:
            messagebox.showwarning('Task running', 'Wait for the current task to finish.')
            return
        if not messagebox.askyesno('Administrator permissions', 'Restart RaksToolKit as administrator?'):
            return
        try:
            relaunch_as_admin()
        except OSError as exc:
            messagebox.showerror('Elevation failed', str(exc))
            return
        self.destroy()

    def start_task(self, task):
        if self.running_task:
            return
        if not self.admin:
            messagebox.showwarning('Administrator required', 'Restart as Administrator to run this task.')
            return
        description = {
            'Flush DNS Cache': 'Clear the Windows DNS resolver cache?',
            'DISM RestoreHealth': 'Repair the Windows component store with DISM? This may take a while.',
            'SFC Scan': 'Scan and repair protected Windows system files? This may take a while.',
        }[task]
        if not messagebox.askyesno('Confirm maintenance', description):
            return
        self.running_task = task
        self.set_maintenance_status(f'Running: {task}...', '#e0b66a')
        self.update_task_buttons()
        self.append_log(f'\n--- Starting: {task} ---')
        threading.Thread(target=self.task_worker, args=(task,), daemon=True).start()

    def task_worker(self, task):
        try:
            if task == 'Flush DNS Cache':
                self.events.put(('line', flush_dns()))
                code = 0
            else:
                with subprocess.Popen(REPAIR_COMMANDS[task], stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, errors='replace',
                                      bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW) as proc:
                    for line in proc.stdout:
                        if line.strip():
                            self.events.put(('line', line.rstrip()))
                    code = proc.wait()
            self.events.put(('done', task, code))
        except Exception as exc:
            self.events.put(('error', task, str(exc)))

    def start_update_check(self):
        if self.running_task:
            return
        task = 'Check for Updates'
        self.running_task = task
        self.set_maintenance_status('Checking for application updates...', '#e0b66a')
        self.update_task_buttons()
        self.append_log('\n--- Checking available updates (winget upgrade) ---')
        threading.Thread(target=self.update_check_worker, daemon=True).start()

    def update_check_worker(self):
        task = 'Check for Updates'
        try:
            code = check_updates(lambda line: self.events.put(('line', line)))
            self.events.put(('done', task, code))
        except Exception as exc:
            self.events.put(('error', task, str(exc)))

    def start_cleanup(self, mode):
        if self.running_task:
            return
        selected = {name for name, var in self.cleanup_selection.items() if var.get()}
        if not selected:
            messagebox.showinfo('Nothing selected', 'Choose at least one temporary folder.')
            return
        if mode == 'clean':
            if not self.cleanup_scan or self.cleanup_scan[0] != selected:
                messagebox.showwarning('Scan first', 'Scan these selections before cleaning.')
                return
            if not messagebox.askyesno('Confirm deletion',
                    'Delete eligible temporary files older than 24 hours? This cannot be undone.'):
                return
        self.running_task = f'Cleanup: {mode}'
        self.set_maintenance_status(f'Running cleanup: {mode}...', '#e0b66a')
        self.update_task_buttons()
        self.append_log(f'\n--- Cleanup {mode}: {", ".join(sorted(selected))} ---')
        threading.Thread(target=self.cleanup_worker, args=(mode, selected), daemon=True).start()

    def cleanup_worker(self, mode, selected):
        try:
            result = scan(selected) if mode == 'scan' else clean(selected, dry_run=mode == 'dry')
            self.events.put(('cleanup_done', mode, selected, result))
        except Exception as exc:
            self.events.put(('error', f'Cleanup: {mode}', str(exc)))

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == 'line':
                    self.append_log(event[1])
                elif event[0] == 'done':
                    _, task, code = event
                    self.append_log(f'--- {task}: {"completed" if code == 0 else "failed"} (exit code {code}) ---')
                    self.set_maintenance_status(
                        f'{task}: completed successfully.' if code == 0 else f'{task}: failed (exit code {code}).',
                        '#70c080' if code == 0 else '#f08080')
                    self.running_task = None
                    self.update_task_buttons()
                elif event[0] == 'cleanup_done':
                    _, mode, selected, result = event
                    self.cleanup_scan = (selected, result) if mode == 'scan' else None
                    for name, values in result.items():
                        count, size = values[:2]
                        skipped = f', skipped: {values[2]}' if len(values) > 2 else ''
                        self.append_log(f'{name}: {count} files, {size / 1048576:.2f} MiB{skipped}')
                    self.append_log('Dry run only; no files deleted.' if mode == 'dry' else
                                    'Scan finished.' if mode == 'scan' else 'Cleanup finished.')
                    self.set_maintenance_status(
                        'Cleanup scan completed.' if mode == 'scan' else
                        'Dry run completed; no files deleted.' if mode == 'dry' else
                        'Cleanup completed.', '#70c080')
                    self.running_task = None
                    self.update_task_buttons()
                elif event[0] == 'gaming_data':
                    self.gaming_busy = False
                    _, gpu, games = event
                    if self.current_page == 'Gaming':
                        self.gaming_status.configure(text='Gaming diagnostics updated.')
                        self.update_gpu_cards(gpu)
                        text = '; '.join(f'{name} (PID {pid}, {mib} MiB RAM)' for name, pid, mib in games)
                        self.games_label.configure(text=self.display_text('Known running games: ' + (text or 'None detected')))
                elif event[0] == 'gaming_error':
                    if event[1].startswith('Power plans:'):
                        self.power_plan_refresh_busy = False
                        self.set_power_plan_status(f'{event[1]}', '#f08080')
                        self.update_power_plan_buttons()
                    else:
                        self.gaming_busy = False
                    if self.current_page == 'Gaming':
                        self.gaming_status.configure(text=self.display_text(f'Diagnostics: {event[1]}'))
                elif event[0] == 'latency':
                    if self.current_page == 'Gaming':
                        self.latency_label.configure(text=self.display_text(f'TCP latency: {event[1]}'))
                elif event[0] == 'power_plans':
                    self.power_plan_refresh_busy = False
                    plans = event[1]
                    self.gaming_plans = {f'{name} [{guid[:8]}]': guid for guid, name, active in plans}
                    if self.current_page == 'Gaming':
                        labels = list(self.gaming_plans) or ['No power plans found']
                        self.power_plan_menu.configure(values=labels)
                        active = next((f'{name} [{guid[:8]}]' for guid, name, is_active in plans if is_active), labels[0])
                        self.power_plan_menu.set(active)
                    self.set_power_plan_status(
                        'Power plans refreshed.' if plans else 'No power plans found.',
                        '#70c080' if plans else '#f08080')
                    self.update_power_plan_buttons()
                elif event[0] == 'power_applied':
                    self.append_log('--- Power plan activated successfully ---')
                    self.set_power_plan_status('Power plan activated successfully.', '#70c080')
                    self.running_task = None
                    self.update_task_buttons()
                    self.start_power_plan_refresh()
                elif event[0] == 'error':
                    _, task, error = event
                    self.append_log(f'ERROR ({task}): {error}')
                    self.set_maintenance_status(f'{task}: failed. Check the log for details.', '#f08080')
                    if task == 'Change power plan':
                        self.set_power_plan_status(f'Power plan change failed: {error}', '#f08080')
                    self.running_task = None
                    self.update_task_buttons()
                    self.update_power_plan_buttons()
        except queue.Empty:
            pass
        self.after(100, self.process_events)


if __name__ == '__main__':
    RaksToolKit().mainloop()

# Backward-compatible alias for existing tests and integrations.
WinToolKit = RaksToolKit
