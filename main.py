import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os
import signal
import time
import json
from datetime import datetime

class VMController:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced QEMU Controller")
        self.qemu_process = None
        self.pid_file = "qemu_vm.pid"
        self.profiles_dir = "qemu_profiles"
        self.current_profile = None
        self.advanced_settings = None
        
        self.default_config = {
            "vnc_display": ":1",
            "vnc_port": 5901
        }
        
        self.create_widgets()
        self.create_profiles_dir()
        self.refresh_profiles()
        
    def create_profiles_dir(self):
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)
            
    def get_current_settings(self):
        settings = {
            "ram": self.ram.get(),
            "cpu": self.cpu.get(),
            "boot_order": self.boot_order.get(),
            "hdd_enabled": self.hdd_enabled.get(),
            "disk_image": self.disk_image.get(),
            "cdrom_enabled": self.cdrom_enabled.get(),
            "iso_path": self.iso_path.get(),
            "network": "user",
            "usb_support": False,
            "secure_boot": False,
            "uefi_firmware": ""
        }
        
        if self.advanced_settings:
            settings.update({
                "network": self.advanced_settings.network.get(),
                "usb_support": self.advanced_settings.usb_support.get(),
                "secure_boot": self.advanced_settings.secure_boot.get(),
                "uefi_firmware": self.advanced_settings.uefi_firmware.get()
            })
            
        return settings
    
    def apply_settings(self, settings):
        self.ram.delete(0, tk.END)
        self.ram.insert(0, settings.get("ram", "2048"))
        
        self.cpu.delete(0, tk.END)
        self.cpu.insert(0, settings.get("cpu", "2"))
        
        self.boot_order.set(settings.get("boot_order", "cdrom"))
        
        self.hdd_enabled.set(settings.get("hdd_enabled", True))
        self.disk_image.delete(0, tk.END)
        self.disk_image.insert(0, settings.get("disk_image", ""))
        
        self.cdrom_enabled.set(settings.get("cdrom_enabled", True))
        self.iso_path.delete(0, tk.END)
        self.iso_path.insert(0, settings.get("iso_path", ""))
        
        if self.advanced_settings:
            self.advanced_settings.network.set(settings.get("network", "user"))
            self.advanced_settings.usb_support.set(settings.get("usb_support", False))
            self.advanced_settings.secure_boot.set(settings.get("secure_boot", False))
            self.advanced_settings.uefi_firmware.delete(0, tk.END)
            self.advanced_settings.uefi_firmware.insert(0, settings.get("uefi_firmware", ""))

    def create_widgets(self):
        # Profile management
        profile_frame = ttk.Frame(self.root)
        profile_frame.pack(pady=5, padx=10, fill=tk.X)
        
        self.profile_var = tk.StringVar()
        self.profile_selector = ttk.Combobox(profile_frame, textvariable=self.profile_var, width=25)
        self.profile_selector.grid(row=0, column=0, padx=5)
        self.profile_selector.bind("<<ComboboxSelected>>", self.load_selected_profile)
        
        ttk.Button(profile_frame, text="Save", command=self.save_profile).grid(row=0, column=1, padx=2)
        ttk.Button(profile_frame, text="Load", command=self.load_profile_dialog).grid(row=0, column=2, padx=2)
        ttk.Button(profile_frame, text="Delete", command=self.delete_profile).grid(row=0, column=3, padx=2)
        ttk.Button(profile_frame, text="Refresh", command=self.refresh_profiles).grid(row=0, column=4, padx=2)

        # Hardware configuration
        hardware_frame = ttk.LabelFrame(self.root, text="Hardware Configuration")
        hardware_frame.pack(pady=5, padx=10, fill=tk.X)
        
        ttk.Label(hardware_frame, text="RAM (MB):").grid(row=0, column=0, padx=5)
        self.ram = ttk.Entry(hardware_frame, width=10)
        self.ram.insert(0, "2048")
        self.ram.grid(row=0, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(hardware_frame, text="CPU Cores:").grid(row=0, column=2, padx=5)
        self.cpu = ttk.Entry(hardware_frame, width=5)
        self.cpu.insert(0, "2")
        self.cpu.grid(row=0, column=3, padx=5, sticky=tk.W)
        
        ttk.Label(hardware_frame, text="Boot Order:").grid(row=1, column=0, padx=5)
        self.boot_order = ttk.Combobox(hardware_frame, values=["cdrom", "disk", "network"], width=8)
        self.boot_order.current(0)
        self.boot_order.grid(row=1, column=1, padx=5, sticky=tk.W)

        # Devices management
        devices_frame = ttk.LabelFrame(self.root, text="Devices Management")
        devices_frame.pack(pady=5, padx=10, fill=tk.X)
        
        self.hdd_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            devices_frame,
            text="Enable HDD",
            variable=self.hdd_enabled
        ).grid(row=0, column=0, padx=5, sticky=tk.W)
        
        ttk.Label(devices_frame, text="Disk Image:").grid(row=0, column=1, padx=5)
        self.disk_image = ttk.Entry(devices_frame, width=30)
        self.disk_image.grid(row=0, column=2, padx=5)
        ttk.Button(
            devices_frame,
            text="Browse",
            command=lambda: self.browse_file("Disk", self.disk_image)
        ).grid(row=0, column=3, padx=5)
        
        self.cdrom_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            devices_frame,
            text="Enable CD-ROM",
            variable=self.cdrom_enabled
        ).grid(row=1, column=0, padx=5, sticky=tk.W)
        
        ttk.Label(devices_frame, text="ISO File:").grid(row=1, column=1, padx=5)
        self.iso_path = ttk.Entry(devices_frame, width=30)
        self.iso_path.grid(row=1, column=2, padx=5)
        ttk.Button(
            devices_frame,
            text="Browse",
            command=lambda: self.browse_file("ISO", self.iso_path)
        ).grid(row=1, column=3, padx=5)

        # Control buttons
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10)
        
        self.btn_start = ttk.Button(
            control_frame,
            text="Start VM",
            command=self.start_vm
        )
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(
            control_frame,
            text="Stop VM",
            command=self.stop_vm,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Connect VNC",
            command=self.connect_vnc
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Advanced Settings",
            command=self.show_advanced
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame,
            text="Exit",
            command=self.root.quit
        ).pack(side=tk.LEFT, padx=5)

    def browse_file(self, file_type, entry_field):
        file_types = (
            ("ISO files", "*.iso"),
            ("All files", "*.*")
        ) if file_type == "ISO" else (
            ("QCOW2 files", "*.qcow2"),
            ("All files", "*.*")
        )
        
        filename = filedialog.askopenfilename(filetypes=file_types)
        if filename:
            entry_field.delete(0, tk.END)
            entry_field.insert(0, filename)

    def validate_settings(self):
        errors = []
        if self.hdd_enabled.get() and not self.disk_image.get():
            errors.append("HDD enabled but no disk image selected")
        if self.cdrom_enabled.get() and not self.iso_path.get():
            errors.append("CD-ROM enabled but no ISO selected")
        if not self.ram.get().isdigit():
            errors.append("Invalid RAM value")
        if not self.cpu.get().isdigit():
            errors.append("Invalid CPU cores value")
        return errors

    def start_vm(self):
        if self.qemu_process and self.qemu_process.poll() is None:
            messagebox.showwarning("Warning", "VM is already running!")
            return
            
        validation_errors = self.validate_settings()
        if validation_errors:
            messagebox.showerror("Configuration Error", "\n".join(validation_errors))
            return
        
        boot = self.boot_order.get()
        if boot == "cdrom":
            boot = "d"
        elif boot == "disk":
            boot = "c"
        elif boot == "network":
            boot = "n"

        try:
            qemu_command = [
                "qemu-system-x86_64",
                "-enable-kvm",
                "-m", self.ram.get(),
                "-smp", self.cpu.get(),
                "-vnc", self.default_config["vnc_display"],
                "-daemonize",
                "-boot", f"order={boot}"
            ]

            qemu_command += ["-pidfile", self.pid_file]
            
            if self.hdd_enabled.get():
                qemu_command += ["-hda", self.disk_image.get()]
            if self.cdrom_enabled.get():
                qemu_command += ["-cdrom", self.iso_path.get()]
                
            if self.advanced_settings:
                qemu_command += self.get_advanced_params()
            
            self.qemu_process = subprocess.Popen(
                qemu_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            messagebox.showinfo("Info", "VM started successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start VM: {str(e)}")

    def stop_vm(self):
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, "r") as pid_file:
                    pid = int(pid_file.read().strip())
            
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
            
                try:
                    os.kill(pid, 0)
                    os.kill(pid, signal.SIGKILL)
                    messagebox.showinfo("Info", "VM forcefully stopped")
                except OSError:
                    messagebox.showinfo("Info", "VM stopped successfully")
            
                os.remove(self.pid_file)
            else:
                messagebox.showwarning("Warning", "No running VM found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop VM: {str(e)}")
        finally:
            self.qemu_process = None
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

    def get_advanced_params(self):
        params = []
        if self.advanced_settings:
            if self.advanced_settings.network.get() == "tap":
                params += ["-net", "nic", "-net", "tap"]
            elif self.advanced_settings.network.get() == "user":
                params += ["-net", "user", "-net", "nic"]
                
            if self.advanced_settings.usb_support.get():
                params += ["-usb"]
                
            if self.advanced_settings.secure_boot.get():
                params += ["-machine", "q35,smm=on", "-global", "driver=cfi.pflash01,property=secure,value=on"]
                
            if self.advanced_settings.uefi_firmware.get():
                params += [
                    "-drive",
                    f"if=pflash,format=raw,readonly=on,file={self.advanced_settings.uefi_firmware.get()}"
                ]
        return params

    def connect_vnc(self):
        try:
            subprocess.Popen(["vncviewer", f"localhost:{self.default_config['vnc_port']}"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect VNC: {str(e)}")

    def show_advanced(self):
        if not self.advanced_settings:
            self.advanced_settings = AdvancedSettings(self.root, self)
        self.advanced_settings.deiconify()

    def refresh_profiles(self):
        profiles = [f for f in os.listdir(self.profiles_dir) if f.endswith('.json')]
        self.profile_selector['values'] = [os.path.splitext(p)[0] for p in profiles]

    def save_profile(self):
        settings = self.get_current_settings()
        default_name = f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_path = filedialog.asksaveasfilename(
            initialdir=self.profiles_dir,
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(settings, f, indent=4)
            self.refresh_profiles()

    def load_profile_dialog(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.profiles_dir,
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            self.load_profile(file_path)

    def load_profile(self, file_path):
        try:
            with open(file_path, 'r') as f:
                settings = json.load(f)
            self.apply_settings(settings)
            self.current_profile = os.path.basename(file_path)
            self.profile_var.set(os.path.splitext(self.current_profile)[0])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {str(e)}")

    def load_selected_profile(self, event=None):
        profile_name = self.profile_var.get()
        if profile_name:
            file_path = os.path.join(self.profiles_dir, f"{profile_name}.json")
            self.load_profile(file_path)

    def delete_profile(self):
        profile_name = self.profile_var.get()
        if profile_name:
            file_path = os.path.join(self.profiles_dir, f"{profile_name}.json")
            try:
                os.remove(file_path)
                self.refresh_profiles()
                self.profile_var.set('')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete profile: {str(e)}")

class AdvancedSettings(tk.Toplevel):
    def __init__(self, parent, main_app):
        super().__init__(parent)
        self.title("Advanced Settings")
        self.main_app = main_app
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Hardware Tab
        hardware_tab = ttk.Frame(notebook)
        notebook.add(hardware_tab, text="Hardware")
        
        ttk.Label(hardware_tab, text="Network:").grid(row=0, column=0, padx=5, pady=2)
        self.network = ttk.Combobox(hardware_tab, values=["user", "tap", "none"], width=15)
        self.network.current(0)
        self.network.grid(row=0, column=1, padx=5, pady=2)
        
        self.usb_support = tk.BooleanVar()
        ttk.Checkbutton(
            hardware_tab,
            text="Enable USB",
            variable=self.usb_support
        ).grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        self.secure_boot = tk.BooleanVar()
        ttk.Checkbutton(
            hardware_tab,
            text="Enable Secure Boot",
            variable=self.secure_boot
        ).grid(row=2, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        ttk.Label(hardware_tab, text="UEFI Firmware:").grid(row=3, column=0, padx=5, pady=2)
        self.uefi_firmware = ttk.Entry(hardware_tab, width=25)
        self.uefi_firmware.grid(row=3, column=1, padx=5, pady=2)
        ttk.Button(
            hardware_tab,
            text="Browse",
            command=lambda: self.browse_file("UEFI", self.uefi_firmware)
        ).grid(row=3, column=2, padx=5, pady=2)
        
        # Disk Management Tab
        disk_tab = ttk.Frame(notebook)
        notebook.add(disk_tab, text="Disk Management")
        
        ttk.Label(disk_tab, text="Disk Name:").grid(row=0, column=0, padx=5, pady=2)
        self.disk_name = ttk.Entry(disk_tab, width=25)
        self.disk_name.grid(row=0, column=1, columnspan=2, padx=5, pady=2)
        
        ttk.Label(disk_tab, text="Disk Size:").grid(row=1, column=0, padx=5, pady=2)
        self.disk_size = ttk.Entry(disk_tab, width=10)
        self.disk_size.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        
        ttk.Label(disk_tab, text="Save Path:").grid(row=2, column=0, padx=5, pady=2)
        self.disk_path = ttk.Entry(disk_tab, width=25)
        self.disk_path.grid(row=2, column=1, padx=5, pady=2)
        ttk.Button(
            disk_tab,
            text="Browse",
            command=self.browse_disk_path
        ).grid(row=2, column=2, padx=5, pady=2)
        
        ttk.Button(
            disk_tab,
            text="Create Virtual Disk",
            command=self.create_disk
        ).grid(row=3, column=0, columnspan=3, pady=10)

    def browse_disk_path(self):
        path = filedialog.askdirectory()
        if path:
            self.disk_path.delete(0, tk.END)
            self.disk_path.insert(0, path)

    def create_disk(self):
        disk_name = self.disk_name.get()
        disk_size = self.disk_size.get()
        save_path = self.disk_path.get()
        
        if not all([disk_name, disk_size, save_path]):
            messagebox.showwarning("Warning", "Please fill all disk parameters!")
            return
            
        if not disk_name.endswith(".qcow2"):
            disk_name += ".qcow2"
            
        full_path = os.path.join(save_path, disk_name)
        
        try:
            subprocess.run(
                ["qemu-img", "create", "-f", "qcow2", full_path, disk_size],
                check=True,
                capture_output=True
            )
            messagebox.showinfo("Success", f"Virtual disk created at:\n{full_path}")
            self.main_app.disk_image.delete(0, tk.END)
            self.main_app.disk_image.insert(0, full_path)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to create disk:\n{e.stderr.decode()}")

    def browse_file(self, file_type, entry_field):
        filename = filedialog.askopenfilename(
            filetypes=[("EFI files", "*.fd")] if file_type == "UEFI" else [("All files", "*.*")]
        )
        if filename:
            entry_field.delete(0, tk.END)
            entry_field.insert(0, filename)

if __name__ == "__main__":
    root = tk.Tk()
    app = VMController(root)
    root.mainloop()
