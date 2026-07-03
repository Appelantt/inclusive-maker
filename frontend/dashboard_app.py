"""Dashboard moderne avec graphiques temps reel pour Inclusive Maker."""

import glob
import os
import subprocess
import sys
import time
from collections import deque

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
import pyqtgraph as pg

from inclusive_maker.acquisition.eeg_source import UnifiedEEGSource
from inclusive_maker.signal_processing.features import compute_all_bandpowers
from inclusive_maker.brain_algo.mental_state_detector import MentalStateDetector
from inclusive_maker.brain_algo.command_mapper import CommandMapper
from inclusive_maker.remote_command.protocol import CommandPacket
from inclusive_maker.shared.constants import EEG_SAMPLING_RATE, BANDS
from inclusive_maker.shared.logger import get_logger

logger = get_logger(__name__)


COLORS = {"OPEN": "#4FC3F7", "CLOSE": "#FF9800", "IDLE": "#9E9E9E", "OK": "#2E7D32"}


class DashboardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inclusive Maker - Dashboard temps reel")
        self.resize(1100, 750)
        self.eeg_source = None
        self.detector = MentalStateDetector()
        self.mapper = CommandMapper()
        self._client = None
        self._lsl = None
        self.max_points = 200
        self.alpha_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.beta_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self.command_history = deque([0.0] * self.max_points, maxlen=self.max_points)
        self._build_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        # La connexion a la source EEG (recherche LSL) peut prendre plusieurs
        # secondes. On l'effectue APRES l'affichage de la fenetre pour eviter que
        # l'application paraisse gelee ("Ne repond pas") au demarrage.
        self.source_label.setText("Source : connexion en cours...")
        self.source_label.setStyleSheet("color: #F9A825;")
        self.btn_start.setEnabled(False)
        QTimer.singleShot(150, self._initial_connect)

    def _initial_connect(self):
        """Cree la source EEG apres l'affichage de la fenetre."""
        self.log.append("Recherche de la source EEG (casque via Unicorn LSL)...")
        QApplication.processEvents()
        try:
            self.eeg_source = UnifiedEEGSource()
        except Exception as e:
            logger.exception("Erreur creation de la source EEG")
            self.log.append(f"[ERREUR] Impossible de creer la source EEG : {e}")
            self.eeg_source = None
        self.btn_start.setEnabled(True)
        self._refresh_source_label()

    def _get_client(self):
        if self._client is None:
            try:
                from inclusive_maker.remote_command.client import CommandClient
                self._client = CommandClient()
            except Exception as e:
                logger.warning(f"UDP client indisponible : {e}")
                self._client = False
        return self._client

    def _get_lsl(self):
        if self._lsl is None:
            try:
                from inclusive_maker.remote_command.lsl_streamer import CommandLSLStreamer
                self._lsl = CommandLSLStreamer()
            except Exception as e:
                logger.warning(f"LSL streamer indisponible : {e}")
                self._lsl = False
        return self._lsl

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        left = QVBoxLayout()
        title = QLabel("Dashboard Inclusive Maker")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        left.addWidget(title)

        self.status_label = QLabel("ETAT : IDLE")
        self.status_label.setFont(QFont("Arial", 36, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            f"color: {COLORS['IDLE']}; background-color: white; border: 4px solid {COLORS['IDLE']}; border-radius: 20px; padding: 20px;"
        )
        left.addWidget(self.status_label)

        self.gauge = pg.PlotWidget()
        self.gauge.setTitle("Commande envoyee")
        self.gauge.setYRange(-1.5, 1.5)
        self.gauge.setXRange(0, self.max_points)
        self.gauge.hideAxis("left")
        self.gauge.hideAxis("bottom")
        self.gauge_line = self.gauge.plot(pen=pg.mkPen(color=COLORS["IDLE"], width=4))
        self.gauge.setMaximumHeight(160)
        left.addWidget(self.gauge)

        self.detail_label = QLabel("alpha=0.0  beta=0.0")
        self.detail_label.setFont(QFont("Arial", 14))
        self.detail_label.setAlignment(Qt.AlignCenter)
        left.addWidget(self.detail_label)

        self.source_label = QLabel("Source : SIMULATEUR")
        self.source_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.source_label.setAlignment(Qt.AlignCenter)
        left.addWidget(self.source_label)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton(" Demarrer")
        self.btn_start.setFont(QFont("Arial", 16, QFont.Bold))
        self.btn_start.setStyleSheet(f"background-color: {COLORS['OK']}; color: white; padding: 12px; border-radius: 10px;")
        self.btn_start.clicked.connect(self._start)
        self.btn_stop = QPushButton(" Arreter")
        self.btn_stop.setFont(QFont("Arial", 16, QFont.Bold))
        self.btn_stop.setStyleSheet("background-color: #D32F2F; color: white; padding: 12px; border-radius: 10px;")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        left.addLayout(btn_layout)

        casque_layout = QHBoxLayout()
        self.btn_open_lsl = QPushButton(" Ouvrir Unicorn LSL")
        self.btn_open_lsl.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_open_lsl.setStyleSheet("background-color: #37474F; color: white; padding: 10px; border-radius: 10px;")
        self.btn_open_lsl.clicked.connect(self._open_unicorn_lsl)
        self.btn_reconnect = QPushButton(" Reconnecter le casque")
        self.btn_reconnect.setFont(QFont("Arial", 12, QFont.Bold))
        self.btn_reconnect.setStyleSheet("background-color: #1565C0; color: white; padding: 10px; border-radius: 10px;")
        self.btn_reconnect.clicked.connect(self._reconnect)
        casque_layout.addWidget(self.btn_open_lsl)
        casque_layout.addWidget(self.btn_reconnect)
        left.addLayout(casque_layout)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        left.addWidget(self.log)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMinimumWidth(420)
        main_layout.addWidget(left_widget)

        right = QVBoxLayout()
        self.alpha_plot = pg.PlotWidget(title="Puissance Alpha (8-13 Hz)")
        self.alpha_plot.setYRange(0, 120)
        self.alpha_plot.setXRange(0, self.max_points)
        self.alpha_plot.showGrid(x=True, y=True)
        self.alpha_curve = self.alpha_plot.plot(pen=pg.mkPen(color="#4FC3F7", width=2))
        right.addWidget(self.alpha_plot)

        self.beta_plot = pg.PlotWidget(title="Puissance Beta (13-30 Hz)")
        self.beta_plot.setYRange(0, 50)
        self.beta_plot.setXRange(0, self.max_points)
        self.beta_plot.showGrid(x=True, y=True)
        self.beta_curve = self.beta_plot.plot(pen=pg.mkPen(color="#FF9800", width=2))
        right.addWidget(self.beta_plot)

        right_widget = QWidget()
        right_widget.setLayout(right)
        main_layout.addWidget(right_widget)

    def _refresh_source_label(self):
        """Met a jour l'affichage de la source EEG et la raison eventuelle du fallback."""
        if self.eeg_source is None:
            self.source_label.setStyleSheet("color: #C62828;")
            self.source_label.setText("Source : ERREUR (aucune source EEG)")
            return
        mode = self.eeg_source.get_mode()
        detail = self.eeg_source.get_status_detail()
        if self.eeg_source.is_native():
            self.source_label.setStyleSheet("color: #2E7D32;")
            if mode == "lsl":
                self.source_label.setText("Source : CASQUE UNICORN (LSL) - connecte")
            elif mode == "gtec_ble":
                self.source_label.setText("Source : CASQUE UNICORN (Bluetooth) - connecte")
            else:
                self.source_label.setText("Source : CASQUE UNICORN - connecte")
            self.log.append(f"[OK] {detail}")
        else:
            self.source_label.setStyleSheet("color: #C62828;")
            self.source_label.setText("Source : SIMULATEUR (casque non connecte)")
            if detail:
                self.log.append(f"[SIMULATEUR] {detail}")
            self.log.append(
                "Astuce : ouvre 'Unicorn LSL' (bouton ci-dessous), selectionne le casque "
                "(UN-...), clique Open puis Start, puis clique 'Reconnecter le casque'."
            )

    def _find_unicorn_lsl(self):
        """Cherche UnicornLSL.exe dans les emplacements connus d'Unicorn Suite."""
        patterns = [
            os.path.join(os.path.expanduser("~"), "Documents", "gtec", "Unicorn Suite",
                         "Hybrid Black", "Unicorn LSL", "UnicornLSL.exe"),
            r"C:\Program Files\gtec\Unicorn Suite\Hybrid Black\Unicorn LSL\UnicornLSL.exe",
            os.path.join(os.path.expanduser("~"), "Documents", "gtec", "**", "UnicornLSL.exe"),
            r"C:\Program Files\gtec\**\UnicornLSL.exe",
        ]
        for pat in patterns:
            for match in glob.glob(pat, recursive=True):
                if os.path.isfile(match):
                    return match
        return None

    def _open_unicorn_lsl(self):
        """Lance l'application Unicorn LSL pour demarrer le streaming du casque."""
        exe = self._find_unicorn_lsl()
        if not exe:
            self.log.append(
                "[X] UnicornLSL.exe introuvable. Ouvre-le manuellement depuis "
                "Unicorn Suite, puis clique 'Reconnecter le casque'."
            )
            return
        try:
            subprocess.Popen([exe], cwd=os.path.dirname(exe))
            self.log.append(
                "Unicorn LSL lance. Dans sa fenetre : selectionne le casque (UN-...), "
                "clique 'Open' puis 'Start', puis reviens cliquer 'Reconnecter le casque'."
            )
        except Exception as e:
            logger.exception("Echec lancement UnicornLSL")
            self.log.append(f"[ERREUR] Impossible de lancer Unicorn LSL : {e}")

    def _reconnect(self):
        """Retente la connexion au casque sans redemarrer l'application."""
        was_running = self.timer.isActive()
        self.timer.stop()
        self.log.append("--- Tentative de reconnexion au casque... ---")
        self.btn_reconnect.setEnabled(False)
        self.btn_reconnect.setText(" Reconnexion en cours...")
        QApplication.processEvents()
        try:
            if self.eeg_source is None:
                self.eeg_source = UnifiedEEGSource()
            else:
                self.eeg_source.reconnect()
        except Exception as e:
            logger.exception("Erreur pendant la reconnexion")
            self.log.append(f"[ERREUR reconnexion] {e}")
        self.btn_reconnect.setEnabled(True)
        self.btn_reconnect.setText(" Reconnecter le casque")
        self._refresh_source_label()
        mode = self.eeg_source.get_mode() if self.eeg_source else "aucune"
        logger.info(f"Reconnexion terminee | Source EEG: {mode}")
        if was_running and self.eeg_source is not None:
            self.timer.start(250)

    def _start(self):
        if self.eeg_source is None:
            self.log.append("[X] Aucune source EEG. Clique 'Reconnecter le casque' d'abord.")
            return
        self.timer.start(250)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log.append("Dashboard demarre.")
        mode = self.eeg_source.get_mode()
        logger.info(f"=== Dashboard demarre | Source EEG: {mode} | "
                    f"ML: {self.detector.uses_ml} | Profil: {self.mapper.profile} ===")
        self._last_logged_state = None

    def _stop(self):
        self.timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.log.append("Dashboard arrete.")

    def _update(self):
        if self.eeg_source is None:
            return
        try:
            if not self.eeg_source.is_native():
                self.eeg_source.set_state(self._next_demo_state())
            eeg = self.eeg_source.read_window(1.0)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            state = self.detector.detect(features)
            alpha = features["alpha"]
            beta = features["beta"]
            # Logger uniquement quand l'etat change (evite le spam)
            if state != getattr(self, "_last_logged_state", None):
                logger.info(f"Etat mental detecte: {state} | alpha={alpha:.1f} beta={beta:.1f}")
                self._last_logged_state = state
            self.alpha_history.append(alpha)
            self.beta_history.append(beta)
            value = {"OPEN": 1.0, "CLOSE": -1.0, "IDLE": 0.0}.get(state, 0.0)
            self.command_history.append(value)
            x = list(range(len(self.alpha_history)))
            self.alpha_curve.setData(x, list(self.alpha_history))
            self.beta_curve.setData(x, list(self.beta_history))
            self.gauge_line.setData(x, list(self.command_history))
            color = COLORS.get(state, COLORS["IDLE"])
            self.status_label.setText(f"ETAT : {state}")
            self.status_label.setStyleSheet(
                f"color: {color}; background-color: white; border: 4px solid {color}; border-radius: 20px; padding: 20px;"
            )
            self.gauge_line.setPen(pg.mkPen(color=color, width=4))
            self.detail_label.setText(f"alpha={alpha:.1f}  beta={beta:.1f}")
            cmd = self.mapper.map(state)
            packet = CommandPacket(
                action=cmd["action"], value=cmd["value"], label=cmd["label"], timestamp=time.time()
            )
            client = self._get_client()
            if client:
                try:
                    client.send(packet)
                    logger.info(f"Commande envoyee (UDP): action={cmd['action']} value={cmd['value']:.1f} label={cmd['label']}")
                except Exception as e:
                    logger.warning(f"Erreur envoi UDP : {e}")
            lsl = self._get_lsl()
            if lsl:
                try:
                    lsl.send(packet)
                    logger.info(f"Commande envoyee (LSL): action={cmd['action']} label={cmd['label']}")
                except Exception as e:
                    logger.warning(f"Erreur envoi LSL : {e}")
            self.log.append(f"[{time.strftime('%H:%M:%S')}] {state} | a={alpha:.1f} b={beta:.1f}")
        except Exception as e:
            logger.exception("Erreur dans _update")
            self.log.append(f"[ERREUR] {e}")

    def _next_demo_state(self):
        t = time.time() % 12
        if t < 4:
            return "OPEN"
        if t < 8:
            return "CLOSE"
        return "IDLE"

    def closeEvent(self, event):
        self.timer.stop()
        client = self._get_client()
        if client:
            try:
                client.close()
            except Exception:
                pass
        if self.eeg_source is not None:
            try:
                self.eeg_source.disconnect()
            except Exception:
                pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = DashboardApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
