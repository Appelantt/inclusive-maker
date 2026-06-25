"""Interface graphique de tutoriel d'entrainement pour Inclusive Maker.

Cette interface guide l'utilisateur pour calibrer ses etats mentaux
(OPEN, CLOSE, IDLE) et les associer aux commandes du gant.
"""

import sys
import time
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QComboBox
)
from PySide6.QtCore import QTimer, Qt

from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.remote_command.client import CommandClient
from inclusive_maker.remote_command.protocol import CommandPacket
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS


class EEGSimulator:
    """Simulateur de signal EEG pour le tutoriel (remplacer par vrai casque)."""

    def __init__(self):
        self.state = "IDLE"

    def set_state(self, state: str):
        self.state = state

    def read(self, n_samples: int) -> np.ndarray:
        t = np.arange(n_samples) / EEG_SAMPLING_RATE
        data = np.zeros((n_samples, 8))
        for ch in range(8):
            noise = np.random.normal(0, 1, n_samples)
            alpha = 0.0
            if self.state == "OPEN":
                alpha = 20 * np.sin(2 * np.pi * 10 * t)
            elif self.state == "CLOSE":
                alpha = 2 * np.sin(2 * np.pi * 10 * t)
                beta = 8 * np.sin(2 * np.pi * 20 * t)
                noise += beta
            else:  # IDLE
                alpha = 8 * np.sin(2 * np.pi * 10 * t)
            data[:, ch] = alpha + noise
        return data


class TrainingApp(QMainWindow):
    """Fenetre principale du tutoriel d'entrainement."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inclusive Maker - Tutoriel d'entrainement")
        self.resize(600, 500)

        self.simulator = EEGSimulator()
        self.detector = MentalStateDetector(
            open_ratio=4.0,
            close_ratio=8.0,
            smoothing_window=3,
        )
        self.mapper = CommandMapper()
        self.client = CommandClient()

        self._build_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(500)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("Commande cerebrale : tutoriel")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.instructions = QLabel(
            "Selectionnez un etat mental a entraîner. "
            "Le systeme va apprendre a associer votre activite cerebrale a une commande."
        )
        self.instructions.setWordWrap(True)
        layout.addWidget(self.instructions)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Etat a entraîner :"))
        self.state_combo = QComboBox()
        self.state_combo.addItems(["OPEN", "CLOSE", "IDLE"])
        self.state_combo.currentTextChanged.connect(self._on_state_changed)
        hbox.addWidget(self.state_combo)
        layout.addLayout(hbox)

        self.calibrate_btn = QPushButton("Lancer la calibration")
        self.calibrate_btn.clicked.connect(self._calibrate)
        layout.addWidget(self.calibrate_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.command_label = QLabel("Commande detectee : IDLE")
        self.command_label.setStyleSheet("font-size: 24px; color: gray;")
        self.command_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.command_label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.send_btn = QPushButton("Envoyer commande detectee")
        self.send_btn.clicked.connect(self._send_command)
        layout.addWidget(self.send_btn)

    def _on_state_changed(self, state: str):
        self.simulator.set_state(state)
        self.instructions.setText(f"Entraînez l'etat : {state}")

    def _calibrate(self):
        self.progress.setValue(0)
        target = self.state_combo.currentText()
        self.log.append(f"Calibration pour l'etat {target}...")
        self.simulator.set_state(target)
        for i in range(1, 11):
            eeg = self.simulator.read(EEG_SAMPLING_RATE)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            self.detector.detect(features)
            self.progress.setValue(i * 10)
        self.log.append(f"Calibration {target} terminee.")

    def _update(self):
        eeg = self.simulator.read(EEG_SAMPLING_RATE)
        features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
        state = self.detector.detect(features)
        self.command_label.setText(f"Commande detectee : {state}")
        color = {"OPEN": "green", "CLOSE": "red", "IDLE": "gray"}.get(state, "gray")
        self.command_label.setStyleSheet(f"font-size: 24px; color: {color};")

    def _send_command(self):
        state = self.command_label.text().replace("Commande detectee : ", "")
        cmd = self.mapper.map(state)
        packet = CommandPacket(
            action=cmd["action"],
            value=cmd["value"],
            label=cmd["label"],
            timestamp=time.time(),
        )
        self.client.send(packet)
        self.log.append(f"Envoye : {packet.to_dict()}")

    def closeEvent(self, event):
        self.client.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = TrainingApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
