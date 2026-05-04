#!/usr/bin/env bash
#
# Import an SSH key pair into Bitwarden as an SSH Key item using the Bitwarden CLI.
#
# Requires: bw (Bitwarden CLI) and jq.
# The vault must be unlocked and BW_SESSION exported, e.g.:
#   export BW_SESSION="$(bw unlock --raw)"

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bw_lib.sh"

usage() {
    cat <<EOF
Usage: $0 --name NAME --folder FOLDER --private_key PATH [--public_key PATH]

Options:
    --name          Name of the SSH key entry in Bitwarden.
    --folder        Folder in which the entry is created (created if missing).
    --private_key   Path to the private key file.
    --public_key    Path to the public key file.
                    If not specified, uses <private_key>.pub when it exists,
                    otherwise derives the public key from the private key
                    via ssh-keygen -y.
    -h, --help      Show this help and exit.
EOF
}

name=""
folder=""
private_key=""
public_key=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)         name="$2"; shift 2 ;;
        --folder)       folder="$2"; shift 2 ;;
        --private_key)  private_key="$2"; shift 2 ;;
        --public_key)   public_key="$2"; shift 2 ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

for arg in name folder private_key; do
    if [[ -z "${!arg}" ]]; then
        echo "Missing required argument: --${arg}" >&2
        usage >&2
        exit 2
    fi
done

derive_public_key=""
if [[ -z "$public_key" ]]; then
    if [[ -r "${private_key}.pub" ]]; then
        public_key="${private_key}.pub"
    else
        derive_public_key=1
    fi
fi

bw_require_tools

if [[ -n "$derive_public_key" ]] && ! command -v ssh-keygen >/dev/null 2>&1; then
    echo "ssh-keygen is required to derive the public key from $private_key" >&2
    exit 1
fi

if [[ ! -r "$private_key" ]]; then
    echo "Cannot read private key file: $private_key" >&2
    exit 1
fi
if [[ -z "$derive_public_key" && ! -r "$public_key" ]]; then
    echo "Cannot read public key file: $public_key" >&2
    exit 1
fi

bw_ensure_unlocked
bw sync >/dev/null

folder_id="$(bw_get_or_create_folder_id "$folder")"

private_key_content="$(cat "$private_key")"
if [[ -n "$derive_public_key" ]]; then
    public_key_content="$(ssh-keygen -y -f "$private_key")"
else
    public_key_content="$(cat "$public_key")"
fi

fingerprint=""
if command -v ssh-keygen >/dev/null 2>&1; then
    fingerprint="$(printf '%s\n' "$public_key_content" | ssh-keygen -l -f - 2>/dev/null | awk '{print $2}' || true)"
fi

item_json="$(jq -n \
    --arg name "$name" \
    --arg folderId "$folder_id" \
    --arg privateKey "$private_key_content" \
    --arg publicKey "$public_key_content" \
    --arg fingerprint "$fingerprint" \
    '{
        organizationId: null,
        collectionIds: null,
        folderId: $folderId,
        type: 5,
        name: $name,
        notes: null,
        favorite: false,
        fields: [],
        sshKey: {
            privateKey: $privateKey,
            publicKey: $publicKey,
            keyFingerprint: $fingerprint
        },
        reprompt: 0
    }')"

created_id="$(printf '%s' "$item_json" | bw encode | bw create item | jq -r '.id')"

echo "Created SSH key item '$name' (id: $created_id) in folder '$folder'."
