"""
Fonction Lambda — Pipeline d'Ingestion IoT en Temps Réel
Cours   : Introduction à AWS
Étudiant: Amos Kokou KOUGBLENOU
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# ─── Configuration du logger ───────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ─── Clients boto3 (initialisés une seule fois, hors handler) ─────────────
s3_client       = boto3.client("s3")
dynamodb_client = boto3.resource("dynamodb")

# ─── Variables d'environnement ─────────────────────────────────────────────
S3_BUCKET      = os.environ["S3_BUCKET"]
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]


# ══════════════════════════════════════════════════════════════════════════════
#  HANDLER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def lambda_handler(event, context):
    """
    Point d'entrée de la fonction Lambda.
    Reçoit une requête HTTP POST depuis API Gateway (format payload v2.0).
    """
    logger.info("Événement reçu : %s", json.dumps(event))

    # ── 1. Parser le corps JSON de la requête ─────────────────────────────
    try:
        body = parse_body(event)
    except (ValueError, KeyError) as exc:
        logger.error("Erreur de parsing du payload : %s", str(exc))
        return build_response(400, {"error": f"Payload invalide : {str(exc)}"})

    # ── 2. Valider la structure du payload ────────────────────────────────
    try:
        measurements = extract_measurements(body)
    except ValueError as exc:
        logger.error("Structure du payload incorrecte : %s", str(exc))
        return build_response(422, {"error": str(exc)})

    # ── 3. Générer les métadonnées de l'exécution ─────────────────────────
    request_id = str(uuid.uuid4())
    now        = datetime.now(timezone.utc)
    timestamp  = now.isoformat()

    # ── 4. Sauvegarder le payload brut dans S3 (partitionnement temporel) ─
    try:
        s3_key = save_to_s3(body, request_id, now)
        logger.info("Fichier brut sauvegardé dans S3 : s3://%s/%s", S3_BUCKET, s3_key)
    except ClientError as exc:
        logger.error("Erreur S3 : %s", str(exc))
        return build_response(500, {"error": "Impossible d'écrire dans S3."})

    # ── 5. Calculer les métriques à la volée ──────────────────────────────
    avg_temperature, error_count = compute_metrics(measurements)
    logger.info(
        "Métriques calculées — temp_moy=%.2f°C, anomalies=%d",
        avg_temperature, error_count
    )

    # ── 6. Enregistrer le rapport dans DynamoDB ───────────────────────────
    try:
        save_to_dynamodb(request_id, timestamp, s3_key, avg_temperature, error_count)
        logger.info("Rapport enregistré dans DynamoDB (request_id=%s)", request_id)
    except ClientError as exc:
        logger.error("Erreur DynamoDB : %s", str(exc))
        return build_response(500, {"error": "Impossible d'écrire dans DynamoDB."})

    # ── 7. Réponse HTTP 201 Created ───────────────────────────────────────
    response_body = {
        "message"         : "Données ingérées avec succès.",
        "request_id"      : request_id,
        "timestamp"       : timestamp,
        "s3_path"         : f"s3://{S3_BUCKET}/{s3_key}",
        "avg_temperature" : round(avg_temperature, 2),
        "error_count"     : error_count,
        "record_count"    : len(measurements),
    }
    return build_response(201, response_body)


# ══════════════════════════════════════════════════════════════════════════════
#  FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def parse_body(event: dict) -> dict:
    """
    Extrait et désérialise le corps JSON de l'événement API Gateway (v2.0).
    Lève ValueError si le corps est absent ou mal formé.
    """
    raw_body = event.get("body")
    if raw_body is None:
        raise ValueError("Le corps de la requête est absent (body=null).")

    # API Gateway peut envoyer le body en base64 si isBase64Encoded=True
    if event.get("isBase64Encoded", False):
        import base64
        raw_body = base64.b64decode(raw_body).decode("utf-8")

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON mal formé : {exc}") from exc


def extract_measurements(body: dict) -> list:
    """
    Valide que le payload contient une liste 'measurements' non vide,
    avec les clés obligatoires sensor_id, temperature et status.
    """
    measurements = body.get("measurements")

    if not isinstance(measurements, list):
        raise ValueError("Le champ 'measurements' est absent ou n'est pas une liste.")
    if len(measurements) == 0:
        raise ValueError("La liste 'measurements' est vide.")

    required_keys = {"sensor_id", "temperature", "status"}
    for i, record in enumerate(measurements):
        missing = required_keys - set(record.keys())
        if missing:
            raise ValueError(
                f"Enregistrement [{i}] — clés manquantes : {missing}"
            )
        # Vérifier que temperature est bien un nombre
        if not isinstance(record["temperature"], (int, float)):
            raise ValueError(
                f"Enregistrement [{i}] — 'temperature' doit être un nombre, "
                f"reçu : {type(record['temperature']).__name__}"
            )

    return measurements


def save_to_s3(payload: dict, request_id: str, now: datetime) -> str:
    """
    Sauvegarde le payload brut dans S3 avec partitionnement temporel :
      raw-zone/year=YYYY/month=MM/<request_id>.json
    Retourne la clé S3 du fichier créé.
    """
    s3_key = (
        f"raw-zone/"
        f"year={now.year:04d}/"
        f"month={now.month:02d}/"
        f"{request_id}.json"
    )

    s3_client.put_object(
        Bucket      = S3_BUCKET,
        Key         = s3_key,
        Body        = json.dumps(payload, ensure_ascii=False, indent=2),
        ContentType = "application/json",
    )
    return s3_key


def compute_metrics(measurements: list) -> tuple:
    """
    Calcule :
      - la température moyenne de la série reçue
      - le nombre d'enregistrements dont le statut est 'ERROR'
    Retourne (avg_temperature: float, error_count: int).
    """
    temperatures = [record["temperature"] for record in measurements]
    avg_temperature = sum(temperatures) / len(temperatures)

    error_count = sum(
        1 for record in measurements
        if str(record.get("status", "")).upper() == "ERROR"
    )
    return avg_temperature, error_count


def save_to_dynamodb(
    request_id   : str,
    timestamp    : str,
    s3_key       : str,
    avg_temp     : float,
    error_count  : int,
) -> None:
    """
    Enregistre un rapport d'exécution condensé dans la table DynamoDB.
    Clé primaire : request_id (HASH) + timestamp (RANGE).
    """
    table = dynamodb_client.Table(DYNAMODB_TABLE)
    table.put_item(
        Item={
            "request_id"      : request_id,
            "timestamp"       : timestamp,
            "s3_path"         : s3_key,
            "avg_temperature" : str(round(avg_temp, 2)),   # DynamoDB accepte Decimal ou String
            "error_count"     : error_count,
            "s3_bucket"       : S3_BUCKET,
        }
    )


def build_response(status_code: int, body: dict) -> dict:
    """
    Construit une réponse HTTP compatible API Gateway (format v2.0).
    """
    return {
        "statusCode": status_code,
        "headers"   : {
            "Content-Type"                : "application/json",
            "Access-Control-Allow-Origin" : "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
