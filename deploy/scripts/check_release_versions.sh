#!/bin/bash
# This script checks for updates in GHGA GitHub repositories based on service configurations in the charts/ directory, reporting services with new releases and those skipped due to specific criteria or missing information.

# Base directory for charts
CHARTS_DIR="charts"

# Optional GitHub token to increase API rate limit
TOKEN=""

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --token) TOKEN="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

cd "$(dirname "$0")/.."

has_values_yaml(){
 [[ -f "$1/values.yaml" ]]
}

# Extract appVersion from Chart.yaml
extract_app_version() {
    grep 'appVersion:' "$1/Chart.yaml" | cut -d '"' -f 2
}

# Extract GitHub repository name from values.yaml
extract_github_repo_name(){
    grep 'image:' -A 1 "$1/values.yaml" | tail -n1 | awk -F'/' '{gsub(/"/, "", $2); print $2}'       
}

# Get the latest release version from GitHub API
get_latest_github_release() {

    local curl_cmd="curl -s \"https://api.github.com/repos/ghga-de/$1/releases/latest\""
    if [ -n "$TOKEN" ]; then
        curl_cmd+=" --header \"Authorization: Bearer $TOKEN\""
    fi
    local response=$(eval "$curl_cmd")

    if echo "$response" | grep -q 'rate limit exceeded'; then
        echo "RateLimitExceeded"
    elif echo "$response" | grep -q 'Not Found'; then
        echo "NotFound"
    else
        echo "$response" | grep 'tag_name' | cut -d '"' -f 4
    fi
}

declare -a skipped_services
declare -a updated_services

for service in "$CHARTS_DIR"/*; do
    if [[ -d "$service" ]] && has_values_yaml "$service"; then
        service_name=$(basename "$service")
        github_repo_name=$(extract_github_repo_name "$service")

        configured_version=$(extract_app_version "$service")
        latest_version="$(get_latest_github_release "$github_repo_name")"

        # If API Rate limit exceeded, exit
        if [ "$latest_version" == "RateLimitExceeded" ]; then
            echo "API Rate limit exceeded"
            exit 1
        fi
        
        # If the GitHub API returns 404
        if [ "$latest_version" == "NotFound" ]; then    
            # If service has no release, skip
            if [[ "$configured_version" == "0.0.0" ]]; then
                skipped_services+=("$service_name: No release (0.0.0)")
            else
                skipped_services+=("$service_name: Repository not found")
            fi
            continue
        fi

        if [ "$latest_version" != "$configured_version" ]; then
            updated_services+=("$service_name: $configured_version < $latest_version")
        fi
    else
        skipped_services+=("$service: values.yaml not found")
    fi
done

# Report skipped services
echo "Skipped:"
for service in "${skipped_services[@]}"; do
    echo " $service"
done

# Report updated services
echo "New release available:"
for service in "${updated_services[@]}"; do
    echo " $service"
done