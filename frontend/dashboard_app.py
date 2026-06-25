"""Dashboard moderne avec graphiques temps reel pour Inclusive Maker."""

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

from inclusive_maker.acquisition.generator import EEGGenerator
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
        self.eeg_generator = EEGGenerator("IDLE")
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

    def _start(self):
        self.timer.start(250)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log.append("Dashboard demarre.")

    def _stop(self):
        self.timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.log.append("Dashboard arrete.")

    def _update(self):
        try:
            self.eeg_generator.set_state(self._next_demo_state())
            eeg = self.eeg_generator.read_window(1.0)
            features = compute_all_bandpowers(eeg, EEG_SAMPLING_RATE, BANDS)
            state = self.detector.detect(features)
            alpha = features["alpha"]
            beta = features["beta"]
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
                except Exception as e:
                    logger.warning(f"Erreur envoi UDP : {e}")
            lsl = self._get_lsl()
            if lsl:
                try:
                    lsl.send(packet)
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
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = DashboardApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
