# Pipeline-Ingestion-de-Donnees-IoT
Ce projet met en place une architecture serverless hautement disponible sur AWS pour ingérer en temps réel les flux de données envoyés par des milliers de capteurs IoT industriels via des requêtes HTTP POST.

# Deploiement de la pile

aws cloudformation deploy \
  --template-file infrastructure/template.yaml \
  --stack-name akougblenou-iot-pipeline \
  --capabilities CAPABILITY_NAMED_IAM \
  --region eu-west-3
  
# Verifier le statut apres deploiement

aws cloudformation describe-stacks \
  --stack-name akougblenou-iot-pipeline \
  --region eu-west-3 \
  --query "Stacks[0].StackStatus"
  
# Recuperer l'output (url cloudfront)

aws cloudformation describe-stacks \
  --stack-name akougblenou-iot-pipeline \
  --region eu-west-3 \
  --query "Stacks[0].Outputs"
  
### ========================== Fonction Lambda
# Mise a jour de la function lambda
# _________commande bash________
cd src
zip function.zip index.py 

aws lambda update-function-code \
  --function-name akougblenou-iot-ingestion \
  --zip-file fileb://function.zip \
  --region eu-west-3
  
# ========================== URL
# recuperation de l'URL CloudFrontIngestionURL

aws cloudformation describe-stacks

# ========================= Test
# Test valide → doit retourner HTTP 201

python3 test_client.py

# Test corrompu → doit déclencher une erreur Lambda visible dans CloudWatch

python3 test_client.py --corrupt

# ========================== Fichier HTML
# Uploader dans s3
# _________commande bash________
cd static

aws s3 cp index.html \
  s3://akougblenou-tech-doc/index.html \
  --region eu-west-3

# INFO

# Cet url doit retourner Access Denied
#       https://akougblenou-tech-doc.s3.eu-west-3.amazonaws.com/index.html
# Valider l'accès via CloudFront OAC
#       https://<CloudFrontDocURL>






