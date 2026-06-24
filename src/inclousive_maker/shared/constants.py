"""Constantes globales du projet."""

EEG_SAMPLING_RATE = 250  # Hz
EEG_CHANNEL_COUNT = 8
DEFAULT_UDP_IP = "127.0.0.1"
DEFAULT_UDP_PORT = 56000
DEFAULT_LSL_STREAM_NAME = "inclousive_maker_commands"

BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
}
