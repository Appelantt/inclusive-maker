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

# Canaux analyses pour le BCI (alpha/beta)
# C3 = main droite, C4 = main gauche, Cz = reference, Fz = frontal
ANALYZED_CHANNELS = [0, 1, 2, 3]  # Fz, C3, Cz, C4
ANALYZED_NAMES = ["Fz", "C3", "Cz", "C4"]

# Nombre de tests de calibration (2 "FERMER" + 2 "OUVRIR" = 4 tests)
CALIB_TRIES = 4
# Duree d'une consigne de calibration (secondes)
CALIB_CUE_DUR = 5.0
CALIB_REST_DUR = 3.0
CALIB_PREP_DUR = 3.0

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

    def set_state(self, state, alpha=0.0, beta=0.0, command=0.0,
                  all_channels=None):
        """all_channels = liste de (name, alpha, beta, command) pour Fz,C3,Cz,C4."""
        self._state = state
        self._alpha = alpha
        self._beta = beta
        self._command = command
        self._all_channels = all_channels
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
        painter.setFont(QtGui.QFont("Segoe UI", 16, QtGui.QFont.Weight.Bold))
        painter.setPen(text_color)
        painter.drawText(QtCore.QRectF(0, 8, w, 32),
                         QtCore.Qt.AlignmentFlag.AlignCenter, text)

        # Valeurs alpha/beta/commande pour C3 (principal)
        painter.setFont(QtGui.QFont("Consolas", 8))
        painter.setPen(QtGui.QColor("#ccc"))
        info = f"C3: alpha={self._alpha:.2f} beta={self._beta:.2f} cmd={self._command:+.3f}"
        painter.drawText(QtCore.QRectF(0, 40, w, 16),
                         QtCore.Qt.AlignmentFlag.AlignCenter, info)

        # Valeurs pour les autres canaux (Fz, Cz, C4)
        y_off = 56
        if hasattr(self, "_all_channels") and self._all_channels:
            for name, a, b, c in self._all_channels:
                if name == "C3":
                    continue  # deja affiche ci-dessus
                painter.setFont(QtGui.QFont("Consolas", 8))
                painter.setPen(QtGui.QColor("#aaa"))
                line = f"{name}: a={a:.2f} b={b:.2f} cmd={c:+.3f}"
                painter.drawText(QtCore.QRectF(0, y_off, w, 14),
                                 QtCore.Qt.AlignmentFlag.AlignCenter, line)
                y_off += 14

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
#  FENETRE DE CALIBRATION GUIDE
# ======================================================================
class CalibrationDialog(QtWidgets.QDialog):
    """Fenetre de calibration guidee : 4 tests (2 fermer + 2 ouvrir).

    L'utilisateur imagine fermer/ouvrir la main, on enregistre les
    puissances alpha/beta sur C3, puis on entraine un LDA.
    Si la calibration echoue (precision < 60%), on annule tout.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration - Inclusive Maker")
        self.setModal(True)
        self.resize(600, 400)
        self.setStyleSheet("background-color: #1a1a1a; color: #e0e0e0;")

        self._pipeline = None
        self._scope = None
        self._running = False
        self._phase = "idle"  # idle, prep, fermer, ouvrir, repos, done, failed
        self._phase_start = 0
        self._test_num = 0
        self._schedule = []  # (t_start, t_end, label) 1=FERMER, 0=OUVRIR
        self._t0 = 0

        # Label d'instruction (grand)
        self.instruction_label = QtWidgets.QLabel("Preparation...")
        self.instruction_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.instruction_label.setFont(QtGui.QFont("Segoe UI", 24, QtGui.QFont.Weight.Bold))
        self.instruction_label.setStyleSheet("color: #fff; padding: 20px;")

        # Compte a rebours
        self.countdown_label = QtWidgets.QLabel("")
        self.countdown_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.countdown_label.setFont(QtGui.QFont("Segoe UI", 48, QtGui.QFont.Weight.Bold))
        self.countdown_label.setStyleSheet("color: #00d4ff;")

        # Progression
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, CALIB_TRIES)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background: #333; border: 1px solid #555; border-radius: 4px; }"
            "QProgressBar::chunk { background: #27ae60; }"
        )

        # Bouton demarrer
        self.btn_start = QtWidgets.QPushButton("Demarrer la calibration")
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; border: none; "
            "padding: 12px 24px; border-radius: 6px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #27ae60cc; }"
        )
        self.btn_start.clicked.connect(self._start_calibration)

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.instruction_label, stretch=1)
        layout.addWidget(self.countdown_label, stretch=2)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.btn_start)

        # Timer pour le compte a rebours
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(100)  # 10 Hz

    def _set_phase(self, phase):
        self._phase = phase
        self._phase_start = time.time()

    def _start_calibration(self):
        """Demarre le pipeline et la sequence de calibration."""
        self.btn_start.setEnabled(False)

        # Construire le pipeline gpype (source -> filtre -> scope)
        try:
            self._pipeline = gp.Pipeline()
            FRAME_SIZE = 5
            devices = list_serials()

            if not devices:
                QtWidgets.QMessageBox.warning(self, "Erreur",
                    "Aucun casque Unicorn detecte.\n"
                    "Allume le casque et relance l'application.")
                self.reject()
                return

            # Essayer chaque casque
            connected = False
            for sn in devices:
                print(f"Calibration: tentative {sn}...")
                try:
                    source = gp.HybridBlack(serial=sn, frame_size=FRAME_SIZE)
                    bandpass = gp.Bandpass(f_lo=1, f_hi=30)
                    notch50 = gp.Bandstop(f_lo=48, f_hi=52)
                    notch60 = gp.Bandstop(f_lo=58, f_hi=62)
                    self._scope = gp.TimeSeriesScope(
                        amplitude_limit=100, time_window=2, name="calib")
                    self._pipeline.connect(source, bandpass)
                    self._pipeline.connect(bandpass, notch50)
                    self._pipeline.connect(notch50, notch60)
                    self._pipeline.connect(notch60, self._scope)
                    self._pipeline.start()
                    connected = True
                    print(f"Calibration: connecte a {sn}")
                    break
                except Exception as e:
                    print(f"  {sn} ne repond pas: {e}")
                    self._pipeline = None
                    continue

            if not connected:
                QtWidgets.QMessageBox.warning(self, "Erreur",
                    "Aucun casque n'a repondu.\n"
                    "Allume le casque, ferme Unicorn Suite, et relance.")
                self.reject()
                return

        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Erreur", f"Connexion impossible:\n{e}")
            self.reject()
            return

        self._running = True
        self._t0 = time.time()
        self._test_num = 0
        self._schedule = []

        # Phase preparation
        self._set_phase("prep")
        self.instruction_label.setText("Preparation...")
        self.instruction_label.setStyleSheet("color: #fff; padding: 20px;")
        self.countdown_label.setText(f"{int(CALIB_PREP_DUR)}")

    def _tick(self):
        """Met a jour l'affichage et la sequence de calibration."""
        if not self._running:
            return

        elapsed = time.time() - self._phase_start

        if self._phase == "prep":
            remaining = max(0, int(CALIB_PREP_DUR - elapsed))
            self.countdown_label.setText(str(remaining))
            if elapsed >= CALIB_PREP_DUR:
                self._next_test()

        elif self._phase == "fermer":
            remaining = max(0, int(CALIB_CUE_DUR - elapsed))
            self.countdown_label.setText(str(remaining))
            if elapsed >= CALIB_CUE_DUR:
                # Enregistrer la plage
                ts = self._phase_start - self._t0 + 1.5  # skip 1.5s debut
                te = time.time() - self._t0
                self._schedule.append((ts, te, 1))  # 1 = FERMER
                self._set_phase("repos")
                self.instruction_label.setText("Repos...")
                self.instruction_label.setStyleSheet("color: #aaa; padding: 20px;")
                self.countdown_label.setText(f"{int(CALIB_REST_DUR)}")

        elif self._phase == "ouvrir":
            remaining = max(0, int(CALIB_CUE_DUR - elapsed))
            self.countdown_label.setText(str(remaining))
            if elapsed >= CALIB_CUE_DUR:
                ts = self._phase_start - self._t0 + 1.5
                te = time.time() - self._t0
                self._schedule.append((ts, te, 0))  # 0 = OUVRIR
                self._set_phase("repos")
                self.instruction_label.setText("Repos...")
                self.instruction_label.setStyleSheet("color: #aaa; padding: 20px;")
                self.countdown_label.setText(f"{int(CALIB_REST_DUR)}")

        elif self._phase == "repos":
            remaining = max(0, int(CALIB_REST_DUR - elapsed))
            self.countdown_label.setText(str(remaining))
            if elapsed >= CALIB_REST_DUR:
                self._next_test()

        elif self._phase == "done":
            if elapsed >= 1:
                self._finish_calibration()

    def _next_test(self):
        """Passe au test suivant (alternance FERMER / OUVRIR)."""
        self._test_num += 1
        self.progress_bar.setValue(self._test_num)

        if self._test_num > CALIB_TRIES:
            self._set_phase("done")
            self.instruction_label.setText("Calibration terminee !")
            self.instruction_label.setStyleSheet("color: #27ae60; padding: 20px;")
            self.countdown_label.setText("")
            return

        if self._test_num % 2 == 1:
            # Tests impairs = FERMER
            self._set_phase("fermer")
            self.instruction_label.setText(">>> IMAGINE FERMER LA MAIN <<<")
            self.instruction_label.setStyleSheet("color: #c0392b; padding: 20px;")
        else:
            # Tests pairs = OUVRIR
            self._set_phase("ouvrir")
            self.instruction_label.setText("<<< IMAGINE OUVRIR LA MAIN >>>")
            self.instruction_label.setStyleSheet("color: #27ae60; padding: 20px;")
        self.countdown_label.setText(f"{int(CALIB_CUE_DUR)}")

    def _finish_calibration(self):
        """Arrete le pipeline, entraine le LDA, sauvegarde ou annule."""
        self._running = False
        if self._pipeline:
            try:
                self._pipeline.stop()
            except Exception:
                pass
            self._pipeline = None

        # Recuperer les donnees du buffer du scope
        buf = self._scope._data_buffer if self._scope else None
        if buf is None or buf.shape[0] < 100:
            QtWidgets.QMessageBox.warning(self, "Erreur",
                "Pas assez de donnees enregistrees.\nLa calibration a echoue.")
            self._phase = "failed"
            self.reject()
            return

        # Calculer alpha/beta via FFT sur C3 pour chaque fenetre etiquetee
        eeg = buf[:, :8]
        n_total = eeg.shape[0]
        t_total = n_total / FS
        # Temps de chaque sample (relatif au debut)
        t_samples = np.arange(n_total) / FS

        X = []
        y = []
        for (ts, te, label) in self._schedule:
            # Indices des samples dans la plage [ts, te]
            mask = (t_samples >= ts) & (t_samples < te)
            idx = np.where(mask)[0]
            if len(idx) < 50:
                continue
            # Sous-echantillonnage : fenetres de 250 samples glissantes
            for i in range(0, len(idx) - 250, 62):
                window_data = eeg[idx[i]:idx[i] + 250, MOTOR_CHANNEL]
                if len(window_data) < 250:
                    continue
                window_func = np.hanning(250)
                fft = np.abs(np.fft.rfft(window_data * window_func))
                freqs = np.fft.rfftfreq(250, d=1.0 / FS)
                alpha_mask = (freqs >= 8) & (freqs <= 12)
                beta_mask = (freqs >= 13) & (freqs <= 30)
                a = float(np.sum(fft[alpha_mask] ** 2))
                b = float(np.sum(fft[beta_mask] ** 2))
                X.append([a, b])
                y.append(label)

        X = np.array(X)
        y = np.array(y)

        print(f"Calibration: {len(y)} echantillons "
              f"(fermer={int(np.sum(y==1))}, ouvrir={int(np.sum(y==0))})")

        if len(np.unique(y)) < 2 or len(y) < 10:
            QtWidgets.QMessageBox.warning(self, "Calibration echouee",
                "Pas assez de donnees exploitables.\n"
                "Assure-toi que le casque est bien positionne\n"
                "et que les electrodes C3 repondent (vert).")
            self._phase = "failed"
            self.reject()
            return

        # Entrainement LDA
        try:
            from sklearn.preprocessing import StandardScaler
            from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
            from sklearn.model_selection import cross_val_score

            scaler = StandardScaler().fit(X)
            Xs = scaler.transform(X)
            lda = LinearDiscriminantAnalysis()
            try:
                cv = cross_val_score(lda, Xs, y, cv=min(5, np.bincount(y).min()))
                acc = float(np.mean(cv))
            except Exception:
                acc = 0.5
            lda.fit(Xs, y)

            coef = lda.coef_[0]
            wa = float(coef[0] / scaler.scale_[0])
            wb = float(coef[1] / scaler.scale_[1])
            bias = float(lda.intercept_[0]
                         - coef[0] * scaler.mean_[0] / scaler.scale_[0]
                         - coef[1] * scaler.mean_[1] / scaler.scale_[1])

            print(f"Calibration: precision = {acc*100:.0f}%")

            # Verifier que la precision est suffisante (> 60%)
            if acc < 0.60:
                QtWidgets.QMessageBox.warning(self, "Calibration echouee",
                    f"Precision trop faible : {acc*100:.0f}%\n\n"
                    "La calibration ne permet pas de detecter\n"
                    "correctement l'ouverture/fermeture.\n\n"
                    "Verifie le contact des electrodes (C3 doit etre vert)\n"
                    "et refais la calibration.")
                self._phase = "failed"
                self.reject()
                return

            # Sauvegarder
            os.makedirs(os.path.dirname(CALIB_PATH), exist_ok=True)
            with open(CALIB_PATH, "w", encoding="utf-8") as f:
                json.dump({"wa": wa, "wb": wb, "bias": bias,
                           "accuracy": acc, "n_samples": int(len(y)),
                           "channel": "C3", "features": ["alpha_power", "beta_power"]},
                          f, indent=2)
            print(f"Calibration sauvegardee : {CALIB_PATH}")

            QtWidgets.QMessageBox.information(self, "Calibration reussie !",
                f"Precision : {acc*100:.0f}%\n"
                f"Poids : sign({wa:.3g}*alpha + {wb:.3g}*beta + {bias:.3g})\n\n"
                "La detection main ouverte/fermee est active.")
            self.accept()

        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Erreur",
                f"Erreur pendant l'entrainement :\n{e}")
            self._phase = "failed"
            self.reject()


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

        Pipeline simple (evite les problemes de buffer) :
          source -> Bandpass 1-30 Hz + Notch 50/60 Hz -> Scope EEG (8 canaux)

        Les calculs alpha/beta/etat sont faits en numpy dans _refresh_stats
        directement depuis le buffer du scope, sur 4 canaux (Fz, C3, Cz, C4).
        """
        p = gp.Pipeline()

        # frame_size equilibre : pas trop petit (overflow) ni trop grand (underrun)
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
        """Calcule les stats depuis le _data_buffer du scope gpype natif.

        Calcule pour les 8 canaux :
          - std(diff) pour la qualite d'impedance
        Calcule pour 4 canaux (Fz, C3, Cz, C4) :
          - puissance alpha (8-12 Hz) via FFT
          - puissance beta (13-30 Hz) via FFT
          - commande = (beta - alpha) / (alpha + beta + 1)
        L'etat de la main est base sur C3 (canal moteur main droite).
        """
        if not self._running:
            return

        buf = self.gp_scope._data_buffer
        if buf is None or buf.shape[0] < 50:
            return

        eeg = buf[:, :8]

        # --- Qualite d'impedance (8 canaux) ---
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

        # --- Calcul alpha/beta via FFT sur 4 canaux (Fz, C3, Cz, C4) ---
        n = eeg.shape[0]
        window = np.hanning(n)
        freqs = np.fft.rfftfreq(n, d=1.0 / FS)

        alpha_powers = []
        beta_powers = []
        for ch_idx in ANALYZED_CHANNELS:
            sig = eeg[:, ch_idx] * window
            fft = np.abs(np.fft.rfft(sig))
            # Puissance alpha (8-12 Hz)
            alpha_mask = (freqs >= 8) & (freqs <= 12)
            alpha_pow = float(np.sum(fft[alpha_mask] ** 2)) if np.any(alpha_mask) else 0.0
            # Puissance beta (13-30 Hz)
            beta_mask = (freqs >= 13) & (freqs <= 30)
            beta_pow = float(np.sum(fft[beta_mask] ** 2)) if np.any(beta_mask) else 0.0
            alpha_powers.append(alpha_pow)
            beta_powers.append(beta_pow)

        # Etat de la main base sur C3 (index 1 dans ANALYZED_CHANNELS)
        c3_idx = 1  # C3 est le 2e canal analyse
        alpha_c3 = alpha_powers[c3_idx]
        beta_c3 = beta_powers[c3_idx]
        command_c3 = (beta_c3 - alpha_c3) / (alpha_c3 + beta_c3 + 1e-10)

        calib = load_calibration()
        if calib is not None:
            wa, wb, bias = calib
            etat = 1.0 if (wa * alpha_c3 + wb * beta_c3 + bias) >= 0 else -1.0
        else:
            etat = 1.0 if command_c3 >= 0 else -1.0

        # Prepare les valeurs pour les 4 canaux
        all_ch = []
        for i, name in enumerate(ANALYZED_NAMES):
            a = alpha_powers[i]
            b = beta_powers[i]
            cmd = (b - a) / (a + b + 1e-10)
            all_ch.append((name, a, b, cmd))

        # Mise a jour du widget main (avec valeurs C3 + tous les canaux)
        self.hand_state.set_state(etat, alpha_c3, beta_c3, command_c3,
                                  all_channels=all_ch)

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
    parser.add_argument("--skip-calib", action="store_true",
                        help="Passer la calibration (deja calibre)")
    args = parser.parse_args()

    print()
    print("  DIAGNOSTIC CAPTEURS - Unicorn Hybrid Black (gpype natif)")
    print("  Interface graphique avec TimeSeriesScope natif gpype")
    print()
    print("  >>> Allume le casque, FERME Unicorn Suite/LSL/Recorder <<<")
    print()

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    # --- Phase 1 : Calibration (obligatoire sauf --skip-calib) ---
    if not args.sim and not args.skip_calib:
        calib = load_calibration()
        if calib is None:
            print("Aucune calibration trouvee. Calibration obligatoire.")
            must_calib = True
        else:
            print(f"Calibration existante : precision = {calib}")
            reponse = QtWidgets.QMessageBox.question(
                None, "Calibration existante",
                "Une calibration a deja ete effectuee.\n\n"
                "Veux-tu refaire la calibration ?\n"
                "(Non = utiliser la calibration existante)",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No
            )
            must_calib = (reponse == QtWidgets.QMessageBox.StandardButton.Yes)

        if must_calib:
            print("Lancement de la calibration guidee (4 tests)...")
            dialog = CalibrationDialog()
            result = dialog.exec()
            if result != QtWidgets.QDialog.DialogCode.Accepted:
                print("Calibration echouee ou annulee. Le logiciel ne peut pas fonctionner.")
                QtWidgets.QMessageBox.critical(
                    None, "Impossible de continuer",
                    "Sans calibration, le logiciel ne peut pas detecter\n"
                    "l'ouverture ou la fermeture de la main.\n\n"
                    "Verifie que :\n"
                    "- Le casque est allume et bien positionne\n"
                    "- L'electrode C3 est bien connectee (vert)\n"
                    "- Unicorn Suite / LSL / Recorder sont fermes\n\n"
                    "Puis relance l'application.")
                return 1
            print("Calibration reussie ! Lancement du dashboard...")
        else:
            print("Utilisation de la calibration existante.")
    elif args.sim:
        print("Mode simulation : calibration ignoree.")

    # --- Phase 2 : Dashboard ---
    diag = DiagnosticApp()

    if args.sim:
        QtCore.QTimer.singleShot(500, diag._on_sim)

    diag.run()
    diag.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())