from pathlib import Path

OUT = Path(r'C:\Users\Admin\Desktop\inclusive-maker\frontend\inclusive_app_tk.py')
if OUT.exists():
    OUT.unlink()

PARTS = []

PARTS.append(r'''"""Interface graphique inclusive avec Tkinter pour Philippe.

Adaptations par rapport a la version de base :
- Affichage du mode de source EEG (simulateur / LSL / casque Unicorn)
- Mode securite : FERMER par defaut si etat incertain
- Controle clavier 4 touches (sans eye-tracking, car fatiguant)
- Profils d'activite : main robot, cerf-volant, sport (kanoe/ski/quadrix)
"""

import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np

from inclusive_maker.acquisition.eeg_source import UnifiedEEGSource
from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.brain_algo.safety_controller import SafetyController
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
    "WARN": "#FBC02D",
    "SAFE": "#C62828",
}

ICONS = {"OPEN": "\u270b", "CLOSE": "\u270a", "IDLE": "\u23f8"}
ACTIVITY_LABELS = {
    "main_robot": "Main robotique / prothese",
    "cerf_volant": "Cerf-volant (tenir la barre)",
    "sport": "Kanoe / Ski / Quadrix",
}

LARGE_FONT = ("Arial", 18)
TITLE_FONT = ("Arial", 24, "bold")
STATUS_FONT = ("Arial", 28, "bold")
''')

PARTS.append(r'''
class InclusiveAppTk:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inclusive Maker - Commande cerebrale (Philippe)")
        self.root.geometry("900x800")
        self.root.configure(bg=COLORS["BG"])

        # Source EEG reelle ou simulee
        self.eeg_source = UnifiedEEGSource(force_generator=False)
        self.detector = MentalStateDetector()
        self.mapper = CommandMapper(profile="cerf_volant")
        self.safety = SafetyController(safe_mode=True, idle_is_safe=False)
        self.client = CommandClient()

        self.current_state = tk.StringVar(value="IDLE")
        self.status_text = tk.StringVar(value="Pret")
        self.log_text = tk.StringVar(value="Journal d'activite\n")
        self.safe_mode_var = tk.BooleanVar(value=True)
        self.profile_var = tk.StringVar(value="cerf_volant")
        self.source_mode_var = tk.StringVar(value=self.eeg_source.get_mode())
        self.last_command_label = tk.StringVar(value="Aucune commande")

        self._build_ui()

        self.update_job = None

        # Raccourcis clavier 4 touches
        self.root.bind("<KeyPress-o>", lambda e: self._manual_command("OPEN"))
        self.root.bind("<KeyPress-f>", lambda e: self._manual_command("CLOSE"))
        self.root.bind("<KeyPress-p>", lambda e: self._manual_command("IDLE"))
        self.root.bind("<KeyPress-Escape>", lambda e: self._emergency_close())
        self.root.bind("<KeyPress-O>", lambda e: self._manual_command("OPEN"))
        self.root.bind("<KeyPress-F>", lambda e: self._manual_command("CLOSE"))
        self.root.bind("<KeyPress-P>", lambda e: self._manual_command("IDLE"))
''')

