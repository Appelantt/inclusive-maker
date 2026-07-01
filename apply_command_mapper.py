from pathlib import Path

p = Path(r'C:\Users\Admin\Desktop\inclusive-maker\src\inclusive_maker\brain_algo\command_mapper.py')
text = p.read_text(encoding='utf-8')

# Supprimer l'ancien __init__ et map, puis ajouter les nouveaux profils
cut = text.find('    def __init__(self, commands:')
if cut == -1:
    raise RuntimeError('pattern not found')

new_tail = '''
    # Logique inversée pour le cerf-volant :
    # - FERMER = tenir la barre / piloter / "s'amuser"
    # - OUVRIR = lâcher / poser le cerf-volant / pause
    CERF_VOLANT_COMMANDS = {
        "OPEN": {
            "action": "CLOSE",
            "value": -1.0,
            "label": "kite_hold_bar",
        },
        "CLOSE": {
            "action": "OPEN",
            "value": 1.0,
            "label": "kite_release_bar",
        },
        "IDLE": {
            "action": "IDLE",
            "value": 0.0,
            "label": "idle",
        },
    }

    # Kanöé, ski, quadrix : maintenir la poignée fermée par défaut
    SPORT_COMMANDS = {
        "OPEN": {
            "action": "CLOSE",
            "value": -1.0,
            "label": "sport_hold",
        },
        "CLOSE": {
            "action": "OPEN",
            "value": 1.0,
            "label": "sport_release",
        },
        "IDLE": {
            "action": "IDLE",
            "value": 0.0,
            "label": "idle",
        },
    }

    PROFILES = {
        "main_robot": DEFAULT_COMMANDS,
        "cerf_volant": CERF_VOLANT_COMMANDS,
        "sport": SPORT_COMMANDS,
    }

    def __init__(self, profile: str = "main_robot", commands: dict[str, dict[str, Any]] | None = None):
        self.profile = profile
        if commands is not None:
            self.commands = commands
        else:
            self.commands = self.PROFILES.get(profile, self.DEFAULT_COMMANDS).copy()

    def set_profile(self, profile: str) -> None:
        """Change le profil de commande."""
        self.profile = profile
        self.commands = self.PROFILES.get(profile, self.DEFAULT_COMMANDS).copy()

    def map(self, state: str) -> dict[str, Any]:
        """Retourne la commande associée à l'état."""
        return self.commands.get(state, self.commands["IDLE"]).copy()
'''

p.write_text(text[:cut] + new_tail, encoding='utf-8')
print('command_mapper.py updated')
