"""Source EEG basee sur le stream LSL du casque Unicorn.

Le casque Unicorn Hybrid Black communique en Bluetooth classique (port COM
serie). Le moyen le plus fiable de recuperer ses donnees dans l'application est
l'application officielle "Unicorn LSL" (UnicornLSL.exe, fournie avec Unicorn
Suite) : elle lit le casque et le diffuse en Lab Streaming Layer (LSL).

Cette source resout le flux LSL de maniere robuste : elle accepte n'importe quel
flux ressemblant au casque (type EEG, nom contenant "Unicorn"/"UN-", ou 8+
canaux a ~250 Hz), car l'app Unicorn LSL n'etiquette pas toujours le flux en
type "EEG".
"""

from typing import Optional

import numpy as np
from pylsl import StreamInlet, resolve_streams

from ..shared.constants import EEG_SAMPLING_RATE, EEG_CHANNEL_COUNT
from ..shared.logger import get_logger

logger = get_logger(__name__)


class UnicornLSLSource:
    """Connecte au stream EEG LSL emis par l'app Unicorn LSL (ou Unicorn Recorder)."""

    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._inlet: Optional[StreamInlet] = None
        self._info = None
        self._connect()

    @staticmethod
    def _looks_like_unicorn(info) -> bool:
        """Heuristique : ce flux LSL ressemble-t-il au casque Unicorn ?"""
        try:
            name = (info.name() or "").lower()
            stype = (info.type() or "").lower()
            srate = info.nominal_srate()
            nch = info.channel_count()
        except Exception:
            return False
        if "eeg" in stype:
            return True
        if "unicorn" in name or name.startswith("un-"):
            return True
        # Casque Unicorn : 250 Hz, au moins 8 canaux EEG (souvent 8 ou 17).
        if nch >= EEG_CHANNEL_COUNT and 240 <= srate <= 260:
            return True
        return False

    def _connect(self) -> None:
        logger.info("Recherche d'un flux LSL du casque Unicorn (app Unicorn LSL)...")
        try:
            streams = resolve_streams(wait_time=self.timeout)
        except Exception as e:
            logger.warning(f"Erreur lors de la resolution LSL : {e}")
            streams = []

        if not streams:
            raise RuntimeError(
                "Aucun flux LSL trouve. Ouvre l'application 'Unicorn LSL' "
                "(UnicornLSL.exe), selectionne le casque et clique sur 'Open' / "
                "'Start' pour lancer le streaming, puis reconnecte."
            )

        # Choisir le meilleur candidat parmi les flux disponibles.
        candidates = [s for s in streams if self._looks_like_unicorn(s)]
        chosen = candidates[0] if candidates else streams[0]

        if not candidates:
            logger.warning(
                f"Aucun flux ne ressemble clairement au casque Unicorn ; "
                f"utilisation du premier flux disponible : {chosen.name()}"
            )

        self._info = chosen
        self._inlet = StreamInlet(chosen, max_buflen=360)
        logger.info(
            f"Flux LSL connecte : {chosen.name()} "
            f"(type={chosen.type()}, {chosen.channel_count()} canaux, "
            f"{chosen.nominal_srate()} Hz)"
        )

    def read_window(self, duration_seconds: float) -> np.ndarray:
        """Lit une fenetre EEG de duree donnee depuis le flux LSL."""
        n_samples = int(duration_seconds * EEG_SAMPLING_RATE)
        data, _ = self._inlet.pull_chunk(timeout=duration_seconds + 1.0, max_samples=n_samples)
        arr = np.array(data)
        if arr.size == 0:
            return np.zeros((n_samples, EEG_CHANNEL_COUNT))
        # Garder uniquement les 8 premiers canaux (EEG).
        if arr.shape[1] > EEG_CHANNEL_COUNT:
            arr = arr[:, :EEG_CHANNEL_COUNT]
        # Completer si pas assez d'echantillons.
        if arr.shape[0] < n_samples:
            pad = np.zeros((n_samples - arr.shape[0], arr.shape[1]))
            arr = np.vstack([arr, pad])
        return arr

    def set_state(self, state: str) -> None:
        """Inactif pour le flux LSL reel (l'etat vient du cerveau de l'utilisateur)."""
        pass

    def is_native(self) -> bool:
        return True

    def disconnect(self) -> None:
        # StreamInlet n'a pas de close() dans pylsl ; libere au garbage collection.
        self._inlet = None
        logger.info("Flux LSL Unicorn deconnecte.")
