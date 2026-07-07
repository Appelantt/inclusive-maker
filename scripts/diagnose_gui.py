#!/usr/bin/env python3
"""Diagnostic capteur par capteur - Interface graphique 100% gpype natif.

Utilise gp.MainApp + app.add_widget (le pattern officiel gpype) comme le
code de reference. Le TimeSeriesScope natif est ajoute via add_widget() ce
qui demarre son timer de rafraichissement automatiquement.

Layout (grille 4x3) :
  [Tete]     [EEG temps reel (8 canaux) - gp.TimeSeriesScope natif]
  [Boutons]  [Barres d'amplitude par canal]
  [Stats]    [Stats suite]

Usage :
    venv\\Scripts\\python.exe scripts\\diagnose_gui.py [--sim] [--serial UN-xxxx]
"""

import argparse
import os
import sys
import time
import json
import threading
import numpy as np

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gpype as gp  # noqa: E402
from gpype.backend.core.node import Node  # noqa: E402
Node._is_executed_in_ide = lambda self: True

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402
import pyqtgraph as pg  # noqa: E402

ELECTRODES = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "PO8", "Oz"]
FS = 250.0
MOTOR_CHANNEL = 1  # C3 = canal 1 (cortex moteur gauche = main droite)
CALIB_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "calibration.json")

ELECTRODE_POS = {
    "Fz":  (0.50, 0.18),
    "C3":  (0.26, 0.46),
    "Cz":  (0.50, 0.46),
    "C4":  (0.74, 0.46),
    "Pz":  (0.50, 0.72),
    "PO7": (0.32, 0.82),
    "PO8": (0.68, 0.82),
    "Oz":  (0.50, 0.90),
}


def list_serials():
    try:
        from gpype.backend.sources.hybrid_black import _ensure_unicorn_path
        _ensure_unicorn_path()
        import UnicornPy
        return list(UnicornPy.GetAvailableDevices(True) or [])
    except Exception:
        return []


def _is_connect_error(exc):
    return "couldn't connect" in str(exc).lower()


def load_calibration():
    """Charge la calibration LDA {wa, wb, bias} si presente, sinon None."""
    try:
        with open(CALIB_PATH, encoding="utf-8") as f:
            c = json.load(f)
        return float(c["wa"]), float(c["wb"]), float(c["bias"])
    except Exception:
        return None


# ======================================================================
#  WIDGET : Etat de la main (OUVERTE / FERMEE)
# ======================================================================
class HandStateWidget(QtWidgets.QWidget):
    """Affiche l'etat de la main en grand : OUVERTE (vert) ou FERMEE (rouge)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self.setStyleSheet("background-color: #2b2b2b; border-radius: 8px;")
        self._state = None  # None, +1 (FERME), -1 (OUVERT)
        self._alpha = 0.0
        self._beta = 0.0
        self._command = 0.0

    def set_state(self, state, alpha=0.0, beta=0.0, command=0.0):
        self._state = state
        self._alpha = alpha
        self._beta = beta
        self._command = command
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Fond selon l'etat
        if self._state is None:
            bg_color = QtGui.QColor("#2b2b2b")
            text = "EN ATTENTE"
            text_color = QtGui.QColor("#888")
        elif self._state >= 0:
            bg_color = QtGui.QColor("#c0392b")  # rouge = FERME
            bg_color.setAlpha(180)
            text = "MAIN FERMEE"
            text_color = QtGui.QColor("#fff")
        else:
            bg_color = QtGui.QColor("#27ae60")  # vert = OUVERT
            bg_color.setAlpha(180)
            text = "MAIN OUVERTE"
            text_color = QtGui.QColor("#fff")

        painter.fillRect(self.rect(), bg_color)

        # Texte principal (grand)
        painter.setFont(QtGui.QFont("Segoe UI", 18, QtGui.QFont.Weight.Bold))
        painter.setPen(text_color)
        painter.drawText(QtCore.QRectF(0, 10, w, 40),
                         QtCore.Qt.AlignmentFlag.AlignCenter, text)

        # Valeurs alpha/beta/commande (petit)
        painter.setFont(QtGui.QFont("Consolas", 9))
        painter.setPen(QtGui.QColor("#ccc"))
        info = f"alpha={self._alpha:.4f}  beta={self._beta:.4f}  cmd={self._command:+.4f}"
        painter.drawText(QtCore.QRectF(0, 50, w, 20),
                         QtCore.Qt.AlignmentFlag.AlignCenter, info)

        painter.end()


# ======================================================================
#  WIDGET : Tete avec electrodes colorees
# ======================================================================
class HeadMapWidget(QtWidgets.QWidget):
    """Tete vue de dessus avec electrodes colorees selon la qualite."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 300)
        self._qualities = [None] * 8
        self._active = False

    def set_quality(self, ch, label):
        if 0 <= ch < 8:
            self._qualities[ch] = label
            self.update()

    def set_active(self, active):
        self._active = active
        self.update()

    def _qcolor(self, label):
        if label is None:
            return QtGui.QColor("#666")
        if "BON" in label or "OK" in label:
            return QtGui.QColor("#27ae60")
        elif "MEDIOCRE" in label or "BRUIT?" in label:
            return QtGui.QColor("#f1c40f")
        elif "MAUVAIS" in label or "BRUIT" in label:
            return QtGui.QColor("#e67e22")
        else:
            return QtGui.QColor("#c0392b")

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 + 10
        radius = min(w, h) * 0.40

        # Tete
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#333")))
        painter.setPen(QtGui.QPen(QtGui.QColor("#888"), 2))
        painter.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)

        # Nez
        nose = QtGui.QPolygonF([
            QtCore.QPointF(cx, cy - radius - 10),
            QtCore.QPointF(cx - 8, cy - radius),
            QtCore.QPointF(cx + 8, cy - radius),
        ])
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#555")))
        painter.drawPolygon(nose)

        # Electrodes
        for i, name in enumerate(ELECTRODES):
            ex = ELECTRODE_POS[name][0] * w
            ey = ELECTRODE_POS[name][1] * h
            color = self._qcolor(self._qualities[i]) if self._active else QtGui.QColor("#666")
            r = 13
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(QtGui.QColor("#ddd"), 1.5))
            painter.drawEllipse(QtCore.QPointF(ex, ey), r, r)
            painter.setFont(QtGui.QFont("Segoe UI", 7, QtGui.QFont.Weight.Bold))
            painter.setPen(QtGui.QColor("#fff"))
            painter.drawText(QtCore.QRectF(ex - r, ey - r, 2 * r, 2 * r),
                             QtCore.Qt.AlignmentFlag.AlignCenter, name)

        # Statut
        painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Weight.Bold))
        if self._active:
            painter.setPen(QtGui.QColor("#27ae60"))
            painter.drawText(QtCore.QRectF(10, 3, w - 20, 16),
                             QtCore.Qt.AlignmentFlag.AlignCenter, "* Acquisition active")
        else:
            painter.setPen(QtGui.QColor("#888"))
            painter.drawText(QtCore.QRectF(10, 3, w - 20, 16),
                             QtCore.Qt.AlignmentFlag.AlignCenter, "o En attente...")

        painter.end()


# ======================================================================
#  WIDGET : Statistiques par canal (paintEvent custom)
# ======================================================================
class SensorStatsWidget(QtWidgets.QWidget):
    """Tableau de statistiques par canal avec code couleur."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(340)
        self.setMinimumHeight(300)
        self.setStyleSheet("background-color: #1e1e1e;")
        self._stats = []
        self._active = False

    def set_stats(self, stats):
        self._stats = stats
        self.update()

    def set_active(self, active):
        self._active = active
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Titre
        painter.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Weight.Bold))
        painter.setPen(QtGui.QColor("#00d4ff"))
        painter.drawText(QtCore.QRectF(10, 5, w - 20, 22),
                         QtCore.Qt.AlignmentFlag.AlignLeft, "  Statistiques par capteur")
        painter.setPen(QtGui.QPen(QtGui.QColor("#444"), 1))
        painter.drawLine(10, 28, w - 10, 28)

        if not self._stats:
            painter.setFont(QtGui.QFont("Segoe UI", 9))
            painter.setPen(QtGui.QColor("#888"))
            painter.drawText(QtCore.QRectF(10, 35, w - 20, 20),
                             QtCore.Qt.AlignmentFlag.AlignCenter,
                             "En attente de connexion..." if not self._active
                             else "Collecte des donnees...")
            painter.end()
            return

        # En-tetes
        y0 = 38
        painter.setFont(QtGui.QFont("Consolas", 8))
        painter.setPen(QtGui.QColor("#888"))
        painter.drawText(15, y0, "Ch")
        painter.drawText(50, y0, "Electrode")
        painter.drawText(130, y0, "std(diff)")
        painter.drawText(220, y0, "Ratio")
        painter.drawText(280, y0, "Qualite")
        y0 += 8
        painter.setPen(QtGui.QPen(QtGui.QColor("#333"), 1))
        painter.drawLine(10, y0, w - 10, y0)
        y0 += 6

        row_h = 26
        for i, (std_val, ratio, label) in enumerate(self._stats):
            y = y0 + i * row_h

            # Couleur de qualite
            if "BON" in label or "OK" in label:
                color = QtGui.QColor("#27ae60")
            elif "MEDIOCRE" in label or "BRUIT?" in label:
                color = QtGui.QColor("#f1c40f")
            elif "MAUVAIS" in label or "BRUIT" in label:
                color = QtGui.QColor("#e67e22")
            else:
                color = QtGui.QColor("#c0392b")

            # Fond colore subtil
            bg = QtGui.QColor(color)
            bg.setAlpha(30)
            painter.fillRect(QtCore.QRectF(10, y - 2, w - 20, row_h - 4), bg)

            painter.setFont(QtGui.QFont("Consolas", 9))
            painter.setPen(QtGui.QColor("#ccc"))
            painter.drawText(15, y + 14, str(i))
            painter.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Weight.Bold))
            painter.setPen(QtGui.QColor("#fff"))
            painter.drawText(50, y + 14, ELECTRODES[i])
            painter.setFont(QtGui.QFont("Consolas", 9))
            painter.setPen(QtGui.QColor("#ccc"))
            painter.drawText(130, y + 14, f"{std_val:.4f}")
            painter.drawText(220, y + 14, f"{ratio:.2f}")

            # Pastille + texte qualite
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(QtGui.QColor("#ddd"), 1))
            painter.drawEllipse(QtCore.QPointF(290, y + 10), 7, 7)
            painter.setPen(color)
            painter.setFont(QtGui.QFont("Segoe UI", 8, QtGui.QFont.Weight.Bold))
            painter.drawText(305, y + 14, label)

        painter.end()


# ======================================================================
#  WIDGET : Barres d'amplitude (pyqtgraph)
# ======================================================================
class AmplitudeBarsWidget(pg.PlotWidget):
    """Barres horizontales montrant l'amplitude std(diff) par canal."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground("#1e1e1e")
        self.setLabel("bottom", "Amplitude std(diff) / mediane (sans DC)")
        self.setLabel("left", "Canal")
        self.showGrid(x=True, alpha=0.3)
        self.setMouseEnabled(x=False, y=False)
        self.setYRange(-0.5, 7.5)
        self.setXRange(0, 2)
        self.getPlotItem().getAxis("left").setTicks([
            [(i, ELECTRODES[i]) for i in range(8)]
        ])
        self._bars = []

    def update_bars(self, std_vals):
        if not std_vals:
            return

        # Retirer les anciennes barres
        for b in self._bars:
            self.removeItem(b)
        self._bars = []

        med = max(float(np.median(std_vals)), 1e-6)
        max_norm = 0

        for ch in range(8):
            ratio = std_vals[ch] / med
            norm = min(ratio, 5.0)
            max_norm = max(max_norm, norm)

            if std_vals[ch] < 1e-3 or ratio < 0.3:
                color = "#c0392b"
            elif ratio < 0.6:
                color = "#e67e22"
            elif ratio < 0.85:
                color = "#f1c40f"
            elif ratio < 1.2:
                color = "#27ae60"
            elif ratio < 2.0:
                color = "#f1c40f"
            else:
                color = "#c0392b"

            # Utiliser un simple rectangle (InfiniteRectItem ou BarGraphItem)
            bar = pg.BarGraphItem(
                x0=[0], x1=[norm],
                y0=[ch - 0.3], y1=[ch + 0.3],
                brush=QtGui.QBrush(QtGui.QColor(color)),
                pen=QtGui.QPen(QtGui.QColor(color)),
            )
            self._bars.append(bar)
            self.addItem(bar)

        self.setXRange(0, max(max_norm * 1.2, 1.5))


# ======================================================================
#  NODE : DashboardSink (capture alpha/beta/commande/etat pour l'UI)
# ======================================================================
class DashboardSink(gp.INode):
    """Node gpype qui capture alpha, beta, commande, etat pour l'UI."""

    def __init__(self):
        from gpype.backend.core.i_port import IPort
        import ioiocore as ioc
        input_ports = [IPort.Configuration(name=ioc.Constants.Defaults.PORT_IN)]
        super().__init__(input_ports=input_ports)
        self._alpha = 0.0
        self._beta = 0.0
        self._command = 0.0
        self._state = 0.0
        self._lock = threading.Lock()

    def step(self, data):
        raw = data.get("in")
        if raw is None:
            raw = data.get("data")
        if raw is not None and len(raw) > 0:
            last = np.asarray(raw)[-1]
            if len(last) >= 4:
                with self._lock:
                    self._alpha = float(last[0])
                    self._beta = float(last[1])
                    self._command = float(last[2])
                    self._state = float(last[3])

    def get_values(self):
        with self._lock:
            return self._alpha, self._beta, self._command, self._state


# ======================================================================
#  CLASSE PRINCIPALE : DiagnosticApp (utilise gp.MainApp natif)
# ======================================================================
class DiagnosticApp:
    """Application de diagnostic utilisant gp.MainApp natif gpype.

    Pattern identique au code de reference :
      app = gp.MainApp()
      app.add_widget(scope)
      p.start()
      app.run()
      p.stop()
    """

    def __init__(self):
        # --- Creation de l'application gpype native ---
        self._app = gp.MainApp(
            caption="Diagnostic capteurs - Unicorn Hybrid Black (gpype)",
            position=[50, 50, 1300, 800],
            grid_size=[4, 3],
        )

        # Widgets custom (pas des widgets gpype, on les ajoute manuellement)
        self.head_map = HeadMapWidget()
        self.stats_widget = SensorStatsWidget()
        self.bars_widget = AmplitudeBarsWidget()
        self.hand_state = HandStateWidget()

        # --- TimeSeriesScope natif gpype (le scope EEG temps reel) ---
        self.gp_scope = gp.TimeSeriesScope(
            amplitude_limit=100,
            time_window=10,
            name="EEG temps reel (8 canaux)",
        )

        # --- Boutons ---
        self.btn_sim = QtWidgets.QPushButton("Mode Simulation")
        self.btn_connect = QtWidgets.QPushButton("Connecter casque")
        self.btn_stop = QtWidgets.QPushButton("Arreter")
        self.btn_sim.setStyleSheet(self._btn_style("#2980b9"))
        self.btn_connect.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_stop.setStyleSheet(self._btn_style("#c0392b"))
        self.btn_sim.clicked.connect(self._on_sim)
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)

        # Combo casques
        self.combo_devices = QtWidgets.QComboBox()
        self.combo_devices.setStyleSheet("QComboBox { background: #333; color: #fff; padding: 4px; }")

        # Label de statut
        self.status_label = QtWidgets.QLabel("En attente...")
        self.status_label.setStyleSheet("color: #aaa; font-size: 10px; padding: 4px;")

        # --- Layout de la colonne gauche (tete + boutons) ---
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)

        # Groupe tete
        head_group = QtWidgets.QGroupBox("Casque")
        head_inner = QtWidgets.QVBoxLayout()
        head_inner.addWidget(self.head_map)
        head_inner.addWidget(QtWidgets.QLabel("Casque:"))
        head_inner.addWidget(self.combo_devices)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.btn_sim)
        btn_row.addWidget(self.btn_connect)
        btn_row.addWidget(self.btn_stop)
        head_inner.addLayout(btn_row)
        head_inner.addWidget(self.status_label)
        head_group.setLayout(head_inner)
        head_group.setStyleSheet(self._group_style())
        left_layout.addWidget(head_group)

        # Groupe etat de la main
        hand_group = QtWidgets.QGroupBox("Etat de la main")
        hand_inner = QtWidgets.QVBoxLayout()
        hand_inner.addWidget(self.hand_state)
        hand_group.setLayout(hand_inner)
        hand_group.setStyleSheet(self._group_style())
        left_layout.addWidget(hand_group)

        # Groupe stats
        stats_group = QtWidgets.QGroupBox("Statistiques")
        stats_inner = QtWidgets.QVBoxLayout()
        stats_inner.addWidget(self.stats_widget)
        stats_group.setLayout(stats_inner)
        stats_group.setStyleSheet(self._group_style())
        left_layout.addWidget(stats_group)

        # --- Ajout des widgets dans la grille de MainApp ---
        # Le scope gpype natif est ajoute via add_widget() -> timer demarre
        self._app.add_widget(self.gp_scope, grid_positions=[2, 3, 4, 5, 8])

        # Les widgets custom sont ajoutes directement dans le layout
        self._app._layout.addWidget(left_widget, 0, 0, 3, 1)
        self._app._layout.addWidget(self.bars_widget, 3, 1, 1, 2)

        # --- Etat interne ---
        self._pipeline = None
        self._running = False
        self._sink = None

        # Timer pour rafraichir les stats (2 Hz)
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(500)

        # Remplir la liste des casques
        self._refresh_devices()

    def _btn_style(self, color):
        return (f"QPushButton {{ background-color: {color}; color: white; "
                f"border: none; padding: 8px 12px; border-radius: 4px; "
                f"font-weight: bold; }} "
                f"QPushButton:hover {{ background-color: {color}cc; }} "
                f"QPushButton:disabled {{ background-color: #555; color: #999; }}")

    def _group_style(self):
        return ("QGroupBox { color: #00d4ff; font-size: 10px; font-weight: bold; "
                "border: 1px solid #444; border-radius: 6px; margin-top: 10px; "
                "padding-top: 10px; } "
                "QGroupBox::title { subcontrol-origin: margin; "
                "subcontrol-position: top left; padding: 0 6px; }")

    def _refresh_devices(self):
        self.combo_devices.clear()
        devices = list_serials()
        if devices:
            for d in devices:
                self.combo_devices.addItem(d)
        else:
            self.combo_devices.addItem("(aucun casque)")

    def _on_sim(self):
        self._start("sim", None)

    def _on_connect(self):
        serial = None
        idx = self.combo_devices.currentIndex()
        if idx >= 0:
            text = self.combo_devices.itemText(idx)
            if text.startswith("UN-"):
                serial = text
        self._start("casque", serial)

    def _on_stop(self):
        self._stop()

    def _start(self, mode, serial):
        if self._running:
            self._stop()

        self.status_label.setText("Connexion en cours...")
        self.btn_sim.setEnabled(False)
        self.btn_connect.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.head_map.set_active(False)
        self.stats_widget.set_active(False)

        if mode == "sim":
            candidates = ["__sim__"]
        elif serial:
            candidates = [serial]
        else:
            devices = list_serials()
            candidates = devices if devices else []

        if not candidates and mode != "sim":
            self.status_label.setText("Aucun casque detecte.")
            self._reset_buttons()
            return

        for sn in candidates:
            if sn != "__sim__":
                print(f"Tentative de connexion a {sn}...")
            try:
                self._build_and_start(mode, sn)
                return
            except Exception as e:
                if _is_connect_error(e):
                    print(f"  {sn} ne repond pas, essai suivant...")
                    continue
                print(f"ERREUR: {e}")
                import traceback
                traceback.print_exc()
                break

        self.status_label.setText("Aucun casque n'a repondu.")
        self._reset_buttons()

    def _build_and_start(self, mode, sn):
        """Construit le pipeline gpype et le demarre.

        Pipeline complet :
          source -> Bandpass 1-30 Hz + Notch 50/60 Hz -> Scope EEG (8 canaux)
                 -> selection C3 -> alpha (8-12 Hz) + beta (13-30 Hz)
                 -> commande = (beta - alpha) / (alpha + beta + 1)
                 -> etat = sign(commande) ou LDA si calibration
                 -> DashboardSink (capture pour l'UI)
        """
        p = gp.Pipeline()

        # frame_size equilibre : pas trop petit (overflow) ni trop grand (underrun)
        # 5 samples/cycle = 50 cycles/s (bon compromis pour le Bluetooth)
        FRAME_SIZE = 5

        if sn == "__sim__":
            source = gp.Generator(
                sampling_rate=FS, channel_count=8,
                signal_frequency=10, signal_amplitude=15,
                noise_amplitude=10, frame_size=FRAME_SIZE,
            )
            self.status_label.setText("Mode simulation actif")
        else:
            source = gp.HybridBlack(serial=sn, frame_size=FRAME_SIZE)
            self.status_label.setText(f"Connecte a {sn}")

        # --- Filtrage (comme le code de reference) ---
        bandpass = gp.Bandpass(f_lo=1, f_hi=30)
        notch50 = gp.Bandstop(f_lo=48, f_hi=52)
        notch60 = gp.Bandstop(f_lo=58, f_hi=62)

        # Chaine filtrage -> scope EEG (8 canaux temps reel)
        p.connect(source, bandpass)
        p.connect(bandpass, notch50)
        p.connect(notch50, notch60)
        p.connect(notch60, self.gp_scope)

        # --- Pipeline BCI : alpha/beta sur C3 ---
        # Selection du canal moteur C3
        select_c3 = gp.Router(input_channels=gp.Router.ALL,
                              output_channels={"c3": [MOTOR_CHANNEL]})
        p.connect(notch60, select_c3)

        # Puissance ALPHA (8-12 Hz) : bande -> carre -> moyenne glissante 1 s
        alpha_band = gp.Bandpass(f_lo=8, f_hi=12)
        alpha_pow = gp.Equation("in**2")
        alpha_avg = gp.MovingAverage(window_size=250)
        p.connect(select_c3["c3"], alpha_band)
        p.connect(alpha_band, alpha_pow)
        p.connect(alpha_pow, alpha_avg)

        # Puissance BETA (13-30 Hz)
        beta_band = gp.Bandpass(f_lo=13, f_hi=30)
        beta_pow = gp.Equation("in**2")
        beta_avg = gp.MovingAverage(window_size=250)
        p.connect(select_c3["c3"], beta_band)
        p.connect(beta_band, beta_pow)
        p.connect(beta_pow, beta_avg)

        # Commande = (beta - alpha) / (alpha + beta + 1)
        command = gp.Equation("(b - a) / (a + b + 1)")
        p.connect(alpha_avg, command["a"])
        p.connect(beta_avg, command["b"])

        # Etat binaire : +1 = FERME, -1 = OUVERT
        calib = load_calibration()
        if calib is not None:
            wa, wb, bias = calib
            print(f"Calibration LDA chargee : etat = sign({wa:.4g}*a + {wb:.4g}*b + {bias:.4g})")
            etat = gp.Equation(f"sign(({wa!r})*a + ({wb!r})*b + ({bias!r}))")
            p.connect(alpha_avg, etat["a"])
            p.connect(beta_avg, etat["b"])
        else:
            print("Pas de calibration : etat = sign(commande).")
            etat = gp.Equation("sign(c)")
            p.connect(command, etat["c"])

        # Merger [alpha, beta, commande, etat] pour le DashboardSink
        merger = gp.Router(
            input_channels={"alpha": [0], "beta": [0],
                            "commande": [0], "etat": [0]},
            output_channels=[gp.Router.ALL],
        )
        p.connect(alpha_avg, merger["alpha"])
        p.connect(beta_avg, merger["beta"])
        p.connect(command, merger["commande"])
        p.connect(etat, merger["etat"])

        # Sink custom pour capturer les valeurs pour l'UI
        self._sink = DashboardSink()
        p.connect(merger, self._sink)

        # Demarrage
        p.start()
        self._pipeline = p
        self._running = True
        self.head_map.set_active(True)
        self.stats_widget.set_active(True)
        print("Pipeline demarre. Diagnostic actif.")
        print("(ferme la fenetre pour arreter)")

    def _stop(self):
        if self._pipeline is not None:
            try:
                self._pipeline.stop()
            except Exception:
                pass
            self._pipeline = None
        self._running = False
        self.head_map.set_active(False)
        self.stats_widget.set_active(False)
        self.status_label.setText("Arrete.")
        self._reset_buttons()

    def _reset_buttons(self):
        self.btn_sim.setEnabled(True)
        self.btn_connect.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _refresh_stats(self):
        """Calcule les stats depuis le _data_buffer du scope gpype natif."""
        if not self._running:
            return

        buf = self.gp_scope._data_buffer
        if buf is None or buf.shape[0] < 50:
            return

        eeg = buf[:, :8]
        # std(diff) pour retirer la derive DC
        std_vals = [float(np.std(np.diff(eeg[:, ch]))) for ch in range(8)]
        median_std = max(float(np.median(std_vals)), 1e-6)

        stats = []
        for ch in range(8):
            ratio = std_vals[ch] / median_std
            if std_vals[ch] < 1e-3:
                label = "DECONNECTE"
            elif ratio < 0.3:
                label = "DECONNECTE"
            elif ratio < 0.6:
                label = "MAUVAIS"
            elif ratio < 0.85:
                label = "MEDIOCRE"
            elif ratio < 1.2:
                label = "BON"
            elif ratio < 1.5:
                label = "OK"
            elif ratio < 2.0:
                label = "BRUIT?"
            elif ratio < 3.0:
                label = "BRUIT"
            else:
                label = "DEBRUIT"
            stats.append((std_vals[ch], ratio, label))

        self.stats_widget.set_stats(stats)
        self.bars_widget.update_bars(std_vals)

        for ch in range(8):
            self.head_map.set_quality(ch, stats[ch][2])

        # --- Etat de la main (from DashboardSink) ---
        if self._sink is not None:
            alpha, beta, cmd, etat = self._sink.get_values()
            self.hand_state.set_state(etat, alpha, beta, cmd)

    def run(self):
        """Lance l'application gpype native (bloquant jusqu'a fermeture)."""
        return self._app.run()

    def stop(self):
        self._stop()


# ======================================================================
#  MAIN
# ======================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Diagnostic capteurs - Interface graphique gpype native"
    )
    parser.add_argument("--sim", action="store_true", help="Demarrer en simulation")
    parser.add_argument("--serial", default=None, help="Numero de serie")
    args = parser.parse_args()

    print()
    print("  DIAGNOSTIC CAPTEURS - Unicorn Hybrid Black (gpype natif)")
    print("  Interface graphique avec TimeSeriesScope natif gpype")
    print()
    print("  >>> Allume le casque, FERME Unicorn Suite/LSL/Recorder <<<")
    print()

    diag = DiagnosticApp()

    if args.sim:
        QtCore.QTimer.singleShot(500, diag._on_sim)

    diag.run()
    diag.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())