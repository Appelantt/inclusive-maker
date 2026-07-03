"""Source EEG basee sur gtec-ble (Bluetooth Low Energy direct).

Cette source se connecte directement au casque Unicorn Hybrid Black via le
SDK gtec-ble (Bluetooth Low Energy), sans passer par gpype ni Unicorn Recorder.

Prerequis :
- Le casque doit etre allume et appaire en Bluetooth
- Unicorn Suite ne doit PAS etre en train d utiliser le casque
- La cle de licence gtec-ble est calculee automatiquement (hash SHA256
  de l adresse MAC de la machine)
"""

import hashlib
import time
import uuid
from typing import Optional

import numpy as np

from ..shared.constants import EEG_SAMPLING_RATE, EEG_CHANNEL_COUNT
from ..shared.logger import get_logger

logger = get_logger(__name__)


class GtecBLESource:
    """Connecte au casque Unicorn Hybrid Black via gtec-ble (Bluetooth direct)."""

    SCAN_TIMEOUT = 10.0

    def __init__(self, serial: Optional[str] = None):
        self._serial = serial
        self._amp = None
        self._buffer = []
        self._connected = False
        self._connect()

    def _compute_license_key(self) -> str:
        """Calcule la cle de licence (SHA256 de l adresse MAC)."""
        mac = uuid.getnode()
        mac_str = f"{mac:012x}"
        key = hashlib.sha256(mac_str.encode()).hexdigest()
        logger.info(f"Cle de licence gtec-ble calculee (MAC={mac_str})")
        return key

    def _connect(self) -> None:
        """Etablit la connexion Bluetooth au casque."""
        try:
            from gtec_ble.amplifier import Amplifier
        except ImportError:
            raise RuntimeError("gtec-ble n est pas installe (pip install gtec-ble)")

        logger.info("Enregistrement de la cle de licence gtec-ble...")
        key = self._compute_license_key()
        try:
            Amplifier.register(key=key)
            logger.info("Cle de licence gtec-ble acceptee.")
        except Exception as e:
            raise RuntimeError(f"Echec enregistrement cle gtec-ble : {e}")

        logger.info(f"Scan Bluetooth ({self.SCAN_TIMEOUT}s)...")
        try:
            devices = Amplifier.get_connected_devices()
        except Exception as e:
            raise RuntimeError(f"Echec du scan Bluetooth : {e}")

        if not devices:
            raise RuntimeError(
                "Aucun casque detecte en Bluetooth. Verifiez que :\n"
                "  - Le casque est allume (LED)\n"
                "  - Il est appaire en Bluetooth\n"
                "  - Unicorn Suite / Unicorn Recorder est FERME (sinon il occupe le Bluetooth)"
            )

        logger.info(f"Peripheriques Bluetooth detectes : {devices}")
        target_serial = self._serial or devices[0]
        if self._serial and self._serial not in devices:
            logger.warning(f"Numero serie {self._serial} non trouve, connexion a {devices[0]}")
            target_serial = devices[0]

        logger.info(f"Connexion au casque {target_serial}...")
        try:
            self._amp = Amplifier(serial=target_serial)
        except Exception as e:
            raise RuntimeError(f"Echec de la connexion au casque : {e}")

        try:
            logger.info(f"  Modele       : {self._amp.model_number}")
            logger.info(f"  Numero serie : {self._amp.serial_number}")
            logger.info(f"  Firmware     : {self._amp.firmware_version}")
            logger.info(f"  Fabricant    : {self._amp.manufacturer_name}")
            logger.info(f"  Canaux       : {self._amp.no_of_acquired_channels}")
            logger.info(f"  Frequence    : {self._amp.sampling_rate} Hz")
        except Exception as e:
            logger.warning(f"Impossible de lire les infos du casque : {e}")

        self._amp.set_data_callback(self._on_data)
        self._amp.start()
        self._connected = True
        logger.info("Casque Unicorn connecte via gtec-ble. Acquisition demarree.")
        time.sleep(0.5)

    def _on_data(self, data: np.ndarray) -> None:
        """Callback appele quand de nouvelles donnees EEG arrivent."""
        self._buffer.append(data)

    def read_window(self, duration_seconds: float) -> np.ndarray:
        """Lit une fenetre EEG de duree donnee."""
        n_samples = int(duration_seconds * EEG_SAMPLING_RATE)
        n_channels = EEG_CHANNEL_COUNT

        if self._buffer:
            all_data = np.concatenate(self._buffer, axis=0) if len(self._buffer) > 1 else self._buffer[0]
            self._buffer = []
        else:
            all_data = np.zeros((0, n_channels))

        while all_data.shape[0] < n_samples:
            time.sleep(0.1)
            if self._buffer:
                new_data = np.concatenate(self._buffer, axis=0) if len(self._buffer) > 1 else self._buffer[0]
                self._buffer = []
                all_data = np.vstack([all_data, new_data]) if all_data.shape[0] > 0 else new_data

        if all_data.shape[1] > n_channels:
            all_data = all_data[:, :n_channels]

        if all_data.shape[0] > n_samples:
            all_data = all_data[-n_samples:]
        elif all_data.shape[0] < n_samples:
            pad = np.zeros((n_samples - all_data.shape[0], n_channels))
            all_data = np.vstack([pad, all_data])

        return all_data

    def set_state(self, state: str) -> None:
        """Inactif pour le casque reel."""
        pass

    def is_native(self) -> bool:
        return True

    def disconnect(self) -> None:
        """Arrete l acquisition et deconnecte le casque."""
        if self._amp is not None:
            try:
                self._amp.stop()
            except Exception as e:
                logger.warning(f"Erreur arret acquisition : {e}")
            self._amp = None
        self._connected = False
        self._buffer = []
        logger.info("Casque Unicorn deconnecte via gtec-ble.")