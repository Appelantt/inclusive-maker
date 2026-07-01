import gpype as gp

print("Tentative de connexion au casque Unicorn Hybrid Black...")
try:
    hb = gp.HybridBlack()
    print("Casque connecté avec succès !")
    print("Type:", type(hb))
    print("Attributs disponibles:", [a for a in dir(hb) if not a.startswith("_")])
except Exception as e:
    print(f"Erreur de connexion : {type(e).__name__}: {e}")
