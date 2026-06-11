# Pipeline d'Ingestion de Données IoT en Temps Réel (Serverless)

> **Cours** : Introduction à AWS — Master 1 IABD 2026  
> **Étudiant** : Amos Kokou KOUGBLENOU  
> **Responsable** : Mofiala Hervé LOKOSSOU  
> **Région AWS** : `eu-west-3` (Paris)

---

## 📁 Structure du projet

```
.
├── infrastructure/
│   └── template.yaml       # Infrastructure as Code (CloudFormation)
├── src/
│   ├── index.py            # Code de la fonction AWS Lambda
│   └── test_client.py      # Script de test HTTP client
├── static/
    └── index.html          # Site de documentation technique
```

---

## ☁️ Architecture

```
Capteurs IoT
    │  HTTP POST
    ▼
CloudFront (CDN)
    │
    ▼
API Gateway  ──►  Lambda (Python 3.11)  ──►  S3 Data Lake
                        │
                        └──────────────────►  DynamoDB Feature Store

S3 Tech-Doc  ◄──  CloudFront (OAC)  ◄──  Utilisateur
```

---

## 🚀 Déploiement

### Prérequis

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installé et configuré
- Python 3.11+
- Permissions IAM suffisantes sur ton compte AWS

```bash
aws configure
# AWS Access Key ID     : <ta-clé>
# AWS Secret Access Key : <ton-secret>
# Default region name   : eu-west-3
# Default output format : json
```

---

### 1️⃣ Déployer l'infrastructure CloudFormation

```bash
aws cloudformation deploy \
  --template-file infrastructure/template.yaml \
  --stack-name akougblenou-iot-pipeline \
  --capabilities CAPABILITY_NAMED_IAM \
  --region eu-west-3
```

#### Vérifier le statut de la pile

```bash
aws cloudformation describe-stacks \
  --stack-name akougblenou-iot-pipeline \
  --region eu-west-3 \
  --query "Stacks[0].StackStatus"
```

> ✅ Le statut doit afficher `"CREATE_COMPLETE"`

#### Récupérer les URLs CloudFront (Outputs)

```bash
aws cloudformation describe-stacks \
  --stack-name akougblenou-iot-pipeline \
  --region eu-west-3 \
  --query "Stacks[0].Outputs"
```

> Les deux URLs importantes sont :
> - `CloudFrontIngestionURL` → à utiliser dans `test_client.py`
> - `CloudFrontDocURL` → URL publique de la documentation

---

### 2️⃣ Déployer le code de la fonction Lambda

```bash
cd src
zip function.zip index.py

aws lambda update-function-code \
  --function-name akougblenou-iot-ingestion \
  --zip-file fileb://function.zip \
  --region eu-west-3
```

---

### 3️⃣ Uploader la documentation technique sur S3

```bash
cd static

aws s3 cp index.html \
  s3://akougblenou-tech-doc/index.html \
  --region eu-west-3
```

---

## 🧪 Tests

> Avant de lancer les tests, remplace la valeur de `CLOUDFRONT_INGESTION_URL`  
> dans `src/test_client.py` par ta `CloudFrontIngestionURL` récupérée ci-dessus.

#### Installer la dépendance

```bash
pip install requests
```

#### Test valide — doit retourner HTTP 201

```bash
python3 src/test_client.py
```

#### Test corrompu — doit déclencher une erreur Lambda visible dans CloudWatch

```bash
python3 src/test_client.py --corrupt
```

---

## 🔒 Validation de la sécurité S3 / CloudFront OAC

| URL | Résultat attendu |
|-----|-----------------|
| `https://akougblenou-tech-doc.s3.eu-west-3.amazonaws.com/index.html` | ❌ `Access Denied` (accès S3 direct bloqué) |
| `https://<CloudFrontDocURL>` | ✅ Site de documentation affiché correctement |

---

## 🗑️ Suppression de l'infrastructure

Pour éviter des coûts inutiles, supprime la pile après le projet :

```bash
aws cloudformation delete-stack \
  --stack-name akougblenou-iot-pipeline \
  --region eu-west-3
```

---

## 📄 Licence

Projet académique — Master 1 IABD 2026. Tous droits réservés.
