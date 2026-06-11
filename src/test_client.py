"""
Script de test client — Pipeline d'Ingestion IoT
Cours   : Introduction à AWS
Étudiant: Amos Kokou KOUGBLENOU

Usage :
  # Test nominal (payload valide)
  python test_client.py

  # Test d'échec (payload corrompu)
  python test_client.py --corrupt
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import requests

# ─── URL CloudFront récupérée dans les Outputs CloudFormation ─────────────

CLOUDFRONT_INGESTION_URL = "https://d2k4og569gqpmh.cloudfront.net/prod/ingest"


# ══════════════════════════════════════════════════════════════════════════════
#  PAYLOADS
# ══════════════════════════════════════════════════════════════════════════════

def build_valid_payload() -> dict:
    """
    Payload valide contenant 6 mesures IoT structurées.
    Clés obligatoires : sensor_id, temperature, status.
    """
    return {
        "batch_id"    : "batch-2026-06-11-001",
        "source"      : "usine-nord",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "measurements": [
            {
                "sensor_id"  : "SENSOR-001",
                "temperature": 72.4,
                "status"     : "OK",
                "unit"       : "Celsius",
                "location"   : "Zone A"
            },
            {
                "sensor_id"  : "SENSOR-002",
                "temperature": 85.1,
                "status"     : "ERROR",
                "unit"       : "Celsius",
                "location"   : "Zone A"
            },
            {
                "sensor_id"  : "SENSOR-003",
                "temperature": 68.9,
                "status"     : "OK",
                "unit"       : "Celsius",
                "location"   : "Zone B"
            },
            {
                "sensor_id"  : "SENSOR-004",
                "temperature": 91.3,
                "status"     : "ERROR",
                "unit"       : "Celsius",
                "location"   : "Zone B"
            },
            {
                "sensor_id"  : "SENSOR-005",
                "temperature": 70.0,
                "status"     : "OK",
                "unit"       : "Celsius",
                "location"   : "Zone C"
            },
            {
                "sensor_id"  : "SENSOR-006",
                "temperature": 66.5,
                "status"     : "OK",
                "unit"       : "Celsius",
                "location"   : "Zone C"
            },
        ]
    }


def build_corrupt_payload() -> str:
    """
    Payload délibérément corrompu pour déclencher une exception Lambda.
    Retourne une chaîne JSON mal formée (accolade fermante manquante).
    """
    return '{"measurements": [{"sensor_id": "SENSOR-X", "temperature": "INVALIDE", "status": "OK"}'


# ══════════════════════════════════════════════════════════════════════════════
#  FONCTIONS D'ENVOI
# ══════════════════════════════════════════════════════════════════════════════

def send_request(url: str, payload, corrupt: bool = False) -> None:
    """
    Envoie la requête HTTP POST vers CloudFront/API Gateway
    et affiche la réponse complète.
    """
    headers = {"Content-Type": "application/json"}

    print("=" * 60)
    print(f"  TEST CLIENT — Pipeline IoT (akougblenou)")
    print("=" * 60)
    print(f"\n URL cible      : {url}")
    print(f" Mode           : {'PAYLOAD CORROMPU ' if corrupt else 'PAYLOAD VALIDE '}")
    print(f" Heure d'envoi  : {datetime.now(timezone.utc).isoformat()}")

    if corrupt:
        # Envoi brut de la chaîne corrompue (pas de json.dumps)
        body = payload
        print(f"\n Payload envoyé :\n{body}\n")
    else:
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        nb_mesures = len(payload["measurements"])
        print(f"\n Nombre de mesures : {nb_mesures}")
        print(f"\n Payload envoyé :\n{body}\n")

    print("-" * 60)
    print(" Envoi de la requête POST...")
    print("-" * 60)

    try:
        response = requests.post(url, data=body, headers=headers, timeout=15)

        print(f"\n Réponse reçue !")
        print(f"   Statut HTTP   : {response.status_code} {response.reason}")
        print(f"   Latence       : {response.elapsed.total_seconds():.3f}s")
        print(f"\n Corps de la réponse :")

        try:
            resp_json = response.json()
            print(json.dumps(resp_json, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(response.text)

        # Vérification du code HTTP attendu
        print("\n" + "=" * 60)
        if not corrupt and response.status_code == 201:
            print(" SUCCÈS — Statut HTTP 201 reçu comme attendu.")
        elif corrupt and response.status_code in (400, 422, 500):
            print(f" ÉCHEC ATTENDU — Statut HTTP {response.status_code} reçu (exception Lambda déclenchée).")
        else:
            print(f"  Statut inattendu : {response.status_code}")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n ERREUR : Impossible de joindre le serveur.")
        print("   → Vérifie que CLOUDFRONT_INGESTION_URL est correctement renseignée.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\n ERREUR : La requête a expiré (timeout > 15s).")
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        print(f"\n ERREUR inattendue : {exc}")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Client de test pour le pipeline d'ingestion IoT (akougblenou)"
    )
    parser.add_argument(
        "--corrupt",
        action="store_true",
        help="Envoie un payload délibérément corrompu pour tester la gestion d'erreurs Lambda"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=CLOUDFRONT_INGESTION_URL,
        help="URL CloudFront d'ingestion (remplace la valeur par défaut)"
    )
    args = parser.parse_args()

    if args.corrupt:
        payload = build_corrupt_payload()
    else:
        payload = build_valid_payload()

    send_request(url=args.url, payload=payload, corrupt=args.corrupt)


if __name__ == "__main__":
    main()
