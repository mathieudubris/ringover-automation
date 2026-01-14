import time
import sys
import threading
import json
import os
import ctypes
import webbrowser
import win32gui
import win32api
import win32con
import customtkinter as ctk
import subprocess
import requests
from datetime import datetime
from tkinter import messagebox
from pynput import keyboard, mouse
from PIL import Image

# --- CONFIGURATION ---
FIREBASE_API_KEY = "AIzaSyBrHGF359udLSaLuuCCarl4ovzCMYD-HDg"
PROJECT_ID = "mathieu-dubris"
DB_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/licences"
CONFIG_LICENSE = "license.json"
CONFIG_APP = "config_main.json"
APP_ID = "com.mathieu.ringoverautomation"
DEVELOPER_WEBSITE = "https://mathieu-dubris.web.app"
VERSION = "v1.0.4"
UPDATE_DATE = "2026-01-13 22:25"

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except:
    pass

# --- TRADUCTIONS ---
LANGS = {
    "FR": {
        "start": "DÉMARRER", "stop": "STOP", "mini": "Réduire", "maxi": "Agrandir",
        "delay": "Délai automatique (sec)", "cal1": "1. Calibrer [Suivant]",
        "cal2": "2. Calibrer [Couper]", "reset": "Réinitialiser Positions",
        "activation": "ACTIVATION LICENCE", "activate_btn": "VÉRIFIER LA CLÉ", "help_buy": "Besoin d'aide ou d'une licence ?",
        "loading": "Vérification en cours...", "welcome": "Bienvenue", "valid": "Licence valide",
        "guide_title": "GUIDE D'UTILISATION", "back": "RETOUR", "contact": "Contacter le développeur",
        "msg_sys": "NOTIFICATION", "cal_err": "Veuillez calibrer les boutons avant de démarrer.",
        "win_err": "Ringover n'est pas détecté. Veuillez ouvrir le Power Dialer.", "press_ent": "Appuyez sur ENTRER",
        "cal_ok": "CONFIGURÉ", "guide_text": "1. Ouvrez Ringover Power Dialer.\n2. Calibrez Suivant (Bleu) + ENTREE.\n3. Calibrez Couper (Rouge) + ENTREE.\n4. Cliquez sur DÉMARRER.",
        "success_msg": "Activation réussie !\nHeureux de vous revoir,"
    },
    "EN": {
        "start": "START", "stop": "STOP", "mini": "Minimize", "maxi": "Maximize",
        "delay": "Auto Delay (sec)", "cal1": "1. Calibrate [Next]",
        "cal2": "2. Calibrate [Hangup]", "reset": "Reset Positions",
        "activation": "LICENSE ACTIVATION", "activate_btn": "VERIFY KEY", "help_buy": "Need help or a license?",
        "loading": "Checking license...", "welcome": "Welcome", "valid": "Valid license",
        "guide_title": "USER GUIDE", "back": "BACK", "contact": "Contact Developer",
        "msg_sys": "NOTIFICATION", "cal_err": "Please calibrate buttons before starting.",
        "win_err": "Ringover not detected. Please open Power Dialer.", "press_ent": "Press ENTER",
        "cal_ok": "CONFIGURED", "guide_text": "1. Open Ringover Power Dialer.\n2. Calibrate Next (Blue) + ENTER.\n3. Calibrate Hangup (Red) + ENTER.\n4. Click START.",
        "success_msg": "Activation successful!\nWelcome back,"
    }
}

def get_hwid():
    try:
        # Compatible 32/64-bit via WMIC
        cmd = 'wmic cpu get processorid'
        cpu = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        cmd = 'wmic baseboard get serialnumber'
        board = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        return f"{cpu}-{board}"
    except:
        return "ID-UNKNOWN"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ICON_PATH = resource_path("icon.ico")
WINDOW_TITLE_PARTIAL = "Ringover - Power Dialer"

class LicenseManager:
    @staticmethod
    def check_online(key):
        clean_key = key.replace("-", "").upper()
        hwid = get_hwid()
        try:
            url = f"{DB_URL}?key={FIREBASE_API_KEY}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                for doc in documents:
                    fields = doc.get('fields', {})
                    db_key = fields.get('key', {}).get('stringValue')
                    if db_key == clean_key:
                        doc_id = doc['name'].split('/')[-1]
                        db_hwid = fields.get('hwid', {}).get('stringValue', "")
                        db_expires = fields.get('expires', {}).get('stringValue')
                        client_name = fields.get('clientName', {}).get('stringValue', "Client")
                        exp_date = datetime.fromisoformat(db_expires.replace('Z', '+00:00'))
                        days_left = (exp_date.replace(tzinfo=None) - datetime.now()).days
                        if days_left < 0: return False, "Expired", 0, ""
                        if db_hwid == "" or db_hwid == hwid:
                            if db_hwid == "":
                                update_url = f"{DB_URL}/{doc_id}?updateMask.fieldPaths=hwid&key={FIREBASE_API_KEY}"
                                requests.patch(update_url, json={"fields": {"hwid": {"stringValue": hwid}}}, timeout=10)
                            return True, "OK", days_left, client_name
                        return False, "Linked to another PC", 0, ""
                return False, "Invalid Key", 0, ""
            return False, "Server Error", 0, ""
        except: return False, "Connection Error", 0, ""

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.apply_icon()
        width, height = 650, 350
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(fg_color="#123456")
        self.wm_attributes("-transparentcolor", "#123456")
        
        self.container = ctk.CTkFrame(self, corner_radius=30, fg_color="#1a1a1a", border_width=2, border_color="#333333")
        self.container.pack(fill="both", expand=True)
        
        content = ctk.CTkFrame(self.container, fg_color="transparent")
        content.place(relx=0.5, rely=0.45, anchor="center")
        
        if os.path.exists(ICON_PATH):
            img = Image.open(ICON_PATH)
            logo_img = ctk.CTkImage(img, size=(120, 120))
            ctk.CTkLabel(content, image=logo_img, text="").pack(side="left", padx=(0, 25))
            
        ctk.CTkLabel(content, text="RINGOVER\nAUTOMATION", font=("Verdana", 32, "bold"), justify="left", text_color="#f0f0f0").pack(side="left")
        
        self.info_left = ctk.CTkLabel(self.container, text=f"{VERSION} — Updated: {UPDATE_DATE}", font=("Helvetica", 10), text_color="#777777")
        self.info_left.place(relx=0.05, rely=0.88, anchor="w")
        
        ctk.CTkLabel(self.container, text="Powered by Mathieu Dubris", font=("Helvetica", 10, "italic"), text_color="#777777").place(relx=0.95, rely=0.88, anchor="e")
        
        self.fade_in()

    def apply_icon(self):
        if os.path.exists(ICON_PATH):
            self.after(200, lambda: self.iconbitmap(ICON_PATH))

    def fade_in(self):
        alpha = self.attributes("-alpha")
        if alpha < 1.0:
            self.attributes("-alpha", alpha + 0.1)
            self.after(30, self.fade_in)

class RingoverApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("Ringover Automation")
        self.geometry("400x600")
        self.resizable(False, False)
        self.apply_icon()
        
        self.lang = "FR"
        self.rel_auto_x = self.rel_auto_y = self.rel_manual_x = self.rel_manual_y = 0
        self.custom_hotkey = "middle"
        self.is_running = self.is_mini = False
        self.load_settings()

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.notice_container = ctk.CTkFrame(self, fg_color="transparent")
        self.license_container = ctk.CTkFrame(self, fg_color="#e0e0e0") # Couleur modifiée ici
        self.notif_container = ctk.CTkFrame(self, fg_color="transparent")
        
        self.build_all_uis()
        self.show_splash()

    def apply_icon(self):
        if os.path.exists(ICON_PATH):
            self.after(200, lambda: self.iconbitmap(ICON_PATH))

    def adjust_window_size(self):
        self.update_idletasks()
        if self.is_mini: return
        
        active_container = None
        if self.main_container.winfo_viewable(): active_container = self.main_container
        elif self.license_container.winfo_viewable(): active_container = self.license_container
        elif self.notice_container.winfo_viewable(): active_container = self.notice_container
        elif self.notif_container.winfo_viewable(): active_container = self.notif_container
        
        if active_container:
            req_h = active_container.winfo_reqheight() + 40
            self.geometry(f"400x{max(req_h, 450)}")

    def build_all_uis(self):
        self.build_license_ui()
        self.build_main_ui()
        self.build_notice_ui()

    def switch_lang(self):
        self.lang = "EN" if self.lang == "FR" else "FR"
        for child in self.main_container.winfo_children(): child.destroy()
        for child in self.notice_container.winfo_children(): child.destroy()
        for child in self.license_container.winfo_children(): child.destroy()
        self.build_all_uis()
        if self.license_container.winfo_viewable():
            self.license_container.pack(fill="both", expand=True)
        elif self.notice_container.winfo_viewable():
            self.notice_container.pack(fill="both", expand=True)
        else:
            self.main_container.pack(fill="both", expand=True)
        self.adjust_window_size()

    def show_splash(self):
        self.splash = SplashScreen(self)
        threading.Thread(target=self.security_check, daemon=True).start()

    def security_check(self):
        time.sleep(2)
        key = None
        if os.path.exists(CONFIG_LICENSE):
            try:
                with open(CONFIG_LICENSE, "r") as f: key = json.load(f).get("key")
            except: pass
        
        if key:
            success, msg, days, client = LicenseManager.check_online(key)
            if success:
                self.after(0, self.start_app)
            else: self.after(0, self.show_license)
        else: self.after(0, self.show_license)

    def show_notification(self, message, next_action=None, is_success=False):
        if hasattr(self, 'splash'): self.splash.destroy()
        self.deiconify()
        
        if self.is_mini: self.toggle_mini_mode()
            
        self.main_container.pack_forget()
        self.license_container.pack_forget()
        self.notice_container.pack_forget()
        
        for child in self.notif_container.winfo_children(): child.destroy()
        self.notif_container.pack(expand=True, fill="both")
        
        # UI Améliorée pour le succès/bienvenue
        color = "#27ae60" if is_success else "#3b82f6"
        title = LANGS[self.lang]["welcome"] if is_success else LANGS[self.lang]["msg_sys"]
        
        ctk.CTkLabel(self.notif_container, text=title, font=("Verdana", 26, "bold"), text_color=color).pack(pady=(60, 10))
        
        # Séparateur visuel
        line = ctk.CTkFrame(self.notif_container, height=2, width=200, fg_color=color)
        line.pack(pady=10)

        ctk.CTkLabel(self.notif_container, text=message, font=("Helvetica", 16), wraplength=320, justify="center", text_color="#FFFFFF").pack(pady=20)
        
        def on_ok():
            self.notif_container.pack_forget()
            if next_action: next_action()
            else: self.show_main()

        ctk.CTkButton(self.notif_container, text="DÉMARRER" if is_success else "OK", width=180, height=45, corner_radius=10, font=("Helvetica", 14, "bold"), command=on_ok, fg_color=color).pack(pady=30)
        self.adjust_window_size()

    def show_license(self):
        if hasattr(self, 'splash'): self.splash.destroy()
        self.deiconify()
        self.license_container.pack(fill="both", expand=True)
        self.adjust_window_size()

    def start_app(self):
        if hasattr(self, 'splash'): self.splash.destroy()
        self.deiconify()
        self.show_main()
        self.start_listeners()

    def build_license_ui(self):
        # Header Langue
        lang_btn = ctk.CTkButton(self.license_container, text=f"{self.lang}", width=50, height=25, command=self.switch_lang, fg_color="#333")
        lang_btn.pack(anchor="ne", padx=20, pady=20)

        ctk.CTkLabel(self.license_container, text=LANGS[self.lang]["activation"], font=("Verdana", 24, "bold"), text_color="#1a1a1a").pack(pady=(10, 30))
        
        card = ctk.CTkFrame(self.license_container, fg_color="#1a1a1a", corner_radius=20, border_width=1, border_color="#cccccc")
        card.pack(padx=30, fill="x")

        self.license_entry = ctk.CTkEntry(card, width=280, height=50, placeholder_text="XXXX-XXXX-XXXX-XXXX", justify="center", font=("Consolas", 16), fg_color="#000", border_color="#444")
        self.license_entry.pack(pady=(30, 10), padx=20)
        
        # Barre de chargement plus fine et en chargement continu (déterminé)
        self.lic_loader = ctk.CTkProgressBar(card, width=280, height=4, mode="determinate", progress_color="#3b82f6", fg_color="#333")
        self.lic_loader.set(0)
        
        self.lic_status = ctk.CTkLabel(card, text="", font=("Helvetica", 12))
        self.lic_status.pack(pady=5)

        self.btn_activate = ctk.CTkButton(card, text=LANGS[self.lang]["activate_btn"], height=50, width=280, font=("Helvetica", 14, "bold"), fg_color="#27ae60", hover_color="#2ecc71", command=self.validate_license_ui)
        self.btn_activate.pack(pady=(10, 30), padx=20)

        ctk.CTkButton(self.license_container, text=LANGS[self.lang]["help_buy"], fg_color="transparent", text_color="#555", font=("Helvetica", 12, "underline"), command=lambda: webbrowser.open(DEVELOPER_WEBSITE)).pack(pady=20)

    def animate_progress(self, current_val):
        if current_val <= 1.0 and self.is_validating:
            self.lic_loader.set(current_val)
            self.after(30, lambda: self.animate_progress(current_val + 0.02))

    def validate_license_ui(self):
        key = self.license_entry.get().strip()
        if not key: return
        
        self.is_validating = True
        self.btn_activate.configure(state="disabled")
        self.lic_loader.pack(pady=5)
        self.lic_loader.set(0)
        self.animate_progress(0)
        self.lic_status.configure(text=LANGS[self.lang]["loading"], text_color="#3b82f6")
        
        def process():
            success, msg, days, client = LicenseManager.check_online(key)
            time.sleep(1.2) # Pour laisser l'animation se voir
            self.is_validating = False
            
            self.after(0, lambda: self.lic_loader.pack_forget())
            
            if success:
                self.after(0, lambda: self.lic_status.configure(text=LANGS[self.lang]["valid"], text_color="#27ae60"))
                with open(CONFIG_LICENSE, "w") as f: json.dump({"key": key, "client": client}, f)
                welcome_txt = f"{LANGS[self.lang]['success_msg']} {client}!"
                self.after(500, lambda: self.show_notification(welcome_txt, self.start_app, is_success=True))
            else:
                self.after(0, lambda: [self.lic_status.configure(text=msg, text_color="#e74c3c"), self.btn_activate.configure(state="normal")])

        threading.Thread(target=process, daemon=True).start()

    def build_main_ui(self):
        header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkButton(header, text=f"{self.lang}", width=50, command=self.switch_lang, fg_color="#333").pack(side="left", padx=2)
        ctk.CTkButton(header, text="Notice", width=70, fg_color="#333", command=self.show_notice).pack(side="left", padx=2)
        
        self.mini_btn = ctk.CTkButton(header, text=LANGS[self.lang]["mini"], width=80, fg_color="#34495e", command=self.toggle_mini_mode)
        self.mini_btn.pack(side="right")

        self.main_btn = ctk.CTkButton(self.main_container, text=LANGS[self.lang]["start"], width=300, height=60, corner_radius=15, font=("Helvetica", 18, "bold"), fg_color="#27ae60", command=self.start_dialer)
        self.main_btn.pack(pady=20)

        self.settings_pane = ctk.CTkFrame(self.main_container, fg_color="#222222", corner_radius=15)
        self.settings_pane.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(self.settings_pane, text=LANGS[self.lang]["delay"], font=("Helvetica", 12, "bold")).pack(pady=(10,0))
        self.time_menu = ctk.CTkOptionMenu(self.settings_pane, values=["3", "5", "10", "20", "60"], fg_color="#333")
        self.time_menu.set("3")
        self.time_menu.pack(pady=10)

        hk_frame = ctk.CTkFrame(self.settings_pane, fg_color="transparent")
        hk_frame.pack(pady=5)
        self.hotkey_btn = ctk.CTkButton(hk_frame, text=f"Key : {self.custom_hotkey}", width=120, fg_color="#8e44ad", command=self.record_hotkey_thread)
        self.hotkey_btn.pack(side="left", padx=5)
        
        self.reset_hk_btn = ctk.CTkButton(hk_frame, text="↺", width=30, fg_color="#444", command=self.reset_hotkey_to_middle)
        self.reset_hk_btn.pack(side="left", padx=2)

        self.calib_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.calib_frame.pack(fill="x", padx=20, pady=10)
        self.btn_auto = ctk.CTkButton(self.calib_frame, text=LANGS[self.lang]["cal1"], height=40, command=lambda: self.start_calibration("auto"))
        self.btn_auto.pack(fill="x", pady=5)
        self.btn_manual = ctk.CTkButton(self.calib_frame, text=LANGS[self.lang]["cal2"], height=40, command=lambda: self.start_calibration("manual"))
        self.btn_manual.pack(fill="x", pady=5)
        
        ctk.CTkButton(self.calib_frame, text=LANGS[self.lang]["reset"], fg_color="#c0392b", height=30, command=self.reset_calibration).pack(pady=10)
        self.update_calib_ui()

    def build_notice_ui(self):
        nav = ctk.CTkFrame(self.notice_container, fg_color="transparent")
        nav.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(nav, text=LANGS[self.lang]["back"], width=80, fg_color="#444", command=self.show_main).pack(side="left")
        
        ctk.CTkLabel(self.notice_container, text=LANGS[self.lang]["guide_title"], font=("Helvetica", 18, "bold"), text_color="#3b82f6").pack(pady=10)
        ctk.CTkLabel(self.notice_container, text=LANGS[self.lang]["guide_text"], justify="left", font=("Helvetica", 12)).pack(padx=20, pady=10)
        
        ctk.CTkButton(self.notice_container, text=LANGS[self.lang]["contact"], fg_color="#3b82f6", command=lambda: webbrowser.open(DEVELOPER_WEBSITE)).pack(pady=20)

    def reset_hotkey_to_middle(self):
        self.custom_hotkey = "middle"
        self.hotkey_btn.configure(text=f"Key : middle")
        self.save_settings()

    def reset_calibration(self):
        self.rel_auto_x = self.rel_auto_y = self.rel_manual_x = self.rel_manual_y = 0
        self.save_settings()
        self.update_calib_ui()

    def show_notice(self):
        self.main_container.pack_forget()
        self.notice_container.pack(fill="both", expand=True)
        self.adjust_window_size()

    def show_main(self):
        self.notice_container.pack_forget()
        self.notif_container.pack_forget()
        self.main_container.pack(fill="both", expand=True)
        self.adjust_window_size()

    def toggle_mini_mode(self):
        if not self.is_mini:
            self.settings_pane.pack_forget()
            self.calib_frame.pack_forget()
            self.geometry("280x140")
            self.attributes("-topmost", True)
            self.mini_btn.configure(text=LANGS[self.lang]["maxi"])
            self.is_mini = True
        else:
            self.is_mini = False
            self.attributes("-topmost", False)
            self.mini_btn.configure(text=LANGS[self.lang]["mini"])
            self.settings_pane.pack(fill="x", padx=20, pady=5)
            self.calib_frame.pack(fill="x", padx=20, pady=10)
            self.adjust_window_size()

    def start_calibration(self, mode):
        hwnd = self.find_ringover_window()
        if not hwnd:
            self.show_notification(LANGS[self.lang]["win_err"])
            return
            
        btn = self.btn_auto if mode == "auto" else self.btn_manual
        btn.configure(text=LANGS[self.lang]["press_ent"], fg_color="#e67e22")
        threading.Thread(target=self.run_calibration, args=(mode,), daemon=True).start()

    def run_calibration(self, mode):
        hwnd = self.find_ringover_window()
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        with keyboard.Events() as events:
            for e in events:
                if isinstance(e, keyboard.Events.Press) and e.key == keyboard.Key.enter:
                    x, y = win32api.GetCursorPos()
                    if mode == "auto": self.rel_auto_x, self.rel_auto_y = (x-rect[0])/w, (y-rect[1])/h
                    else: self.rel_manual_x, self.rel_manual_y = (x-rect[0])/w, (y-rect[1])/h
                    self.save_settings()
                    self.after(0, self.update_calib_ui)
                    break

    def update_calib_ui(self):
        status = LANGS[self.lang]["cal_ok"]
        self.btn_auto.configure(text=f"{status}" if self.rel_auto_x else LANGS[self.lang]["cal1"], fg_color="#27ae60" if self.rel_auto_x else "#333")
        self.btn_manual.configure(text=f"{status}" if self.rel_manual_x else LANGS[self.lang]["cal2"], fg_color="#27ae60" if self.rel_manual_x else "#333")

    def start_dialer(self):
        if not self.rel_auto_x:
            self.show_notification(LANGS[self.lang]["cal_err"])
            return
            
        if not self.find_ringover_window():
            self.show_notification(LANGS[self.lang]["win_err"])
            return

        self.is_running = not self.is_running
        self.main_btn.configure(text=LANGS[self.lang]["stop"] if self.is_running else LANGS[self.lang]["start"], fg_color="#c0392b" if self.is_running else "#27ae60")
        if self.is_running: threading.Thread(target=self.auto_loop, daemon=True).start()

    def auto_loop(self):
        while self.is_running:
            hwnd = self.find_ringover_window()
            if hwnd: self.background_click(hwnd, self.rel_auto_x, self.rel_auto_y)
            time.sleep(int(self.time_menu.get()))

    def background_click(self, hwnd, rx, ry):
        rect = win32gui.GetWindowRect(hwnd)
        l = win32api.MAKELONG(int(rx*(rect[2]-rect[0])), int(ry*(rect[3]-rect[1])))
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, l)

    def find_ringover_window(self):
        hwnds = []
        win32gui.EnumWindows(lambda h, _: hwnds.append(h) if WINDOW_TITLE_PARTIAL in win32gui.GetWindowText(h) and win32gui.IsWindowVisible(h) else None, None)
        return hwnds[0] if hwnds else None

    def start_listeners(self):
        def on_press(key):
            if self.is_running and str(key).replace("Key.", "").replace("'", "") == self.custom_hotkey:
                self.trigger_manual()
        def on_click(x, y, button, pressed):
            if pressed and self.is_running and self.custom_hotkey == "middle" and button == mouse.Button.middle:
                self.trigger_manual()
        threading.Thread(target=lambda: keyboard.Listener(on_press=on_press).start(), daemon=True).start()
        threading.Thread(target=lambda: mouse.Listener(on_click=on_click).start(), daemon=True).start()

    def trigger_manual(self):
        hwnd = self.find_ringover_window()
        if hwnd and self.rel_manual_x: self.background_click(hwnd, self.rel_manual_x, self.rel_manual_y)

    def record_hotkey_thread(self):
        def record():
            self.hotkey_btn.configure(text="...", fg_color="#e67e22")
            with keyboard.Events() as events:
                for e in events:
                    if isinstance(e, keyboard.Events.Press):
                        self.custom_hotkey = str(e.key).replace("Key.", "").replace("'", "")
                        self.save_settings()
                        break
            self.hotkey_btn.configure(text=f"Key : {self.custom_hotkey}", fg_color="#8e44ad")
        threading.Thread(target=record, daemon=True).start()

    def save_settings(self):
        with open(CONFIG_APP, "w") as f:
            json.dump({"ax": self.rel_auto_x, "ay": self.rel_auto_y, "mx": self.rel_manual_x, "my": self.rel_manual_y, "hk": self.custom_hotkey, "lg": self.lang}, f)

    def load_settings(self):
        if os.path.exists(CONFIG_APP):
            try:
                with open(CONFIG_APP, "r") as f:
                    d = json.load(f)
                    self.rel_auto_x, self.rel_auto_y = d.get("ax", 0), d.get("ay", 0)
                    self.rel_manual_x, self.rel_manual_y = d.get("mx", 0), d.get("my", 0)
                    self.custom_hotkey = d.get("hk", "middle")
                    self.lang = d.get("lg", "FR")
            except: pass

if __name__ == "__main__":
    app = RingoverApp()
    app.mainloop()