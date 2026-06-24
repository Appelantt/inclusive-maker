"""Connecteur pour le casque Unicorn Hybrid Black via g.Pype."""

from typing import Optional

try:
    import gpype as gp
except ImportError:
    gp = None

from ..shared.logger import get_logger
from ..shared.constants import EEG_SAMPLING_RATE, EEG_CHANNEL_COUNT

logger = get_logger(__name__)


class UnicornConnector:
    """Gère la connexion au casque Unicorn Hybrid Black.

    Sous Windows avec Unicorn Suite installé, utilise gp.HybridBlack.
    Sinon, bascule automatiquement sur un générateur synthétique pour le
    développement / démonstration.
    """

    def __init__(
        self,
        use_generator: bool = False,
        include_accel: bool = False,
        include_gyro: bool = False,
        include_aux: bool = False,
    ):
        self.use_generator = use_generator
        self.include_accel = include_accel
        self.include_gyro = include_gyro
        self.include_aux = include_aux
        self._source = None
        self._pipeline = None

    def connect(self) -> object:
        """Initialise la source de données EEG."""
        if self.use_generator or gp is None:
            logger.info("Mode générateur synthétique activé.")
            self._source = gp.Generator(
                sampling_rate=EEG_SAMPLING_RATE,
                channel_count=EEG_CHANNEL_COUNT,
                signal_frequency=10,
                signal_amplitude=10,
                noise_amplitude=5,
            ) if gp else None
        else:
            logger.info("Connexion au casque Unicorn Hybrid Black...")
            self._source = gp.HybridBlack(
                include_accel=self.include_accel,
                include_gyro=self.include_gyro,
                include_aux=self.include_aux,
            )
        return self._source

    def disconnect(self) -> None:
        """Libère la source EEG."""
        self._source = None
        logger.info("Source EEG déconnectée.")

    def get_source(self) -> Optional[object]:
        """Retourne la source active."""
        return self._source
