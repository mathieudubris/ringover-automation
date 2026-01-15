import time
import sys
import threading
import json
import os
import csv
import customtkinter as ctk
import win32gui
import win32api
import win32con
from tkinter import filedialog, messagebox
from pynput import keyboard
from PIL import Image, ImageGrab

# --- CONFIGURATION ---
CONFIG_APP = "config_dialer_v3.json"

class CSVDialerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CSV Auto Dialer - Pro Version")
        self.geometry("1150x750")
        
        # Données de session
        self.csv_data = []
        self.csv_headers = []
        self.current_index = 0
        self.phone_column = None
        self.is_running = False
        self.current_tags = {} 

        # Positions Ringover
        self.rel_paste_x = self.rel_paste_y = 0
        self.rel_call_x = self.rel_call_y = 0
        
        self.load_settings()
        self.build_ui()

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0) 
        self.grid_rowconfigure(0, weight=1)

        # --- ZONE GAUCHE (CONTRÔLE) ---
        self.left_panel = ctk.CTkFrame(self, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Header / Chargement
        self.frame_top = ctk.CTkFrame(self.left_panel, fg_color="#1a1a1a")
        self.frame_top.pack(fill="x", padx=10, pady=10)
        
        self.btn_load_csv = ctk.CTkButton(self.frame_top, text="📂 CHARGER CSV", command=self.load_csv, fg_color="#3b82f6")
        self.btn_load_csv.pack(side="left", padx=10, pady=10)
        
        self.column_menu = ctk.CTkOptionMenu(self.frame_top, values=["Choisir Colonne"], command=self.on_column_selected)
        self.column_menu.pack(side="left", padx=10, pady=10)

        self.btn_dev = ctk.CTkButton(self.frame_top, text="🛠 DEV", width=60, fg_color="#444", command=self.show_dev_panel)
        self.btn_dev.pack(side="right", padx=10)

        # Zone Calibration
        self.frame_calib = ctk.CTkFrame(self.left_panel, fg_color="#222")
        self.frame_calib.pack(fill="x", padx=10, pady=5)
        self.btn_cal_p = ctk.CTkButton(self.frame_calib, text="Calibrer Saisie", command=lambda: self.start_calib("paste"))
        self.btn_cal_p.pack(side="left", expand=True, padx=10, pady=5)
        self.btn_cal_c = ctk.CTkButton(self.frame_calib, text="Calibrer Appel", command=lambda: self.start_calib("call"))
        self.btn_cal_c.pack(side="left", expand=True, padx=5, pady=5)

        # --- ZONE TAGS ---
        self.tag_label = ctk.CTkLabel(self.left_panel, text="QUALIFICATION DE L'APPEL", font=("Verdana", 12, "bold"))
        self.tag_label.pack(pady=(20, 5))
        
        self.frame_tags = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.frame_tags.pack(fill="x", padx=20)

        tags_config = [
            ("Répondeur", "yellow", "black"),
            ("Pas intéressé", "#e74c3c", "white"),
            ("Hors cible", "#fd79a8", "white"),
            ("Non attribué", "#e67e22", "white"),
            ("Faux numéro", "#8b4513", "white"),
            ("Rappel", "#3498db", "white"),
            ("RDV", "#2ecc71", "white")
        ]

        for text, color, tcolor in tags_config:
            btn = ctk.CTkButton(self.frame_tags, text=text, fg_color=color, text_color=tcolor, 
                                 hover_color=color, command=lambda t=text: self.set_tag(t))
            btn.pack(fill="x", pady=2, padx=5)

        # Bouton Start / Download
        self.btn_start = ctk.CTkButton(self.left_panel, text="▶ DÉMARRER LA CAMPAGNE", height=60,
                                       font=("Helvetica", 16, "bold"), fg_color="#27ae60",
                                       command=self.toggle_campaign)
        self.btn_start.pack(fill="x", padx=20, pady=20)

        self.btn_download = ctk.CTkButton(self.left_panel, text="💾 TÉLÉCHARGER RÉSULTATS (CSV)", 
                                           fg_color="#8e44ad", command=self.download_results, state="disabled")
        self.btn_download.pack(fill="x", padx=20, pady=5)

        # --- PANNEAU DROITE (INFOS CLIENT) ---
        self.right_panel = ctk.CTkFrame(self, width=400, fg_color="#111")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.right_panel, text="INFOS CONTACT", font=("Verdana", 14, "bold"), text_color="#3b82f6").pack(pady=10)
        
        self.info_scroll = ctk.CTkScrollableFrame(self.right_panel, width=380, height=600, fg_color="transparent")
        self.info_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # --- OVERLAY DEV (TERMINAL) ---
        self.dev_overlay = ctk.CTkFrame(self, fg_color="#000")
        self.txt_info = ctk.CTkTextbox(self.dev_overlay, fg_color="#000", font=("Consolas", 11), text_color="#0f0")
        self.txt_info.pack(fill="both", expand=True, padx=10, pady=10)
        self.btn_close_dev = ctk.CTkButton(self.dev_overlay, text="FERMER CONSOLE", command=self.hide_dev_panel)
        self.btn_close_dev.pack(pady=5)

        self.update_calib_ui()

    def show_dev_panel(self):
        self.dev_overlay.place(relx=0.5, rely=0.5, relwidth=0.9, relheight=0.8, anchor="center")

    def hide_dev_panel(self):
        self.dev_overlay.place_forget()

    def set_tag(self, tag_name):
        if self.current_index < len(self.csv_data):
            self.current_tags[self.current_index] = tag_name
            self.update_console(f"Ligne {self.current_index + 1} tagguée : {tag_name}")
            self.tag_label.configure(text=f"TAG ACTUEL : {tag_name}", text_color="#2ecc71")

    def display_contact_info(self, contact):
        for widget in self.info_scroll.winfo_children():
            widget.destroy()
        
        for key, value in contact.items():
            f = ctk.CTkFrame(self.info_scroll, fg_color="#1e1e1e")
            f.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(f, text=f"{key}:", font=("Arial", 10, "bold"), text_color="#5fa8ff").pack(anchor="w", padx=5)
            ctk.CTkLabel(f, text=f"{value}", font=("Arial", 12), wraplength=340, justify="left").pack(anchor="w", padx=10, pady=(0,5))

    def load_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.csv_headers = reader.fieldnames
                self.csv_data = list(reader)
            
            self.column_menu.configure(values=self.csv_headers)
            self.column_menu.set(self.csv_headers[0])
            self.phone_column = self.csv_headers[0]
            
            # Reset pour nouvelle campagne
            self.current_index = 0
            self.current_tags = {}
            self.is_running = False
            self.btn_start.configure(text="▶ DÉMARRER LA CAMPAGNE", fg_color="#27ae60", state="normal")
            self.btn_download.configure(state="disabled")
            self.update_console(f"Nouveau CSV chargé. Prêt pour ligne 1.")
            self.display_contact_info(self.csv_data[0])
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def download_results(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            headers = self.csv_headers + ["Qualification_Appel"]
            with open(path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for i, row in enumerate(self.csv_data):
                    row["Qualification_Appel"] = self.current_tags.get(i, "Non qualifié")
                    writer.writerow(row)
            messagebox.showinfo("Succès", "Fichier sauvegardé avec les tags !")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def start_calib(self, mode):
        hwnd = self.find_ringover_window()
        if not hwnd: 
            messagebox.showerror("Erreur", "Ouvrez Ringover")
            return
        self.update_console(f"Calibration {mode}... Placez la souris et tapez ENTRER")
        threading.Thread(target=self.run_calib, args=(mode, hwnd), daemon=True).start()

    def run_calib(self, mode, hwnd):
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        with keyboard.Events() as events:
            for e in events:
                if isinstance(e, keyboard.Events.Press) and e.key == keyboard.Key.enter:
                    x, y = win32api.GetCursorPos()
                    if mode == "paste":
                        self.rel_paste_x, self.rel_paste_y = (x-rect[0])/w, (y-rect[1])/h
                    else:
                        self.rel_call_x, self.rel_call_y = (x-rect[0])/w, (y-rect[1])/h
                    self.save_settings()
                    self.after(0, self.update_calib_ui)
                    break

    def toggle_campaign(self):
        if not self.is_running:
            if not self.csv_data: 
                messagebox.showwarning("Info", "Chargez un CSV d'abord")
                return
            self.is_running = True
            self.btn_start.configure(text="STOP / PAUSE", fg_color="#c0392b")
            threading.Thread(target=self.campaign_loop, daemon=True).start()
        else:
            self.is_running = False
            self.btn_start.configure(text="▶ REPRENDRE LA CAMPAGNE", fg_color="#27ae60")

    def campaign_loop(self):
        while self.is_running and self.current_index < len(self.csv_data):
            contact = self.csv_data[self.current_index]
            self.after(0, lambda c=contact: self.display_contact_info(c))
            
            phone = str(contact.get(self.phone_column, "")).strip()
            hwnd = self.find_ringover_window()
            
            if hwnd and phone:
                self.update_console(f"Traitement ligne {self.current_index + 1} : {phone}")
                self.after(0, lambda: self.tag_label.configure(text="QUALIFICATION DE L'APPEL", text_color="white"))
                
                # 1. Taper le numéro
                self.clean_and_type(hwnd, phone)
                time.sleep(0.4)
                
                # 2. Cliquer sur Appel
                self.background_click(hwnd, self.rel_call_x, self.rel_call_y)
                
                # 3. Attendre la fin
                self.wait_for_call_end(hwnd)
                
                # 4. Petit temps pour le tag final
                time.sleep(1.2)
                
                self.current_index += 1
            else:
                self.current_index += 1
                
        if self.current_index >= len(self.csv_data):
            self.is_running = False
            self.after(0, self.finish_campaign)

    def finish_campaign(self):
        self.btn_start.configure(text="✓ CAMPAGNE TERMINÉE", fg_color="#2c3e50", state="disabled")
        self.btn_download.configure(state="normal")
        messagebox.showinfo("Fini", "Tous les contacts ont été appelés. Vous pouvez télécharger le rapport.")

    def update_console(self, text):
        self.txt_info.configure(state="normal")
        self.txt_info.insert("end", f"[{time.strftime('%H:%M:%S')}] {text}\n")
        self.txt_info.see("end")
        self.txt_info.configure(state="disabled")

    def find_ringover_window(self):
        hwnds = []
        def cb(h, _):
            if "Ringover" in win32gui.GetWindowText(h) and win32gui.IsWindowVisible(h):
                hwnds.append(h)
        win32gui.EnumWindows(cb, None)
        return hwnds[0] if hwnds else None

    def clean_and_type(self, hwnd, text):
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        l = win32api.MAKELONG(int(self.rel_paste_x*w), int(self.rel_paste_y*h))
        
        # Clic pour focus
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, l)
        time.sleep(0.1)
        
        # Sélection totale et suppression propre
        win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_CONTROL, 0)
        win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, ord('A'), 0)
        time.sleep(0.05)
        win32gui.SendMessage(hwnd, win32con.WM_KEYUP, ord('A'), 0)
        win32gui.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_CONTROL, 0)
        time.sleep(0.05)
        win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_DELETE, 0)
        win32gui.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_DELETE, 0)
        time.sleep(0.1)
        
        # Saisie du texte
        for char in text:
            win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
            time.sleep(0.01)

    def background_click(self, hwnd, rx, ry):
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2]-rect[0], rect[3]-rect[1]
        l = win32api.MAKELONG(int(rx*w), int(ry*h))
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l)
        time.sleep(0.05)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, l)

    def wait_for_call_end(self, hwnd):
        is_calling = False
        for _ in range(25): # Attente démarrage
            if not self.is_running: return
            if self.is_button_red(hwnd):
                is_calling = True
                break
            time.sleep(0.5)
        if is_calling:
            while self.is_running and self.is_button_red(hwnd):
                time.sleep(0.8)

    def is_button_red(self, hwnd):
        try:
            rect = win32gui.GetWindowRect(hwnd)
            x = int(rect[0] + self.rel_call_x * (rect[2] - rect[0]))
            y = int(rect[1] + self.rel_call_y * (rect[3] - rect[1]))
            pixel = ImageGrab.grab((x, y, x+1, y+1)).getpixel((0,0))
            return pixel[0] > 160 and pixel[1] < 100 # Détection du rouge
        except: return False

    def update_calib_ui(self):
        if self.rel_paste_x > 0: 
            self.btn_cal_p.configure(fg_color="#27ae60", text="Saisie OK")
        if self.rel_call_x > 0: 
            self.btn_cal_c.configure(fg_color="#27ae60", text="Appel OK")

    def on_column_selected(self, choice):
        self.phone_column = choice

    def save_settings(self):
        with open(CONFIG_APP, "w") as f:
            json.dump({"px": self.rel_paste_x, "py": self.rel_paste_y, "cx": self.rel_call_x, "cy": self.rel_call_y}, f)

    def load_settings(self):
        if os.path.exists(CONFIG_APP):
            try:
                with open(CONFIG_APP, "r") as f:
                    d = json.load(f)
                    self.rel_paste_x, self.rel_paste_y = d.get("px", 0), d.get("py", 0)
                    self.rel_call_x, self.rel_call_y = d.get("cx", 0), d.get("cy", 0)
            except: pass

if __name__ == "__main__":
    app = CSVDialerApp()
    app.mainloop()