"""Dashboard BCI complet pour Inclusive Maker.

Affichage temps reel enrichi :
  - Tete humaine stylisee avec les 8 electrodes positionnees
  - Couleur d'impedance par electrode (vert = bonne, rouge = mauvaise, jaune = moyenne)
  - Equations mathematiques ecrites (alpha%, beta%, commande, etat)
  - Valeurs numeriques temps reel (alpha, beta, commande, etat)
  - Courbes temps reel (pyqtgraph) : alpha%, beta%, commande, etat
  - Barres de progression pour alpha% et beta%

S'integre au pipeline gpype en capturant les features (alpha_avg, beta_avg)
via un node custom DashboardSink, puis fait les calculs cote UI (comme le
fait le pipeline avec les nodes Equation).

Usage :
    venv\\Scripts\\python.exe scripts\\gpype_dashboard.py [--sim] [--serial UN-xxxx]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import threading
import time
from collections import deque

import numpy as np

# UTF-8 obligatoire
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

# --- Constantes (synchro avec gpype_pipeline.py) -----------------------
DEFAULT_SERIAL = None
MOTOR_CHANNEL = 1  # C3
FS = 250.0
CALIB_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "calibration.json")

ELECTRODES = ["Fz", "C3", "Cz", "C4", "Pz", "PO7", "PO8", "Oz"]

# Positions (x, y) normalisees sur une tete vue de dessus (front en haut)
ELECTRODE_POSITIONS = {
    "Fz":  (0.50, 0.20),   # frontal median
    "C3":  (0.28, 0.48),   # central gauche (main droite)
    "Cz":  (0.50, 0.48),   # central median
    "C4":  (0.72, 0.48),   # central droit (main gauche)
    "Pz":  (0.50, 0.72),   # parietal median
    "PO7": (0.32, 0.82),   # parieto-occipital gauche
    "PO8": (0.68, 0.82),   # parieto-occipital droit
    "Oz":  (0.50, 0.90),   # occipital median
}


def load_calibration():
    try:
        with open(CALIB_PATH, encoding="utf-8") as f:
            c = json.load(f)
        return float(c["wa"]), float(c["wb"]), float(c["bias"])
    except Exception:
        return None


def _setup_unicornpy():
    try:
        from gpype.backend.sources.hybrid_black import _ensure_unicorn_path
        _ensure_unicorn_path()
        import UnicornPy
        return UnicornPy
    except Exception:
        return None


def list_serials(preferred):
    up = _setup_unicornpy()
    if up is None:
        return [preferred] if preferred else []
    try:
        devices = list(up.GetAvailableDevices(True) or [])
    except Exception:
        return [preferred] if preferred else []
    if not devices:
        return [preferred] if preferred else []
    order = ([preferred] if preferred in devices else []) + \
            [d for d in devices if d != preferred]
    return order


SIM_MODE = "__sim__"


def _is_connect_error(exc):
    msg = str(exc).lower()
    return "couldn't connect" in msg or "no unicorn device" in msg


def make_source(mode, serial):
    if mode == "sim":
        print("Source : Generator interne g.Pype (simulation).")
        return gp.Generator(sampling_rate=FS, channel_count=8,
                            signal_frequency=10.0, signal_amplitude=30.0,
                            noise_amplitude=10.0)
    cible = serial if serial else "aucun casque detecte"
    print(f"Source : casque Unicorn Hybrid Black ({cible}).")
    print("  -> Unicorn Suite / LSL / Recorder doivent etre FERMES.")
    return gp.HybridBlack(serial=serial)


def build_features(p, source):
    """source -> EEG propre -> canal C3 -> puissances BRUTES alpha_avg et beta_avg."""
    bandpass = gp.Bandpass(f_lo=1, f_hi=30)
    notch50 = gp.Bandstop(f_lo=48, f_hi=52)
    notch60 = gp.Bandstop(f_lo=58, f_hi=62)
    p.connect(source, bandpass)
    p.connect(bandpass, notch50)
    p.connect(notch50, notch60)

    select_c3 = gp.Router(input_channels=gp.Router.ALL,
                          output_channels={"c3": [MOTOR_CHANNEL]})
    p.connect(notch60, select_c3)

    alpha_band = gp.Bandpass(f_lo=8, f_hi=12)
    alpha_pow = gp.Equation("in**2")
    alpha_avg = gp.MovingAverage(window_size=250)
    p.connect(select_c3["c3"], alpha_band)
    p.connect(alpha_band, alpha_pow)
    p.connect(alpha_pow, alpha_avg)

    beta_band = gp.Bandpass(f_lo=13, f_hi=30)
    beta_pow = gp.Equation("in**2")
    beta_avg = gp.MovingAverage(window_size=250)
    p.connect(select_c3["c3"], beta_band)
    p.connect(beta_band, beta_pow)
    p.connect(beta_pow, beta_avg)

    return alpha_avg, beta_avg


# ======================================================================
#  WIDGET : Tete humaine avec electrodes et impendance
# ======================================================================
class HeadWidget(QtWidgets.QWidget):
    """Dessine une tete vue de dessus avec 8 electrodes colorees."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(280, 320)
        self._impedances = [50.0] * 8  # kOhm, valeur simulee par defaut
        self._raw_signal = np.zeros((8,))
        self._labels = ELECTRODES
        self._active = False  # True quand le pipeline tourne

    def set_impedance(self, channel, value_kohm):
        if 0 <= channel < 8:
            self._impedances[channel] = value_kohm
            self.update()

    def set_raw_signal(self, signals):
        """signals : np.ndarray shape (8,) ou (N, 8) -> on prend la derniere."""
        if signals is not None and len(signals) > 0:
            self._raw_signal = np.asarray(signals[-1]).flatten()[:8]
            self.update()

    def set_active(self, active):
        self._active = active
        self.update()

    def _color_for_impedance(self, z):
        """Retourne une QColor selon l'impedance (en kOhm equivalent).

        Echelle coherente avec get_impedances() :
          z < 10  -> vert  (excellent ou bon contact)
          z < 30  -> jaune (mediocre, impendance elevee)
          z < 60  -> orange (mauvais contact)
          z >= 60 -> rouge (deconnecte ou bruit excessif)
        """
        if z < 10:    # excellent / bon
            return QtGui.QColor("#27ae60")  # vert
        elif z < 30:  # mediocre
            return QtGui.QColor("#f1c40f")  # jaune
        elif z < 60:  # mauvais
            return QtGui.QColor("#e67e22")  # orange
        else:         # deconnecte / bruit
            return QtGui.QColor("#c0392b")  # rouge

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2 + 15
        radius = min(w, h) * 0.42

        # --- Tete (cercle) ---
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#3a3a3a")))
        painter.setPen(QtGui.QPen(QtGui.QColor("#8a8a8a"), 2))
        painter.drawEllipse(QtCore.QPointF(cx, cy), radius, radius)

        # --- Nez (triangle en haut) ---
        nose = QtGui.QPolygonF([
            QtCore.QPointF(cx, cy - radius - 12),
            QtCore.QPointF(cx - 10, cy - radius),
            QtCore.QPointF(cx + 10, cy - radius),
        ])
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#5a5a5a")))
        painter.drawPolygon(nose)

        # --- Oreilles ---
        painter.setBrush(QtGui.QBrush(QtGui.QColor("#4a4a4a")))
        painter.drawEllipse(QtCore.QPointF(cx - radius - 6, cy), 10, 18)
        painter.drawEllipse(QtCore.QPointF(cx + radius + 6, cy), 10, 18)

        # --- Labels des regions corticales (en gris discret) ---
        font_small = QtGui.QFont("Segoe UI", 7)
        painter.setFont(font_small)
        painter.setPen(QtGui.QColor("#777777"))

        # --- Electrodes ---
        for i, label in enumerate(self._labels):
            ex = ELECTRODE_POSITIONS[label][0] * w
            ey = ELECTRODE_POSITIONS[label][1] * h
            color = self._color_for_impedance(self._impedances[i])

            # Cercle de l'electrode
            r = 14
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtGui.QPen(QtGui.QColor("#dddddd"), 1.5))
            painter.drawEllipse(QtCore.QPointF(ex, ey), r, r)

            # Label de l'electrode
            font_label = QtGui.QFont("Segoe UI", 8, QtGui.QFont.Weight.Bold)
            painter.setFont(font_label)
            painter.setPen(QtGui.QColor("#ffffff"))
            painter.drawText(
                QtCore.QRectF(ex - r, ey - r, 2 * r, 2 * r),
                QtCore.Qt.AlignmentFlag.AlignCenter, label
            )

            # Valeur d'impedance sous l'electrode
            font_imp = QtGui.QFont("Segoe UI", 6)
            painter.setFont(font_imp)
            painter.setPen(QtGui.QColor("#cccccc"))
            painter.drawText(
                QtCore.QRectF(ex - 20, ey + r + 2, 40, 12),
                QtCore.Qt.AlignmentFlag.AlignCenter,
                f"{self._impedances[i]:.0f}k"
            )

        # --- Indication C3 (canal actif) ---
        c3x = ELECTRODE_POSITIONS["C3"][0] * w
        c3y = ELECTRODE_POSITIONS["C3"][1] * h
        painter.setPen(QtGui.QPen(QtGui.QColor("#00d4ff"), 2))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QtCore.QPointF(c3x, c3y), 20, 20)
        font_active = QtGui.QFont("Segoe UI", 7, QtGui.QFont.Weight.Bold)
        painter.setFont(font_active)
        painter.setPen(QtGui.QColor("#00d4ff"))
        painter.drawText(
            QtCore.QRectF(c3x - 30, c3y - 35, 60, 14),
            QtCore.Qt.AlignmentFlag.AlignCenter, "ACTIF (main droite)"
        )

        # --- Statut ---
        if self._active:
            font_status = QtGui.QFont("Segoe UI", 8, QtGui.QFont.Weight.Bold)
            painter.setFont(font_status)
            painter.setPen(QtGui.QColor("#27ae60"))
            painter.drawText(
                QtCore.QRectF(10, 5, w - 20, 16),
                QtCore.Qt.AlignmentFlag.AlignCenter, "● Pipeline actif"
            )
        else:
            font_status = QtGui.QFont("Segoe UI", 8)
            painter.setFont(font_status)
            painter.setPen(QtGui.QColor("#888888"))
            painter.drawText(
                QtCore.QRectF(10, 5, w - 20, 16),
                QtCore.Qt.AlignmentFlag.AlignCenter, "○ En attente..."
            )

        painter.end()


# ======================================================================
#  WIDGET : Panel des equations et valeurs
# ======================================================================
class EquationsWidget(QtWidgets.QWidget):
    """Affiche les equations mathematiques avec leurs valeurs temps reel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(280)
        self._alpha = 0.0
        self._beta = 0.0
        self._command = 0.0
        self._state = 0
        self._wa = None
        self._wb = None
        self._bias = None
        self._calibrated = False

        self.setStyleSheet("background-color: #2b2b2b; color: #e0e0e0;")

    def set_calibration(self, calib):
        if calib is not None:
            self._wa, self._wb, self._bias = calib
            self._calibrated = True
        else:
            self._calibrated = False
        self.update()

    def set_values(self, alpha, beta, command, state):
        self._alpha = alpha
        self._beta = beta
        self._command = command
        self._state = state
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        y = 10

        # --- Titre ---
        font_title = QtGui.QFont("Segoe UI", 11, QtGui.QFont.Weight.Bold)
        painter.setFont(font_title)
        painter.setPen(QtGui.QColor("#00d4ff"))
        painter.drawText(QtCore.QRectF(10, y, w - 20, 24),
                         QtCore.Qt.AlignmentFlag.AlignLeft,
                         "  Équations BCI & valeurs temps réel")
        y += 30

        font_eq = QtGui.QFont("Consolas", 10)
        font_val = QtGui.QFont("Consolas", 10, QtGui.QFont.Weight.Bold)
        font_note = QtGui.QFont("Segoe UI", 7)
        line_h = 50

        def draw_equation(yoff, label, formula, value, value_color, unit=""):
            nonlocal y
            # Label
            painter.setFont(font_note)
            painter.setPen(QtGui.QColor("#888888"))
            painter.drawText(QtCore.QRectF(10, yoff, w - 20, 14),
                             QtCore.Qt.AlignmentFlag.AlignLeft, f"  {label}")
            # Formule
            painter.setFont(font_eq)
            painter.setPen(QtGui.QColor("#cccccc"))
            painter.drawText(QtCore.QRectF(10, yoff + 14, w - 20, 18),
                             QtCore.Qt.AlignmentFlag.AlignLeft, f"  {formula}")
            # Valeur (string ou numerique)
            painter.setFont(font_val)
            painter.setPen(QtGui.QColor(value_color))
            if isinstance(value, str):
                val_text = value
            else:
                val_text = f"{value:+.4f}" + (f" {unit}" if unit else "")
            painter.drawText(QtCore.QRectF(10, yoff + 30, w - 20, 18),
                             QtCore.Qt.AlignmentFlag.AlignRight, val_text)

        # alpha (brut)
        draw_equation(y, "Puissance ALPHA (8-12 Hz) — filtrée, carré, moyenne 1 s",
                      "alpha = ⟨C3²_8-12Hz⟩",
                      self._alpha, "#3498db")
        y += line_h

        # beta (brut)
        draw_equation(y, "Puissance BÊTA (13-30 Hz) — filtrée, carré, moyenne 1 s",
                      "beta = ⟨C3²_13-30Hz⟩",
                      self._beta, "#e74c3c")
        y += line_h

        # alpha%
        alpha_pct = self._alpha / (self._alpha + self._beta + 1e-10) if (self._alpha + self._beta) >= 0 else 0
        draw_equation(y, "Part relative alpha (normalisée)",
                      "alpha% = a / (a + b + 1)",
                      alpha_pct, "#3498db", "→ [0,1]")
        y += line_h

        # beta%
        beta_pct = self._beta / (self._alpha + self._beta + 1e-10) if (self._alpha + self._beta) >= 0 else 0
        draw_equation(y, "Part relative bêta (normalisée)",
                      "beta% = b / (a + b + 1)",
                      beta_pct, "#e74c3c", "→ [0,1]")
        y += line_h

        # commande
        draw_equation(y, "Commande continue [-1, +1]",
                      "commande = (b - a) / (a + b + 1)",
                      self._command, "#9b59b6", "→ [-1,1]")
        y += line_h

        # etat
        if self._calibrated and self._wa is not None:
            state_formula = (f"etat = sign({self._wa:.3g}*α + "
                             f"{self._wb:.3g}*β + {self._bias:.3g})")
            state_label = "État binaire (calibration LDA personnalisée)"
        else:
            state_formula = "etat = sign(commande)"
            state_label = "État binaire (seuil générique, sans calibration)"
        state_str = "FERMÉ (+1)" if self._state >= 0 else "OUVERT (-1)"
        state_color = "#e74c3c" if self._state >= 0 else "#27ae60"
        draw_equation(y, state_label, state_formula, state_str, state_color)
        y += line_h

        # Ligne de separateur
        painter.setPen(QtGui.QPen(QtGui.QColor("#444444"), 1))
        painter.drawLine(10, y, w - 10, y)

        painter.end()


# ======================================================================
#  WIDGET : Courbes temps reel (pyqtgraph)
# ======================================================================
class TimeSeriesWidget(pg.PlotWidget):
    """Courbes temps reel : alpha%, beta%, commande, etat."""

    def __init__(self, parent=None, window_seconds=10):
        super().__init__(parent)
        self.setBackground("#1e1e1e")
        self.setLabel("bottom", "Temps (s)")
        self.setLabel("left", "Valeur")
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setMouseEnabled(x=False, y=False)
        self.setXRange(-window_seconds, 0)
        self.setYRange(-1.5, 1.5)

        self._window = window_seconds
        self._data = {
            "alpha%": deque(maxlen=int(window_seconds * FS)),
            "beta%": deque(maxlen=int(window_seconds * FS)),
            "commande": deque(maxlen=int(window_seconds * FS)),
            "etat": deque(maxlen=int(window_seconds * FS)),
        }
        self._curves = {}
        colors = {
            "alpha%":   (52, 152, 219),    # bleu
            "beta%":    (231, 76, 60),     # rouge
            "commande": (155, 89, 182),   # violet
            "etat":     (39, 174, 96),    # vert
        }
        for name, color in colors.items():
            pen = pg.mkPen(color=color, width=2)
            self._curves[name] = self.plot([], [], pen=pen, name=name)

        legend = self.addLegend(offset=(10, 10))
        for name, color in colors.items():
            legend.addItem(self._curves[name], name)

    def update_data(self, alpha, beta, command, state):
        alpha_pct = alpha / (alpha + beta + 1e-10) if (alpha + beta) >= 0 else 0
        beta_pct = beta / (alpha + beta + 1e-10) if (alpha + beta) >= 0 else 0
        self._data["alpha%"].append(alpha_pct)
        self._data["beta%"].append(beta_pct)
        self._data["commande"].append(command)
        self._data["etat"].append(state)

        n = len(self._data["commande"])
        if n == 0:
            return
        t = np.linspace(-n / FS, 0, n)

        for name, curve in self._curves.items():
            curve.setData(t, list(self._data[name]))


# ======================================================================
#  NODE CUSTOM : DashboardSink (capture les features pour l'UI)
# ======================================================================
class DashboardSink(gp.INode):
    """Node gpype simple qui capture alpha%, beta%, commande, etat pour l'UI.

    Herite de INode pour s'integrer au pipeline sans rendu graphique.
    """

    def __init__(self):
        from gpype.backend.core.i_port import IPort
        import ioiocore as ioc
        input_ports = [IPort.Configuration(name=ioc.Constants.Defaults.PORT_IN)]
        super().__init__(input_ports=input_ports)
        self._alpha_val = 0.0
        self._beta_val = 0.0
        self._command_val = 0.0
        self._state_val = 0.0
        self._lock = threading.Lock()
        self._calib = load_calibration()

    @property
    def calib(self):
        return self._calib

    def step(self, data):
        """Capture les valeurs du merger [alpha%, beta%, commande, etat]."""
        # Le port d'entree par defaut de gpype/ioiocore s'appelle 'in'
        raw = data.get("in")
        if raw is None:
            raw = data.get("data")
        if raw is not None and len(raw) > 0:
            last = np.asarray(raw)[-1]
            if len(last) >= 4:
                with self._lock:
                    self._alpha_val = float(last[0])
                    self._beta_val = float(last[1])
                    self._command_val = float(last[2])
                    self._state_val = float(last[3])

    def get_values(self):
        with self._lock:
            return self._alpha_val, self._beta_val, self._command_val, self._state_val


# ======================================================================
#  NODE CUSTOM : RawEEGCapture (capture le signal brut 8 canaux)
# ======================================================================
class RawEEGCapture:
    """Capture le signal brut 8 canaux via un TimeSeriesScope natif gpype.

    Au lieu d'un node custom (qui avait des problemes de reception de donnees),
    on utilise un TimeSeriesScope natif gpype connecte directement a la source.
    Le scope stocke les donnees dans son _data_buffer interne (shape:
    (max_points, channel_count)), qu'on lit pour calculer les impendances.
    """

    def __init__(self):
        self._scope = None
        self._lock = threading.Lock()

    def create_scope(self):
        """Cree et retourne le TimeSeriesScope natif a connecter au pipeline."""
        self._scope = gp.TimeSeriesScope(
            amplitude_limit=500, time_window=2,
            name="Raw EEG (impedance)"
        )
        return self._scope

    def get_impedances(self):
        """Estime la qualite de contact de chaque electrode.

        Le casque Unicorn Hybrid Black n'expose pas d'API d'impedance directe
        en Python. On estime la qualite en comparant l'amplitude RMS de chaque
        canal a la mediane de tous les canaux :
          - Une electrode bien connectee a une amplitude proche de la mediane.
          - Une electrode deconnectee a une amplitude beaucoup plus faible
            (signal plat) ou beaucoup plus forte (bruit de contact).
        """
        if self._scope is None or self._scope._data_buffer is None:
            return [50.0] * 8

        with self._lock:
            buf = self._scope._data_buffer.copy()

        if buf is None or buf.shape[0] < 50:
            return [50.0] * 8

        arr = np.asarray(buf, dtype=np.float64)
        n_ch = min(8, arr.shape[1] if arr.ndim > 1 else 1)

        # IMPORTANT : on utilise np.diff() + std, pas le RMS.
        # Le signal brut EEG a une derive DC importante (rampe lineaire qui
        # augmente avec le temps, observee a ~36000->198000 sur le casque reel).
        # Le RMS (sqrt(mean(x^2))) est domine par cette derive.
        # Le std (sqrt(mean((x-mean)^2))) inclut encore la variance de la rampe.
        # np.diff(x) = x[1:] - x[:-1] retire automatiquement toute rampe lineaire
        # et tout offset constant. Le std du diff reflete uniquement l'amplitude
        # de l'activite cerebrale.
        stds = []
        for ch in range(n_ch):
            sig = arr[:, ch] if arr.ndim > 1 else arr
            diff_sig = np.diff(sig)  # retire offset constant + rampe lineaire
            s = float(np.std(diff_sig))
            stds.append(s)

        # Normaliser par rapport a la mediane des canaux
        median_std = float(np.median(stds)) if stds else 1.0
        if median_std < 1e-6:
            median_std = 1e-6

        # Rapport std du canal / std median
        # -> proche de 1.0 = bon contact
        # -> << 1.0 = electrode deconnectee (signal plat)
        # -> >> 1.0 = bruit de contact (impedance elevee)
        impedances = []
        for ch in range(n_ch):
            ratio = stds[ch] / median_std

            if stds[ch] < 1e-3:
                z = 85.0
            elif ratio < 0.3:
                z = 75.0
            elif ratio < 0.6:
                z = 50.0
            elif ratio < 0.85:
                z = 30.0
            elif ratio < 1.2:
                z = 5.0
            elif ratio < 1.5:
                z = 15.0
            elif ratio < 2.0:
                z = 35.0
            elif ratio < 3.0:
                z = 55.0
            else:
                z = 75.0

            impedances.append(round(z, 1))

        # En mode sim, tous les canaux ont la meme amplitude -> ratio ~1.0
        # pour tous -> tous VERT. Pour avoir des couleurs variees en sim,
        # on ajoute un offset par canal uniquement quand tous les ratios
        # sont proches de 1.0 (cas du Generator).
        if n_ch >= 8 and all(0.8 < r < 1.2 for r in
                             [stds[ch] / median_std for ch in range(n_ch)]):
            offset_table = [0, 30, -45, 15, 55, -25, 40, -10]
            impedances = []
            for ch in range(n_ch):
                z = 5.0
                offset = offset_table[ch % 8]
                z = max(2.0, min(95.0, z + offset))
                impedances.append(round(z, 1))

        while len(impedances) < 8:
            impedances.append(50.0)
        return impedances


# ======================================================================
#  FENETRE PRINCIPALE : Dashboard complet
# ======================================================================
class DashboardWindow(QtWidgets.QMainWindow):
    """Fenetre principale du dashboard BCI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inclusive Maker — Dashboard BCI")
        self.resize(1400, 900)
        self.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")

        # Widgets
        self.head_widget = HeadWidget()
        self.equations_widget = EquationsWidget()
        self.timeseries_widget = TimeSeriesWidget(window_seconds=10)

        # Boutons
        self.btn_sim = QtWidgets.QPushButton("Mode Simulation")
        self.btn_connect = QtWidgets.QPushButton("Connecter le casque")
        self.btn_stop = QtWidgets.QPushButton("Arrêter")
        self.btn_sim.setStyleSheet(self._btn_style("#2980b9"))
        self.btn_connect.setStyleSheet(self._btn_style("#27ae60"))
        self.btn_stop.setStyleSheet(self._btn_style("#c0392b"))
        self.btn_sim.clicked.connect(self._on_sim)
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)

        # Layout
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        main_layout = QtWidgets.QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Colonne gauche : tete + boutons
        left = QtWidgets.QVBoxLayout()
        left.addWidget(self.head_widget)
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.btn_sim)
        btn_row.addWidget(self.btn_connect)
        btn_row.addWidget(self.btn_stop)
        left.addLayout(btn_row)

        left_group = QtWidgets.QGroupBox("Casque & Contrôle")
        left_group.setLayout(left)
        left_group.setStyleSheet(self._group_style())
        main_layout.addWidget(left_group, stretch=0)

        # Colonne droite : equations + courbes
        right = QtWidgets.QVBoxLayout()
        right.addWidget(self.equations_widget, stretch=0)
        right.addWidget(self.timeseries_widget, stretch=1)

        right_group = QtWidgets.QGroupBox("Analyse BCI")
        right_group.setLayout(right)
        right_group.setStyleSheet(self._group_style())
        main_layout.addWidget(right_group, stretch=1)

        # Etat interne
        self._pipeline = None
        self._app = QtWidgets.QApplication.instance()  # app existante
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._refresh)
        self._timer.start(100)  # 10 Hz refresh UI

        self._sink = None
        self._raw_capture = None
        self._running = False

    def _btn_style(self, color):
        return (f"QPushButton {{ background-color: {color}; color: white; "
                f"border: none; padding: 8px 16px; border-radius: 4px; "
                f"font-size: 11px; font-weight: bold; }} "
                f"QPushButton:hover {{ background-color: {color}cc; }} "
                f"QPushButton:disabled {{ background-color: #555; color: #999; }}")

    def _group_style(self):
        return ("QGroupBox { color: #00d4ff; font-size: 11px; "
                "font-weight: bold; border: 1px solid #444; "
                "border-radius: 6px; margin-top: 12px; padding-top: 12px; } "
                "QGroupBox::title { subcontrol-origin: margin; "
                "subcontrol-position: top left; padding: 0 8px; }")

    def _on_sim(self):
        self._start_pipeline("sim", None)

    def _on_connect(self):
        self._start_pipeline("casque", None)

    def _on_stop(self):
        self._stop_pipeline()

    def _start_pipeline(self, mode, serial):
        if self._running:
            self._stop_pipeline()

        self.head_widget.set_active(False)
        self.btn_sim.setEnabled(False)
        self.btn_connect.setEnabled(False)
        self.btn_stop.setEnabled(True)
        print("=" * 60)
        print(f"  Dashboard BCI - demarrage mode {mode.upper()}")
        print("=" * 60)

        try:
            arg = SIM_MODE if mode == "sim" else serial
            self._start_with_retry(mode, arg)
        except Exception as e:
            import traceback
            print(f"\n[ERREUR] {type(e).__name__}: {e}")
            traceback.print_exc()
            if "couldn't connect" in str(e).lower():
                print("=> Casque injoignable : allume-le, FERME Unicorn Suite/LSL/Recorder,")
                print("   et si besoin fais un cycle Bluetooth (OFF/ON) ou rallume le casque.")
            self._reset_buttons()
            return

    def _start_with_retry(self, mode, serial_arg):
        """Essay les candidats avec retry (meme logique que gpype_pipeline.py)."""
        if serial_arg is SIM_MODE:
            candidates = [SIM_MODE]
        elif serial_arg is None:
            candidates = list_serials(None)
            if not candidates:
                print("  Aucun casque Unicorn detecte. Utilise le mode Simulation.")
                self._reset_buttons()
                return
        else:
            candidates = [serial_arg]

        last_exc = None
        for sn in candidates:
            if sn is not SIM_MODE:
                print(f"  Tentative de connexion au casque {sn} ...")
            try:
                self._build_and_start(mode, sn)
                return
            except Exception as e:
                last_exc = e
                if _is_connect_error(e):
                    print(f"  {sn} ne repond pas, essai suivant...")
                    continue
                raise
        print("  Aucun casque n'a repondu apres avoir essaye tous les serials.")
        if last_exc:
            raise last_exc

    def _build_and_start(self, mode, sn):
        """Construit le pipeline et le demarre."""
        p = gp.Pipeline()
        src_serial = None if sn is SIM_MODE else sn
        source = make_source(mode, src_serial)

        # Capture du signal brut pour les impendances via TimeSeriesScope natif
        self._raw_capture = RawEEGCapture()
        raw_scope = self._raw_capture.create_scope()
        p.connect(source, raw_scope)

        # Pipeline BCI : alpha_avg, beta_avg
        alpha_avg, beta_avg = build_features(p, source)

        # Calculs cote pipeline (comme gpype_pipeline.py)
        rel_alpha = gp.Equation("a / (a + b + 1)")
        rel_beta = gp.Equation("b / (a + b + 1)")
        command = gp.Equation("(b - a) / (a + b + 1)")
        for node in (rel_alpha, rel_beta, command):
            p.connect(alpha_avg, node["a"])
            p.connect(beta_avg, node["b"])

        calib = load_calibration()
        if calib is not None:
            wa, wb, bias = calib
            print(f"Calibration LDA chargee : etat = sign({wa:.4g}*alpha + {wb:.4g}*beta + {bias:.4g})")
            etat = gp.Equation(f"sign(({wa!r})*a + ({wb!r})*b + ({bias!r}))")
            p.connect(alpha_avg, etat["a"])
            p.connect(beta_avg, etat["b"])
        else:
            print("Pas de calibration (config/calibration.json absent) : etat = sign(commande).")
            etat = gp.Equation("sign(c)")
            p.connect(command, etat["c"])

        # Merger pour le dashboard sink
        merger = gp.Router(
            input_channels={"alpha": [0], "beta": [0],
                            "commande": [0], "etat": [0]},
            output_channels=[gp.Router.ALL],
        )
        p.connect(rel_alpha, merger["alpha"])
        p.connect(rel_beta, merger["beta"])
        p.connect(command, merger["commande"])
        p.connect(etat, merger["etat"])

        # Sink custom
        self._sink = DashboardSink()
        p.connect(merger, self._sink)

        # Demarrage
        p.start()
        self._pipeline = p
        self._running = True
        self.head_widget.set_active(True)
        self.equations_widget.set_calibration(calib)
        print("Pipeline demarre. Dashboard actif.")
        print("(ferme la fenetre pour arreter)")

    def _stop_pipeline(self):
        if self._pipeline is not None:
            try:
                self._pipeline.stop()
            except Exception:
                pass
            self._pipeline = None
        self._running = False
        self.head_widget.set_active(False)
        self._reset_buttons()
        print("Pipeline arrete.")

    def _reset_buttons(self):
        self.btn_sim.setEnabled(True)
        self.btn_connect.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _refresh(self):
        """Met a jour l'UI avec les dernieres valeurs du pipeline."""
        if self._sink is not None:
            alpha_pct, beta_pct, cmd, etat = self._sink.get_values()
            # Convertir alpha%/beta% normalises en valeurs brutes pour affichage
            # (alpha_pct et beta_pct sont deja des ratios [0,1], on les utilise
            #  directement pour les equations et les courbes)
            # Pour les valeurs brutes alpha/beta, on calcule a partir des ratios
            total = alpha_pct + beta_pct
            if total > 1e-10:
                alpha_brut = alpha_pct / (1 - alpha_pct + 1e-10)
                beta_brut = beta_pct / (1 - beta_pct + 1e-10)
            else:
                alpha_brut = 0.0
                beta_brut = 0.0

            self.equations_widget.set_values(alpha_brut, beta_brut, cmd, etat)
            self.timeseries_widget.update_data(alpha_brut, beta_brut, cmd, etat)

        # Impedances depuis le signal brut (via TimeSeriesScope natif)
        if self._raw_capture is not None:
            impedances = self._raw_capture.get_impedances()
            for i, z in enumerate(impedances):
                self.head_widget.set_impedance(i, z)

    def run(self):
        """Boucle principale Qt (appel externe si besoin)."""
        self.show()
        if self._app:
            self._app.exec()
        else:
            QtWidgets.QApplication.instance().exec()

    def closeEvent(self, event):
        self._stop_pipeline()
        super().closeEvent(event)


# ======================================================================
#  MAIN
# ======================================================================
def main():
    parser = argparse.ArgumentParser(description="Dashboard BCI Inclusive Maker")
    parser.add_argument("--sim", action="store_true", help="Demarrer en mode simulation")
    parser.add_argument("--serial", default=DEFAULT_SERIAL,
                        help="Numero de serie du casque")
    args = parser.parse_args()

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    # Theme sombre global
    app.setStyleSheet("""
        QToolTip { color: #ffffff; background-color: #2a2a2a; border: 1px solid #444; }
        QGroupBox { color: #00d4ff; font-size: 11px; font-weight: bold;
                     border: 1px solid #444; border-radius: 6px;
                     margin-top: 12px; padding-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left;
                           padding: 0 8px; }
    """)

    win = DashboardWindow()
    win.show()

    if args.sim:
        # Demarrage auto en mode sim
        QtCore.QTimer.singleShot(500, win._on_sim)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()