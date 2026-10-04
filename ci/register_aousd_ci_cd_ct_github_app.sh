#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ci/register_aousd_ci_cd_ct_github_app.sh OWNER REPO

Opens a preconfigured GitHub App registration page. The App is owned by OWNER
and dispatches events to the AOUSD CI-CD-CT repository OWNER/REPO.
EOF
}

if [[ $# -ne 2 ]]; then
    usage >&2
    exit 2
fi

aousd_ci_cd_ct_owner="$1"
aousd_ci_cd_ct_repo="$2"
github_app_name="${aousd_ci_cd_ct_owner}-${aousd_ci_cd_ct_repo}-dispatcher"
github_app_description="Dispatch%20OpenUSD%20events%20to%20AOUSD%20CI-CD-CT"
github_app_homepage="https%3A%2F%2Fgithub.com%2F${aousd_ci_cd_ct_owner}%2F${aousd_ci_cd_ct_repo}"

registration_url="https://github.com/organizations/${aousd_ci_cd_ct_owner}/settings/apps/new"
registration_url+="?name=${github_app_name}"
registration_url+="&description=${github_app_description}"
registration_url+="&url=${github_app_homepage}"
registration_url+="&request_oauth_on_install=false"
registration_url+="&public=false"
registration_url+="&webhook_active=false"
registration_url+="&actions=write"

printf 'Opening the preconfigured GitHub App registration page:\n%s\n' "${registration_url}"
python3 -m webbrowser "${registration_url}"
