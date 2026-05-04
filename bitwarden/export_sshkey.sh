#!/usr/bin/env bash
#
# Export an SSH Key item from Bitwarden into local private/public key files.
#
# Requires: bw (Bitwarden CLI) and jq.
# If the vault is locked, the script will prompt for the master password via `bw unlock`.

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bw_lib.sh"

usage() {
    cat <<EOF
Usage: $0 --name NAME [--folder FOLDER] --private_key PATH [--public_key PATH]

Options:
    --name          Name of the SSH key entry in Bitwarden.
    --folder        Folder name to disambiguate when multiple items share a name.
    --private_key   Destination path for the private key file (mode 0600).
    --public_key    Destination path for the public key file (mode 0644).
                    Defaults to <private_key>.pub if not specified.
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

for arg in name private_key; do
    if [[ -z "${!arg}" ]]; then
        echo "Missing required argument: --${arg}" >&2
        usage >&2
        exit 2
    fi
done

if [[ -z "$public_key" ]]; then
    public_key="${private_key}.pub"
fi

bw_require_tools
bw_ensure_unlocked
bw sync >/dev/null

folder_filter='.'
if [[ -n "$folder" ]]; then
    folder_id="$(bw_find_folder_id "$folder")"
    if [[ -z "$folder_id" ]]; then
        echo "Folder not found: $folder" >&2
        exit 1
    fi
    folder_filter="map(select(.folderId == \"$folder_id\"))"
fi

items_json="$(bw list items --search "$name" \
    | jq --arg n "$name" '[.[] | select(.type == 5 and .name == $n)]' \
    | jq "$folder_filter")"

count="$(printf '%s' "$items_json" | jq 'length')"
case "$count" in
    0)
        echo "No SSH Key item found with name '$name'${folder:+ in folder '$folder'}." >&2
        exit 1
        ;;
    1)
        ;;
    *)
        echo "Multiple SSH Key items match name '$name'${folder:+ in folder '$folder'}. Use --folder to disambiguate." >&2
        exit 1
        ;;
esac

private_key_content="$(printf '%s' "$items_json" | jq -r '.[0].sshKey.privateKey')"
public_key_content="$(printf '%s' "$items_json" | jq -r '.[0].sshKey.publicKey')"

if [[ -z "$private_key_content" || "$private_key_content" == "null" ]]; then
    echo "Item '$name' has no private key." >&2
    exit 1
fi
if [[ -z "$public_key_content" || "$public_key_content" == "null" ]]; then
    echo "Item '$name' has no public key." >&2
    exit 1
fi

umask_old="$(umask)"
umask 077
printf '%s\n' "$private_key_content" > "$private_key"
umask "$umask_old"
chmod 600 "$private_key"

printf '%s\n' "$public_key_content" > "$public_key"
chmod 644 "$public_key"

echo "Exported SSH key '$name' to:"
echo "  private: $private_key"
echo "  public:  $public_key"
