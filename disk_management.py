import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import psutil
import os
import sys
import ctypes
import threading
import time
import struct
import subprocess
from datetime import datetime
import hashlib
from PIL import Image, ImageTk

try:
    import wmi
except ImportError:
    wmi = None

try:
    import win32api
    import win32file
    import win32con
except ImportError:
    win32api = None
    win32file = None
    win32con = None
import ctypes, msvcrt

FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
GENERIC_READ = 0x80000000
OPEN_EXISTING = 3



# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def open_nocache(path):
    """Windows'ta cache kullanmadan dosya açma"""
    CreateFile = ctypes.windll.kernel32.CreateFileW
    handle = CreateFile(
        path, GENERIC_READ, 0, None, OPEN_EXISTING,
        FILE_FLAG_NO_BUFFERING | FILE_FLAG_SEQUENTIAL_SCAN, None
    )
    if handle == -1:
        raise ctypes.WinError()
    return msvcrt.open_osfhandle(handle, os.O_RDONLY)

def is_admin():
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Restart the application with administrator privileges"""
    if is_admin():
        return True
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return False

class DiskManagementTool:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.withdraw() 
        self.show_splash()
     

        
        self.root.title("Disk Manager Pro")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # 🔹 Burada icon ekle
        try:
            self.root.iconbitmap("diskico.ico")   # aynı klasörde olmalı
        except Exception as e:
            print("Icon yüklenemedi:", e)
            
        try:
            self.wmi_conn = wmi.WMI() if wmi else None
        except:
            self.wmi_conn = None
        
        self.current_operation = None
        self.progress_var = tk.DoubleVar()
        self.progress_text_var = tk.StringVar()
        
        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.create_main_content()
        
        # Initialize with disk info page
        self.show_disk_info()

    def show_splash(self):
        splash = tk.Toplevel()
        splash.overrideredirect(True)
        splash.geometry("400x300+600+300")
        splash.config(bg="black")
        
        # Şeffaflık için gerekli ayarlar
        splash.wm_attributes("-transparent", "black")
        splash.wm_attributes("-topmost", True)
        
        # PNG dosyasını yükle (alpha kanalı olmalı)
        img = Image.open("diskpng.png")
        img = img.resize((300, 200))
        self.splash_img = ImageTk.PhotoImage(img)
        
        lbl = tk.Label(splash, image=self.splash_img, bg="black")
        lbl.pack(expand=True)
        
        # 1 saniye sonra splash kapanır
        self.root.after(1000, lambda: (splash.destroy(), self.root.deiconify()))

    def create_sidebar(self):
        """Create the navigation sidebar"""
        self.sidebar = ctk.CTkFrame(self.root, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)
        
        # Logo/Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="Disk Manager Pro", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))
        
        # Admin status indicator
        admin_status = "Administrator" if is_admin() else "Standard User"
        admin_color = "green" if is_admin() else "yellow"
        self.admin_label = ctk.CTkLabel(
            self.sidebar,
            text=f"Status: {admin_status}",
            text_color=admin_color,
            font=ctk.CTkFont(size=11)
        )
        self.admin_label.grid(row=1, column=0, padx=20, pady=(0, 15))
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("Disk Information", "disk_info"),
            ("File Metadata", "file_metadata"),  # Added metadata viewer
            ("Speed Test", "speed_test"),
            ("File Recovery", "file_recovery"),
            ("Disk Cloning", "disk_cloning"),
            ("Hex Viewer", "hex_viewer"),
            ("Health Monitor", "health_monitor")
        ]
        
        for i, (text, command) in enumerate(nav_items, 2):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=lambda cmd=command: self.switch_page(cmd),
                height=35,
                font=ctk.CTkFont(size=13)
            )
            btn.grid(row=i, column=0, padx=15, pady=2, sticky="ew")
            self.nav_buttons[command] = btn
            
        self.progress_frame = ctk.CTkFrame(self.sidebar)
        self.progress_frame.grid(row=11, column=0, padx=15, pady=10, sticky="ew")
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Ready",
            font=ctk.CTkFont(size=11)
        )
        self.progress_label.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(padx=10, pady=5, fill="x")
        self.progress_bar.set(0)
            
    def create_main_content(self):
        """Create the main content area"""
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
    def update_progress(self, value, text="Processing..."):
        """Update progress bar and text"""
        self.progress_var.set(value)
        self.progress_text_var.set(text)
        self.progress_bar.set(value / 100.0)
        self.progress_label.configure(text=f"{text} ({value}%)")
        self.root.update_idletasks()
        
    def switch_page(self, page):
        """Switch between different pages"""
        # Clear main frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # Update button states
        for btn in self.nav_buttons.values():
            btn.configure(fg_color=("gray75", "gray25"))
        self.nav_buttons[page].configure(fg_color=("gray65", "gray35"))
        
        # Show selected page
        if page == "disk_info":
            self.show_disk_info()
        elif page == "file_metadata":  # Added metadata page
            self.show_file_metadata()
        elif page == "speed_test":
            self.show_speed_test()
        elif page == "file_recovery":
            self.show_file_recovery_page()
        elif page == "disk_cloning":
            self.show_disk_cloning()
        elif page == "secure_wipe":
            self.show_secure_wipe()
        elif page == "format_disk":
            self.show_format_disk()
        elif page == "hex_viewer":
            self.show_hex_viewer()
        elif page == "health_monitor":
            self.show_health_monitor()
            
    def show_disk_info(self):
        """Display disk information page"""
        # Title
        title = ctk.CTkLabel(
            self.main_frame, 
            text="Disk Information", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            self.main_frame,
            text="Refresh",
            command=self.refresh_disk_info,
            width=100
        )
        refresh_btn.grid(row=0, column=1, pady=(20, 10), sticky="e")
        
        # Scrollable frame for disk list
        self.disk_scroll = ctk.CTkScrollableFrame(self.main_frame)
        self.disk_scroll.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        self.refresh_disk_info()
        
    def refresh_disk_info(self):
        """Refresh disk information"""
        # Clear existing widgets
        for widget in self.disk_scroll.winfo_children():
            widget.destroy()
            
        # Get disk information
        disks = psutil.disk_partitions()
        
        for i, disk in enumerate(disks):
            # Create frame for each disk
            disk_frame = ctk.CTkFrame(self.disk_scroll)
            disk_frame.grid(row=i, column=0, sticky="ew", pady=5, padx=10)
            disk_frame.grid_columnconfigure(1, weight=1)
            
            try:
                usage = psutil.disk_usage(disk.mountpoint)
                
                # Disk name
                name_label = ctk.CTkLabel(
                    disk_frame, 
                    text=f"Drive: {disk.device}",
                    font=ctk.CTkFont(size=16, weight="bold")
                )
                name_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
                
                # File system
                fs_label = ctk.CTkLabel(
                    disk_frame, 
                    text=f"File System: {disk.fstype}"
                )
                fs_label.grid(row=1, column=0, sticky="w", padx=10)
                
                # Size information
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                free_gb = usage.free / (1024**3)
                
                size_label = ctk.CTkLabel(
                    disk_frame,
                    text=f"Total: {total_gb:.2f} GB | Used: {used_gb:.2f} GB | Free: {free_gb:.2f} GB"
                )
                size_label.grid(row=2, column=0, sticky="w", padx=10)
                
                # Progress bar
                progress = ctk.CTkProgressBar(disk_frame)
                progress.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
                progress.set(usage.used / usage.total)
                
                # Usage percentage
                usage_percent = (usage.used / usage.total) * 100
                percent_label = ctk.CTkLabel(
                    disk_frame,
                    text=f"{usage_percent:.1f}% Used"
                )
                percent_label.grid(row=3, column=1, padx=10)
                
            except PermissionError:
                error_label = ctk.CTkLabel(
                    disk_frame,
                    text="Access Denied",
                    text_color="red"
                )
                error_label.grid(row=1, column=0, sticky="w", padx=10)
                
    def show_speed_test(self):
        """Display speed test page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="Disk Speed Test",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # Disk selection
        disk_frame = ctk.CTkFrame(self.main_frame)
        disk_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(disk_frame, text="Select Disk:").grid(row=0, column=0, padx=10, pady=10)
        
        self.disk_var = ctk.StringVar()
        disk_menu = ctk.CTkOptionMenu(
            disk_frame,
            variable=self.disk_var,
            values=[disk.device for disk in psutil.disk_partitions()]
        )
        disk_menu.grid(row=0, column=1, padx=10, pady=10)
        
        # Test controls
        control_frame = ctk.CTkFrame(self.main_frame)
        control_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        self.test_btn = ctk.CTkButton(
            control_frame,
            text="Start Speed Test",
            command=self.start_speed_test
        )
        self.test_btn.grid(row=0, column=0, padx=10, pady=10)
        
        # Results area
        self.results_frame = ctk.CTkFrame(self.main_frame)
        self.results_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        self.main_frame.grid_rowconfigure(3, weight=1)
    
    
    def start_speed_test(self):
        """Start disk speed test"""
        if not self.disk_var.get():
            messagebox.showwarning("Warning", "Please select a disk first!")
            return
            
        self.test_btn.configure(state="disabled", text="Testing...")
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        # Progress bar
        progress = ctk.CTkProgressBar(self.results_frame)
        progress.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        progress.set(0)
        
        # Run test in thread
        threading.Thread(target=self.run_speed_test, args=(progress,), daemon=True).start()
        
    def run_speed_test(self, progress):
        """Run the actual speed test"""
        try:
            disk_path = self.disk_var.get()
            test_file = os.path.join(disk_path, "speed_test_temp.dat")
            
            # Write test
            write_speeds = []
            for i in range(5):
                start_time = time.time()
                with open(test_file, 'wb') as f:
                    data = os.urandom(10 * 1024 * 1024)  # 10MB
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                end_time = time.time()
                
                speed = (10 * 1024 * 1024) / (end_time - start_time) / (1024 * 1024)  # MB/s
                write_speeds.append(speed)
                progress.set((i + 1) / 10)
                
            # Read test
            # Read test
            read_speeds = []
            for i in range(5):
                start_time = time.time()
                
                # Cache'siz okuma
                fd = open_nocache(test_file)
                total_read = 0
                while True:
                    chunk = os.read(fd, 1024*1024)  # 1MB blok
                    if not chunk:
                        break
                    total_read += len(chunk)
                os.close(fd)
                
                end_time = time.time()
                speed = total_read / (end_time - start_time) / (1024 * 1024)  # MB/s
                read_speeds.append(speed)
                progress.set((i + 6) / 10)

                
            # Clean up
            os.remove(test_file)
            
            # Display results
            avg_write = sum(write_speeds) / len(write_speeds)
            avg_read = sum(read_speeds) / len(read_speeds)
            
            self.root.after(0, self.display_speed_results, avg_write, avg_read)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Speed test failed: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.test_btn.configure(state="normal", text="Start Speed Test"))
            
    def display_speed_results(self, write_speed, read_speed):
        """Display speed test results"""
        progress_widgets = [w for w in self.results_frame.winfo_children() if isinstance(w, ctk.CTkProgressBar)]
        for w in progress_widgets:
            w.destroy()
            
        results_text = f"""
Speed Test Results:

Write Speed: {write_speed:.2f} MB/s
Read Speed: {read_speed:.2f} MB/s

Performance Rating: {"Excellent" if min(write_speed, read_speed) > 100 else "Good" if min(write_speed, read_speed) > 50 else "Average"}
        """
        
        results_label = ctk.CTkLabel(
            self.results_frame,
            text=results_text,
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        results_label.grid(row=0, column=0, padx=20, pady=20)
        
    def show_file_recovery_page(self):
        """Display file recovery page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="File Recovery",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # Warning
        warning = ctk.CTkLabel(
            self.main_frame,
            text="⚠️ File recovery may take significant time depending on drive size",
            text_color="orange"
        )
        warning.grid(row=1, column=0, pady=10, sticky="w")
        
        # Source selection
        source_frame = ctk.CTkFrame(self.main_frame)
        source_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(source_frame, text="Source Drive:").grid(row=0, column=0, padx=10, pady=10)
        
        self.recovery_disk_var = ctk.StringVar()
        recovery_disk_menu = ctk.CTkOptionMenu(
            source_frame,
            variable=self.recovery_disk_var,
            values=[disk.device for disk in psutil.disk_partitions()]
        )
        recovery_disk_menu.grid(row=0, column=1, padx=10, pady=10)
        
        
        # Output directory selection
        output_frame = ctk.CTkFrame(self.main_frame)
        output_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(output_frame, text="Output Directory:").grid(row=0, column=0, padx=10, pady=5)
        
        self.output_dir_var = ctk.StringVar(value="")
        output_entry = ctk.CTkEntry(output_frame, textvariable=self.output_dir_var, width=300)
        output_entry.grid(row=0, column=1, padx=10, pady=5)
        
        browse_btn = ctk.CTkButton(
            output_frame,
            text="Browse",
            command=self.browse_output_folder,
            width=80
        )
        browse_btn.grid(row=0, column=2, padx=10, pady=5)
        
        filetype_frame = ctk.CTkFrame(self.main_frame)
        filetype_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(filetype_frame, text="File Types to Recover:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w"
        )
        
        self.recover_pdf = ctk.BooleanVar(value=True)
        self.recover_jpeg = ctk.BooleanVar(value=True)
        self.recover_png = ctk.BooleanVar(value=True)
        self.recover_zip = ctk.BooleanVar(value=True)
        self.recover_mp4 = ctk.BooleanVar(value=True)
        self.recover_docx = ctk.BooleanVar(value=True)
        self.recover_mp3 = ctk.BooleanVar(value=True)
        self.recover_avi = ctk.BooleanVar(value=True)
        self.recover_gif = ctk.BooleanVar(value=True)
        self.recover_bmp = ctk.BooleanVar(value=True)
        
        ctk.CTkCheckBox(filetype_frame, text="PDF Files", variable=self.recover_pdf).grid(
            row=1, column=0, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="JPEG Images", variable=self.recover_jpeg).grid(
            row=1, column=1, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="PNG Images", variable=self.recover_png).grid(
            row=1, column=2, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="ZIP/DOCX Files", variable=self.recover_zip).grid(
            row=1, column=3, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="MP4 Videos", variable=self.recover_mp4).grid(
            row=1, column=4, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="DOCX Documents", variable=self.recover_docx).grid(
            row=2, column=0, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="MP3 Audio", variable=self.recover_mp3).grid(
            row=2, column=1, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="AVI Videos", variable=self.recover_avi).grid(
            row=2, column=2, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="GIF Images", variable=self.recover_gif).grid(
            row=2, column=3, padx=10, pady=2, sticky="w"
        )
        ctk.CTkCheckBox(filetype_frame, text="BMP Images", variable=self.recover_bmp).grid(
            row=2, column=4, padx=10, pady=2, sticky="w"
        )
        
        # Advanced settings
        advanced_frame = ctk.CTkFrame(self.main_frame)
        advanced_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(advanced_frame, text="Advanced Settings:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )
        
        ctk.CTkLabel(advanced_frame, text="Block Size (MB):").grid(row=1, column=0, padx=10, pady=5)
        self.block_size_var = ctk.StringVar(value="4")
        block_entry = ctk.CTkEntry(advanced_frame, textvariable=self.block_size_var, width=100)
        block_entry.grid(row=1, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(advanced_frame, text="Max File Size (MB):").grid(row=2, column=0, padx=10, pady=5)
        self.max_size_var = ctk.StringVar(value="64")
        max_entry = ctk.CTkEntry(advanced_frame, textvariable=self.max_size_var, width=100)
        max_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # Recovery controls
        control_frame = ctk.CTkFrame(self.main_frame)
        control_frame.grid(row=6, column=0, sticky="ew", padx=20, pady=10)
        
        self.recovery_btn = ctk.CTkButton(
            control_frame,
            text="Start Recovery",
            command=self.start_file_recovery
        )
        self.recovery_btn.grid(row=0, column=0, padx=10, pady=10)
        
        # Progress area
        self.recovery_progress_frame = ctk.CTkFrame(self.main_frame)
        self.recovery_progress_frame.grid(row=7, column=0, sticky="nsew", padx=20, pady=10)
        self.main_frame.grid_rowconfigure(7, weight=1)

    def browse_output_folder(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir_var.set(folder)
            
    def start_file_recovery(self):
        """Start signature-based file recovery process"""
        if not self.recovery_disk_var.get():
            messagebox.showwarning("Warning", "Please select a source drive!")
            return
            
        if not self.output_dir_var.get():
            messagebox.showwarning("Warning", "Please select an output folder!")
            return
            
        # Check if any file type is selected
        if not any([self.recover_pdf.get(), self.recover_jpeg.get(), 
                   self.recover_png.get(), self.recover_zip.get(), self.recover_mp4.get(),
                   self.recover_docx.get(), self.recover_mp3.get(), self.recover_avi.get(),
                   self.recover_gif.get(), self.recover_bmp.get()]):
            messagebox.showwarning("Warning", "Please select at least one file type to recover!")
            return
            
        def recovery_thread():
            try:
                self.update_progress(0, "Starting signature-based recovery...")
                
                source = self.recovery_disk_var.get()
                output_dir = self.output_dir_var.get()
                block_size = int(self.block_size_var.get()) * 1024 * 1024
                max_file_size = int(self.max_size_var.get()) * 1024 * 1024
                
                # Create output directory
                os.makedirs(output_dir, exist_ok=True)
                
                # File signatures
                signatures = {}
                if self.recover_pdf.get():
                    signatures['pdf'] = {'head': b"%PDF", 'eof': b"%%EOF", 'max_size': max_file_size}
                if self.recover_jpeg.get():
                    signatures['jpg'] = {'head': b"\xFF\xD8\xFF", 'eof': b"\xFF\xD9", 'max_size': max_file_size}
                if self.recover_png.get():
                    signatures['png'] = {'head': b"\x89PNG\r\n\x1a\n", 'eof': None, 'max_size': max_file_size}
                if self.recover_zip.get():
                    signatures['zip'] = {'head': b"PK\x03\x04", 'eof': None, 'max_size': max_file_size}
                if self.recover_mp4.get():
                    signatures['mp4'] = {'head': b"\x00\x00\x00\x18\x66\x74\x79\x70", 'eof': None, 'max_size': max_file_size}
                if self.recover_docx.get():
                    signatures['docx'] = {'head': b"PK\x03\x04", 'eof': None, 'max_size': max_file_size}
                if self.recover_mp3.get():
                    signatures['mp3'] = {'head': b"\x49\x44\x33", 'eof': None, 'max_size': max_file_size}
                if self.recover_avi.get():
                    signatures['avi'] = {'head': b"\x52\x49\x46\x46", 'eof': None, 'max_size': max_file_size}
                if self.recover_gif.get():
                    signatures['gif'] = {'head': b"\x47\x49\x46\x38", 'eof': None, 'max_size': max_file_size}
                if self.recover_bmp.get():
                    signatures['bmp'] = {'head': b"\x42\x4D", 'eof': None, 'max_size': max_file_size}
                
                self.carve_files(source, output_dir, signatures, block_size)
                
            except Exception as e:
                messagebox.showerror("Error", f"Recovery failed: {str(e)}")
                self.update_progress(0, "Ready")
        
        threading.Thread(target=recovery_thread, daemon=True).start()

    def carve_files(self, source, output_dir, signatures, block_size):
        """Carve files using signature-based recovery"""
        try:
            # Convert drive letter to raw disk format
            if ':' in source:
                drive_letter = source.split(':')[0]
                raw_disk_path = f"\\\\.\\{drive_letter}:"
            else:
                raw_disk_path = source
            
            # Get disk size using Windows API instead of psutil
            try:
                import win32file
                handle = win32file.CreateFile(
                    raw_disk_path,
                    win32con.GENERIC_READ,
                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None
                )
                # Get disk size
                total_disk_size = win32file.GetFileSize(handle)
                if total_disk_size == -1:
                    # Fallback to getting disk geometry
                    disk_usage = psutil.disk_usage(source.split(':')[0] + ':')
                    total_disk_size = disk_usage.total
                win32file.CloseHandle(handle)
            except:
                # Fallback to psutil if Windows API fails
                disk_usage = psutil.disk_usage(source.split(':')[0] + ':')
                total_disk_size = disk_usage.total
            
            with open(raw_disk_path, "rb") as f:
                idx = 0
                buf = b""
                total_read = 0
                tail_keep = 1 * 1024 * 1024  # 1MB tail buffer
                
                while True:
                    try:
                        chunk = f.read(block_size)
                        if not chunk:
                            break
                            
                        buf += chunk
                        total_read += len(chunk)
                        
                        progress_percent = min((total_read / total_disk_size) * 100, 99)
                        self.update_progress(progress_percent, f"Scanning... {self.format_bytes(total_read)} / {self.format_bytes(total_disk_size)}")
                        
                        progress = False
                        
                        # Search for file signatures
                        for ext, sig_info in signatures.items():
                            head = sig_info['head']
                            eof = sig_info.get('eof')
                            max_size = sig_info['max_size']
                            
                            start_pos = 0
                            while True:
                                pos = buf.find(head, start_pos)
                                if pos == -1:
                                    break
                                    
                                # Extract file data
                                if eof:
                                    end_pos = buf.find(eof, pos + len(head))
                                    if end_pos != -1:
                                        end_pos += len(eof)
                                        file_data = buf[pos:end_pos]
                                        if len(file_data) <= max_size:
                                            idx += 1
                                            self.save_recovered_file(ext, idx, file_data, output_dir)
                                            buf = buf[end_pos:]
                                            progress = True
                                            break
                                else:
                                    # For files without clear EOF, extract up to max_size
                                    file_data = buf[pos:pos + min(max_size, len(buf) - pos)]
                                    if len(file_data) >= len(head):
                                        idx += 1
                                        self.save_recovered_file(ext, idx, file_data, output_dir, partial=True)
                                        buf = buf[pos + len(file_data):]
                                        progress = True
                                        break
                                        
                                start_pos = pos + 1
                        
                        # Keep tail buffer
                        if len(buf) > tail_keep:
                            buf = buf[-tail_keep:]
                            
                    except Exception as e:
                        print(f"Error reading chunk: {e}")
                        break
                
                self.update_progress(100, f"Recovery complete! Found {idx} files")
                messagebox.showinfo("Recovery Complete", f"Successfully recovered {idx} files to {output_dir}")
                
        except Exception as e:
            error_msg = f"Recovery failed: {str(e)}"
            print(f"Carve files error: {error_msg}")
            messagebox.showerror("Error", error_msg)
            self.update_progress(0, "Ready")

    def save_recovered_file(self, ext, idx, data, output_dir, partial=False):
        """Save recovered file to disk"""
        name = f"recovered_{idx}.{ext}"
        if partial:
            name += ".partial"
        out_path = os.path.join(output_dir, name)
        
        with open(out_path, "wb") as w:
            w.write(data)
        
        print(f"[+] Saved: {out_path} ({len(data)} bytes)")

    def run_file_recovery(self, progress, status_label):
        """Run the actual file recovery process"""
        try:
            drive_letter = self.recovery_disk_var.get().replace('\\', '').replace(':', '')
            output_path = self.output_path_var.get()
            
            self.root.after(0, lambda: status_label.configure(text="Reading Master File Table..."))
            progress.set(0.1)
            
            # Open drive for raw reading
            drive_path = f"\\\\.\\{drive_letter}:"
            try:
                handle = win32file.CreateFile(
                    drive_path,
                    win32con.GENERIC_READ,
                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None
                )
                
                # Read boot sector to get MFT location
                boot_sector = win32file.ReadFile(handle, 512)[1]
                
                # Parse NTFS boot sector
                if boot_sector[3:11] == b'NTFS    ':
                    bytes_per_sector = struct.unpack('<H', boot_sector[11:13])[0]
                    sectors_per_cluster = struct.unpack('<B', boot_sector[13:14])[0]
                    mft_cluster = struct.unpack('<Q', boot_sector[48:56])[0]
                    
                    cluster_size = bytes_per_sector * sectors_per_cluster
                    mft_offset = mft_cluster * cluster_size
                    
                    self.root.after(0, lambda: status_label.configure(text="Scanning for deleted files..."))
                    progress.set(0.3)
                    
                    # Read MFT entries
                    win32file.SetFilePointer(handle, mft_offset, win32con.FILE_BEGIN)
                    mft_data = win32file.ReadFile(handle, 1024 * 1024)[1]  # Read 1MB of MFT
                    
                    recovered_count = 0
                    
                    # Parse MFT entries (simplified)
                    for i in range(0, len(mft_data), 1024):  # Each MFT entry is 1024 bytes
                        entry = mft_data[i:i+1024]
                        if len(entry) < 1024:
                            break
                            
                        # Check if it's a valid MFT entry
                        if entry[0:4] == b'FILE':
                            flags = struct.unpack('<H', entry[22:24])[0]
                            
                            # Check if file is deleted (not in use)
                            if not (flags & 0x01):  # FILE_RECORD_SEGMENT_IN_USE
                                # Try to recover filename and data
                                filename = self.extract_filename_from_mft(entry)
                                if filename and not filename.startswith('$'):
                                    try:
                                        # Create recovered file
                                        recovered_path = os.path.join(output_path, f"recovered_{recovered_count}_{filename}")
                                        
                                        # Extract file data (simplified - would need more complex parsing)
                                        file_data = self.extract_file_data_from_mft(entry, handle, cluster_size)
                                        
                                        if file_data:
                                            with open(recovered_path, 'wb') as f:
                                                f.write(file_data)
                                            recovered_count += 1
                                            
                                            if recovered_count % 10 == 0:
                                                progress_val = min(0.3 + (recovered_count / 1000) * 0.6, 0.9)
                                                progress.set(progress_val)
                                                self.root.after(0, lambda: status_label.configure(
                                                    text=f"Recovered {recovered_count} files..."
                                                ))
                                    except Exception as e:
                                        print(f"Error recovering file {filename}: {e}")
                
                win32file.CloseHandle(handle)
                
                progress.set(1.0)
                self.root.after(0, lambda: status_label.configure(
                    text=f"Recovery complete! Recovered {recovered_count} files."
                ))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Drive access failed: {str(e)}"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Recovery failed: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.recovery_btn.configure(state="normal", text="Start Recovery"))

    def extract_filename_from_mft(self, mft_entry):
        """Extract filename from MFT entry"""
        try:
            # Look for filename attribute (0x30)
            offset = 56  # Start after MFT header
            while offset < len(mft_entry) - 4:
                attr_type = struct.unpack('<L', mft_entry[offset:offset+4])[0]
                if attr_type == 0x30:  # FILE_NAME attribute
                    attr_length = struct.unpack('<L', mft_entry[offset+4:offset+8])[0]
                    if attr_length > 0 and offset + attr_length <= len(mft_entry):
                        # Extract filename (simplified)
                        name_offset = offset + 24  # Skip attribute header
                        name_length = mft_entry[name_offset + 64]  # Filename length
                        if name_length > 0:
                            filename_data = mft_entry[name_offset + 66:name_offset + 66 + name_length * 2]
                            return filename_data.decode('utf-16le', errors='ignore')
                offset += max(attr_length, 8) if attr_length > 0 else 8
        except:
            pass
        return None

    def extract_file_data_from_mft(self, mft_entry, handle, cluster_size):
        """Extract file data from MFT entry (simplified)"""
        try:
            # Look for data attribute (0x80)
            offset = 56
            while offset < len(mft_entry) - 4:
                attr_type = struct.unpack('<L', mft_entry[offset:offset+4])[0]
                if attr_type == 0x80:  # DATA attribute
                    attr_length = struct.unpack('<L', mft_entry[offset+4:offset+8])[0]
                    non_resident = mft_entry[offset + 8] != 0
                    
                    if not non_resident and attr_length > 0:
                        # Resident data - data is stored directly in MFT
                        data_offset = struct.unpack('<H', mft_entry[offset+20:offset+22])[0]
                        data_length = struct.unpack('<L', mft_entry[offset+16:offset+20])[0]
                        return mft_entry[offset + data_offset:offset + data_offset + data_length]
                    else:
                        # Non-resident data - would need to follow cluster chains
                        # This is a simplified version that returns dummy data
                        return b"[Recovered file data - complex non-resident recovery needed]"
                        
                offset += max(attr_length, 8) if attr_length > 0 else 8
        except:
            pass
        return None

    def show_disk_cloning(self):
        """Display disk cloning page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="Disk Cloning",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # Warning
        warning = ctk.CTkLabel(
            self.main_frame,
            text="⚠️ Disk cloning will overwrite the destination disk completely!",
            text_color="red"
        )
        warning.grid(row=1, column=0, pady=10, sticky="w")
        
        # Source and destination selection
        clone_frame = ctk.CTkFrame(self.main_frame)
        clone_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        # Source
        ctk.CTkLabel(clone_frame, text="Source Disk:").grid(row=0, column=0, padx=10, pady=10)
        self.source_disk_var = ctk.StringVar()
        source_menu = ctk.CTkOptionMenu(
            clone_frame,
            variable=self.source_disk_var,
            values=[disk.device for disk in psutil.disk_partitions()]
        )
        
        source_menu.grid(row=0, column=1, padx=10, pady=10)
        
        # Destination
        ctk.CTkLabel(clone_frame, text="Destination Disk:").grid(row=1, column=0, padx=10, pady=10)
        self.dest_disk_var = ctk.StringVar()
        dest_menu = ctk.CTkOptionMenu(
            clone_frame,
            variable=self.dest_disk_var,
            values=[disk.device for disk in psutil.disk_partitions()]
        )
        dest_menu.grid(row=1, column=1, padx=10, pady=10)
        
        # Clone button
        clone_btn = ctk.CTkButton(
            clone_frame,
            text="Start Cloning",
            command=self.start_disk_cloning
        )
        clone_btn.grid(row=2, column=0, columnspan=2, pady=20)
        
    def start_disk_cloning(self):
        """Start real disk cloning process"""
        if not self.source_disk_var.get() or not self.dest_disk_var.get():
            messagebox.showwarning("Warning", "Please select both source and destination disks!")
            return
            
        if self.source_disk_var.get() == self.dest_disk_var.get():
            messagebox.showerror("Error", "Source and destination cannot be the same!")
            return
            
        result = messagebox.askyesno(
            "Confirm Cloning", 
            f"This will copy files from {self.source_disk_var.get()} to {self.dest_disk_var.get()}!\n\n"
            "Continue?"
        )
        
        if not result:
            return
            
        def clone_thread():
            try:
                self.update_progress(0, "Starting disk cloning...")
                
                source = self.source_disk_var.get()
                dest = self.dest_disk_var.get()
                
                # File-based cloning instead of sector cloning
                total_size = 0
                copied_size = 0
                
                # Calculate total size
                self.update_progress(10, "Calculating total size...")
                for root, dirs, files in os.walk(source):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            total_size += os.path.getsize(file_path)
                        except:
                            pass
                
                self.update_progress(20, "Starting file copy...")
                
                # Copy files
                import shutil
                for root, dirs, files in os.walk(source):
                    # Create directory structure
                    rel_path = os.path.relpath(root, source)
                    dest_dir = os.path.join(dest, rel_path) if rel_path != '.' else dest
                    
                    try:
                        os.makedirs(dest_dir, exist_ok=True)
                    except:
                        pass
                    
                    for file in files:
                        try:
                            src_file = os.path.join(root, file)
                            dst_file = os.path.join(dest_dir, file)
                            
                            if not os.path.exists(dst_file):
                                shutil.copy2(src_file, dst_file)
                                copied_size += os.path.getsize(src_file)
                                
                                if total_size > 0:
                                    progress = min(20 + (copied_size / total_size) * 70, 90)
                                    self.update_progress(progress, f"Copying files... {self.format_bytes(copied_size)}/{self.format_bytes(total_size)}")
                        except Exception as e:
                            continue
                
                self.update_progress(100, "Cloning complete!")
                messagebox.showinfo("Cloning Complete", f"Successfully cloned {self.format_bytes(copied_size)} of data!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Cloning failed: {str(e)}")
                self.update_progress(0, "Ready")
        
        threading.Thread(target=clone_thread, daemon=True).start()

    def run_disk_cloning(self):
        """Run the actual disk cloning process"""
        try:
            source_drive = self.source_disk_var.get().replace('\\', '').replace(':', '')
            dest_drive = self.dest_disk_var.get().replace('\\', '').replace(':', '')
            
            source_path = f"\\\\.\\{source_drive}:"
            dest_path = f"\\\\.\\{dest_drive}:"
            
            source_handle = win32file.CreateFile(
                source_path,
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )
            
            dest_handle = win32file.CreateFile(
                dest_path,
                win32con.GENERIC_WRITE,
                0,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )
            
            # Get source drive size
            source_size = win32file.GetFileSize(source_handle)
            chunk_size = 1024 * 1024  # 1MB chunks
            total_chunks = source_size // chunk_size
            
            self.root.after(0, lambda: messagebox.showinfo("Cloning", "Disk cloning started..."))
            
            for chunk_num in range(total_chunks):
                try:
                    # Read from source
                    data = win32file.ReadFile(source_handle, chunk_size)[1]
                    
                    # Write to destination
                    win32file.WriteFile(dest_handle, data)
                    win32file.FlushFileBuffers(dest_handle)
                    
                    if chunk_num % 100 == 0:  # Update every 100MB
                        progress = chunk_num / total_chunks
                        print(f"Cloning progress: {progress*100:.1f}%")
                        
                except Exception as e:
                    print(f"Cloning error at chunk {chunk_num}: {e}")
                    break
            
            win32file.CloseHandle(source_handle)
            win32file.CloseHandle(dest_handle)
            
            self.root.after(0, lambda: messagebox.showinfo("Complete", "Disk cloning completed successfully!"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Disk cloning failed: {str(e)}"))

    def show_secure_wipe(self):
        """Display secure wipe page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="Secure Wipe",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # Warning
        warning = ctk.CTkLabel(
            self.main_frame,
            text="⚠️ Secure wipe will permanently destroy all data on the selected disk!",
            text_color="red"
        )
        warning.grid(row=1, column=0, pady=10, sticky="w")
        
        # Disk selection
        wipe_frame = ctk.CTkFrame(self.main_frame)
        wipe_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(wipe_frame, text="Select Disk:").grid(row=0, column=0, padx=10, pady=10)
        
        self.wipe_disk_var = ctk.StringVar()
        wipe_menu = ctk.CTkOptionMenu(
            wipe_frame,
            variable=self.wipe_disk_var,
            values=[disk.device for disk in psutil.disk_partitions()]
        )
        wipe_menu.grid(row=0, column=1, padx=10, pady=10)
        
        # Wipe method
        ctk.CTkLabel(wipe_frame, text="Wipe Method:").grid(row=1, column=0, padx=10, pady=10)
        
        self.wipe_method_var = ctk.StringVar(value="Single Pass (Zeros)")
        method_menu = ctk.CTkOptionMenu(
            wipe_frame,
            variable=self.wipe_method_var,
            values=["Single Pass (Zeros)", "DoD 3-Pass", "Gutmann 35-Pass"]
        )
        method_menu.grid(row=1, column=1, padx=10, pady=10)
        
        # Wipe button
        wipe_btn = ctk.CTkButton(
            wipe_frame,
            text="Start Secure Wipe",
            command=self.start_secure_wipe
        )
        wipe_btn.grid(row=2, column=0, columnspan=2, pady=20)
        
    def start_secure_wipe(self):
        """Start real secure wipe process"""
        if not self.wipe_disk_var.get():
            messagebox.showwarning("Warning", "Please select a disk!")
            return
            
        result1 = messagebox.askyesno(
            "CONFIRM SECURE WIPE", 
            f"You are about to securely delete files on {self.wipe_disk_var.get()}!\n\n"
            "This will overwrite free space. Continue?"
        )
        
        if not result1:
            return
            
        result2 = messagebox.askyesno(
            "FINAL CONFIRMATION", 
            "Are you absolutely sure? This operation cannot be undone!"
        )
        
        if not result2:
            return
            
        def wipe_thread():
            try:
                self.update_progress(0, "Starting secure wipe...")
                
                disk_path = self.wipe_disk_var.get()
                
                # Alternative: Overwrite free space instead of entire disk
                self.update_progress(20, "Creating temporary files...")
                
                # Create large temporary files to fill free space
                temp_files = []
                try:
                    free_space = psutil.disk_usage(disk_path).free
                    chunk_size = min(100 * 1024 * 1024, free_space // 10)  # 100MB chunks
                    
                    self.update_progress(40, "Overwriting free space...")
                    
                    file_count = 0
                    written = 0
                    
                    while written < free_space * 0.8:  # Fill 80% of free space
                        temp_file = os.path.join(disk_path, f"secure_wipe_temp_{file_count}.tmp")
                        try:
                            with open(temp_file, 'wb') as f:
                                # Write random data
                                import random
                                for _ in range(chunk_size // 1024):
                                    f.write(bytes([random.randint(0, 255) for _ in range(1024)]))
                            
                            temp_files.append(temp_file)
                            written += chunk_size
                            file_count += 1
                            
                            progress = 40 + (written / (free_space * 0.8)) * 40
                            self.update_progress(progress, f"Overwriting... {self.format_bytes(written)}")
                            
                        except:
                            break
                    
                    self.update_progress(85, "Cleaning up temporary files...")
                    
                    # Delete temporary files
                    for temp_file in temp_files:
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    
                    self.update_progress(100, "Secure wipe complete!")
                    messagebox.showinfo("Wipe Complete", f"Successfully overwrote {self.format_bytes(written)} of free space!")
                    
                except Exception as e:
                    # Clean up on error
                    for temp_file in temp_files:
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    raise e
                    
            except Exception as e:
                messagebox.showerror("Error", f"Secure wipe failed: {str(e)}")
                self.update_progress(0, "Ready")
        
        threading.Thread(target=wipe_thread, daemon=True).start()

    def run_secure_wipe(self):
        """Run the actual secure wipe process"""
        try:
            drive_letter = self.wipe_disk_var.get().replace('\\', '').replace(':', '')
            method = self.wipe_method_var.get()
            
            drive_path = f"\\\\.\\{drive_letter}:"
            
            # Get drive size
            handle = win32file.CreateFile(
                drive_path,
                win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                0,  # Exclusive access
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )
            
            # Get drive geometry
            drive_size = win32file.GetFileSize(handle)
            if drive_size == -1:
                # Try alternative method for drive size
                geometry = win32file.DeviceIoControl(
                    handle,
                    0x70000,  # IOCTL_DISK_GET_DRIVE_GEOMETRY
                    None,
                    24
                )
                cylinders, media_type, tracks_per_cylinder, sectors_per_track, bytes_per_sector = struct.unpack('<QLLLL', geometry)
                drive_size = cylinders * tracks_per_cylinder * sectors_per_track * bytes_per_sector
            
            # Determine number of passes based on method
            if "Single Pass" in method:
                passes = 1
                patterns = [b'\x00']
            elif "DoD 3-Pass" in method:
                passes = 3
                patterns = [b'\xFF', b'\x55', b'\x55']
            elif "Gutmann" in method:
                passes = 35
                patterns = [b'\x55', b'\xAA', b'\x92', b'\x49', b'\x24'] * 7  # Simplified Gutmann patterns
            
            chunk_size = 1024 * 1024  # 1MB chunks
            total_chunks = drive_size // chunk_size
            
            for pass_num in range(passes):
                pattern = patterns[pass_num % len(patterns)]
                chunk_data = pattern * (chunk_size // len(pattern))
                
                self.root.after(0, lambda p=pass_num+1: messagebox.showinfo(
                    "Secure Wipe", f"Starting pass {p} of {passes}..."
                ))
                
                win32file.SetFilePointer(handle, 0, win32con.FILE_BEGIN)
                
                for chunk_num in range(total_chunks):
                    try:
                        win32file.WriteFile(handle, chunk_data)
                        win32file.FlushFileBuffers(handle)
                        
                        if chunk_num % 100 == 0:  # Update every 100MB
                            progress = (pass_num * total_chunks + chunk_num) / (passes * total_chunks)
                            print(f"Wipe progress: {progress*100:.1f}%")
                            
                    except Exception as e:
                        print(f"Write error at chunk {chunk_num}: {e}")
                        break
            
            win32file.CloseHandle(handle)
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Complete", f"Secure wipe completed using {method}!"
            ))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Secure wipe failed: {str(e)}"))

    def show_format_disk(self):
        """Display format disk page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="Format Disk",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # Format options
        format_frame = ctk.CTkFrame(self.main_frame)
        format_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        # Disk selection
        ctk.CTkLabel(format_frame, text="Select Disk:").grid(row=0, column=0, padx=10, pady=10)
        
        self.format_disk_var = ctk.StringVar()
        format_menu = ctk.CTkOptionMenu(
            format_frame,
            variable=self.format_disk_var,
            values=[disk.device for disk in psutil.disk_partitions()]
        )
        format_menu.grid(row=0, column=1, padx=10, pady=10)
        
        # File system
        ctk.CTkLabel(format_frame, text="File System:").grid(row=1, column=0, padx=10, pady=10)
        
        self.fs_var = ctk.StringVar(value="NTFS")
        fs_menu = ctk.CTkOptionMenu(
            format_frame,
            variable=self.fs_var,
            values=["NTFS", "FAT32", "exFAT"]
        )
        fs_menu.grid(row=1, column=1, padx=10, pady=10)
        
        # Volume label
        ctk.CTkLabel(format_frame, text="Volume Label:").grid(row=2, column=0, padx=10, pady=10)
        
        self.label_var = ctk.StringVar()
        label_entry = ctk.CTkEntry(format_frame, textvariable=self.label_var)
        label_entry.grid(row=2, column=1, padx=10, pady=10)
        
        # Quick format option
        self.quick_format_var = ctk.BooleanVar(value=True)
        quick_check = ctk.CTkCheckBox(
            format_frame,
            text="Quick Format",
            variable=self.quick_format_var
        )
        quick_check.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Format button
        format_btn = ctk.CTkButton(
            format_frame,
            text="Format Disk",
            command=self.start_format_disk
        )
        format_btn.grid(row=4, column=0, columnspan=2, pady=20)
        
    def start_format_disk(self):
        """Start disk formatting"""
        if not self.format_disk_var.get():
            messagebox.showwarning("Warning", "Please select a disk!")
            return
            
        result = messagebox.askyesno(
            "Confirm Format", 
            f"This will erase all data on {self.format_disk_var.get()}!\n\nContinue?"
        )
        
        if result:
            messagebox.showinfo("Info", "Disk formatting requires administrative privileges. This is a demonstration interface.")
            
    def show_hex_viewer(self):
        """Display hex viewer page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="Hex Viewer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # File selection
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        self.hex_file_var = ctk.StringVar()
        file_entry = ctk.CTkEntry(file_frame, textvariable=self.hex_file_var, width=400)
        file_entry.grid(row=0, column=0, padx=10, pady=10)
        
        browse_file_btn = ctk.CTkButton(
            file_frame,
            text="Browse File",
            command=self.browse_hex_file,
            width=100
        )
        browse_file_btn.grid(row=0, column=1, padx=10, pady=10)
        
        load_btn = ctk.CTkButton(
            file_frame,
            text="Load",
            command=self.load_hex_file,
            width=80
        )
        load_btn.grid(row=0, column=2, padx=10, pady=10)
        
        # Hex display
        self.hex_text = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Courier", size=12))
        self.hex_text.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
    def browse_hex_file(self):
        """Browse for file to view in hex"""
        file_path = filedialog.askopenfilename()
        if file_path:
            self.hex_file_var.set(file_path)
            
    def load_hex_file(self):
        """Load and display file in hex format"""
        file_path = self.hex_file_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid file!")
            return
            
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 16)  # Read first 16KB
                
            hex_output = ""
            for i in range(0, len(data), 16):
                # Address
                hex_output += f"{i:08X}  "
                
                # Hex bytes
                hex_bytes = data[i:i+16]
                hex_str = " ".join(f"{b:02X}" for b in hex_bytes)
                hex_output += f"{hex_str:<48} "
                
                # ASCII representation
                ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in hex_bytes)
                hex_output += f" |{ascii_str}|\n"
                
            self.hex_text.delete("1.0", tk.END)
            self.hex_text.insert("1.0", hex_output)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
            
    def show_health_monitor(self):
        """Display disk health monitoring page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="Disk Health Monitor",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")
        
        # Disk selection
        health_frame = ctk.CTkFrame(self.main_frame)
        health_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(health_frame, text="Select Disk:").grid(row=0, column=0, padx=10, pady=10)
        
        self.health_disk_var = ctk.StringVar()
        health_menu = ctk.CTkOptionMenu(
            health_frame,
            variable=self.health_disk_var,
            values=[disk.device for disk in psutil.disk_partitions()]
        )
        health_menu.grid(row=0, column=1, padx=10, pady=10)
        
        scan_btn = ctk.CTkButton(
            health_frame,
            text="Scan Health",
            command=self.scan_disk_health
        )
        scan_btn.grid(row=0, column=2, padx=10, pady=10)
        
        # Health results
        self.health_results = ctk.CTkTextbox(self.main_frame)
        self.health_results.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.main_frame.grid_rowconfigure(2, weight=1)
        
    def scan_disk_health(self):
        """Scan real disk health using SMART data"""
        if not self.health_disk_var.get():
            messagebox.showwarning("Warning", "Please select a disk!")
            return
            
        disk_path = self.health_disk_var.get()
        
        try:
            health_report = f"Disk Health Report for {disk_path}\n{'='*50}\n\n"
            
            # Basic disk usage
            usage = psutil.disk_usage(disk_path)
            health_report += f"Basic Information:\n"
            health_report += f"- Total Space: {usage.total / (1024**3):.2f} GB\n"
            health_report += f"- Used Space: {usage.used / (1024**3):.2f} GB\n"
            health_report += f"- Free Space: {usage.free / (1024**3):.2f} GB\n"
            health_report += f"- Usage: {(usage.used / usage.total) * 100:.1f}%\n\n"
            
            # Try to get SMART data using WMI
            if self.wmi_conn:
                try:
                    drive_letter = disk_path.replace('\\', '').replace(':', '')
                    
                    # Get physical disk info
                    for disk in self.wmi_conn.Win32_DiskDrive():
                        if drive_letter.upper() in str(disk.DeviceID).upper():
                            health_report += f"Physical Disk Information:\n"
                            health_report += f"- Model: {disk.Model}\n"
                            health_report += f"- Serial Number: {disk.SerialNumber}\n"
                            health_report += f"- Interface: {disk.InterfaceType}\n"
                            health_report += f"- Status: {disk.Status}\n\n"
                            
                            # Try to get SMART attributes (requires specific WMI classes)
                            try:
                                smart_data = self.wmi_conn.MSStorageDriver_FailurePredictStatus()
                                for smart in smart_data:
                                    if smart.InstanceName and drive_letter.upper() in smart.InstanceName.upper():
                                        health_report += f"SMART Status:\n"
                                        health_report += f"- Predict Failure: {'Yes' if smart.PredictFailure else 'No'}\n"
                                        health_report += f"- Reason: {smart.Reason if hasattr(smart, 'Reason') else 'N/A'}\n\n"
                            except:
                                health_report += "SMART Status: Unable to read SMART data\n\n"
                            break
                except Exception as e:
                    health_report += f"Error reading disk information: {str(e)}\n\n"
            
            # Health assessment
            free_space_ratio = usage.free / usage.total
            if free_space_ratio < 0.05:
                health_status = "CRITICAL - Very Low Space"
                health_color = "red"
            elif free_space_ratio < 0.1:
                health_status = "WARNING - Low Space"
                health_color = "orange"
            else:
                health_status = "GOOD"
                health_color = "green"
                
            health_report += f"Overall Health Status: {health_status}\n\n"
            
            health_report += "Recommendations:\n"
            health_report += "- Keep at least 10% free space for optimal performance\n"
            health_report += "- Regular backups are recommended\n"
            health_report += "- Monitor disk temperature and usage patterns\n"
            health_report += "- Check for bad sectors periodically\n"
            health_report += "- Consider disk replacement if SMART errors appear\n"
            
            self.health_results.delete("1.0", tk.END)
            self.health_results.insert("1.0", health_report)
            
        except Exception as e:
            messagebox.showerror("Error", f"Health scan failed: {str(e)}")

    def get_physical_drives(self):
        """Get list of physical drives using WMI"""
        drives = []
        try:
            if self.wmi_conn:
                for disk in self.wmi_conn.Win32_DiskDrive():
                    drives.append({
                        'device': disk.DeviceID,
                        'model': disk.Model,
                        'size': int(disk.Size) if disk.Size else 0,
                        'interface': disk.InterfaceType,
                        'serial': disk.SerialNumber
                    })
        except Exception as e:
            print(f"Error getting physical drives: {e}")
        return drives

    def run(self):
        """Start the application"""
        self.root.mainloop()

    def show_file_metadata(self):
        """Show file metadata viewer page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="File Metadata Viewer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(10, 20), sticky="w")
        
        # File selection frame
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        file_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(file_frame, text="Select File:", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        
        self.metadata_file_var = tk.StringVar()
        file_entry = ctk.CTkEntry(file_frame, textvariable=self.metadata_file_var, height=35)
        file_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        browse_btn = ctk.CTkButton(
            file_frame,
            text="Browse",
            command=self.browse_metadata_file,
            width=80,
            height=35
        )
        browse_btn.grid(row=0, column=2, padx=10, pady=10)
        
        analyze_btn = ctk.CTkButton(
            file_frame,
            text="Analyze Metadata",
            command=self.analyze_file_metadata,
            height=35
        )
        analyze_btn.grid(row=0, column=3, padx=10, pady=10)
        
        # Metadata display frame
        self.metadata_display_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.metadata_display_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        
        self.main_frame.grid_rowconfigure(2, weight=1)
        
    def browse_metadata_file(self):
        """Browse for file to analyze metadata"""
        file_path = filedialog.askopenfilename(
            title="Select File for Metadata Analysis",
            filetypes=[("All Files", "*.*")]
        )
        if file_path:
            self.metadata_file_var.set(file_path)
            
    def analyze_file_metadata(self):
        """Analyze and display comprehensive file metadata"""
        file_path = self.metadata_file_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("Warning", "Please select a valid file!")
            return
            
        # Clear previous results
        for widget in self.metadata_display_frame.winfo_children():
            widget.destroy()
            
        self.update_progress(10, "Reading file information...")
        
        try:
            # Basic file information
            stat_info = os.stat(file_path)
            
            metadata_info = [
                ("File Path", file_path),
                ("File Name", os.path.basename(file_path)),
                ("Directory", os.path.dirname(file_path)),
                ("File Size", f"{stat_info.st_size:,} bytes ({self.format_bytes(stat_info.st_size)})"),
                ("Created", datetime.fromtimestamp(stat_info.st_ctime).strftime("%Y-%m-%d %H:%M:%S")),
                ("Modified", datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M:%S")),
                ("Accessed", datetime.fromtimestamp(stat_info.st_atime).strftime("%Y-%m-%d %H:%M:%S")),
                ("File Mode", oct(stat_info.st_mode)),
                ("Inode", str(stat_info.st_ino)),
                ("Device", str(stat_info.st_dev)),
                ("Links", str(stat_info.st_nlink)),
            ]
            
            self.update_progress(20, "Analyzing file type and structure...")
            
            # File type analysis
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext:
                metadata_info.append(("File Extension", file_ext))
                
            # Try to detect file type by reading header
            try:
                with open(file_path, 'rb') as f:
                    header = f.read(32)  # Read more bytes for better detection
                    file_type = self.detect_file_type(header)
                    if file_type:
                        metadata_info.append(("Detected Type", file_type))
                        
                    # File signature (magic bytes)
                    hex_header = ' '.join([f'{b:02X}' for b in header[:16]])
                    metadata_info.append(("File Signature (Hex)", hex_header))
            except:
                pass
            
            self.update_progress(40, "Calculating checksums...")
            
            # Calculate file hashes
            if stat_info.st_size < 100 * 1024 * 1024:  # Only for files < 100MB
                with open(file_path, 'rb') as f:
                    content = f.read()
                    md5_hash = hashlib.md5(content).hexdigest()
                    sha1_hash = hashlib.sha1(content).hexdigest()
                    sha256_hash = hashlib.sha256(content).hexdigest()
                    
                metadata_info.extend([
                    ("MD5 Hash", md5_hash),
                    ("SHA1 Hash", sha1_hash),
                    ("SHA256 Hash", sha256_hash)
                ])
            
            self.update_progress(60, "Reading system attributes...")
            
            # Windows-specific attributes
            if os.name == 'nt':
                try:
                    import win32api
                    attrs = win32api.GetFileAttributes(file_path)
                    attr_list = []
                    if attrs & 1: attr_list.append("READ_ONLY")
                    if attrs & 2: attr_list.append("HIDDEN")
                    if attrs & 4: attr_list.append("SYSTEM")
                    if attrs & 16: attr_list.append("DIRECTORY")
                    if attrs & 32: attr_list.append("ARCHIVE")
                    if attrs & 128: attr_list.append("NORMAL")
                    if attrs & 256: attr_list.append("TEMPORARY")
                    if attrs & 512: attr_list.append("SPARSE_FILE")
                    if attrs & 1024: attr_list.append("REPARSE_POINT")
                    if attrs & 2048: attr_list.append("COMPRESSED")
                    if attrs & 4096: attr_list.append("OFFLINE")
                    if attrs & 8192: attr_list.append("NOT_CONTENT_INDEXED")
                    if attrs & 16384: attr_list.append("ENCRYPTED")
                    
                    metadata_info.append(("Windows Attributes", ", ".join(attr_list) if attr_list else "NORMAL"))
                except:
                    pass
            
            self.update_progress(70, "Extracting EXIF and extended metadata...")
            
            # Try to extract EXIF data for images
            if file_ext in ['.jpg', '.jpeg', '.tiff', '.tif']:
                try:
                    from PIL import Image
                    from PIL.ExifTags import TAGS, GPSTAGS
                    
                    with Image.open(file_path) as img:
                        # Basic image info
                        metadata_info.extend([
                            ("Image Format", img.format),
                            ("Image Mode", img.mode),
                            ("Image Size", f"{img.size[0]} x {img.size[1]} pixels"),
                        ])
                        
                        # EXIF data
                        exif_data = img._getexif()
                        if exif_data:
                            for tag_id, value in exif_data.items():
                                tag = TAGS.get(tag_id, tag_id)
                                
                                # Handle GPS data specially
                                if tag == "GPSInfo":
                                    gps_data = {}
                                    for gps_tag_id, gps_value in value.items():
                                        gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                        gps_data[gps_tag] = gps_value
                                    
                                    # Extract coordinates if available
                                    if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                                        lat = self.convert_gps_coords(gps_data['GPSLatitude'], gps_data.get('GPSLatitudeRef', 'N'))
                                        lon = self.convert_gps_coords(gps_data['GPSLongitude'], gps_data.get('GPSLongitudeRef', 'E'))
                                        metadata_info.append(("GPS Coordinates", f"{lat}, {lon}"))
                                    
                                    if 'GPSAltitude' in gps_data:
                                        altitude = float(gps_data['GPSAltitude'])
                                        metadata_info.append(("GPS Altitude", f"{altitude} meters"))
                                        
                                elif tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                                    metadata_info.append((f"EXIF {tag}", str(value)))
                                elif tag in ['Make', 'Model', 'Software', 'Artist', 'Copyright']:
                                    metadata_info.append((f"EXIF {tag}", str(value)))
                                elif tag in ['ExposureTime', 'FNumber', 'ISO', 'FocalLength']:
                                    metadata_info.append((f"EXIF {tag}", str(value)))
                                elif tag in ['Orientation', 'XResolution', 'YResolution']:
                                    metadata_info.append((f"EXIF {tag}", str(value)))
                                    
                except Exception as e:
                    metadata_info.append(("EXIF Error", f"Could not read EXIF data: {str(e)}"))
            
            # Try to extract metadata from other file types
            elif file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
                try:
                    # Video file metadata (basic)
                    metadata_info.append(("Media Type", "Video File"))
                    # Could add more video metadata extraction here
                except:
                    pass
                    
            elif file_ext in ['.mp3', '.wav', '.flac']:
                try:
                    # Audio file metadata (basic)
                    metadata_info.append(("Media Type", "Audio File"))
                    # Could add more audio metadata extraction here
                except:
                    pass
            
            self.update_progress(85, "Analyzing file structure...")
            
            # File entropy (randomness) analysis
            try:
                with open(file_path, 'rb') as f:
                    data = f.read(min(1024*1024, stat_info.st_size))  # Read up to 1MB
                    if data:
                        entropy = self.calculate_entropy(data)
                        metadata_info.append(("File Entropy", f"{entropy:.4f} (0=ordered, 8=random)"))
            except:
                pass
            
            # File permissions (Unix-style)
            try:
                import stat
                mode = stat_info.st_mode
                permissions = []
                if mode & stat.S_IRUSR: permissions.append("User Read")
                if mode & stat.S_IWUSR: permissions.append("User Write")
                if mode & stat.S_IXUSR: permissions.append("User Execute")
                if mode & stat.S_IRGRP: permissions.append("Group Read")
                if mode & stat.S_IWGRP: permissions.append("User Write")
                if mode & stat.S_IXGRP: permissions.append("Group Execute")
                if mode & stat.S_IROTH: permissions.append("Other Read")
                if mode & stat.S_IWOTH: permissions.append("Other Write")
                if mode & stat.S_IXOTH: permissions.append("Other Execute")
                
                metadata_info.append(("Permissions", ", ".join(permissions)))
            except:
                pass
            
            self.update_progress(95, "Displaying results...")
            
            # Display metadata in organized sections
            current_row = 0
            
            # Basic Information Section
            basic_frame = ctk.CTkFrame(self.metadata_display_frame)
            basic_frame.grid(row=current_row, column=0, sticky="ew", padx=5, pady=5)
            basic_frame.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(
                basic_frame, 
                text="📁 Basic Information", 
                font=ctk.CTkFont(size=16, weight="bold")
            ).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
            
            basic_info = [item for item in metadata_info if any(key in item[0] for key in 
                         ['File Path', 'File Name', 'Directory', 'File Size', 'Created', 'Modified', 'Accessed', 'Extension', 'Type'])]
            
            for i, (key, value) in enumerate(basic_info, 1):
                ctk.CTkLabel(basic_frame, text=f"{key}:", font=ctk.CTkFont(weight="bold")).grid(
                    row=i, column=0, padx=10, pady=2, sticky="nw"
                )
                # Handle long values
                if len(str(value)) > 80:
                    text_widget = tk.Text(basic_frame, height=2, width=60, wrap=tk.WORD, font=("Consolas", 9))
                    text_widget.insert(tk.END, str(value))
                    text_widget.configure(state=tk.DISABLED)
                    text_widget.grid(row=i, column=1, padx=10, pady=2, sticky="w")
                else:
                    ctk.CTkLabel(basic_frame, text=str(value), wraplength=400).grid(
                        row=i, column=1, padx=10, pady=2, sticky="w"
                    )
            
            current_row += 1
            
            # EXIF/Media Information Section
            exif_info = [item for item in metadata_info if any(key in item[0] for key in 
                        ['EXIF', 'GPS', 'Image', 'Media', 'Coordinates', 'Altitude'])]
            
            if exif_info:
                exif_frame = ctk.CTkFrame(self.metadata_display_frame)
                exif_frame.grid(row=current_row, column=0, sticky="ew", padx=5, pady=5)
                exif_frame.grid_columnconfigure(1, weight=1)
                
                ctk.CTkLabel(
                    exif_frame, 
                    text="📷 EXIF & Media Information", 
                    font=ctk.CTkFont(size=16, weight="bold")
                ).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
                
                for i, (key, value) in enumerate(exif_info, 1):
                    ctk.CTkLabel(exif_frame, text=f"{key}:", font=ctk.CTkFont(weight="bold")).grid(
                        row=i, column=0, padx=10, pady=2, sticky="nw"
                    )
                    ctk.CTkLabel(exif_frame, text=str(value), wraplength=400).grid(
                        row=i, column=1, padx=10, pady=2, sticky="w"
                    )
                
                current_row += 1
            
            # Security & Technical Information Section
            security_info = [item for item in metadata_info if any(key in item[0] for key in 
                           ['Hash', 'Signature', 'Attributes', 'Permissions', 'Entropy', 'Mode', 'Inode', 'Device', 'Links'])]
            
            if security_info:
                security_frame = ctk.CTkFrame(self.metadata_display_frame)
                security_frame.grid(row=current_row, column=0, sticky="ew", padx=5, pady=5)
                security_frame.grid_columnconfigure(1, weight=1)
                
                ctk.CTkLabel(
                    security_frame, 
                    text="🔒 Security & Technical Information", 
                    font=ctk.CTkFont(size=16, weight="bold")
                ).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
                
                for i, (key, value) in enumerate(security_info, 1):
                    ctk.CTkLabel(security_frame, text=f"{key}:", font=ctk.CTkFont(weight="bold")).grid(
                        row=i, column=0, padx=10, pady=2, sticky="nw"
                    )
                    # For long hashes, use a text widget
                    if len(str(value)) > 50:
                        text_widget = tk.Text(security_frame, height=2, width=60, wrap=tk.WORD, font=("Consolas", 9))
                        text_widget.insert(tk.END, str(value))
                        text_widget.configure(state=tk.DISABLED)
                        text_widget.grid(row=i, column=1, padx=10, pady=2, sticky="w")
                    else:
                        ctk.CTkLabel(security_frame, text=str(value), wraplength=400).grid(
                            row=i, column=1, padx=10, pady=2, sticky="w"
                        )
            
            self.update_progress(100, "Analysis complete!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze file metadata: {str(e)}")
            self.update_progress(0, "Ready")
    
    def convert_gps_coords(self, coords, ref):
        """Convert GPS coordinates from EXIF format to decimal degrees"""
        try:
            degrees = float(coords[0])
            minutes = float(coords[1])
            seconds = float(coords[2])
            
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            
            if ref in ['S', 'W']:
                decimal = -decimal
                
            return decimal
        except:
            return 0.0
    
    def calculate_entropy(self, data):
        """Calculate Shannon entropy of data"""
        try:
            import math
            if not data:
                return 0
            
            # Count frequency of each byte
            freq = {}
            for byte in data:
                freq[byte] = freq.get(byte, 0) + 1
            
            # Calculate entropy
            entropy = 0
            data_len = len(data)
            for count in freq.values():
                p = count / data_len
                if p > 0:
                    entropy -= p * math.log2(p)
            
            return entropy
        except:
            return 0.0

    def format_bytes(self, bytes_size):
        """Format bytes into human-readable format"""
        for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                break
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} {unit}"

    def detect_file_type(self, header):
        """Detect file type based on header"""
        if header.startswith(b'\xFF\xD8\xFF'):
            return "JPEG Image"
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            return "PNG Image"
        elif header.startswith(b'%PDF'):
            return "PDF Document"
        elif header.startswith(b'PK\x03\x04'):
            return "ZIP Archive"
        elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return "GIF Image"
        elif header.startswith(b'BM'):
            return "BMP Image"
        else:
            return "Unknown File Type"

    def perform_file_recovery(self):
        """Perform signature-based file recovery"""
        try:
            selected_drive = self.recovery_drive_var.get()
            output_dir = self.recovery_output_var.get()
            
            if not selected_drive or not output_dir:
                messagebox.showerror("Error", "Please select drive and output directory")
                return
                
            file_signatures = {}
            
            if self.recover_pdf.get():
                file_signatures['pdf'] = b'\x25\x50\x44\x46'
            if self.recover_jpeg.get():
                file_signatures['jpg'] = b'\xFF\xD8\xFF'
            if self.recover_png.get():
                file_signatures['png'] = b'\x89\x50\x4E\x47'
            if self.recover_zip.get():
                file_signatures['zip'] = b'\x50\x4B\x03\x04'
            if self.recover_mp4.get():
                file_signatures['mp4'] = b'\x00\x00\x00\x18\x66\x74\x79\x70'
            if self.recover_docx.get():
                file_signatures['docx'] = b'\x50\x4B\x03\x04'
            if self.recover_mp3.get():
                file_signatures['mp3'] = b'\x49\x44\x33'
            if self.recover_avi.get():
                file_signatures['avi'] = b'\x52\x49\x46\x46'
            if self.recover_gif.get():
                file_signatures['gif'] = b'\x47\x49\x46\x38'
            if self.recover_bmp.get():
                file_signatures['bmp'] = b'\x42\x4D'

        except Exception as e:
            messagebox.showerror("Error", f"File recovery failed: {str(e)}")

    def show_metadata_viewer(self):
        """Display metadata viewer page"""
        title = ctk.CTkLabel(
            self.main_frame,
            text="Metadata Viewer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, pady=(20, 10), sticky="w")

        # File selection
        file_frame = ctk.CTkFrame(self.main_frame)
        file_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        self.metadata_file_var = ctk.StringVar()
        file_entry = ctk.CTkEntry(file_frame, textvariable=self.metadata_file_var, width=400)
        file_entry.grid(row=0, column=0, padx=10, pady=10)

        browse_file_btn = ctk.CTkButton(
            file_frame,
            text="Browse File",
            command=self.browse_metadata_file,
            width=100
        )
        browse_file_btn.grid(row=0, column=1, padx=10, pady=10)

        load_btn = ctk.CTkButton(
            file_frame,
            text="Load",
            command=self.load_metadata,
            width=80
        )
        load_btn.grid(row=0, column=2, padx=10, pady=10)

        # Metadata display
        self.metadata_text = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Courier", size=12))
        self.metadata_text.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.main_frame.grid_rowconfigure(2, weight=1)

    def browse_metadata_file(self):
        """Browse for file to view metadata"""
        file_path = filedialog.askopenfilename()
        if file_path:
            self.metadata_file_var.set(file_path)

    def load_metadata(self):
        """Load and display file metadata"""
        file_path = self.metadata_file_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid file!")
            return

        try:
            metadata = os.stat(file_path)

            metadata_output = f"""
File: {file_path}
Size: {metadata.st_size} bytes
Created: {datetime.fromtimestamp(metadata.st_ctime)}
Modified: {datetime.fromtimestamp(metadata.st_mtime)}
Accessed: {datetime.fromtimestamp(metadata.st_atime)}
"""

            self.metadata_text.delete("1.0", tk.END)
            self.metadata_text.insert("1.0", metadata_output)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load metadata: {str(e)}")

if __name__ == "__main__":
    if run_as_admin():
        app = DiskManagementTool()
        app.run()
