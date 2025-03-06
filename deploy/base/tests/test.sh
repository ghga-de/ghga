helm dep up test-service --skip-refresh
helm template test-service ./test-service --output-dir ./rendered
helm lint ./test-service
