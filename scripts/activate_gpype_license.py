#!/usr/bin/env python3
"""Activation de la licence g.tec (g.Pype Runtime) sur cette machine.

Chez g.tec, une cle de licence ne se "pose" pas dans un fichier : elle s'ACTIVE
en ligne. L'activation contacte le serveur g.tec, lie la cle a CET ordinateur,
puis stocke la licence localement. Il faut donc 3 informations :

    - la cle de licence          (fournie par g.tec)
    - l'email du compte g.tec     (celui de la commande / du compte g.tec)
    - le nom exact du produit     (ex. "gPype" ; voir l'email/facture g.tec)

Usage :
    venv\\Scripts\\python.exe scripts\\activate_gpype_license.py ^
        --key  "TA-CLE-ICI" ^
        --email "ton@email.com" ^
        --product "gPype"

Sans arguments, le script demande les infos de facon interactive.
Pour verifier une licence deja active :
    venv\\Scripts\\python.exe scripts\\activate_gpype_license.py --check --product "gPype"
"""

import argparse
import sys

try:
    from gtec_licensing import api as gl
except Exception as e:  # pragma: no cover
    print(f"[X] Module gtec_licensing introuvable : {e}")
    sys.exit(2)


def code_name(code) -> str:
    """Traduit un ErrorCode g.tec en texte lisible."""
    try:
        return f"{int(code)} ({gl.ErrorCode(code).name})"
    except Exception:
        return str(code)


def do_check(product: str) -> int:
    code = gl.check_license(product)
    print(f"check_license({product!r}) -> {code_name(code)}")
    if code == gl.ErrorCode.SUCCESS:
        print("[OK] Licence valide et active sur cette machine.")
        return 0
    print("[i] Aucune licence active pour ce produit (ou nom de produit incorrect).")
    return 1


def do_activate(key: str, product: str, email: str) -> int:
    print(f"Activation du produit {product!r} pour {email} ...")
    code = gl.activate(key, product, email)
    print(f"activate(...) -> {code_name(code)}")
    if code == gl.ErrorCode.SUCCESS:
        print("[OK] Licence activee ! g.Pype peut maintenant tourner hors IDE.")
        return 0
    if code == gl.ErrorCode.ALREADY_ACTIVATED:
        print("[OK] Cette licence etait deja activee sur cette machine.")
        return 0
    print("[X] Echec de l'activation. Verifie :")
    print("    - la cle (copiee sans espace),")
    print("    - l'email (celui du compte g.tec),")
    print("    - le NOM DU PRODUIT exact (voir l'email/facture g.tec),")
    print("    - la connexion internet (l'activation est en ligne).")
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description="Activation licence g.tec / g.Pype")
    p.add_argument("--key", help="Cle de licence g.tec")
    p.add_argument("--email", help="Email du compte g.tec")
    p.add_argument("--product", default="gPype",
                   help="Nom du produit (defaut: gPype ; voir email g.tec)")
    p.add_argument("--check", action="store_true",
                   help="Verifie seulement l'etat de la licence")
    args = p.parse_args()

    if args.check:
        return do_check(args.product)

    key = args.key or input("Cle de licence : ").strip()
    email = args.email or input("Email du compte g.tec : ").strip()
    product = args.product or input("Nom du produit (ex. gPype) : ").strip()

    if not key or not email or not product:
        print("[X] Cle, email et produit sont obligatoires.")
        return 2

    rc = do_activate(key, product, email)
    if rc == 0:
        print("\nVerification :")
        do_check(product)
    return rc


if __name__ == "__main__":
    sys.exit(main())
