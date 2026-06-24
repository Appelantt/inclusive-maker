"""Interface graphique inclusive avec Tkinter.

Tkinter est natif a Python : pas besoin d'installer PySide6.
Flux linéaire accessible :
1. Accueil
2. Calibration
3. Entraînement
4. Controle
"""

import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.remote_command.client import CommandClient
from inclusive_maker.remote_command.protocol import CommandPacket
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS

# Palette accessible
COLORS = {
    "OPEN": "#4FC3F7",
    "CLOSE": "#FF9800",
    "IDLE": "#9E9E9E",
    "OK": "#2E7D32",
    "ERROR": "#D32F2F",
    "BG": "#F5F5F5",
    "TEXT": "#212121",
}

ICONS = {"OPEN": "✋", "CLOSE": "✊", "IDLE": "⏸"}

LARGE_FONT = ("Arial", 18)
TITLE_FONT = ("Arial", 24, "bold")
STATUS_FONT = ("Arial", 28, "bold")


class InclusiveAppTk:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inclusive Maker - Commande cerebrale")
        self.root.geometry("800x700")
        self.root.configure(bg=COLORS["BG"])

        self.eeg_generator = EEGGenerator("IDLE")
        self.detector = MentalStateDetector()
        self.mapper = CommandMapper()
        self.client = CommandClient()

        self.current_state = tk.StringVar(value="IDLE")
        self.status_text = tk.StringVar(value="Pret")
        self.log_text = tk.StringVar(value="Journal d'activite\n")

        self._build_ui()

        self.update_job = None

    def _build_ui(self):
        # Titre
        title = tk.Label(self.root, text="Inclusive Maker", font=TITLE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"])
        title.pack(pady=10)

        self.step_label = tk.Label(self.root, text="Etape 1 / 4 : Accueil", font=LARGE_FONT, bg=COLORS["BG"], fg="#616161")
        self.step_label.pack(pady=5)

        # Container des pages
        self.pages = ttk.Notebook(self.root)
        self.pages.pack(fill="both", expand=True, padx=20, pady=10)
        self.pages.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.tab_welcome = self._create_welcome_tab()
        self.tab_calib = self._create_calibration_tab()
        self.tab_train = self._create_training_tab()
        self.tab_control = self._create_control_tab()

        self.pages.add(self.tab_welcome, text="1. Accueil")
        self.pages.add(self.tab_calib, text="2. Calibration")
        self.pages.add(self.tab_train, text="3. Entraînement")
        self.pages.add(self.tab_control, text="4. Controle")

        # Barre de navigation
        nav = tk.Frame(self.root, bg=COLORS["BG"])
        nav.pack(fill="x", padx=20, pady=10)

        self.btn_prev = tk.Button(nav, text="← Precedent", font=LARGE_FONT, command=self._prev_tab)
        self.btn_prev.pack(side="left")

        self.btn_next = tk.Button(nav, text="Suivant →", font=LARGE_FONT, command=self._next_tab, bg=COLORS["OK"], fg="white")
        self.btn_next.pack(side="right")

        # Log
        tk.Label(self.root, text="Journal :", font=LARGE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"], anchor="w").pack(fill="x", padx=20)
        self.log = tk.Text(self.root, height=6, font=("Arial", 14), wrap="word")
        self.log.pack(fill="x", padx=20, pady=5)

        self._update_nav_buttons()

    def _create_welcome_tab(self):
        frame = tk.Frame(self.pages, bg=COLORS["BG"])
        lbl = tk.Label(
            frame,
            text=(
                "Bienvenue dans le tutoriel de commande cerebrale.\n\n"
                "Ce systeme vous apprend a controler l'ouverture et la fermeture d'un gant "
                "a l'aide de votre activite cerebrale.\n\n"
                "Navigation : utilisez les onglets ou les boutons Precedent / Suivant."
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
                "1. Detendez-vous, fermez les yeux 10 s → OUVRIR\n"
                "2. Concentrez-vous, imaginez fermer la main 10 s → FERMER\n"
                "3. Repos neutre 10 s → NEUTRE"
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

        self.control_details = tk.Label(frame, text="alpha=--\nbeta=--", font=LARGE_FONT, bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.control_details.pack(pady=10)

        btn_frame = tk.Frame(frame, bg=COLORS["BG"])
        btn_frame.pack(pady=20)

        self.btn_start = tk.Button(btn_frame, text="▶ Démarrer", font=LARGE_FONT, command=self._start_control, bg=COLORS["OK"], fg="white")
        self.btn_start.pack(side="left", padx=10)

        self.btn_stop = tk.Button(btn_frame, text="⏹ Arreter", font=LARGE_FONT, command=self._stop_control, bg=COLORS["ERROR"], fg="white")
        self.btn_stop.pack(side="left", padx=10)
        self.btn_stop.config(state="disabled")

        return frame

    def _on_tab_changed(self, event=None):
        idx = self.pages.index(self.pages.select())
        names = ["Accueil", "Calibration", "Entraînement", "Controle"]
        self.step_label.config(text=f"Etape {idx + 1} / 4 : {names[idx]}")
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        idx = self.pages.index(self.pages.select())
        self.btn_prev.config(state="normal" if idx > 0 else "disabled")
        self.btn_next.config(text="Terminer" if idx == 3 else "Suivant →")

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
        self.log.insert("end", message + "\n")
        self.log.see("end")

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
        self.eeg_generator.set_state(state)
        self.calib_status.config(text=f"Calibration : {ICONS[state]} {state}", fg=COLORS[state])
        self.calib_progress["value"] = int((index / len(states)) * 100)
        self._log(f"Calibration de l'etat {state}...")

        def step(i=0):
            if i >= 10:
                self._calibrate_states(states, index + 1)
                return
            eeg = self.eeg_generator.read_window(1.0)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            self.detector.detect(features)
            self.calib_progress["value"] = int(((index + (i + 1) / 10) / len(states)) * 100)
            self.root.after(100, lambda: step(i + 1))

        step()

    def _train_state(self, state):
        self.eeg_generator.set_state(state)
        self.train_status.config(text=f"Etat cible : {ICONS[state]} {state}", fg=COLORS[state])

        eeg = self.eeg_generator.read_window(2.0)
        features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
        self.detector.reset()
        detected = self.detector.detect(features)

        if detected == state:
            self.train_feedback.config(text=f"Bravo ! {state} bien detecte.", fg=COLORS["OK"])
        else:
            self.train_feedback.config(text=f"Essayez encore. Detecte : {detected}, attendu : {state}", fg=COLORS["ERROR"])

        self._log(f"Entraînement {state} : detecte={detected}")

    def _start_control(self):
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self._log("Controle demarre.")
        self._update_control()

    def _stop_control(self):
        if self.update_job:
            self.root.after_cancel(self.update_job)
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.control_status.config(text="Commande : IDLE (arrete)", fg=COLORS["IDLE"])
        self._log("Controle arrete.")

    def _update_control(self):
        eeg = self.eeg_generator.read_window(1.0)
        features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
        state = self.detector.detect(features)

        self.control_status.config(text=f"Commande : {ICONS[state]} {state}", fg=COLORS[state])
        self.control_details.config(text=f"alpha={features['alpha']:.1f}\nbeta={features['beta']:.1f}")

        cmd = self.mapper.map(state)
        packet = CommandPacket(
            action=cmd["action"],
            value=cmd["value"],
            label=cmd["label"],
            timestamp=time.time(),
        )
        self.client.send(packet)

        self.update_job = self.root.after(500, self._update_control)

    def on_close(self):
        self._stop_control()
        self.client.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = InclusiveAppTk(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
