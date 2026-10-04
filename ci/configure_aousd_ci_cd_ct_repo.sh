#!/usr/bin/env bash

set -euo pipefail

AOUSD_CI_CD_CT_DEFAULT_BRANCH="aousd-ci-cd-ct"

usage() {
    cat <<'EOF'
Usage: ci/configure_aousd_ci_cd_ct_repo.sh CI_OWNER CI_REPO SOURCE_OWNER SOURCE_REPO

Configures CI_OWNER/CI_REPO as the AOUSD CI-CD-CT repository and allows
dispatches from SOURCE_OWNER/SOURCE_REPO, the OpenUSD Source repository.

Prerequisites:
  - gh is authenticated as a user who can administer the repository.
  - Branch aousd-ci-cd-ct has been pushed to the repository.
  - The GitHub App is installed on this repository.

The script makes aousd-ci-cd-ct the default branch so GitHub can process its
workflow_dispatch workflow.
EOF
}

if [[ $# -ne 4 ]]; then
    usage >&2
    exit 2
fi

aousd_ci_cd_ct_owner="$1"
aousd_ci_cd_ct_repo="$2"
openusd_source_owner="$3"
openusd_source_repo="$4"
aousd_ci_cd_ct_repository="${aousd_ci_cd_ct_owner}/${aousd_ci_cd_ct_repo}"
openusd_source_repository="${openusd_source_owner}/${openusd_source_repo}"

gh auth status
gh api \
    "repos/$aousd_ci_cd_ct_repository/branches/$AOUSD_CI_CD_CT_DEFAULT_BRANCH" \
    --silent
gh repo edit \
    "$aousd_ci_cd_ct_repository" \
    --default-branch "$AOUSD_CI_CD_CT_DEFAULT_BRANCH"
gh variable set OPENUSD_SOURCE_REPOSITORY \
    --repo "$aousd_ci_cd_ct_repository" \
    --body "$openusd_source_repository"

echo "Configured AOUSD CI-CD-CT repository: $aousd_ci_cd_ct_repository"
