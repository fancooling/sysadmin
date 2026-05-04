# Shared helpers for Bitwarden CLI scripts.
# Source this from another bash script, e.g.:
#   source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bw_lib.sh"

bw_require_tools() {
    local tool
    for tool in bw jq; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            echo "Required command not found: $tool" >&2
            return 1
        fi
    done
}

# If the vault is locked, prompt for the master password and export BW_SESSION.
# Errors out if the CLI is not logged in.
bw_ensure_unlocked() {
    local status
    status="$(bw status | jq -r '.status')"
    case "$status" in
        unlocked)
            ;;
        locked)
            BW_SESSION="$(bw unlock --raw)"
            export BW_SESSION
            ;;
        unauthenticated)
            echo "Bitwarden CLI is not logged in. Run: bw login" >&2
            return 1
            ;;
        *)
            echo "Unexpected bw status: $status" >&2
            return 1
            ;;
    esac
}

# Print folder id for the given name, or empty if not found.
bw_find_folder_id() {
    local folder="$1"
    bw list folders --search "$folder" \
        | jq -r --arg n "$folder" '.[] | select(.name == $n) | .id' \
        | head -n 1
}

# Print folder id for the given name, creating the folder if it does not exist.
bw_get_or_create_folder_id() {
    local folder="$1" id
    id="$(bw_find_folder_id "$folder")"
    if [[ -z "$id" ]]; then
        id="$(bw get template folder \
            | jq --arg n "$folder" '.name = $n' \
            | bw encode \
            | bw create folder \
            | jq -r '.id')"
    fi
    printf '%s' "$id"
}
