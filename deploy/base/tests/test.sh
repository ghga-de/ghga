#!/bin/bash

# Check if an argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <service-name>"
  exit 1
fi

SERVICE_NAME=$1

# Run Helm commands with the provided service name
helm dep up "$SERVICE_NAME" --skip-refresh
helm template --namespace test  "$SERVICE_NAME" ./"$SERVICE_NAME" --output-dir ./rendered --debug
helm lint ./"$SERVICE_NAME"
