"""Interface graphique inclusive avec Tkinter - version Philippe.

Tkinter est natif a Python : pas besoin d'installer PySide6.
Adaptations pour Philippe :
- Pas d'interface visuelle a regarder comme declencheur principal
- Backup clavier 4 touches : O, F, P, Escape
- Mode securite : IDLE remappe en CLOSE par defaut
- OPEN autorise uniquement s'il est stable
- Affichage du mode source EEG (simulateur / lsl / gpype)
- Profils d'activite : main_robot, cerf_volant, sport
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import time
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np

from inclusive_maker.acquisition.eeg_source import UnifiedEEGSource
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.brain_algo.safety_controller import SafetyController
from inclusive_maker.remote_command.client import CommandClient
from inclusive_maker.remote_command.protocol import CommandPacket
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS
from inclusive_maker.shared.logger import get_logger

logger = get_logger(__name__)

# Palette accessible
COLORS = {
    "OPEN": "#4FC3F7",
    "CLOSE": "#FF9800",
    "IDLE": "#9E9E9E",
    "OK": "#2E7D32",
    "WARN": "#F57C00",
    "ERROR": "#D32F2F",
    "BG": "#F5F5F5",
    "TEXT": "#212121",
}

ICONS = {"OPEN": "✋", "CLOSE": "✊", "IDLE": "⏸"}

LARGE_FONT = ("Arial", 18)
TITLE_FONT = ("Arial", 24, "bold")
STATUS_FONT = ("Arial", 28, "bold")
BIG_BUTTON_FONT = ("Arial", 22, "bold")

DEMO_CYCLE_SECONDS = 12
MANUAL_SOURCE = "manuel"
EMERGENCY_SOURCE = "urgence"
AUTO_SOURCE = "auto"


class InclusiveAppTk:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inclusive Maker - Commande cerebrale (Philippe)")
        self.root.geometry("900x800")
        self.root.configure(bg=COLORS["BG"])

        self.eeg_source = UnifiedEEGSource()
        self.detector = MentalStateDetector()
        self.safety = SafetyController(safe_mode=True, idle_is_safe=False)
        self.mapper = CommandMapper(profile="main_robot")
        self.client = CommandClient()

        self.current_state = tk.StringVar(value="IDLE")
        self.status_text = tk.StringVar(value="Pret")
        self.last_cmd_message = tk.StringVar(value="Aucune commande envoyee")
        self.auto_control_active = False
        self.emergency_active = False
        self._demo_timer = 0.0

        self._build_ui()
        self._bind_keyboard()

        self.update_job = None

    def _build_ui(self):
        title = tk.Label(
            self.root,
            text="Inclusive Maker - Commande cerebrale (Philippe)",
            font=TITLE_FONT,
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
        )
        title.pack(pady=10)

        self.source_bar = tk.Frame(self.root, bg=COLORS["BG"])
        self.source_bar.pack(fill="x", padx=20, pady=5)

        mode = self.eeg_source.get_mode()
        self.source_label = tk.Label(
            self.source_bar,
            text=f"Source EEG : {mode.upper()}",
            font=("Arial", 14, "bold"),
            bg=self._source_color(mode),
            fg="white",
            padx=10,
            pady=5,
        )
        self.source_label.pack(side="left")

        self.safe_mode_var = tk.BooleanVar(value=True)
        self.safe_check = tk.Checkbutton(
            self.source_bar,
            text="Mode securite : fermer si incertain",
            variable=self.safe_mode_var,
            font=("Arial", 14),
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
            command=self._toggle_safe_mode,
        )
        self.safe_check.pack(side="left", padx=20)

        tk.Label(self.source_bar, text="Profil :", font=("Arial", 14), bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(side="left")
        self.profile_var = tk.StringVar(value="main_robot")
        self.profile_combo = ttk.Combobox(
            self.source_bar,
            textvariable=self.profile_var,
            values=["main_robot", "cerf_volant", "sport"],
            font=("Arial", 14),
            state="readonly",
            width=12,
        )
        self.profile_combo.pack(side="left", padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_changed)

        self.step_label = tk.Label(self.root, text="Etape 1 / 4 : Accueil", font=LARGE_FONT, bg=COLORS["BG"], fg="#616161")
        self.step_label.pack(pady=5)

        self.pages = ttk.Notebook(self.root)
        self.pages.pack(fill="both", expand=True, padx=20, pady=10)
        self.pages.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.tab_welcome = self._create_welcome_tab()
        self.tab_calib = self._create_calibration_tab()
        self.tab_train = self._create_training_tab()
        self.tab_control = self._create_control_tab()

        self.pages.add(self.tab_welcome, text="1. Accueil")
        self.pages.add(self.tab_calib, text="2. Calibration")
        self.pages.add(self.tab_train, text="3. Entrainement")
        self.pages.add(self.tab_control, text="4. Controle")

        manual_frame = tk.LabelFrame(self.root, text="Commandes manuelles", font=LARGE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"])
        manual_frame.pack(fill="x", padx=20, pady=10)

        manual_btns = tk.Frame(manual_frame, bg=COLORS["BG"])
        manual_btns.pack(pady=10)

        self.btn_manual_open = tk.Button(
            manual_btns,
            text="O\nOUVRIR",
            font=BIG_BUTTON_FONT,
            bg=COLORS["OPEN"],
            fg="white",
            width=8,
            height=2,
            command=self._manual_open,
        )
        self.btn_manual_open.pack(side="left", padx=10)

        self.btn_manual_close = tk.Button(
            manual_btns,
            text="F\nFERMER",
            font=BIG_BUTTON_FONT,
            bg=COLORS["CLOSE"],
            fg="white",
            width=8,
            height=2,
            command=self._manual_close,
        )
        self.btn_manual_close.pack(side="left", padx=10)

        self.btn_manual_pause = tk.Button(
            manual_btns,
            text="P\nPAUSE",
            font=BIG_BUTTON_FONT,
            bg=COLORS["IDLE"],
            fg="white",
            width=8,
            height=2,
            command=self._manual_pause,
        )
        self.btn_manual_pause.pack(side="left", padx=10)

        self.btn_manual_emergency = tk.Button(
            manual_btns,
            text="ECHAP\nURGENCE",
            font=BIG_BUTTON_FONT,
            bg=COLORS["ERROR"],
            fg="white",
            width=10,
            height=2,
            command=self._emergency_stop,
        )
        self.btn_manual_emergency.pack(side="left", padx=10)

        self.cmd_message_label = tk.Label(
            self.root,
            textvariable=self.last_cmd_message,
            font=("Arial", 16, "bold"),
            bg="white",
            fg=COLORS["TEXT"],
            padx=10,
            pady=5,
        )
        self.cmd_message_label.pack(fill="x", padx=20, pady=5)

        nav = tk.Frame(self.root, bg=COLORS["BG"])
        nav.pack(fill="x", padx=20, pady=10)

        self.btn_prev = tk.Button(nav, text="<- Precedent", font=LARGE_FONT, command=self._prev_tab)
        self.btn_prev.pack(side="left")

        self.btn_next = tk.Button(nav, text="Suivant ->", font=LARGE_FONT, command=self._next_tab, bg=COLORS["OK"], fg="white")
        self.btn_next.pack(side="right")

        tk.Label(self.root, text="Journal :", font=LARGE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"], anchor="w").pack(fill="x", padx=20)
        self.log = tk.Text(self.root, height=6, font=("Arial", 14), wrap="word")
        self.log.pack(fill="x", padx=20, pady=5)

        self._update_nav_buttons()

    def _bind_keyboard(self):
        self.root.bind("o", lambda e: self._manual_open())
        self.root.bind("O", lambda e: self._manual_open())
        self.root.bind("f", lambda e: self._manual_close())
        self.root.bind("F", lambda e: self._manual_close())
        self.root.bind("p", lambda e: self._manual_pause())
        self.root.bind("P", lambda e: self._manual_pause())
        self.root.bind("<Escape>", lambda e: self._emergency_stop())

    def _source_color(self, mode: str) -> str:
        if mode == "gpype":
            return COLORS["OK"]
        if mode == "lsl":
            return COLORS["WARN"]
        return COLORS["IDLE"]

    def _toggle_safe_mode(self):
        if self.safe_mode_var.get():
            self.safety.enable_safe_mode()
            self._log("Mode securite active.")
        else:
            self.safety.disable_safe_mode()
            self._log("Mode securite desactive.")

    def _on_profile_changed(self, event=None):
        profile = self.profile_var.get()
        self.mapper.set_profile(profile)
        self._log(f"Profil change : {profile}")
        self.last_cmd_message.set(f"Profil actif : {profile}")

    def _create_welcome_tab(self):
        frame = tk.Frame(self.pages, bg=COLORS["BG"])
        lbl = tk.Label(
            frame,
            text=(
                "Bienvenue dans le tutoriel de commande cerebrale.\n\n"
                "Ce systeme vous apprend a controler l'ouverture et la fermeture d'un gant "
                "a l'aide de votre activite cerebrale.\n\n"
                "Navigation : utilisez les onglets ou les boutons Precedent / Suivant.\n\n"
                "Raccourcis clavier : O = Ouvrir, F = Fermer, P = Pause, Echap = Urgence."
            ),
            font=LARGE_FONT,
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
            wraplength=700,
            justify="center",
        )
        lbl.pack(expand=True)
        return frame

    def _create_calibration_tab(self):
        frame = tk.Frame(self.pages, bg=COLORS["BG"])

        self.calib_info = tk.Label(
            frame,
            text=(
                "Nous allons calibrer 3 etats mentaux :\n\n"
                "1. Detendez-vous, fermez les yeux 10 s -> OUVRIR\n"
                "2. Concentrez-vous, imaginez fermer la main 10 s -> FERMER\n"
                "3. Repos neutre 10 s -> NEUTRE"
            ),
            font=LARGE_FONT,
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
            wraplength=700,
            justify="left",
        )
        self.calib_info.pack(pady=20)

        self.calib_progress = ttk.Progressbar(frame, maximum=100, length=600)
        self.calib_progress.pack(pady=10)

        self.calib_status = tk.Label(frame, text="Pret", font=STATUS_FONT, bg="white", fg=COLORS["IDLE"])
        self.calib_status.pack(pady=20, ipadx=20, ipady=20)

        self.btn_calib = tk.Button(frame, text="Lancer la calibration (demo)", font=LARGE_FONT, command=self._run_calibration)
        self.btn_calib.pack(pady=10)

        return frame

    def _create_training_tab(self):
        frame = tk.Frame(self.pages, bg=COLORS["BG"])

        tk.Label(frame, text="Choisissez un etat a entraîner :", font=LARGE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=10)

        btn_frame = tk.Frame(frame, bg=COLORS["BG"])
        btn_frame.pack(pady=10)

        for state, color in [("OPEN", COLORS["OPEN"]), ("CLOSE", COLORS["CLOSE"]), ("IDLE", COLORS["IDLE"])]:
            btn = tk.Button(
                btn_frame,
                text=f"{ICONS[state]} {state}",
                font=LARGE_FONT,
                bg=color,
                fg="white",
                width=10,
                command=lambda s=state: self._train_state(s),
            )
            btn.pack(side="left", padx=10)

        self.train_status = tk.Label(frame, text="Etat cible : IDLE", font=STATUS_FONT, bg="white", fg=COLORS["IDLE"])
        self.train_status.pack(pady=20, ipadx=20, ipady=20)

        self.train_feedback = tk.Label(frame, text="Cliquez sur un bouton pour commencer", font=LARGE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.train_feedback.pack(pady=10)

        return frame

    def _create_control_tab(self):
        frame = tk.Frame(self.pages, bg=COLORS["BG"])

        tk.Label(frame, text="Controle en temps reel", font=LARGE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=10)

        self.control_status = tk.Label(frame, text="Commande : IDLE", font=STATUS_FONT, bg="white", fg=COLORS["IDLE"])
        self.control_status.pack(pady=20, ipadx=20, ipady=20)

        self.raw_state_label = tk.Label(
            frame,
            text="Etat brut detecte : --",
            font=("Arial", 16),
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
        )
        self.raw_state_label.pack(pady=5)

        self.safe_state_label = tk.Label(
            frame,
            text="Etat apres securite : --",
            font=("Arial", 16),
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
        )
        self.safe_state_label.pack(pady=5)

        self.control_details = tk.Label(frame, text="alpha=--\nbeta=--", font=LARGE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.control_details.pack(pady=10)

        btn_frame = tk.Frame(frame, bg=COLORS["BG"])
        btn_frame.pack(pady=20)

        self.btn_start = tk.Button(btn_frame, text="▶ Demarrer", font=LARGE_FONT, command=self._start_control, bg=COLORS["OK"], fg="white")
        self.btn_start.pack(side="left", padx=10)

        self.btn_stop = tk.Button(btn_frame, text="⏹ Arreter", font=LARGE_FONT, command=self._stop_control, bg=COLORS["ERROR"], fg="white")
        self.btn_stop.pack(side="left", padx=10)
        self.btn_stop.config(state="disabled")

        return frame

    def _on_tab_changed(self, event=None):
        idx = self.pages.index(self.pages.select())
        names = ["Accueil", "Calibration", "Entrainement", "Controle"]
        self.step_label.config(text=f"Etape {idx + 1} / 4 : {names[idx]}")
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        idx = self.pages.index(self.pages.select())
        self.btn_prev.config(state="normal" if idx > 0 else "disabled")
        self.btn_next.config(text="Terminer" if idx == 3 else "Suivant ->")

    def _next_tab(self):
        idx = self.pages.index(self.pages.select())
        if idx < 3:
            self.pages.select(idx + 1)
        else:
            self.root.quit()

    def _prev_tab(self):
        idx = self.pages.index(self.pages.select())
        if idx > 0:
            self.pages.select(idx - 1)

    def _log(self, message: str):
        self.log.insert("end", message + "\\n")
        self.log.see("end")

    def _send_command(self, state: str, source: str = MANUAL_SOURCE):
        cmd = self.mapper.map(state)
        packet = CommandPacket(
            action=cmd["action"],
            value=cmd["value"],
            label=cmd["label"],
            timestamp=time.time(),
        )
        try:
            self.client.send(packet)
            logger.info(f"Commande envoyee [{source}]: {state} -> {cmd['action']} (label={cmd['label']}, profil={self.mapper.profile})")
        except Exception as e:
            self._log(f"Erreur envoi commande : {e}")
            logger.error(f"Erreur envoi commande [{source}]: {e}")

        icon = ICONS.get(state, "?")
        profile = self.mapper.profile
        self.last_cmd_message.set(f"[{source.upper()}] {icon} {state} -> {cmd['action']} ({cmd['label']}) [profil={profile}]")
        self._log(f"Commande envoyee [{source}] : {state} -> {cmd['action']} (label={cmd['label']}, profil={profile})")

    def _manual_open(self):
        self._send_command("OPEN", source=MANUAL_SOURCE)
        self.control_status.config(text=f"Commande manuelle : {ICONS['OPEN']} OPEN", fg=COLORS["OPEN"])

    def _manual_close(self):
        self._send_command("CLOSE", source=MANUAL_SOURCE)
        self.control_status.config(text=f"Commande manuelle : {ICONS['CLOSE']} CLOSE", fg=COLORS["CLOSE"])

    def _manual_pause(self):
        self._send_command("IDLE", source=MANUAL_SOURCE)
        self.control_status.config(text=f"Commande manuelle : {ICONS['IDLE']} IDLE", fg=COLORS["IDLE"])

    def _emergency_stop(self):
        self.emergency_active = True
        self.auto_control_active = False
        if self.update_job:
            self.root.after_cancel(self.update_job)
            self.update_job = None
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

        self._send_command("CLOSE", source=EMERGENCY_SOURCE)
        self.control_status.config(text="URGENCE : CLOSE (mains fermees)", fg=COLORS["ERROR"])
        self.last_cmd_message.set("[URGENCE] ECHAP -> CLOSE : controle automatique arrete")
        self._log('URGENCE activee par ECHAP.')
        logger.warning("URGENCE activee (Echap) - mains fermees, controle auto arrete")
        messagebox.showwarning("Urgence", "Mode urgence active.\nLes mains restent FERMEES.\nControle automatique arrete.")
        self.emergency_active = False

    def _run_calibration(self):
        self.btn_calib.config(state="disabled")
        self._log("Calibration demarree.")
        self._calibrate_states(["OPEN", "CLOSE", "IDLE"], 0)

    def _calibrate_states(self, states, index):
        if index >= len(states):
            self.calib_status.config(text="Calibration OK", fg=COLORS["OK"])
            self.calib_info.config(text="Le systeme est calibre. Passez a l'entraînement.")
            self.btn_calib.config(state="normal")
            self._log("Calibration terminee.")
            return

        state = states[index]
        self.eeg_source.set_state(state)
        self.calib_status.config(text=f"Calibration : {ICONS[state]} {state}", fg=COLORS[state])
        self.calib_progress["value"] = int((index / len(states)) * 100)
        self._log(f"Calibration de l'etat {state}...")

        def step(i=0):
            if i >= 10:
                self._calibrate_states(states, index + 1)
                return
            eeg = self.eeg_source.read_window(1.0)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            self.detector.detect(features)
            self.calib_progress["value"] = int(((index + (i + 1) / 10) / len(states)) * 100)
            self.root.after(100, lambda: step(i + 1))

        step()

    def _train_state(self, state):
        self.eeg_source.set_state(state)
        self.train_status.config(text=f"Etat cible : {ICONS[state]} {state}", fg=COLORS[state])

        eeg = self.eeg_source.read_window(2.0)
        features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
        self.detector.reset()
        detected = self.detector.detect(features)

        if detected == state:
            self.train_feedback.config(text=f"Bravo ! {state} bien detecte.", fg=COLORS["OK"])
        else:
            self.train_feedback.config(text=f"Essayez encore. Detecte : {detected}, attendu : {state}", fg=COLORS["ERROR"])

        self._log(f'Entrainement {state} : detecte={detected}')

    def _start_control(self):
        self.auto_control_active = True
        self.emergency_active = False
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self._demo_timer = time.time()
        self._log("Controle demarre.")
        logger.info(f"=== Controle automatique demarre | Source EEG: {self.eeg_source.get_mode()} | Profil: {self.mapper.profile} | ML: {self.detector.uses_ml} ===")
        self._update_control()

    def _stop_control(self):
        self.auto_control_active = False
        if self.update_job:
            self.root.after_cancel(self.update_job)
            self.update_job = None
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.control_status.config(text="Commande : IDLE (arrete)", fg=COLORS["IDLE"])
        self._log("Controle arrete.")

    def _update_control(self):
        if not self.auto_control_active or self.emergency_active:
            return

        if self.eeg_source.get_mode() == "simulateur":
            elapsed = time.time() - self._demo_timer
            cycle_position = int((elapsed % DEMO_CYCLE_SECONDS) / (DEMO_CYCLE_SECONDS / 3))
            demo_states = ["OPEN", "CLOSE", "IDLE"]
            demo_state = demo_states[cycle_position % 3]
            self.eeg_source.set_state(demo_state)

        eeg = self.eeg_source.read_window(1.0)
        features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
        raw_state = self.detector.detect(features)
        safe_state = self.safety.filter_state(raw_state)
        if safe_state != getattr(self, '_last_logged_state', None):
            logger.info('Etat: brut=%s securite=%s | alpha=%.1f beta=%.1f' % (raw_state, safe_state, features['alpha'], features['beta']))
            self._last_logged_state = safe_state

        self.raw_state_label.config(text=f"Etat brut detecte : {ICONS.get(raw_state, '?')} {raw_state}")
        self.safe_state_label.config(text=f"Etat apres securite : {ICONS.get(safe_state, '?')} {safe_state}")
        self.control_status.config(text=f"Commande : {ICONS[safe_state]} {safe_state}", fg=COLORS[safe_state])
        self.control_details.config(text=f"alpha={features['alpha']:.1f}\nbeta={features['beta']:.1f}")

        self._send_command(safe_state, source=AUTO_SOURCE)

        self.update_job = self.root.after(500, self._update_control)

    def on_close(self):
        self._stop_control()
        try:
            self.eeg_source.disconnect()
        except Exception as e:
            self._log(f"Erreur deconnexion EEG : {e}")
        self.client.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = InclusiveAppTk(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
