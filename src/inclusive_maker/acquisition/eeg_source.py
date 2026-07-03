"""Source EEG unifiee pour le casque Unicorn ou le simulateur.

Expose une interface commune :
    - read_window(duration_seconds: float) -> np.ndarray
    - set_state(state: str)              -> change l'etat (simulateur uniquement)
    - is_native() -> bool
    - get_mode() -> str
    - get_status_detail() -> str         -> explication lisible du mode actif
    - reconnect() -> None                -> retente la connexion au casque

Ordre de priorite :
1. Casque Unicorn via gtec-ble (Bluetooth direct, sans licence IDE)
2. Casque Unicorn via gpype (si g.Pype Runtime disponible)
3. Stream LSL depuis Unicorn Recorder (si Unicorn Recorder tourne)
4. Simulateur interne EEGGenerator
"""

import os

import numpy as np

from .generator import EEGGenerator
from .gtec_ble_source import GtecBLESource
from .unicorn_connector import UnicornConnector
from .unicorn_lsl_source import UnicornLSLSource
from ..shared.constants import EEG_SAMPLING_RATE
from ..shared.logger import get_logger

logger = get_logger(__name__)


def _env_flag(name: str) -> bool:
    """True si la variable d'environnement vaut 1/true/yes/on."""
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


class UnifiedEEGSource:
    """Wrapper commun pour gtec-ble, gp.HybridBlack, LSL Unicorn Recorder et EEGGenerator."""

    def __init__(self, force_generator: bool = False):
        self._source = None
        self._is_native = False
        self._mode = "simulateur"
        self._status_detail = ""
        # Permet de forcer le simulateur via la variable d'environnement
        # (utilisee par le lanceur run_inclusive_maker.bat, choix 3).
        self._force_generator = force_generator or _env_flag("FORCE_GENERATOR")
        self._connect()

    def _connect(self) -> None:
        """Tente les differentes sources dans l'ordre de priorite."""
        if self._force_generator:
            self._source = EEGGenerator("IDLE")
            self._is_native = False
            self._mode = "simulateur"
            self._status_detail = "Simulateur force (FORCE_GENERATOR)."
            logger.info("Source EEG : generateur synthetique interne (force).")
            return

        failures = []

        # 1. LSL (app "Unicorn LSL") -- chemin principal pour l'Unicorn Hybrid
        #    Black, qui communique en Bluetooth classique (port COM serie).
        try:
            self._source = UnicornLSLSource()
            self._is_native = True
            self._mode = "lsl"
            self._status_detail = "Casque Unicorn connecte via LSL (app Unicorn LSL)."
            logger.info("Source EEG : casque Unicorn via LSL (app Unicorn LSL).")
            return
        except Exception as e:
            failures.append(f"LSL (app Unicorn LSL) : {e}")
            logger.warning(f"LSL Unicorn indisponible : {e}")

        # 2. gtec-ble (Bluetooth Low Energy direct) -- ne marche que pour les
        #    casques BLE, pas pour l'Unicorn Hybrid Black en Bluetooth classique.
        try:
            self._source = GtecBLESource()
            self._is_native = True
            self._mode = "gtec_ble"
            self._status_detail = "Casque Unicorn connecte en Bluetooth direct (gtec-ble)."
            logger.info("Source EEG : casque Unicorn via gtec-ble (Bluetooth direct).")
            return
        except Exception as e:
            failures.append(f"Bluetooth direct BLE (gtec-ble) : {e}")
            logger.warning(f"gtec-ble Unicorn indisponible : {e}")

        # 3. gpype HybridBlack (necessite un runtime g.Pype licencie)
        try:
            connector = UnicornConnector()
            connector.connect()
            if connector.is_native():
                self._source = connector.get_source()
                self._is_native = True
                self._mode = "gpype"
                self._status_detail = "Casque Unicorn connecte via g.Pype Runtime."
                logger.info("Source EEG : casque Unicorn via gpype.")
                return
            failures.append("g.Pype : runtime licencie requis (execution hors IDE supporte).")
        except Exception as e:
            failures.append(f"g.Pype : {e}")
            logger.warning(f"gpype Unicorn indisponible : {e}")

        # 4. Fallback simulateur
        self._source = EEGGenerator("IDLE")
        self._is_native = False
        self._mode = "simulateur"
        self._status_detail = (
            "Casque introuvable, bascule sur le simulateur.\n"
            "Pour utiliser le vrai casque Unicorn Hybrid Black :\n"
            "  1. Ouvre l'application 'Unicorn LSL' (UnicornLSL.exe, dans Unicorn Suite).\n"
            "  2. Selectionne le casque (UN-...) et lance le streaming (Open/Start).\n"
            "  3. Reviens ici et clique sur 'Reconnecter le casque'.\n"
            "Detail des tentatives :\n  - " + "\n  - ".join(failures)
        )
        logger.info("Source EEG : generateur synthetique interne.")
        logger.info(self._status_detail)

    def reconnect(self) -> None:
        """Deconnecte proprement la source actuelle et retente la connexion."""
        self.disconnect()
        self._source = None
        self._is_native = False
        self._mode = "simulateur"
        self._status_detail = ""
        self._connect()

    def read_window(self, duration_seconds: float) -> np.ndarray:
        """Lit une fenetre EEG de duree donnee."""
        if self._mode == "gpype":
            n_samples = int(duration_seconds * EEG_SAMPLING_RATE)
            data = self._source.get_data(n_samples)
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            return data[:, :8] if data.shape[1] > 8 else data
        return self._source.read_window(duration_seconds)

    def set_state(self, state: str) -> None:
        """Change l'etat simule (uniquement pour le simulateur)."""
        if not self._is_native:
            self._source.set_state(state)

    def is_native(self) -> bool:
        return self._is_native

    def get_mode(self) -> str:
        return self._mode

    def get_status_detail(self) -> str:
        """Retourne une explication lisible du mode actif / de la raison du fallback."""
        return self._status_detail

    def disconnect(self) -> None:
        if self._source is not None:
            try:
                if self._mode != "gpype":
                    self._source.disconnect()
            except Exception as e:
                logger.warning(f"Erreur deconnexion source EEG : {e}")
        logger.info(f"Source EEG {self._mode} deconnectee.")
