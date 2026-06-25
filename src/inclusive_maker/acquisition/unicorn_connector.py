"""Connecteur pour le casque Unicorn Hybrid Black via g.Pype.

Avec le SDK g.tec installé sur Windows, le connecteur utilise gp.HybridBlack.
Sans le SDK natif, il bascule automatiquement sur le générateur interne du
projet (EEGGenerator) pour permettre le développement et les tests sans matériel.
"""

from typing import Optional

try:
    import gpype as gp
except ImportError:
    gp = None

from .generator import EEGGenerator
from ..shared.logger import get_logger
from ..shared.constants import EEG_SAMPLING_RATE, EEG_CHANNEL_COUNT

logger = get_logger(__name__)


class UnicornConnector:
    """Gère la connexion au casque Unicorn Hybrid Black avec fallback simulateur."""

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
        self._source: Optional[object] = None
        self._is_native = False

    def connect(self) -> object:
        """Initialise la source de données EEG.

        Retourne:
            - gp.HybridBlack si g.Pype et le SDK natif sont disponibles.
            - EEGGenerator sinon.
        """
        if not self.use_generator and gp is not None:
            try:
                logger.info("Connexion au casque Unicorn Hybrid Black...")
                self._source = gp.HybridBlack(
                    include_accel=self.include_accel,
                    include_gyro=self.include_gyro,
                    include_aux=self.include_aux,
                )
                self._is_native = True
                logger.info("Casque Unicorn connecté.")
                return self._source
            except Exception as e:
                logger.warning(f"Connexion Unicorn impossible : {e}")
                logger.warning("Basculement sur le générateur synthétique interne.")

        logger.info("Mode générateur synthétique interne activé.")
        self._source = EEGGenerator("IDLE")
        self._is_native = False
        return self._source

    def disconnect(self) -> None:
        """Libère la source EEG."""
        self._source = None
        self._is_native = False
        logger.info("Source EEG déconnectée.")

    def get_source(self) -> Optional[object]:
        """Retourne la source active."""
        return self._source

    def is_native(self) -> bool:
        """True si la source est le vrai casque Unicorn, False si simulateur."""
        return self._is_native
