#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ci/configure_openusd_source_repo.sh SOURCE_OWNER SOURCE_REPO CI_OWNER CI_REPO APP_ID PRIVATE_KEY_FILE

Configures SOURCE_OWNER/SOURCE_REPO as the OpenUSD source repository and
CI_OWNER/CI_REPO as the AOUSD CI-CD-CT dispatch destination.

Prerequisites:
  - gh is authenticated as a user who can administer the repository.
  - The GitHub App has Actions: Read and write permission.
  - The App is installed on the AOUSD CI-CD-CT repository.

The script configures the App ID and private key used by the dispatcher in the
OpenUSD source repository.
EOF
}

if [[ $# -ne 6 ]]; then
    usage >&2
    exit 2
fi

openusd_source_owner="$1"
openusd_source_repo="$2"
aousd_ci_cd_ct_owner="$3"
aousd_ci_cd_ct_repo="$4"
app_id="$5"
private_key_file="$6"
openusd_source_repository="${openusd_source_owner}/${openusd_source_repo}"

if [[ ! -f "$private_key_file" ]]; then
    echo "Private key file does not exist: $private_key_file" >&2
    exit 1
fi

gh auth status
gh variable set AOUSD_CI_APP_ID \
    --repo "$openusd_source_repository" \
    --body "$app_id"
gh variable set AOUSD_CI_REPOSITORY_OWNER \
    --repo "$openusd_source_repository" \
    --body "$aousd_ci_cd_ct_owner"
gh variable set AOUSD_CI_REPOSITORY_NAME \
    --repo "$openusd_source_repository" \
    --body "$aousd_ci_cd_ct_repo"
gh secret set AOUSD_CI_APP_PRIVATE_KEY \
    --repo "$openusd_source_repository" < "$private_key_file"

echo "Configured OpenUSD source repository: $openusd_source_repository"
