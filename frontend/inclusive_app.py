"""Application graphique inclusive pour la commande cérébrale.

Flux linéaire accessible :
1. Accueil
2. Calibration (associer ses états mentaux aux commandes)
3. Entraînement (répéter les états)
4. Contrôle en temps réel

Règles d'accessibilité appliquées :
- Couleurs + icônes + textes pour les daltoniens
- Gros boutons et typographie lisible
- Navigation au clavier (Tab, Entrée, Espace)
- Retours visuels, textuels et sonores
- Pas de menus complexes, une seule action principale par écran
"""

import sys
import time
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QStackedWidget, QTextEdit,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

from inclusive_maker.acquisition.generator import EEGGenerator
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.remote_command.client import CommandClient
from inclusive_maker.remote_command.protocol import CommandPacket
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS


# Palette accessible (daltonisme-friendly)
COLORS = {
    "OPEN": "#4FC3F7",   # bleu clair
    "CLOSE": "#FF9800",  # orange
    "IDLE": "#9E9E9E",   # gris
    "OK": "#2E7D32",     # vert
    "ALERT": "#7B1FA2",  # violet
    "ERROR": "#D32F2F",  # rouge
    "BG": "#F5F5F5",     # fond gris très clair
    "TEXT": "#212121",   # texte foncé
}

ICONS = {
    "OPEN": "✋",
    "CLOSE": "✊",
    "IDLE": "⏸",
    "NEXT": "➡",
    "BACK": "⬅",
}


def set_accessible_button(btn: QPushButton, color_key: str = ""):
    """Applique un style accessible aux boutons."""
    color = COLORS.get(color_key, "#424242")
    text_color = "#FFFFFF" if color_key else "#212121"
    btn.setMinimumHeight(56)
    btn.setFont(QFont("Arial", 16, QFont.Bold))
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            color: {text_color};
            border: 3px solid #212121;
            border-radius: 12px;
            padding: 12px 24px;
        }}
        QPushButton:focus {{
            outline: 4px solid #FFD600;
            border: 3px solid #212121;
        }}
    """)
    btn.setFocusPolicy(Qt.StrongFocus)


def set_status_label(label: QLabel, state: str, text: str):
    """Met à jour un label avec couleur, icône et texte."""
    color = COLORS.get(state, COLORS["IDLE"])
    icon = ICONS.get(state, "")
    label.setText(f"{icon} {text}")
    label.setStyleSheet(f"""
        font-size: 32px;
        font-weight: bold;
        color: {color};
        background-color: #FFFFFF;
        border: 4px solid {color};
        border-radius: 16px;
        padding: 20px;
    """)


class InclusiveApp(QMainWindow):
    """Application principale avec navigation linéaire."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inclusive Maker - Commande cerebrale")
        self.resize(800, 700)

        # Moteur EEG
        self.eeg_generator = EEGGenerator("IDLE")
        self.detector = MentalStateDetector()
        self.mapper = CommandMapper()
        self.client = CommandClient()
        self.current_target_state = "IDLE"
        self._auto_send = False

        self._build_ui()

        # Timer de mise à jour EEG (2 Hz)
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_eeg)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Titre global
        self.title_label = QLabel("🧠 Inclusive Maker")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.title_label.setStyleSheet(f"color: {COLORS['TEXT']};")
        main_layout.addWidget(self.title_label)

        # Sous-titre / étape
        self.step_label = QLabel("Etape 1 sur 4 : Accueil")
        self.step_label.setAlignment(Qt.AlignCenter)
        self.step_label.setFont(QFont("Arial", 18))
        self.step_label.setStyleSheet("color: #616161;")
        main_layout.addWidget(self.step_label)

        # Zone de navigation linéaire
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, stretch=1)

        # Création des écrans
        self.stack.addWidget(self._screen_welcome())
        self.stack.addWidget(self._screen_calibration())
        self.stack.addWidget(self._screen_training())
        self.stack.addWidget(self._screen_control())

        # Barre de navigation
        nav = QHBoxLayout()
        self.btn_prev = QPushButton(f"{ICONS['BACK']} Precedent")
        set_accessible_button(self.btn_prev)
        self.btn_prev.clicked.connect(self._prev_screen)

        self.btn_next = QPushButton(f"Suivant {ICONS['NEXT']}")
        set_accessible_button(self.btn_next, "OK")
        self.btn_next.clicked.connect(self._next_screen)

        nav.addWidget(self.btn_prev)
        nav.addStretch()
        nav.addWidget(self.btn_next)
        main_layout.addLayout(nav)

        # Log accessible
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(100)
        self.log.setFont(QFont("Arial", 14))
        self.log.setStyleSheet("background-color: #FFFFFF; border: 2px solid #9E9E9E; border-radius: 8px;")
        main_layout.addWidget(QLabel("Journal d'activite :"))
        main_layout.addWidget(self.log)

        self._update_nav_buttons()

    # ----------------- Écrans -----------------

    def _screen_welcome(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignCenter)

        info = QLabel(
            "Bienvenue dans le tutoriel de commande cerebrale.\n\n"
            "Ce systeme vous apprend a controler l'ouverture et la fermeture d'un gant "
            "a l'aide de votre activite cerebrale.\n\n"
            "Cliquez sur 'Suivant' pour commencer la calibration."
        )
        info.setWordWrap(True)
        info.setFont(QFont("Arial", 18))
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet(f"color: {COLORS['TEXT']};")
        layout.addWidget(info)

        return screen

    def _screen_calibration(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignCenter)

        self.calib_instructions = QLabel(
            "Nous allons calibrer le systeme sur 3 etats mentaux.\n\n"
            "1. Detendez-vous et fermez les yeux 10 secondes → OPEN\n"
            "2. Concentrez-vous / imaginez fermer la main 10 secondes → CLOSE\n"
            "3. Repos neutre 10 secondes → IDLE"
        )
        self.calib_instructions.setWordWrap(True)
        self.calib_instructions.setFont(QFont("Arial", 18))
        layout.addWidget(self.calib_instructions)

        self.calib_progress = QProgressBar()
        self.calib_progress.setRange(0, 100)
        self.calib_progress.setTextVisible(True)
        self.calib_progress.setStyleSheet("font-size: 16px; height: 30px;")
        layout.addWidget(self.calib_progress)

        self.calib_status = QLabel("Pret pour la calibration")
        set_status_label(self.calib_status, "IDLE", "Pret pour la calibration")
        layout.addWidget(self.calib_status)

        self.btn_calib = QPushButton("Lancer la calibration (mode demonstration)")
        set_accessible_button(self.btn_calib, "OK")
        self.btn_calib.clicked.connect(self._run_calibration)
        layout.addWidget(self.btn_calib)

        return screen

    def _screen_training(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignCenter)

        instructions = QLabel(
            "Entrainement : le systeme affiche un etat, simulez-le mentalement.\n\n"
            "Utilisez les boutons ci-dessous pour choisir l'etat a entraîner."
        )
        instructions.setWordWrap(True)
        instructions.setFont(QFont("Arial", 18))
        layout.addWidget(instructions)

        hbox = QHBoxLayout()
        for state, color_key in [("OPEN", "OPEN"), ("CLOSE", "CLOSE"), ("IDLE", "IDLE")]:
            btn = QPushButton(f"{ICONS[state]} {state}")
            set_accessible_button(btn, color_key)
            btn.clicked.connect(lambda checked, s=state: self._train_state(s))
            hbox.addWidget(btn)
        layout.addLayout(hbox)

        self.train_status = QLabel("Etat cible : IDLE")
        set_status_label(self.train_status, "IDLE", "Etat cible : IDLE")
        layout.addWidget(self.train_status)

        self.train_feedback = QLabel("Cliquez sur un bouton pour commencer")
        self.train_feedback.setFont(QFont("Arial", 18))
        self.train_feedback.setAlignment(Qt.AlignCenter)
        self.train_feedback.setStyleSheet(f"color: {COLORS['TEXT']};")
        layout.addWidget(self.train_feedback)

        return screen

    def _screen_control(self) -> QWidget:
        screen = QWidget()
        layout = QVBoxLayout(screen)
        layout.setAlignment(Qt.AlignCenter)

        instructions = QLabel(
            "Mode controle en temps reel.\n\n"
            "Le systeme detecte votre etat mental et envoie la commande au gant."
        )
        instructions.setWordWrap(True)
        instructions.setFont(QFont("Arial", 18))
        layout.addWidget(instructions)

        self.control_status = QLabel("Commande : IDLE")
        set_status_label(self.control_status, "IDLE", "Commande : IDLE")
        layout.addWidget(self.control_status)

        self.control_details = QLabel("Puissance alpha : --\nPuissance beta : --")
        self.control_details.setFont(QFont("Arial", 16))
        self.control_details.setAlignment(Qt.AlignCenter)
        self.control_details.setStyleSheet(f"color: {COLORS['TEXT']};")
        layout.addWidget(self.control_details)

        hbox = QHBoxLayout()
        self.btn_start_control = QPushButton("Démarrer le controle")
        set_accessible_button(self.btn_start_control, "OK")
        self.btn_start_control.clicked.connect(self._start_control)

        self.btn_stop_control = QPushButton("Arreter")
        set_accessible_button(self.btn_stop_control, "ERROR")
        self.btn_stop_control.clicked.connect(self._stop_control)
        self.btn_stop_control.setEnabled(False)

        hbox.addWidget(self.btn_start_control)
        hbox.addWidget(self.btn_stop_control)
        layout.addLayout(hbox)

        return screen

    # ----------------- Navigation -----------------

    def _next_screen(self):
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            self._update_nav_buttons()
            self._on_screen_changed(idx + 1)

    def _prev_screen(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_nav_buttons()
            self._on_screen_changed(idx - 1)

    def _update_nav_buttons(self):
        idx = self.stack.currentIndex()
        self.btn_prev.setEnabled(idx > 0)
        if idx == self.stack.count() - 1:
            self.btn_next.setText("Terminer")
        else:
            self.btn_next.setText(f"Suivant {ICONS['NEXT']}")
        self.step_label.setText(f"Etape {idx + 1} sur {self.stack.count()} : {self._screen_name(idx)}")

    def _screen_name(self, idx: int) -> str:
        names = ["Accueil", "Calibration", "Entraînement", "Controle"]
        return names[idx]

    def _on_screen_changed(self, idx: int):
        self.timer.stop()
        self.eeg_generator.set_state("IDLE")
        if idx == 3:
            pass  # control demarre manuellement

    # ----------------- Actions EEG -----------------

    def _run_calibration(self):
        self.log.append("Calibration demarree.")
        self.btn_calib.setEnabled(False)
        states = ["OPEN", "CLOSE", "IDLE"]
        self._calibrate_states(states, 0)

    def _calibrate_states(self, states: list, index: int):
        if index >= len(states):
            set_status_label(self.calib_status, "OK", "Calibration terminee")
            self.calib_instructions.setText("Le systeme est calibre. Passez a l'entraînement.")
            self.btn_calib.setEnabled(True)
            self.log.append("Calibration terminee.")
            return

        state = states[index]
        self.eeg_generator.set_state(state)
        set_status_label(self.calib_status, state, f"Calibrage : {state}")
        self.calib_progress.setValue(int((index / len(states)) * 100))
        self.log.append(f"Calibration de l'etat {state}...")

        # Simulation de 10 fenetres de 1 seconde
        def step(i=0):
            if i >= 10:
                self._calibrate_states(states, index + 1)
                return
            eeg = self.eeg_generator.read_window(1.0)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            self.detector.detect(features)
            self.calib_progress.setValue(int(((index + (i + 1) / 10) / len(states)) * 100))
            QTimer.singleShot(100, lambda: step(i + 1))

        step()

    def _train_state(self, state: str):
        self.current_target_state = state
        self.eeg_generator.set_state(state)
        set_status_label(self.train_status, state, f"Etat cible : {state}")

        # Detecte et compare
        eeg = self.eeg_generator.read_window(2.0)
        features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
        detected = self.detector.detect(features)

        if detected == state:
            self.train_feedback.setText(f"Bravo ! L'etat {state} est bien detecte.")
            self.train_feedback.setStyleSheet(f"color: {COLORS['OK']}; font-weight: bold;")
        else:
            self.train_feedback.setText(f"Essayez encore. Detecte : {detected}, attendu : {state}")
            self.train_feedback.setStyleSheet(f"color: {COLORS['ERROR']}; font-weight: bold;")

        self.log.append(f"Entraînement {state} : detecte={detected}")

    def _start_control(self):
        self.timer.start(500)
        self.btn_start_control.setEnabled(False)
        self.btn_stop_control.setEnabled(True)
        self.log.append("Controle en temps reel demarre.")

    def _stop_control(self):
        self.timer.stop()
        self.btn_start_control.setEnabled(True)
        self.btn_stop_control.setEnabled(False)
        set_status_label(self.control_status, "IDLE", "Commande : IDLE (arrete)")
        self.log.append("Controle arrete.")

    def _update_eeg(self):
        eeg = self.eeg_generator.read_window(1.0)
        features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
        state = self.detector.detect(features)

        set_status_label(self.control_status, state, f"Commande : {state}")
        self.control_details.setText(
            f"Puissance alpha : {features['alpha']:.1f}\nPuissance beta : {features['beta']:.1f}"
        )

        cmd = self.mapper.map(state)
        packet = CommandPacket(
            action=cmd["action"],
            value=cmd["value"],
            label=cmd["label"],
            timestamp=time.time(),
        )
        self.client.send(packet)

    def closeEvent(self, event):
        self.timer.stop()
        self.client.close()
        event.accept()


def main():
    app = QApplication(sys.argv)

    # Palette globale accessible
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(COLORS["BG"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["TEXT"]))
    app.setPalette(palette)

    window = InclusiveApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
