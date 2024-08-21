#!/bin/bash

# Stop the script if any command fails
set -e

docker-compose -f docker_files/docker-compose-sales.yaml build
docker push xiomacr.azurecr.io/rdx-azure:sales-pipeline

# Create the container
az container create \
  --resource-group MYSQL-RDX \
  --name slaes-pipelines \
  --image xiomacr.azurecr.io/rdx-azure:sales-pipelines \
  --registry-login-server xiomacr.azurecr.io \
  --registry-username xiomacr \
  --registry-password PnyetZwWwcAvqLexeM0A9907iua/01p5TxRcFwiKPX+ACRCegbCA \
  --dns-name-label sales-pipelines-dns \
  --restart-policy OnFailure


  # stocks pr pipeline
docker-compose -f docker_files/docker-compose-stocks-pr.yaml build
docker push xiomacr.azurecr.io/rdx-azure:stocks-pr-pipeline

# Create the container
az container create \
  --resource-group MYSQL-RDX \
  --name stocks-pr-pipelines \
  --image xiomacr.azurecr.io/rdx-azure:stocks-pr-pipelines \
  --registry-login-server xiomacr.azurecr.io \
  --registry-username xiomacr \
  --registry-password PnyetZwWwcAvqLexeM0A9907iua/01p5TxRcFwiKPX+ACRCegbCA \
  --dns-name-label stocks-pr-pipelines-dns \
  --restart-policy OnFailure