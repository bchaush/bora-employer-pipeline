#!/bin/bash
# CAREER_OS_DOCUMENT_RENDERING_CAPABILITY_V1 operator provisioning (OPERATOR_PYTHON_INSTALL_V1).
#
# The ONLY governed invocation (PROVISIONING_INVOCATION_V1), run by a human as root on the
# root-owned staged copy of PROVISIONING_STAGING_V1 after gate (3):
#
#   /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin LANG=C LC_ALL=C HOME=/nonexistent TMPDIR=/tmp \
#     DEBIAN_FRONTEND=noninteractive PIP_CONFIG_FILE=/dev/null PYTHONDONTWRITEBYTECODE=1 \
#     /bin/bash -p /var/lib/career-os-render-provision/stage-<provisioning_script_sha256>/provision_document_rendering_env.sh \
#     --approved-plan-digest <hex> --approved-interpreter-sha256 <hex> --approved-identity-digest <hex> \
#     --identity-paths <interpreter path>:<stdlib dir>:<pip package dir> --checkout-root <absolute checkout path>
#
# Any other way of running it is outside the contract. The script sources and imports no
# repository file, never edits an apt source, keyring or configuration, and grants no authority.

# PROVISIONING_PROCESS_STATE_V1: bash builtins only, before any function is defined.
umask 0022
__entry_umask=$(umask)
if [[ "$__entry_umask" != "0022" ]]; then
    printf 'PROVISIONING_ABORT status=PROVISIONING_ENV_VIOLATION reason=ENTRY_UMASK detail=%s\n' "$__entry_umask"
    exit 70
fi
cd / || exit 70
if [[ "$PWD" != "/" ]]; then
    printf 'PROVISIONING_ABORT status=PROVISIONING_ENV_VIOLATION reason=ENTRY_CWD detail=\n'
    exit 70
fi
exec 0</dev/null
ulimit -c 0 || exit 70
ulimit -Sn 1024 || exit 70
__entry_ulimit_a=$(ulimit -a)
if [[ "$-" != *p* ]]; then
    printf 'PROVISIONING_ABORT status=PROVISIONING_ENV_VIOLATION reason=ENTRY_PRIVILEGED detail=%s\n' "$-"
    exit 70
fi
__entry_env=()
mapfile -d '' -t __entry_env < "/proc/$$/environ"
__entry_expected=("PATH=/usr/sbin:/usr/bin:/sbin:/bin" "LANG=C" "LC_ALL=C" "HOME=/nonexistent" "TMPDIR=/tmp"
                  "DEBIAN_FRONTEND=noninteractive" "PIP_CONFIG_FILE=/dev/null" "PYTHONDONTWRITEBYTECODE=1")
if (( ${#__entry_env[@]} != ${#__entry_expected[@]} )); then
    printf 'PROVISIONING_ABORT status=PROVISIONING_ENV_VIOLATION reason=ENTRY_ENVIRON detail=COUNT\n'
    exit 70
fi
for __entry_want in "${__entry_expected[@]}"; do
    __entry_seen=0
    for __entry_have in "${__entry_env[@]}"; do
        [[ "$__entry_have" == "$__entry_want" ]] && __entry_seen=$((__entry_seen + 1))
    done
    if (( __entry_seen != 1 )); then
        printf 'PROVISIONING_ABORT status=PROVISIONING_ENV_VIOLATION reason=ENTRY_ENVIRON detail=%s\n' "${__entry_want%%=*}"
        exit 70
    fi
done
if [[ -n "$(declare -F)" ]]; then
    printf 'PROVISIONING_ABORT status=PROVISIONING_ENV_VIOLATION reason=ENTRY_FUNCTIONS detail=\n'
    exit 70
fi
unset PS4
# SHELLOPTS and BASHOPTS are readonly shell variables that bash itself creates; they are required
# to be absent from the environment (not exported), which is what the closed environment can produce.
if [[ -v BASH_ENV || -v ENV || -v PS4 || "${SHELLOPTS@a}" == *x* || "${BASHOPTS@a}" == *x* ]]; then
    printf 'PROVISIONING_ABORT status=PROVISIONING_ENV_VIOLATION reason=ENTRY_SHELL_VARIABLES detail=\n'
    exit 70
fi
for __entry_fd in /proc/$$/fd/*; do
    [[ -L "$__entry_fd" ]] || continue
    case "${__entry_fd##*/}" in
        0|1|2|255) ;;
        *)
            printf 'PROVISIONING_ABORT status=PROVISIONING_ENV_VIOLATION reason=ENTRY_FD detail=%s\n' "${__entry_fd##*/}"
            exit 70
            ;;
    esac
done
unset __entry_env __entry_expected __entry_want __entry_have __entry_seen __entry_fd
set -f

#BEGIN FUNCTIONS
readonly T_ENV=/usr/bin/env
readonly T_BASH=/bin/bash
readonly T_SHA256SUM=/usr/bin/sha256sum
readonly T_SORT=/usr/bin/sort
readonly T_CAT=/usr/bin/cat
readonly T_CP=/usr/bin/cp
readonly T_RM=/usr/bin/rm
readonly T_MKDIR=/usr/bin/mkdir
readonly T_CHMOD=/usr/bin/chmod
readonly T_MKTEMP=/usr/bin/mktemp
readonly T_READLINK=/usr/bin/readlink
readonly T_REALPATH=/usr/bin/realpath
readonly T_STAT=/usr/bin/stat
readonly T_FIND=/usr/bin/find
readonly T_READELF=/usr/bin/readelf
readonly T_LDCONFIG=/usr/sbin/ldconfig
readonly T_DPKG=/usr/bin/dpkg
readonly T_DPKG_QUERY=/usr/bin/dpkg-query
readonly T_APT_GET=/usr/bin/apt-get
readonly T_APT_CACHE=/usr/bin/apt-cache
readonly T_APT_CONFIG=/usr/bin/apt-config
readonly HOST_TOOLS=("$T_ENV" "$T_BASH" "$T_SHA256SUM" "$T_SORT" "$T_CAT" "$T_CP" "$T_RM" "$T_MKDIR" "$T_CHMOD"
                     "$T_MKTEMP" "$T_READLINK" "$T_REALPATH" "$T_STAT" "$T_FIND" "$T_READELF" "$T_LDCONFIG"
                     "$T_DPKG" "$T_DPKG_QUERY" "$T_APT_GET" "$T_APT_CACHE" "$T_APT_CONFIG")
# E2_HELPER_CHAIN_V1: the admitted pip helper chain. These tools are recorded (HOST_TOOL_RECORD_V1) and rechecked
# (TOOL_RECHECK_V1) like every host tool but are NEVER executed by this script; the ABSENT list holds the closed-PATH
# candidates that precede a resolved path.
readonly E2_CHAIN_TOOLS=(/usr/bin/lsb_release /usr/bin/uname /bin/sh /usr/bin/cut /usr/bin/getopt /usr/bin/tr
                         /usr/lib/os-release /etc/os-release)
readonly E2_CHAIN_ABSENT=(/usr/sbin/cut /usr/sbin/getopt /usr/sbin/lsb_release /usr/sbin/tr /usr/sbin/uname)
readonly EMPTY_ALLOWED_SHA256=4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
readonly E2_ALLOWED_SHA256=8fe144fb1cc67e33999a746feea320adb7bb40fd9b6d425a764f74babb10f5e8
readonly STAGING_PARENT=/var/lib/career-os-render-provision
readonly KAT_INPUT=career-os-render-provision-kat-v1
readonly KAT_SHA256=8c4c18304097b08e00ee536fc7c7404861f976a46999944c3b15226af34b88e7
readonly NATIVE_MAX_FILES=512
readonly NATIVE_MAX_DEPTH=16
readonly TAB=$'\t'
readonly NL=$'\n'
readonly RE_HEX64='^[0-9a-f]{64}$'
readonly RE_PRINTABLE='^[ -~]*$'
readonly RE_DPKG_LINE='^(-{0,2})([A-Za-z0-9_-]+)(=(.*)|[[:blank:]]+(.*))?$'
readonly RE_DUMP_LINE='^([^[:space:]]+) "(.*)";$'
readonly RE_PACKAGE_FIELD='^[A-Za-z0-9.+:~_-]+$'
readonly DPKG_NEVER_APPROVABLE=(pre-invoke post-invoke status-logger force- no-triggers admindir root instdir
                                no-act dry-run simulate)
readonly DEB822_FIELDS=(types uris suites components signed-by enabled architectures description x-repolib-name)

N=""
PRIV=""
MAIN_PID=$BASHPID
NO_CLEANUP=0
ID_INTERP=""
ID_STDLIB=""
ID_PIP=""
LOADER=""
E2_LAUNCH=""
CHILD_ENV=("PATH=/usr/sbin:/usr/bin:/sbin:/bin" "LANG=C" "LC_ALL=C" "HOME=/nonexistent" "TMPDIR=/tmp"
           "DEBIAN_FRONTEND=noninteractive" "PIP_CONFIG_FILE=/dev/null" "PYTHONDONTWRITEBYTECODE=1")
declare -A PH=()
declare -a SORTED=()
declare -a SPLIT=()

_evidence() {
    printf 'EVIDENCE %s=%s\n' "$1" "$2"
}

_abort() {
    local status=$1 reason=$2 detail=${3-}
    printf 'PROVISIONING_ABORT status=%s reason=%s detail=%s\n' "$status" "$reason" "$detail"
    printf 'PROVISIONING_ABORT status=%s reason=%s detail=%s\n' "$status" "$reason" "$detail" >&2
    if [[ "$BASHPID" != "$MAIN_PID" ]]; then
        kill -s TERM "$MAIN_PID"
    fi
    exit 70
}

_abort_no_exec() {
    NO_CLEANUP=1
    if [[ -n "$N" && -d "$N" ]]; then
        : > "$N/no-cleanup"
    fi
    _abort "$@"
}

_on_term() {
    exit 70
}

_cleanup() {
    if [[ "$NO_CLEANUP" == 1 || -z "$N" || "$N" != /tmp/career-os-render-provision.* || -e "$N/no-cleanup" ]]; then
        return
    fi
    cd / || return
    "$T_ENV" -i "${CHILD_ENV[@]}" "$T_RM" -rf -- "$N"
}

_closed() {
    local tool=$1
    case "$tool" in
        "$T_ENV"|"$T_BASH"|"$T_SHA256SUM"|"$T_SORT"|"$T_CAT"|"$T_CP"|"$T_RM"|"$T_MKDIR"|"$T_CHMOD"|"$T_MKTEMP"|\
        "$T_READLINK"|"$T_REALPATH"|"$T_STAT"|"$T_FIND"|"$T_READELF"|"$T_LDCONFIG"|"$T_DPKG"|"$T_DPKG_QUERY"|\
        "$T_APT_GET"|"$T_APT_CACHE"|"$T_APT_CONFIG")
            return 0
            ;;
    esac
    if [[ -n "$ID_INTERP" && "$tool" == "$ID_INTERP" ]]; then
        return 0
    fi
    if [[ -n "$E2_LAUNCH" && "$tool" == "$E2_LAUNCH" ]]; then
        return 0
    fi
    if [[ -n "$LOADER" && "$tool" == "$LOADER" && $# -eq 2 && "$2" == "--help" ]]; then
        return 0
    fi
    return 1
}

# Every external command except the private hash tool runs through here (CHILD_ENV_V1).
_x() {
    if [[ $# -eq 2 ]]; then
        _closed "$1" "$2" || _abort PROVISIONING_ENV_VIOLATION UNLISTED_EXECUTABLE "$1"
    else
        _closed "$1" || _abort PROVISIONING_ENV_VIOLATION UNLISTED_EXECUTABLE "$1"
    fi
    "$T_ENV" -i "${CHILD_ENV[@]}" "$@"
}

_set_child_home() {
    CHILD_ENV=("PATH=/usr/sbin:/usr/bin:/sbin:/bin" "LANG=C" "LC_ALL=C" "HOME=$1" "TMPDIR=$1"
               "DEBIAN_FRONTEND=noninteractive" "PIP_CONFIG_FILE=/dev/null" "PYTHONDONTWRITEBYTECODE=1")
}

_printable() {
    [[ "$1" =~ $RE_PRINTABLE && "$1" != *\"* && "$1" != *\\* ]]
}

_require_printable() {
    _printable "$1" || _abort PROVISIONING_ENV_VIOLATION TREE_UNSUPPORTED_NAME "${2-}"
}

# Reads a whole file with the read builtin into REPLY; returns 1 when the file holds a NUL byte.
_read_file() {
    REPLY=""
    local data=""
    if IFS= read -r -d '' data < "$1"; then
        REPLY=$data
        return 1
    fi
    REPLY=$data
    return 0
}

_strip_blank() {
    local s=$1
    s="${s#"${s%%[! $TAB]*}"}"
    s="${s%"${s##*[! $TAB]}"}"
    REPLY=$s
}

_strip_space() {
    local s=$1
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    REPLY=$s
}

_split_colon() {
    local s=$1
    SPLIT=()
    while [[ "$s" == *:* ]]; do
        SPLIT+=("${s%%:*}")
        s=${s#*:}
    done
    SPLIT+=("$s")
}

_dirname() {
    local p=${1%/*}
    REPLY=${p:-/}
}

_normpath() {
    local path=$1 part
    local -a parts=() out=()
    IFS=/ read -r -a parts <<< "$path"
    for part in "${parts[@]}"; do
        case "$part" in
            ""|.) ;;
            ..) (( ${#out[@]} )) && unset 'out[${#out[@]}-1]' ;;
            *) out+=("$part") ;;
        esac
    done
    local joined
    joined=$(IFS=/; printf '%s' "${out[*]}")
    REPLY="/$joined"
}

_sort_into_sorted() {
    SORTED=()
    (( $# )) || return 0
    printf '%s\n' "$@" > "$N/sort.in"
    _x "$T_SORT" -o "$N/sort.out" -- "$N/sort.in" || _abort PROVISIONING_ENV_VIOLATION SORT_FAILED
    mapfile -t SORTED < "$N/sort.out"
}

_sort_unique_into_sorted() {
    SORTED=()
    (( $# )) || return 0
    printf '%s\n' "$@" > "$N/sort.in"
    _x "$T_SORT" -u -o "$N/sort.out" -- "$N/sort.in" || _abort PROVISIONING_ENV_VIOLATION SORT_FAILED
    mapfile -t SORTED < "$N/sort.out"
}

_sort_stable_key1_into_sorted() {
    SORTED=()
    (( $# )) || return 0
    printf '%s\n' "$@" > "$N/sort.in"
    _x "$T_SORT" -s -t "$TAB" -k1,1 -o "$N/sort.out" -- "$N/sort.in" || _abort PROVISIONING_ENV_VIOLATION SORT_FAILED
    mapfile -t SORTED < "$N/sort.out"
}

# -- private hash tool (PRIVATE_LAUNCH_V1) -----------------------------------------------------

_ph_check() {
    local status=${1:-PROVISIONING_ENV_VIOLATION} reason=${2:-PRIVATE_HASH_TOOL} out
    if ! [[ -f "$PRIV" && ! -L "$PRIV" && -O "$PRIV" && -x "$PRIV" ]]; then
        _abort_no_exec "$status" "$reason" "PRIVATE_TOOL_FILE"
    fi
    out=$(printf '%s' "$KAT_INPUT" | ( exec -c "$PRIV" ))
    [[ "$out" == "$KAT_SHA256  -" ]] || _abort_no_exec "$status" "$reason" "PRIVATE_TOOL_KAT"
    out=$( ( exec -c "$PRIV" "$PRIV" ) )
    [[ "$out" == "$HT_SHA256SUM_SHA  $PRIV" ]] || _abort_no_exec "$status" "$reason" "PRIVATE_TOOL_SELF"
}

_ph_run_chunk() {
    local out line rc
    out=$( ( exec -c "$PRIV" -- "$@" ) )
    rc=$?
    (( rc == 0 )) || _abort PROVISIONING_ENV_VIOLATION HASH_FAILED "$1"
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        [[ "${line:64:2}" == "  " && "${line:0:64}" =~ $RE_HEX64 ]] || _abort PROVISIONING_ENV_VIOLATION HASH_OUTPUT
        PH["${line:66}"]=${line:0:64}
    done <<< "$out"
}

# Hashes files with the private tool into the PH map (checks (a) and (b) first).
_ph_files() {
    local path
    local -a chunk=()
    _ph_check
    for path in "$@"; do
        _printable "$path" || _abort PROVISIONING_ENV_VIOLATION TREE_UNSUPPORTED_NAME "$path"
        [[ "$path" == /* ]] || _abort PROVISIONING_ENV_VIOLATION HASH_PATH "$path"
        chunk+=("$path")
        if (( ${#chunk[@]} >= 256 )); then
            _ph_run_chunk "${chunk[@]}"
            chunk=()
        fi
    done
    if (( ${#chunk[@]} )); then
        _ph_run_chunk "${chunk[@]}"
    fi
}

_ph_string() {
    local out
    _ph_check
    out=$(printf '%s' "$1" | ( exec -c "$PRIV" ))
    [[ "${out:64}" == "  -" && "${out:0:64}" =~ $RE_HEX64 ]] || _abort PROVISIONING_ENV_VIOLATION HASH_OUTPUT
    REPLY=${out:0:64}
}

# -- HOST_TOOL_RECORD_V1 and TOOL_RECHECK_V1 -------------------------------------------------------

_owners_of() {
    local path=$1 out rc line pkgs item
    local -a found=()
    out=$(_x "$T_DPKG_QUERY" -S "$path" 2>/dev/null)
    rc=$?
    if (( rc == 1 )); then
        REPLY=UNOWNED
        return
    fi
    (( rc == 0 )) || _abort PROVISIONING_ENV_VIOLATION DPKG_QUERY_FAILED "$path"
    while IFS= read -r line; do
        [[ "$line" == "diversion by "* ]] && continue
        [[ "$line" == *": $path" ]] || continue
        pkgs=${line%": $path"}
        while [[ -n "$pkgs" ]]; do
            item=${pkgs%%, *}
            [[ "$pkgs" == *", "* ]] && pkgs=${pkgs#*, } || pkgs=""
            found+=("${item%%:*}")
        done
    done <<< "$out"
    if (( ${#found[@]} == 0 )); then
        REPLY=UNOWNED
        return
    fi
    _sort_unique_into_sorted "${found[@]}"
    REPLY=$(IFS=,; printf '%s' "${SORTED[*]}")
}

_record_tool() {
    local path=$1 real sha st owners
    real=$(_x "$T_REALPATH" -e -- "$path") || _abort PROVISIONING_ENV_VIOLATION HOST_TOOL_MISSING "$path"
    _printable "$real" || _abort PROVISIONING_ENV_VIOLATION TREE_UNSUPPORTED_NAME "$real"
    sha=$(_x "$T_SHA256SUM" -- "$path") || _abort PROVISIONING_ENV_VIOLATION HOST_TOOL_HASH "$path"
    sha=${sha:0:64}
    [[ "$sha" =~ $RE_HEX64 ]] || _abort PROVISIONING_ENV_VIOLATION HOST_TOOL_HASH "$path"
    st=$(_x "$T_STAT" -c '%d %i %s' -- "$real") || _abort PROVISIONING_ENV_VIOLATION HOST_TOOL_STAT "$path"
    _owners_of "$real"
    owners=$REPLY
    HT_PATHS+=("$path")
    HT_REALS+=("$real")
    HT_SHAS+=("$sha")
    HT_STATS+=("$st")
    HT_OWNERS+=("$owners")
    printf '%s\t%s\t%s\t%s\t%s\n' "$path" "$real" "$sha" "$st" "$owners" >> "$N/host_tool_record.tsv"
    _evidence host_tool_record "$path $real $sha $st $owners"
}

_host_tool_record() {
    local tool i
    HT_PATHS=() HT_REALS=() HT_SHAS=() HT_STATS=() HT_OWNERS=()
    : > "$N/host_tool_record.tsv"
    for tool in "${HOST_TOOLS[@]}" "$ID_INTERP"; do
        _record_tool "$tool"
    done
    _elf_info "${HT_REALS[${#HT_REALS[@]}-1]}"
    LOADER_PATH=${ELF_INTERP[${HT_REALS[${#HT_REALS[@]}-1]}]}
    [[ "$LOADER_PATH" == /* ]] || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED PT_INTERP
    _record_tool "$LOADER_PATH"
    for i in "${!HT_PATHS[@]}"; do
        if [[ "${HT_PATHS[$i]}" == "$T_SHA256SUM" ]]; then
            HT_SHA256SUM_SHA=${HT_SHAS[$i]}
        fi
        if [[ "${HT_PATHS[$i]}" == "$LOADER_PATH" ]]; then
            HT_LOADER_SHA=${HT_SHAS[$i]}
        fi
    done
}

# -- E2_HELPER_CHAIN_V1 (recorded and rechecked, never executed here) -----------------------------

_chain_absent_check() {
    local label=$1 candidate
    for candidate in "${E2_CHAIN_ABSENT[@]}"; do
        if [[ -e "$candidate" || -L "$candidate" ]]; then
            _abort_no_exec APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED "$label:ABSENT:$candidate"
        fi
    done
}

_chain_record() {
    local tool i real owners versions pkg v link
    local -a owner_list=()
    : > "$N/e2_chain.tsv"
    _chain_absent_check STEP1
    for tool in "${E2_CHAIN_TOOLS[@]}"; do
        _record_tool "$tool"
        i=$(( ${#HT_PATHS[@]} - 1 ))
        real=${HT_REALS[$i]}
        owners=${HT_OWNERS[$i]}
        [[ "$owners" != UNOWNED ]] || _abort PROVISIONING_ENV_VIOLATION E2_HELPER_CHAIN "UNOWNED:$tool"
        IFS=, read -r -a owner_list <<< "$owners"
        versions=""
        for pkg in "${owner_list[@]}"; do
            v=$(_x "$T_DPKG_QUERY" -W -f '${Version}' -- "$pkg") \
                || _abort PROVISIONING_ENV_VIOLATION DPKG_QUERY_FAILED "$pkg"
            versions+="${versions:+,}$v"
        done
        link=""
        if [[ -L "$tool" ]]; then
            link=$(_x "$T_READLINK" -- "$tool") || _abort PROVISIONING_ENV_VIOLATION HOST_TOOL_STAT "$tool"
        fi
        [[ "$tool$real$owners$versions$link" != *[\"\\]* ]] \
            || _abort PROVISIONING_ENV_VIOLATION TREE_UNSUPPORTED_NAME "$tool"
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$tool" "$real" "${HT_SHAS[$i]}" "$owners" "$versions" "$link" >> "$N/e2_chain.tsv"
        _evidence e2_chain_tool "$tool $real ${HT_SHAS[$i]} $owners $versions $link"
    done
}

_chain_rows_json() {
    local path real sha owners versions link sep="" out="["
    while IFS="$TAB" read -r path real sha owners versions link; do
        out+="$sep[\"$path\", \"$real\", \"$sha\", \"$owners\", \"$versions\", \"$link\"]"
        sep=", "
    done < "$N/e2_chain.tsv"
    REPLY="$out]"
}

_chain_absent_json() {
    local candidate sep="" out="["
    for candidate in "${E2_CHAIN_ABSENT[@]}"; do
        out+="$sep\"$candidate\""
        sep=", "
    done
    REPLY="$out]"
}

_create_private_tool() {
    local out
    PRIV="$N/sha256sum.private"
    _x "$T_CP" -- "$T_SHA256SUM" "$PRIV" || _abort PROVISIONING_ENV_VIOLATION PRIVATE_HASH_TOOL COPY
    _x "$T_CHMOD" -- 0500 "$PRIV" || _abort PROVISIONING_ENV_VIOLATION PRIVATE_HASH_TOOL CHMOD
    out=$( ( exec -c "$PRIV" "$PRIV" "$T_SHA256SUM" ) )
    [[ "$out" == "$HT_SHA256SUM_SHA  $PRIV${NL}$HT_SHA256SUM_SHA  $T_SHA256SUM" ]] \
        || _abort PROVISIONING_ENV_VIOLATION PRIVATE_HASH_TOOL COPY_HASH
    _ph_check
}

# TOOL_RECHECK_V1 T1-T4, hash-first.
_tool_recheck() {
    local label=$1 path real sha st owners i out
    local -a rec_paths=() rec_reals=() rec_shas=() rec_stats=() rec_owners=()
    # T1: recorded strings, builtins only.
    while IFS="$TAB" read -r path real sha st owners; do
        rec_paths+=("$path")
        rec_reals+=("$real")
        rec_shas+=("$sha")
        rec_stats+=("$st")
        rec_owners+=("$owners")
    done < "$N/host_tool_record.tsv"
    if [[ "${rec_paths[*]}" != "${HT_PATHS[*]}" || "${rec_shas[*]}" != "${HT_SHAS[*]}" ]]; then
        _abort_no_exec APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED "$label:RECORD"
    fi
#T2_T3_BEGIN
    _ph_check APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED
    for i in "${!rec_paths[@]}"; do
        out=$( ( exec -c "$PRIV" -- "${rec_paths[$i]}" "${rec_reals[$i]}" ) )
        if [[ "$out" != "${rec_shas[$i]}  ${rec_paths[$i]}${NL}${rec_shas[$i]}  ${rec_reals[$i]}" ]]; then
            _abort_no_exec APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED "$label:${rec_paths[$i]}"
        fi
    done
#T2_T3_END
    # T4: the tools are verified; re-read realpath, st_dev, st_ino, size and owner.
    for i in "${!rec_paths[@]}"; do
        real=$(_x "$T_REALPATH" -e -- "${rec_paths[$i]}") \
            || _abort_no_exec APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED "$label:${rec_paths[$i]}:REALPATH"
        [[ "$real" == "${rec_reals[$i]}" ]] \
            || _abort_no_exec APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED "$label:${rec_paths[$i]}:REALPATH"
        st=$(_x "$T_STAT" -c '%d %i %s' -- "$real") \
            || _abort_no_exec APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED "$label:${rec_paths[$i]}:STAT"
        [[ "$st" == "${rec_stats[$i]}" ]] \
            || _abort_no_exec APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED "$label:${rec_paths[$i]}:STAT"
        _owners_of "$real"
        [[ "$REPLY" == "${rec_owners[$i]}" ]] \
            || _abort_no_exec APT_UNEXPECTED_CHANGE HOST_TOOL_PACKAGE "$label:${rec_paths[$i]}"
    done
    _chain_absent_check "$label"
    _evidence tool_recheck "$label PASS"
}

# -- ELF facts (readelf) ---------------------------------------------------------------------------

declare -A ELF_CLASS=() ELF_MACHINE=() ELF_INTERP=() ELF_NEEDED=() ELF_RPATH=() ELF_HAS_RPATH=() \
    ELF_RUNPATH=() ELF_HAS_RUNPATH=()

_elf_info() {
    local path=$1 out line stripped
    [[ -v ELF_CLASS[$path] ]] && return 0
    out=$(_x "$T_READELF" -h -l -d -- "$path" 2>/dev/null) \
        || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "READELF:$path"
    local class="" machine="" interp="" needed="" rpath="" has_rpath=0 runpath="" has_runpath=0
    local re_dyn='\((NEEDED|RPATH|RUNPATH)\)[[:space:]]+[^[]*\[(.*)\][[:space:]]*$'
    local re_interp='\[Requesting program interpreter: ([^][:space:]]+)\]'
    while IFS= read -r line; do
        _strip_space "$line"
        stripped=$REPLY
        if [[ "$stripped" == Class:* ]]; then
            _strip_space "${stripped#Class:}"
            class=$REPLY
        elif [[ "$stripped" == Machine:* ]]; then
            _strip_space "${stripped#Machine:}"
            machine=$REPLY
        fi
        if [[ "$line" =~ $re_dyn ]]; then
            case "${BASH_REMATCH[1]}" in
                NEEDED) needed+="${BASH_REMATCH[2]}$NL" ;;
                RPATH)
                    (( has_rpath )) && _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED DUPLICATE_RPATH
                    rpath=${BASH_REMATCH[2]}
                    has_rpath=1
                    ;;
                RUNPATH)
                    (( has_runpath )) && _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED DUPLICATE_RUNPATH
                    runpath=${BASH_REMATCH[2]}
                    has_runpath=1
                    ;;
            esac
        fi
        if [[ "$line" =~ $re_interp ]]; then
            interp=${BASH_REMATCH[1]}
        fi
    done <<< "$out"
    ELF_CLASS[$path]=$class
    ELF_MACHINE[$path]=$machine
    ELF_INTERP[$path]=$interp
    ELF_NEEDED[$path]=$needed
    ELF_RPATH[$path]=$rpath
    ELF_HAS_RPATH[$path]=$has_rpath
    ELF_RUNPATH[$path]=$runpath
    ELF_HAS_RUNPATH[$path]=$has_runpath
}

_is_elf_file() {
    local magic=""
    [[ -f "$1" && ! -L "$1" ]] || return 1
    IFS= read -r -N 4 magic < "$1" 2>/dev/null
    [[ "$magic" == $'\x7fELF' ]]
}

# -- TREE_DIGEST_EXTERNAL_V1 -----------------------------------------------------------------------

# Sets REPLY to the tree digest of $1 for kind STDLIB or PIP and TREE_FILES to its regular files.
_tree_digest() {
    local root=$1 kind=$2 rootreal list entry y m rel link rest parent name digit target
    local -a entries=() file_paths=() link_rels=() link_targets=() link_paths=() lines=() lt_targets=()
    local -A haschild=() excluded=() file_exec=() link_real=()
    [[ -d "$root" && ! -L "$root" ]] || _abort BASE_INTERPRETER_MISMATCH TREE_ROOT "$root"
    rootreal=$(_x "$T_REALPATH" -e -- "$root") || _abort BASE_INTERPRETER_MISMATCH TREE_ROOT "$root"
    list="$N/tree.$kind.lst"
    _x "$T_FIND" "$root" -mindepth 1 -printf '%y\t%m\t%P\t%l\0' > "$list" \
        || _abort BASE_INTERPRETER_MISMATCH TREE_LIST "$root"
    mapfile -d '' -t entries < "$list"
    for entry in "${entries[@]}"; do
        rest=${entry#*"$TAB"}
        rest=${rest#*"$TAB"}
        rel=${rest%%"$TAB"*}
        if [[ "$rel" == */* ]]; then
            haschild["${rel%/*}"]=1
        fi
    done
    TREE_FILES=()
    for entry in "${entries[@]}"; do
        y=${entry%%"$TAB"*}
        rest=${entry#*"$TAB"}
        m=${rest%%"$TAB"*}
        rest=${rest#*"$TAB"}
        rel=${rest%%"$TAB"*}
        link=${rest#*"$TAB"}
        if [[ "$rel" == */* ]]; then
            parent=${rel%/*}
            name=${rel##*/}
        else
            parent=""
            name=$rel
        fi
        if [[ -n "$parent" && -v excluded[$parent] ]]; then
            excluded[$rel]=1
            continue
        fi
        if [[ "$y" == d && "$name" == __pycache__ ]]; then
            excluded[$rel]=1
            continue
        fi
        if [[ "$kind" == STDLIB && -z "$parent" && ( "$name" == site-packages || "$name" == dist-packages ) ]]; then
            excluded[$rel]=1
            continue
        fi
        _require_printable "$rel" "$rel"
        case "$y" in
            d)
                [[ -z "$link" ]] || _abort BASE_INTERPRETER_MISMATCH TREE_ENTRY_TYPE "$rel"
                if [[ ! -v haschild[$rel] ]]; then
                    lines+=("$rel$TAB[\"D\",\"$rel\"]")
                fi
                ;;
            f)
                [[ -z "$link" ]] || _abort BASE_INTERPRETER_MISMATCH TREE_ENTRY_TYPE "$rel"
                m="000$m"
                digit=${m: -3:1}
                file_exec[$rel]=$(( digit & 1 ))
                file_paths+=("$root/$rel")
                TREE_FILES+=("$root/$rel")
                ;;
            l)
                _require_printable "$link" "$rel"
                link_rels+=("$rel")
                link_targets+=("$link")
                link_paths+=("$root/$rel")
                ;;
            *)
                _abort BASE_INTERPRETER_MISMATCH TREE_ENTRY_TYPE "$rel"
                ;;
        esac
    done
    local i out
    local -a reals=() chunk=()
    for (( i = 0; i < ${#link_paths[@]}; i += 256 )); do
        chunk=("${link_paths[@]:i:256}")
        out=$(_x "$T_REALPATH" -- "${chunk[@]}") || _abort BASE_INTERPRETER_MISMATCH TREE_LINK_OUTSIDE "${chunk[0]}"
        mapfile -t -O "${#reals[@]}" reals <<< "$out"
    done
    for i in "${!link_rels[@]}"; do
        target=${reals[$i]}
        _require_printable "$target" "${link_rels[$i]}"
        if [[ "$target" == "$rootreal" || "$target" == "${rootreal%/}/"* ]]; then
            lines+=("${link_rels[$i]}$TAB[\"L\",\"${link_rels[$i]}\",\"${link_targets[$i]}\"]")
        elif [[ "$kind" == STDLIB && -f "$target" ]]; then
            link_real[${link_rels[$i]}]=$target
            lt_targets+=("$target")
        else
            _abort BASE_INTERPRETER_MISMATCH TREE_LINK_OUTSIDE "${link_rels[$i]}"
        fi
    done
    PH=()
    _ph_files "${file_paths[@]}" "${lt_targets[@]}"
    for rel in "${!file_exec[@]}"; do
        lines+=("$rel$TAB[\"F\",\"$rel\",${file_exec[$rel]},\"${PH[$root/$rel]}\"]")
    done
    for i in "${!link_rels[@]}"; do
        rel=${link_rels[$i]}
        if [[ -v link_real[$rel] ]]; then
            lines+=("$rel$TAB[\"LT\",\"$rel\",\"${link_targets[$i]}\",\"${PH[${link_real[$rel]}]}\"]")
        fi
    done
    _sort_into_sorted "${lines[@]}"
    local joined="" first=1 line
    for line in "${SORTED[@]}"; do
        if (( first )); then
            joined=${line#*"$TAB"}
            first=0
        else
            joined+=",${line#*"$TAB"}"
        fi
    done
    _ph_string "[$joined]"
}

# -- NATIVE_CLOSURE_V1 -----------------------------------------------------------------------------

_cache_flags_match() {
    local flags=$1 class=$2 machine=$3 part has_x8664=0 has_x32=0 first=1 ok=0
    local -a parts=()
    IFS=, read -r -a parts <<< "$flags"
    for part in "${parts[@]}"; do
        _strip_space "$part"
        part=$REPLY
        if (( first )); then
            [[ "$part" == libc6 ]] && ok=1
            first=0
        fi
        [[ "$part" == x86-64 ]] && has_x8664=1
        [[ "$part" == x32 ]] && has_x32=1
    done
    (( ok )) || return 1
    if [[ "$class" == ELF64 && "$machine" == "Advanced Micro Devices X86-64" ]]; then
        (( has_x8664 ))
        return
    fi
    if [[ "$class" == ELF32 && "$machine" == "Intel 80386" ]]; then
        (( ! has_x8664 && ! has_x32 ))
        return
    fi
    return 1
}

_parse_loader_help() {
    local text=$1 line state=0 stripped
    local re_dir='^(/[^[:space:]]*) \(system search path\)$'
    SYSTEM_DIRS=()
    while IFS= read -r line; do
        case $state in
            0)
                [[ "$line" == "Shared library search path:" ]] && state=1
                ;;
            1)
                _strip_space "$line"
                [[ "$REPLY" == "(libraries located via /etc/ld.so.cache)" ]] \
                    || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED LOADER_DIRS
                state=2
                ;;
            2)
                _strip_space "$line"
                stripped=$REPLY
                [[ -z "$stripped" ]] && break
                [[ "$stripped" =~ $re_dir ]] || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED LOADER_DIRS
                SYSTEM_DIRS+=("${BASH_REMATCH[1]}")
                ;;
        esac
    done <<< "$text"
    (( state == 2 && ${#SYSTEM_DIRS[@]} )) || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED LOADER_DIRS
}

_record_chain() {
    local path=$1 current=$1 target hops=0
    while [[ -L "$current" ]]; do
        target=$(_x "$T_READLINK" -- "$current") || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "READLINK:$current"
        _require_printable "$target" "$current"
        NC_LINKS["$current$TAB$target"]=1
        if [[ "$target" == /* ]]; then
            current=$target
        else
            _dirname "$current"
            _normpath "${REPLY%/}/$target"
            current=$REPLY
        fi
        hops=$((hops + 1))
        (( hops > 40 )) && _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED LINK_LOOP
    done
    REPLY=$(_x "$T_REALPATH" -- "$path") || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "REALPATH:$path"
    _require_printable "$REPLY" "$path"
}

_has_symlink_component() {
    local path=$1 current="" part
    local -a parts=()
    IFS=/ read -r -a parts <<< "${path#/}"
    unset 'parts[${#parts[@]}-1]'
    for part in "${parts[@]}"; do
        current+="/$part"
        [[ -L "$current" ]] && return 0
    done
    return 1
}

_expand_entries() {
    local value=$1 loaded=$2 soname=$3 item base dir
    _dirname "$loaded"
    base=$REPLY
    _split_colon "$value"
    for item in "${SPLIT[@]}"; do
        item=${item//'${ORIGIN}'/$base}
        item=${item//'$ORIGIN'/$base}
        dir=$item
        while [[ "$dir" == */ ]]; do
            dir=${dir%/}
        done
        CANDIDATES+=("$dir/$soname")
    done
}

# Sets REPLY to native_closure_digest for the roots in NC_ROOTS (NC_ROOTS[0] is the interpreter realpath).
_native_closure() {
    local interp_real=${NC_ROOTS[0]} loader help cache_text line real loaded chain id soname carrier
    local -a cache_soname=() cache_flags=() cache_path=() level=() next=() roots_sorted=() items=()
    local re_cache='^[[:space:]]+([^[:space:]]+) \(([^)]*)\) => ([^[:space:]]+)$'
    declare -gA NC_FILES=() NC_LINKS=() NC_ABSENT=() NC_VISITED=() NC_EDGES=() NC_LOADED_PATHS=()
    declare -ga NODE_LOADED=() NODE_REAL=()
    if [[ -e /etc/ld.so.preload || -L /etc/ld.so.preload ]]; then
        _abort BASE_INTERPRETER_MISMATCH LOADER_PRELOAD
    fi
    _elf_info "$interp_real"
    loader=${ELF_INTERP[$interp_real]}
    [[ "$loader" == /* ]] || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED PT_INTERP
    [[ "$loader" == "$LOADER_PATH" ]] || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED PT_INTERP_CHANGED
    PH=()
    _ph_files "$loader"
    [[ "${PH[$loader]}" == "$HT_LOADER_SHA" ]] || _abort APT_UNEXPECTED_CHANGE HOST_TOOL_CHANGED "$loader"
    LOADER=$loader
    help=$(_x "$loader" --help) || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED LOADER_DIRS
    LOADER=""
    _parse_loader_help "$help"
    cache_text=$(_x "$T_LDCONFIG" -p) || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED LDCONFIG
    local skip=1
    while IFS= read -r line; do
        if (( skip )); then
            skip=0
            continue
        fi
        if [[ "$line" =~ $re_cache ]]; then
            cache_soname+=("${BASH_REMATCH[1]}")
            cache_flags+=("${BASH_REMATCH[2]}")
            cache_path+=("${BASH_REMATCH[3]}")
        fi
    done <<< "$cache_text"
    _record_chain "$loader"
    local loader_real=$REPLY
    NC_FILES[$loader_real]=1
    NC_LOADED_PATHS[$loader]=1

    _sort_unique_into_sorted "${NC_ROOTS[@]}"
    roots_sorted=("${SORTED[@]}")
    local out
    local -a root_reals=() chunk=()
    local i
    for (( i = 0; i < ${#roots_sorted[@]}; i += 256 )); do
        chunk=("${roots_sorted[@]:i:256}")
        out=$(_x "$T_REALPATH" -- "${chunk[@]}") || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED ROOT_REALPATH
        mapfile -t -O "${#root_reals[@]}" root_reals <<< "$out"
    done
    items=()
    for i in "${!roots_sorted[@]}"; do
        _require_printable "${root_reals[$i]}" "${roots_sorted[$i]}"
        items+=("${root_reals[$i]}$TAB${roots_sorted[$i]}$TAB")
    done
    _sort_stable_key1_into_sorted "${items[@]}"
    level=("${SORTED[@]}")
    local depth=0 node_count=0 item rest token carries_origin wreal winner match_count match_path k
    local -a needed_list=() check_list=() preceding=()
    while (( ${#level[@]} )); do
        next=()
        for item in "${level[@]}"; do
            real=${item%%"$TAB"*}
            rest=${item#*"$TAB"}
            loaded=${rest%%"$TAB"*}
            chain=${rest#*"$TAB"}
            [[ -v NC_VISITED[$real] ]] && continue
            (( depth > NATIVE_MAX_DEPTH )) && _abort BASE_INTERPRETER_MISMATCH NATIVE_CLOSURE_LIMIT DEPTH
            _elf_info "$real"
            id=$node_count
            node_count=$((node_count + 1))
            NC_VISITED[$real]=$id
            NODE_LOADED[$id]=$loaded
            NODE_REAL[$id]=$real
            NC_FILES[$real]=1
            NC_LOADED_PATHS[$loaded]=1
            (( ${#NC_FILES[@]} > NATIVE_MAX_FILES )) && _abort BASE_INTERPRETER_MISMATCH NATIVE_CLOSURE_LIMIT FILES
            mapfile -t needed_list <<< "${ELF_NEEDED[$real]%"$NL"}"
            [[ -z "${ELF_NEEDED[$real]}" ]] && needed_list=()
            check_list=("${needed_list[@]}")
            (( ${ELF_HAS_RPATH[$real]} )) && check_list+=("${ELF_RPATH[$real]}")
            (( ${ELF_HAS_RUNPATH[$real]} )) && check_list+=("${ELF_RUNPATH[$real]}")
            for token in "${check_list[@]}"; do
                if [[ "$token" == *'$LIB'* || "$token" == *'${LIB}'* || "$token" == *'$PLATFORM'* \
                      || "$token" == *'${PLATFORM}'* || "$token" == *'$HWCAP'* ]]; then
                    _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "FORBIDDEN_TOKEN:$real"
                fi
            done
            carries_origin=0
            if (( ${ELF_HAS_RPATH[$real]} )) && [[ "${ELF_RPATH[$real]}" == *'$ORIGIN'* || "${ELF_RPATH[$real]}" == *'${ORIGIN}'* ]]; then
                carries_origin=1
            fi
            if (( ${ELF_HAS_RUNPATH[$real]} )) && [[ "${ELF_RUNPATH[$real]}" == *'$ORIGIN'* || "${ELF_RUNPATH[$real]}" == *'${ORIGIN}'* ]]; then
                carries_origin=1
            fi
            if (( carries_origin )); then
                if [[ "$loaded" != "$real" ]] || _has_symlink_component "$loaded"; then
                    _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "ORIGIN_VIA_SYMLINK:$loaded"
                fi
            fi
            for soname in "${needed_list[@]}"; do
                [[ "$soname" == */* ]] && _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "SONAME_SLASH:$soname"
                CANDIDATES=()
                if (( ! ${ELF_HAS_RUNPATH[$real]} )); then
                    for carrier in $id $chain; do
                        if (( ! ${ELF_HAS_RUNPATH[${NODE_REAL[$carrier]}]} && ${ELF_HAS_RPATH[${NODE_REAL[$carrier]}]} )); then
                            _expand_entries "${ELF_RPATH[${NODE_REAL[$carrier]}]}" "${NODE_LOADED[$carrier]}" "$soname"
                        fi
                    done
                else
                    for carrier in $chain; do
                        if (( ! ${ELF_HAS_RUNPATH[${NODE_REAL[$carrier]}]} && ${ELF_HAS_RPATH[${NODE_REAL[$carrier]}]} )); then
                            _expand_entries "${ELF_RPATH[${NODE_REAL[$carrier]}]}" "${NODE_LOADED[$carrier]}" "$soname"
                        fi
                    done
                    _expand_entries "${ELF_RUNPATH[$real]}" "$loaded" "$soname"
                fi
                match_count=0
                match_path=""
                for k in "${!cache_soname[@]}"; do
                    if [[ "${cache_soname[$k]}" == "$soname" ]] \
                        && _cache_flags_match "${cache_flags[$k]}" "${ELF_CLASS[$real]}" "${ELF_MACHINE[$real]}"; then
                        match_count=$((match_count + 1))
                        [[ -z "$match_path" ]] && match_path=${cache_path[$k]}
                    fi
                done
                (( match_count > 1 )) && _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "CACHE_AMBIGUOUS:$soname"
                if (( match_count == 1 )); then
                    [[ "$match_path" == */glibc-hwcaps/* ]] && _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "GLIBC_HWCAPS:$soname"
                    CANDIDATES+=("$match_path")
                fi
                local d
                for d in "${SYSTEM_DIRS[@]}"; do
                    while [[ "$d" == */ ]]; do
                        d=${d%/}
                    done
                    CANDIDATES+=("$d/$soname")
                done
                winner=""
                preceding=()
                for k in "${CANDIDATES[@]}"; do
                    if [[ -e "$k" || -L "$k" ]]; then
                        winner=$k
                        break
                    fi
                    preceding+=("$k")
                done
                [[ -n "$winner" ]] || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "SONAME:$soname:$real"
                _require_printable "$winner" "$soname"
                _record_chain "$winner"
                wreal=$REPLY
                [[ -f "$wreal" ]] || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "SONAME:$soname:$real"
                for k in "${preceding[@]}"; do
                    _require_printable "$k" "$soname"
                    NC_ABSENT[$k]=1
                done
                NC_EDGES[$real]+="$wreal$NL"
                next+=("$wreal$TAB$winner$TAB$id${chain:+ $chain}")
            done
        done
        _sort_stable_key1_into_sorted "${next[@]}"
        level=("${SORTED[@]}")
        depth=$((depth + 1))
    done
    local -A reach=()
    local -a pending=("$interp_real")
    local current e
    local -a edge_list=()
    while (( ${#pending[@]} )); do
        current=${pending[${#pending[@]}-1]}
        unset 'pending[${#pending[@]}-1]'
        [[ -v reach[$current] ]] && continue
        reach[$current]=1
        if [[ -n "${NC_EDGES[$current]-}" ]]; then
            mapfile -t edge_list <<< "${NC_EDGES[$current]%"$NL"}"
            for e in "${edge_list[@]}"; do
                pending+=("$e")
            done
        fi
    done
    for current in "${!reach[@]}"; do
        if (( ${ELF_HAS_RPATH[$current]} )); then
            _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED "MAIN_PROGRAM_RPATH:$current"
        fi
    done
    local -a inputs=() input_paths=() names=()
    local p
    for p in /etc/ld.so.cache /etc/ld.so.conf; do
        if [[ ( -e "$p" || -L "$p" ) && -f "$p" ]]; then
            input_paths+=("$p")
        fi
    done
    if [[ -d /etc/ld.so.conf.d ]]; then
        _x "$T_FIND" /etc/ld.so.conf.d -mindepth 1 -maxdepth 1 -printf '%f\0' > "$N/ldsoconf.lst" \
            || _abort BASE_INTERPRETER_MISMATCH NATIVE_UNRESOLVED LOADER_INPUTS
        mapfile -d '' -t names < "$N/ldsoconf.lst"
        for p in "${names[@]}"; do
            p="/etc/ld.so.conf.d/$p"
            if [[ ( -e "$p" || -L "$p" ) && -f "$p" ]]; then
                input_paths+=("$p")
            fi
        done
    fi
    NC_ABSENT[/etc/ld.so.preload]=1
    PH=()
    _ph_files "${!NC_FILES[@]}" "${input_paths[@]}"
    LOADER_INPUT_PATHS=("${input_paths[@]}")
    local files_json="" links_json="" absent_json="" inputs_json="" dirs_json="" sep
    _sort_into_sorted "${!NC_FILES[@]}"
    sep=""
    for p in "${SORTED[@]}"; do
        files_json+="$sep[\"$p\",\"${PH[$p]}\"]"
        sep=","
    done
    _sort_into_sorted "${!NC_LINKS[@]}"
    sep=""
    for p in "${SORTED[@]}"; do
        links_json+="$sep[\"${p%%"$TAB"*}\",\"${p#*"$TAB"}\"]"
        sep=","
    done
    _sort_into_sorted "${!NC_ABSENT[@]}"
    sep=""
    for p in "${SORTED[@]}"; do
        absent_json+="$sep\"$p\""
        sep=","
    done
    _sort_into_sorted "${input_paths[@]}"
    sep=""
    for p in "${SORTED[@]}"; do
        inputs_json+="$sep[\"$p\",\"${PH[$p]}\"]"
        sep=","
    done
    sep=""
    for p in "${SYSTEM_DIRS[@]}"; do
        _require_printable "$p" "system_dirs"
        dirs_json+="$sep\"$p\""
        sep=","
    done
    NC_JSON="{\"closure\":{\"absent\":[$absent_json],\"files\":[$files_json],\"links\":[$links_json],\"loader\":[\"$loader_real\",\"${PH[$loader_real]}\"],\"loader_inputs\":[$inputs_json],\"system_dirs\":[$dirs_json]},\"spec\":\"NATIVE_CLOSURE_V1\"}"
    NC_CACHE_SHA=${PH[/etc/ld.so.cache]-}
    NC_COUNTS="files=${#NC_FILES[@]} links=${#NC_LINKS[@]} loader_inputs=${#input_paths[@]} absent=${#NC_ABSENT[@]}"
    _ph_string "$NC_JSON"
}

# POST_APT_LD_SO_CACHE_V1 (the ONLY native-closure difference admitted after the apt phase). Returns 0 only when the
# live closure object NC_JSON equals the PRE_APT closure object PRE_NC_JSON with nothing but the SHA-256 of the
# generated loader input /etc/ld.so.cache replaced (this one string equality covers every other file member, link,
# loader, system_dirs, /etc/ld.so.conf, /etc/ld.so.conf.d member, absent member and the resolved non-cache member
# set), the apt phase and its package and transaction checks have completed (identity_critical delta, approved plan),
# the captured apt output of that exact transaction proves the libc-bin trigger, and at STEP6 the cache SHA-256
# equals the value accepted at STEP4. Interpreter, stdlib and pip identity are covered by the caller, which compares
# IDENTITY_DIGEST_V1 evaluated with the PRE_APT native_closure_digest. Any other state returns 1 (no exception).
_post_apt_ld_so_cache() {
    local label=$1 cache=/etc/ld.so.cache pattern_pre pattern_post rest expected
    [[ "$label" == STEP4 || "$label" == STEP6 ]] || return 1
    [[ -n "${APT_PHASE_COMPLETE-}" && -n "${APT_LIBC_BIN_TRIGGER-}" ]] || return 1
    [[ -n "${PRE_NC_JSON-}" && -n "${PRE_CACHE_SHA-}" && -n "${NC_CACHE_SHA-}" && "$NC_CACHE_SHA" != "$PRE_CACHE_SHA" ]] || return 1
    [[ "$PRE_CACHE_SHA" =~ $RE_HEX64 && "$NC_CACHE_SHA" =~ $RE_HEX64 ]] || return 1
    if [[ "$label" == STEP6 ]]; then
        [[ "${ACCEPTED_CACHE_SHA+set}" == set && "$NC_CACHE_SHA" == "$ACCEPTED_CACHE_SHA" ]] || return 1
    fi
    pattern_pre="[\"$cache\",\"$PRE_CACHE_SHA\"]"
    pattern_post="[\"$cache\",\"$NC_CACHE_SHA\"]"
    rest=${PRE_NC_JSON#*"$pattern_pre"}
    [[ "$rest" != "$PRE_NC_JSON" && "$rest" != *"$pattern_pre"* ]] || return 1
    expected=${PRE_NC_JSON/"$pattern_pre"/"$pattern_post"}
    [[ "$expected" == "$NC_JSON" ]] || return 1
    return 0
}

# Sets APT_LIBC_BIN_TRIGGER to the dpkg trigger record of the installed libc-bin version found in the captured
# output of the approved apt-get install (APT_INSTALL_OUTPUT), else to the empty string.
_libc_bin_trigger_check() {
    local row name arch version status line found=0 want=""
    APT_LIBC_BIN_TRIGGER=""
    for row in "${STATE[@]}"; do
        IFS="$TAB" read -r name arch version status <<< "$row"
        if [[ "$name" == libc-bin && "$status" == "install ok installed" ]]; then
            (( found += 1 ))
            want=$version
        fi
    done
    (( found == 1 )) || return 0
    while IFS= read -r line; do
        if [[ "$line" == "Processing triggers for libc-bin ($want) ..." ]]; then
            APT_LIBC_BIN_TRIGGER=$line
        fi
    done <<< "${APT_INSTALL_OUTPUT-}"
    return 0
}

# -- IDENTITY_VERIFICATION_V1 PART 1 (external) ----------------------------------------------------

# Sets REPLY to IDENTITY_DIGEST_V1 for the live identity members with native_closure_digest $1.
_identity_digest_with() {
    _ph_string "{\"executable_sha256\":\"$APPROVED_INTERPRETER_SHA256\",\"installer_pip_package_path\":\"$ID_PIP\",\"installer_pip_package_tree_digest\":\"$PROVEN_PIP_DIGEST\",\"interpreter_path\":\"$ID_INTERP\",\"interpreter_realpath\":\"$INTERP_REAL\",\"native_closure_digest\":\"$1\",\"spec\":\"IDENTITY_DIGEST_V1\",\"stdlib_path\":\"$ID_STDLIB\",\"stdlib_tree_digest\":\"$PROVEN_STDLIB_DIGEST\"}"
}

# Decision of one identity verification from the live values (PROVEN_*, NC_JSON, NC_CACHE_SHA, NC_COUNTS) for label
# PRE_APT, STEP4 or STEP6; emits the identity evidence, enforces the approved identity and POST_APT_LD_SO_CACHE_V1.
_identity_decide() {
    local label=$1
    _identity_digest_with "$PROVEN_CLOSURE_DIGEST"
    PROVEN_IDENTITY=$REPLY
    _evidence "identity_$label" "stdlib_tree_digest=$PROVEN_STDLIB_DIGEST installer_pip_package_tree_digest=$PROVEN_PIP_DIGEST native_closure_digest=$PROVEN_CLOSURE_DIGEST identity_digest=$PROVEN_IDENTITY"
    # POST_APT_LD_SO_CACHE_V1: after STEP4 accepted a cache SHA-256, any later recheck must see exactly that value.
    if [[ "$label" == STEP6 && "${ACCEPTED_CACHE_SHA+set}" == set && "$NC_CACHE_SHA" != "$ACCEPTED_CACHE_SHA" ]]; then
        _abort BASE_INTERPRETER_MISMATCH NATIVE_CLOSURE "$label"
    fi
    if [[ "$PROVEN_IDENTITY" != "$APPROVED_IDENTITY_DIGEST" ]]; then
        if [[ -n "${APPROVED_CLOSURE_DIGEST-}" && "$PROVEN_CLOSURE_DIGEST" != "$APPROVED_CLOSURE_DIGEST" ]]; then
            _post_apt_ld_so_cache "$label" || _abort BASE_INTERPRETER_MISMATCH NATIVE_CLOSURE "$label"
            # Admitted case: IDENTITY_DIGEST_V1 is evaluated with the PRE_APT native_closure_digest (the live values
            # above stay evidence only), so every other identity member must still equal the approved one.
            _identity_digest_with "$APPROVED_CLOSURE_DIGEST"
            [[ "$REPLY" == "$APPROVED_IDENTITY_DIGEST" ]] || _abort BASE_INTERPRETER_MISMATCH IDENTITY_DIGEST "$label"
            _evidence post_apt_ld_so_cache_record "label=$label spec=POST_APT_LD_SO_CACHE_V1"
            _evidence post_apt_ld_so_cache_record "pre_apt_native_closure_digest=$APPROVED_CLOSURE_DIGEST"
            _evidence post_apt_ld_so_cache_record "post_apt_native_closure_digest=$PROVEN_CLOSURE_DIGEST"
            _evidence post_apt_ld_so_cache_record "post_apt_live_identity_digest=$PROVEN_IDENTITY"
            _evidence post_apt_ld_so_cache_record "approved_identity_digest_compared_with_pre_apt_native_closure_digest=$APPROVED_IDENTITY_DIGEST"
            _evidence post_apt_ld_so_cache_record "old_ld_so_cache_sha256=$PRE_CACHE_SHA"
            _evidence post_apt_ld_so_cache_record "new_ld_so_cache_sha256=$NC_CACHE_SHA"
            _evidence post_apt_ld_so_cache_record "pre_apt_members=$PRE_NC_COUNTS"
            _evidence post_apt_ld_so_cache_record "post_apt_members=$NC_COUNTS"
            _evidence post_apt_ld_so_cache_record "other_members_differing=0"
            _evidence post_apt_ld_so_cache_record "apt_transaction_plan_digest=$APPROVED_PLAN_DIGEST apt_install_argv_sha256=$APT_TRANSACTION_SHA256"
            _evidence post_apt_ld_so_cache_record "libc_bin_trigger=$APT_LIBC_BIN_TRIGGER"
            [[ "$label" == STEP4 ]] && ACCEPTED_CACHE_SHA=$NC_CACHE_SHA
            return 0
        fi
        _abort BASE_INTERPRETER_MISMATCH IDENTITY_DIGEST "$label"
    fi
    if [[ "$label" == PRE_APT ]]; then
        PRE_NC_JSON=$NC_JSON
        PRE_CACHE_SHA=$NC_CACHE_SHA
        PRE_NC_COUNTS=$NC_COUNTS
    fi
    [[ "$label" == STEP4 ]] && ACCEPTED_CACHE_SHA=$NC_CACHE_SHA
    APPROVED_CLOSURE_DIGEST=$PROVEN_CLOSURE_DIGEST
    return 0
}

_identity_external() {
    local label=$1 interp_real out f
    interp_real=$(_x "$T_REALPATH" -e -- "$ID_INTERP") || _abort BASE_INTERPRETER_MISMATCH EXECUTABLE_SHA256 "$label:REALPATH"
    _require_printable "$interp_real" interpreter
    [[ "$interp_real" != *:* ]] || _abort BASE_INTERPRETER_MISMATCH IDENTITY_DIGEST "$label:REALPATH_COLON"
    PH=()
    _ph_files "$interp_real"
    [[ "${PH[$interp_real]}" == "$APPROVED_INTERPRETER_SHA256" ]] \
        || _abort BASE_INTERPRETER_MISMATCH EXECUTABLE_SHA256 "$label"
    INTERP_REAL=$interp_real
    _tree_digest "$ID_STDLIB" STDLIB
    PROVEN_STDLIB_DIGEST=$REPLY
    STDLIB_FILES=("${TREE_FILES[@]}")
    [[ -d "$ID_PIP" && ! -L "$ID_PIP" ]] || _abort PIP_UNAVAILABLE PIP_UNAVAILABLE "$label:$ID_PIP"
    _tree_digest "$ID_PIP" PIP
    PROVEN_PIP_DIGEST=$REPLY
    PIP_FILES=("${TREE_FILES[@]}")
    NC_ROOTS=("$interp_real")
    for f in "${STDLIB_FILES[@]}" "${PIP_FILES[@]}"; do
        _is_elf_file "$f" && NC_ROOTS+=("$f")
    done
    _native_closure
    PROVEN_CLOSURE_DIGEST=$REPLY
    _identity_decide "$label"
}

# SYS_PATH_VALIDATION_V1 rule (1): $1 = newline-separated entries, $2 = optional prefix lib dir.
_sys_path_rule1() {
    local entries=$1 prefix_lib=${2-} entry real stdlib_real parent out
    local -a list=() parents=()
    stdlib_real=$(_x "$T_REALPATH" -e -- "$ID_STDLIB") || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND STDLIB
    mapfile -t list <<< "$entries"
    for entry in "${list[@]}"; do
        [[ -n "$entry" ]] || continue
        if [[ -e "$entry" || -L "$entry" ]]; then
            [[ -d "$entry" ]] || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "$entry"
            real=$(_x "$T_REALPATH" -e -- "$entry") || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "$entry"
            [[ "$real" == "$stdlib_real" || "$real" == "${stdlib_real%/}/"* ]] \
                || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "$entry"
        fi
    done
    _dirname "${ID_STDLIB%/}"
    parents=("$REPLY")
    [[ -n "$prefix_lib" ]] && parents+=("$prefix_lib")
    for parent in "${parents[@]}"; do
        out=$(_x "$T_FIND" "$parent" -mindepth 1 -maxdepth 1 -name 'python*.zip' -printf '%p\n') \
            || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "ZIP_LISTING:$parent"
        [[ -z "$out" ]] || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "$out"
    done
}

# STARTUP_PATH_INPUTS_V1 (rule 6) for one launch form: $1 launch path, $2 realpath, $3 permitted candidate.
_startup_path_inputs() {
    local launch=$1 real=$2 permitted=${3-} directory parent ancestor c out name
    local -a dirs=() candidates=() pth=()
    _dirname "$launch"
    dirs=("$REPLY")
    _dirname "$real"
    [[ "$REPLY" != "${dirs[0]}" ]] && dirs+=("$REPLY")
    for directory in "${dirs[@]}"; do
        _dirname "$directory"
        parent=$REPLY
        candidates+=("${directory%/}/pyvenv.cfg" "${parent%/}/pyvenv.cfg" "${directory%/}/pybuilddir.txt")
        if [[ -d "$directory" ]]; then
            _x "$T_FIND" "$directory" -mindepth 1 -maxdepth 1 -name '*._pth' -printf '%f\0' > "$N/pth.lst" \
                || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "PTH_LISTING:$directory"
            mapfile -d '' -t pth < "$N/pth.lst"
            for name in "${pth[@]}"; do
                candidates+=("${directory%/}/$name")
            done
        fi
    done
    _dirname "$real"
    ancestor=$REPLY
    while :; do
        candidates+=("${ancestor%/}/Modules/Setup.local")
        [[ "$ancestor" == / ]] && break
        _dirname "$ancestor"
        ancestor=$REPLY
    done
    for c in "${candidates[@]}"; do
        if [[ -e "$c" || -L "$c" ]]; then
            [[ -n "$permitted" && "$c" == "$permitted" ]] && continue
            _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "STARTUP_PATH_INPUT:$c"
        fi
        STARTUP_ABSENT+=("$c")
    done
}

_pip_copy() {
    local copy="$N/pipcopy/pip"
    if [[ ! -e "$copy" ]]; then
        _x "$T_MKDIR" -m 0700 -- "$N/pipcopy" || _abort PIP_UNAVAILABLE PIP_UNAVAILABLE PIPCOPY_DIR
        _x "$T_CP" -R --no-dereference --preserve=mode -- "$ID_PIP" "$copy" || _abort PIP_UNAVAILABLE PIP_UNAVAILABLE PIPCOPY
        _x "$T_FIND" "$copy" -depth -path '*/__pycache__*' -delete || _abort PIP_UNAVAILABLE PIP_UNAVAILABLE PIPCOPY_PYCACHE
    fi
    _tree_digest "$copy" PIP
    [[ "$REPLY" == "$PROVEN_PIP_DIGEST" ]] || _abort PIP_MISMATCH PIP_MISMATCH PIPCOPY_DIGEST
}

_require_empty_pycache() {
    local out
    out=$(_x "$T_FIND" "$N/pycache" -mindepth 1 -printf '%p\n') || _abort PROVISIONING_ENV_VIOLATION PYCACHE "$1"
    [[ -z "$out" ]] || _abort PROVISIONING_ENV_VIOLATION PYCACHE "$1"
}

# Runs one governed execution and requires exit 0 plus the success lines DENIED_EVENTS=0 and ALLOWED_EVENTS=<approved digest>.
_governed() {
    local label=$1 out rc expected_allowed=$EMPTY_ALLOWED_SHA256
    shift
    [[ "$label" == E2 ]] && expected_allowed=$E2_ALLOWED_SHA256
    _require_empty_pycache "$label"
    _evidence governed_execution "$label $(printf '%q ' "${@:1:6}")<code:$label>"
    out=$(_x "$@")
    rc=$?
    printf '%s\n' "$out" | while IFS= read -r line; do printf 'GOVERNED[%s] %s\n' "$label" "$line"; done
    if (( rc != 0 )); then
        _abort PROVISIONING_ENV_VIOLATION GOVERNED_EXECUTION_FAILED "$label:$rc"
    fi
    [[ "$out" == *"${NL}DENIED_EVENTS=0${NL}ALLOWED_EVENTS=$expected_allowed" \
       || "$out" == "DENIED_EVENTS=0${NL}ALLOWED_EVENTS=$expected_allowed" ]] \
        || _abort PROVISIONING_ENV_VIOLATION PROCESS_CREATION "$label:NO_SUCCESS_LINE"
    GOVERNED_COUNT=$((GOVERNED_COUNT + 1))
}

# -- APT_TRUST_MODEL_V1 ----------------------------------------------------------------------------

_apt_config_shell() {
    local out err line name value expected prefix body i
    local -a names=(SOURCELIST SOURCEPARTS TRUSTED TRUSTEDPARTS PREFERENCES PREFERENCESPARTS LISTS STATUS ARCHIVES)
    local -a keys=(Dir::Etc::sourcelist/f Dir::Etc::sourceparts/d Dir::Etc::trusted/f Dir::Etc::trustedparts/d
                   Dir::Etc::preferences/f Dir::Etc::preferencesparts/d Dir::State::lists/d Dir::State::status/f
                   Dir::Cache::archives/d)
    local -a argv=() lines=()
    for i in "${!names[@]}"; do
        argv+=("${names[$i]}" "${keys[$i]}")
    done
    out=$(_x "$T_APT_CONFIG" shell "${argv[@]}" 2>"$N/apt-config-shell.err") \
        || _abort APT_CONFIG_UNAPPROVED SHELL_OUTPUT_MALFORMED EXIT_STATUS
    _read_file "$N/apt-config-shell.err" || _abort APT_CONFIG_UNAPPROVED SHELL_OUTPUT_MALFORMED NUL
    [[ -z "$REPLY" ]] || _abort APT_CONFIG_UNAPPROVED SHELL_OUTPUT_MALFORMED STDERR
    mapfile -t lines <<< "$out"
    (( ${#lines[@]} == ${#names[@]} )) || _abort APT_CONFIG_UNAPPROVED SHELL_OUTPUT_MALFORMED LINE_COUNT
    declare -gA APT_PATHS=()
    for i in "${!names[@]}"; do
        line=${lines[$i]}
        prefix="${names[$i]}='"
        [[ "$line" == "$prefix"* && "$line" == *"'" && ${#line} -ge $(( ${#prefix} + 1 )) ]] \
            || _abort APT_CONFIG_UNAPPROVED SHELL_OUTPUT_MALFORMED "LINE:${names[$i]}"
        body=${line:${#prefix}}
        body=${body%"'"}
        local stripped=${body//"'\\''"/}
        [[ "$stripped" != *"'"* ]] || _abort APT_CONFIG_UNAPPROVED SHELL_OUTPUT_MALFORMED "QUOTE:${names[$i]}"
        value=${body//"'\\''"/"'"}
        [[ "$value" == /* ]] || _abort APT_CONFIG_UNAPPROVED SHELL_OUTPUT_MALFORMED "NOT_ABSOLUTE:${names[$i]}"
        if [[ "${keys[$i]}" == */d && "$value" == */ && "$value" != / ]]; then
            value=${value%/}
        fi
        _printable "$value" || _abort APT_CONFIG_UNAPPROVED SHELL_OUTPUT_MALFORMED "PATH:${names[$i]}"
        APT_PATHS[${names[$i]}]=$value
        _evidence apt_path "${names[$i]}=$value"
    done
}

_os_release_check() {
    local line key value
    local -A have=()
    _read_file /etc/os-release || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED OS_RELEASE
    while IFS= read -r line; do
        [[ "$line" == *=* ]] || continue
        key=${line%%=*}
        value=${line#*=}
        value=${value#\"}
        value=${value%\"}
        have[$key]=$value
    done <<< "$REPLY"
    while IFS="$TAB" read -r key value; do
        [[ "${have[$key]-}" == "$value" ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "OS_RELEASE:$key"
    done < "$N/x0/os_release.tsv"
    _evidence os_release "ID=${have[ID]-} VERSION_ID=${have[VERSION_ID]-} VERSION_CODENAME=${have[VERSION_CODENAME]-}"
}

_keyring_path_ok() {
    [[ "$1" == /* && "$1" != *[[:space:]]* ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "SIGNED_BY_NOT_KEYRING_PATH:$2"
}

_add_source_tuples() {
    local types=$1 uris=$2 suites=$3 components=$4 keyring=$5 origin=$6 t u s c
    local -a ta=() ua=() sa=() ca=()
    read -r -a ta <<< "$types"
    read -r -a ua <<< "$uris"
    read -r -a sa <<< "$suites"
    read -r -a ca <<< "$components"
    (( ${#ca[@]} )) || ca=("")
    [[ -e "$keyring" ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "KEYRING_UNREADABLE:$keyring"
    if [[ ! -v KEYRING_SHA[$keyring] ]]; then
        PH=()
        _ph_files "$keyring"
        KEYRING_SHA[$keyring]=${PH[$keyring]}
    fi
    for t in "${ta[@]}"; do
        for u in "${ua[@]}"; do
            for s in "${sa[@]}"; do
                for c in "${ca[@]}"; do
                    EFFECTIVE_TUPLES+=("$t$TAB$u$TAB$s$TAB$c$TAB$keyring$TAB${KEYRING_SHA[$keyring]}")
                done
            done
        done
    done
}

_parse_one_line_sources() {
    local text=$1 origin=$2 raw line kind rest option_text item name value
    local re_opts='^([^[:space:]]+)[[:space:]]+\[([^]]*)\][[:space:]]+(.*)$'
    local -a fields=() items=()
    local -A options=()
    while IFS= read -r raw; do
        _strip_space "${raw%%#*}"
        line=$REPLY
        [[ -n "$line" ]] || continue
        options=()
        if [[ "$line" =~ $re_opts ]]; then
            kind=${BASH_REMATCH[1]}
            option_text=${BASH_REMATCH[2]}
            rest=${BASH_REMATCH[3]}
            read -r -a items <<< "$option_text"
            for item in "${items[@]}"; do
                [[ "$item" == *=* ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "OPTION:$origin"
                name=${item%%=*}
                name=${name,,}
                value=${item#*=}
                [[ "$name" == signed-by || "$name" == arch ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "OPTION:$origin:$name"
                [[ ! -v options[$name] ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "OPTION:$origin:$name"
                options[$name]=$value
            done
        else
            kind=${line%% *}
            if [[ "$line" == *" "* ]]; then
                rest=${line#* }
            else
                rest=""
            fi
        fi
        read -r -a fields <<< "$rest"
        (( ${#fields[@]} >= 2 )) || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "ONE_LINE_SHAPE:$origin"
        [[ "$kind" == deb || "$kind" == deb-src ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "TYPE:$origin"
        [[ -v options[signed-by] ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "SIGNED_BY_ABSENT:$origin"
        _keyring_path_ok "${options[signed-by]}" "$origin"
        if [[ "${fields[1]}" == */ ]]; then
            _add_source_tuples "$kind" "${fields[0]}" "${fields[1]}" "" "${options[signed-by]}" "$origin"
        else
            _add_source_tuples "$kind" "${fields[0]}" "${fields[1]}" "${fields[*]:2}" "${options[signed-by]}" "$origin"
        fi
    done <<< "$text"
}

_finish_deb822_stanza() {
    local origin=$1 key known enabled
    (( ${#STANZA_ORDER[@]} )) || return 0
    for key in "${STANZA_ORDER[@]}"; do
        known=0
        local f
        for f in "${DEB822_FIELDS[@]}"; do
            [[ "$key" == "$f" ]] && known=1
        done
        (( known )) || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "FIELD:$origin:$key"
    done
    _strip_space "${STANZA[enabled]-yes}"
    enabled=${REPLY,,}
    [[ "$enabled" == no ]] && return 0
    [[ "$enabled" == yes ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "ENABLED_VALUE:$origin"
    [[ -v STANZA[signed-by] ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "SIGNED_BY_ABSENT:$origin"
    local -a tokens=()
    read -r -a tokens <<< "${STANZA[signed-by]}"
    if (( ${STANZA_LINES[signed-by]} != 1 || ${#tokens[@]} != 1 )); then
        _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "SIGNED_BY_NOT_KEYRING_PATH:$origin"
    fi
    for key in types uris suites; do
        read -r -a tokens <<< "${STANZA[$key]-}"
        (( ${#tokens[@]} )) || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "DEB822_SHAPE:$origin:$key"
    done
    read -r -a tokens <<< "${STANZA[types]}"
    for key in "${tokens[@]}"; do
        [[ "$key" == deb || "$key" == deb-src ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "TYPE:$origin"
    done
    _keyring_path_ok "${STANZA[signed-by]//[[:space:]]/}" "$origin"
    _add_source_tuples "${STANZA[types]}" "${STANZA[uris]}" "${STANZA[suites]}" "${STANZA[components]-}" \
        "${STANZA[signed-by]//[[:space:]]/}" "$origin"
}

_parse_deb822_sources() {
    local text=$1 origin=$2 raw name value last=""
    declare -gA STANZA=() STANZA_LINES=()
    declare -ga STANZA_ORDER=()
    while IFS= read -r raw || [[ -n "$raw" ]]; do
        _strip_space "$raw"
        if [[ -z "$REPLY" ]]; then
            _finish_deb822_stanza "$origin"
            STANZA=() STANZA_LINES=() STANZA_ORDER=()
            last=""
            continue
        fi
        [[ "$raw" == \#* ]] && continue
        if [[ "$raw" == [\ $TAB]* ]]; then
            [[ -n "$last" ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "DEB822_SHAPE:$origin"
            _strip_space "$raw"
            STANZA[$last]+=" $REPLY"
            STANZA_LINES[$last]=$(( ${STANZA_LINES[$last]} + 1 ))
            continue
        fi
        [[ "$raw" == *:* ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "DEB822_SHAPE:$origin"
        name=${raw%%:*}
        value=${raw#*:}
        _strip_space "$name"
        [[ -n "$name" && "$REPLY" == "$name" ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "DEB822_SHAPE:$origin"
        name=${name,,}
        [[ ! -v STANZA[$name] ]] || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "DUPLICATE_FIELD:$origin:$name"
        _strip_space "$value"
        STANZA[$name]=$REPLY
        STANZA_LINES[$name]=1
        STANZA_ORDER+=("$name")
        last=$name
    done <<< "$text"
    _finish_deb822_stanza "$origin"
}

# SOURCE_EXPANSION_V1 / SOURCE_FIELDS_V1 against the X0-authenticated approved tuples.
_check_sources() {
    local list=${APT_PATHS[SOURCELIST]} parts=${APT_PATHS[SOURCEPARTS]} name path
    local -a names=() approved=() effective=()
    declare -gA KEYRING_SHA=()
    EFFECTIVE_TUPLES=()
    if [[ -e "$list" ]]; then
        _read_file "$list" || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "NUL:$list"
        _parse_one_line_sources "$REPLY" "$list"
        _evidence apt_source_file "$list one-line"
    fi
    if [[ -d "$parts" ]]; then
        _x "$T_FIND" "$parts" -mindepth 1 -maxdepth 1 -printf '%f\0' > "$N/sourceparts.lst" \
            || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED SOURCEPARTS_LISTING
        mapfile -d '' -t names < "$N/sourceparts.lst"
        _sort_into_sorted "${names[@]}"
        for name in "${SORTED[@]}"; do
            path="$parts/$name"
            _printable "$path" || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "NAME:$path"
            if [[ "$name" == *.list ]]; then
                _read_file "$path" || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "NUL:$path"
                _parse_one_line_sources "$REPLY" "$path"
                _evidence apt_source_file "$path one-line"
            elif [[ "$name" == *.sources ]]; then
                _read_file "$path" || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED "NUL:$path"
                _parse_deb822_sources "$REPLY" "$path"
                _evidence apt_source_file "$path deb822"
            else
                _evidence apt_source_file_ignored "$path"
            fi
        done
    fi
    _sort_unique_into_sorted "${EFFECTIVE_TUPLES[@]}"
    effective=("${SORTED[@]}")
    mapfile -t approved < "$N/x0/sources.tsv"
    _sort_unique_into_sorted "${approved[@]}"
    approved=("${SORTED[@]}")
    local line
    for line in "${effective[@]}"; do
        _evidence apt_effective_source "$line"
    done
    if [[ "${effective[*]}" != "${approved[*]}" || ${#effective[@]} -ne ${#approved[@]} ]]; then
        _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED SOURCE_SET
    fi
    local trusted=${APT_PATHS[TRUSTED]} trustedparts=${APT_PATHS[TRUSTEDPARTS]}
    local -a record=()
    [[ -f "$trusted" ]] && record+=("$trusted")
    if [[ -d "$trustedparts" ]]; then
        _x "$T_FIND" "$trustedparts" -mindepth 1 -maxdepth 1 -printf '%f\0' > "$N/trustedparts.lst" \
            || _abort APT_SOURCE_UNAPPROVED APT_SOURCE_UNAPPROVED TRUSTEDPARTS_LISTING
        mapfile -d '' -t names < "$N/trustedparts.lst"
        for name in "${names[@]}"; do
            [[ -f "$trustedparts/$name" ]] && record+=("$trustedparts/$name")
        done
    fi
    if (( ${#record[@]} )); then
        PH=()
        _ph_files "${record[@]}"
        for path in "${record[@]}"; do
            _evidence apt_trusted_keyring "$path ${PH[$path]}"
        done
    fi
}

_never_approvable() {
    local k=$1 v=$2 lv=${2,,} is_true=1
    case "$lv" in
        0|no|false|without|off|disable) is_true=0 ;;
    esac
    REPLY=""
    case "$k" in
        acquire::allowinsecurerepositories|acquire::allowdowngradetoinsecurerepositories|\
        acquire::allowweakrepositories|apt::get::allowunauthenticated)
            (( is_true )) && REPLY=INSECURE_MODE
            ;;
        acquire::check-valid-until)
            (( is_true )) || REPLY=CHECK_VALID_UNTIL
            ;;
        acquire::verify-peer|acquire::verify-host)
            (( is_true )) || REPLY=VERIFY_PEER
            ;;
        apt::default-release)
            [[ -n "$v" ]] && REPLY=DEFAULT_RELEASE
            ;;
        dir)
            [[ "$v" != / ]] && REPLY=DIR_RELOCATED
            ;;
        rootdir)
            [[ "$v" != / ]] && REPLY=ROOTDIR
            ;;
    esac
    [[ -n "$REPLY" ]] && return 0
    local re_verify='^acquire::[^:]+(::[^:]+)?::verify-(peer|host)$'
    local re_hashes='^apt::hashes::[^:]+::(untrusted|weak)$'
    if [[ "$k" =~ $re_verify ]] && (( ! is_true )); then
        REPLY=VERIFY_PEER
    elif [[ "$k" == dpkg::options* && ( "$lv" == *--force-* || "$lv" == *--admindir* || "$lv" == *--root* || "$lv" == *--instdir* ) ]]; then
        REPLY=DPKG_OPTIONS
    elif [[ "$k" =~ $re_hashes ]] && (( is_true )); then
        REPLY=HASHES
    elif [[ "$k" == apt::key::* && "${k##*::}" == gpgvcommand && -n "$v" ]]; then
        REPLY=GPGV_COMMAND
    fi
    [[ -n "$REPLY" ]]
}

_effective_key() {
    local lowered=$1 rest name remainder
    REPLY=$lowered
    if [[ "$lowered" == binary::* ]]; then
        rest=${lowered#binary::}
        if [[ "$rest" == *::* ]]; then
            name=${rest%%::*}
            remainder=${rest#*::}
            if [[ -n "$name" ]]; then
                [[ "$remainder" == binary::* ]] && _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED "BINARY_SCOPE_NESTED:$lowered"
                REPLY=$remainder
            fi
        fi
    fi
}

# CONFIG_CHECK_V1 (APT_KEY_CASE_V1, BINARY_SCOPE_V1) and the pins rule.
_check_apt_config() {
    local dump line key value lowered eff name
    local -a subset=() approved=() lowered_pairs=()
    local -A by_effective=()
    dump=$(_x "$T_APT_CONFIG" dump) || _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED DUMP_FAILED
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        [[ "$line" =~ $RE_DUMP_LINE ]] || _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED DUMP_LINE_MALFORMED
        key=${BASH_REMATCH[1]}
        value=${BASH_REMATCH[2]}
        lowered=${key,,}
        [[ "$lowered" == binary || "$lowered" == commandline* ]] && continue
        subset+=("$key$TAB$value")
        lowered_pairs+=("$lowered$TAB$value")
        _evidence apt_config "$key \"$value\""
    done <<< "$dump"
    for line in "${lowered_pairs[@]}"; do
        lowered=${line%%"$TAB"*}
        value=${line#*"$TAB"}
        [[ "$lowered" == *:: ]] && continue
        _effective_key "$lowered"
        eff=$REPLY
        if [[ -v by_effective[$eff] && "${by_effective[$eff]}" != "$value" ]]; then
            _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED "DUPLICATE_KEY:$eff"
        fi
        by_effective[$eff]=$value
    done
    for line in "${lowered_pairs[@]}"; do
        lowered=${line%%"$TAB"*}
        value=${line#*"$TAB"}
        _effective_key "$lowered"
        for name in "$lowered" "$REPLY"; do
            if [[ "$name" == *:: ]]; then
                while [[ "$name" == *: ]]; do
                    name=${name%:}
                done
            fi
            if _never_approvable "$name" "$value"; then
                _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED "NEVER_APPROVABLE:$name:$REPLY"
            fi
        done
    done
    [[ "${APT_PATHS[STATUS]}" == /var/lib/dpkg/status ]] \
        || _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED NEVER_APPROVABLE:STATUS_PATH
    _sort_into_sorted "${lowered_pairs[@]}"
    lowered_pairs=("${SORTED[@]}")
    mapfile -t approved < "$N/x0/apt_config.tsv"
    _sort_into_sorted "${approved[@]}"
    approved=("${SORTED[@]}")
    if (( ${#lowered_pairs[@]} != ${#approved[@]} )); then
        _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED CONFIG_MISMATCH
    fi
    local i
    for i in "${!approved[@]}"; do
        [[ "${lowered_pairs[$i]}" == "${approved[$i]}" ]] || _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED CONFIG_MISMATCH
    done
}

_check_pins() {
    local path stripped policy line in_pinned=0 name
    local -a files=() names=()
    local re_priority='^[[:space:]]*(-?[0-9]+) '
    [[ -e "${APT_PATHS[PREFERENCES]}" ]] && files+=("${APT_PATHS[PREFERENCES]}")
    if [[ -d "${APT_PATHS[PREFERENCESPARTS]}" ]]; then
        _x "$T_FIND" "${APT_PATHS[PREFERENCESPARTS]}" -mindepth 1 -maxdepth 1 -printf '%f\0' > "$N/prefparts.lst" \
            || _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED PREFERENCES_LISTING
        mapfile -d '' -t names < "$N/prefparts.lst"
        for name in "${names[@]}"; do
            files+=("${APT_PATHS[PREFERENCESPARTS]}/$name")
        done
    fi
    for path in "${files[@]}"; do
        _read_file "$path" || _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED "PIN:$path"
        while IFS= read -r line; do
            _strip_space "$line"
            stripped=$REPLY
            if [[ -n "$stripped" && "$stripped" != \#* ]]; then
                _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED "PIN:$path"
            fi
        done <<< "$REPLY"
    done
    if (( ${#files[@]} )); then
        PH=()
        _ph_files "${files[@]}"
        for path in "${files[@]}"; do
            _evidence apt_preferences_file "$path ${PH[$path]}"
        done
    fi
    policy=$(_x "$T_APT_CACHE" policy) || _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED POLICY_FAILED
    while IFS= read -r line; do
        if [[ "$line" == "Pinned packages:"* ]]; then
            in_pinned=1
            continue
        fi
        _strip_space "$line"
        if (( in_pinned )) && [[ -n "$REPLY" ]]; then
            _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED PIN
        fi
        if (( ! in_pinned )) && [[ "$line" =~ $re_priority ]]; then
            case "${BASH_REMATCH[1]}" in
                100|500|1) ;;
                *) _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED "PIN_PRIORITY:${BASH_REMATCH[1]}" ;;
            esac
        fi
    done <<< "$policy"
}

# DPKG_CONFIG_RECORD_V1 discovery and parse (strict DPKG_CONFIG_CHECK_V1 grammar).
_dpkg_record() {
    local path name st uid mode data line stripped lname value
    local -a candidates=(/etc/dpkg/dpkg.cfg) names=() file_lines=() rows=()
    DPKG_SER=()
    DPKG_PATHS=()
    declare -gA DPKG_FILE_SHA=() DPKG_FILE_OPTS=()
    for path in /nonexistent/.dpkg.cfg "$N/.dpkg.cfg"; do
        if [[ -e "$path" || -L "$path" ]]; then
            _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_FILE_SET "ABSENT_REQUIRED:$path"
        fi
    done
    if [[ -d /etc/dpkg/dpkg.cfg.d && ! -L /etc/dpkg/dpkg.cfg.d ]]; then
        _x "$T_FIND" /etc/dpkg/dpkg.cfg.d -mindepth 1 -maxdepth 1 -printf '%f\0' > "$N/dpkgcfgd.lst" \
            || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_FILE_SET LISTING
        mapfile -d '' -t names < "$N/dpkgcfgd.lst"
        for name in "${names[@]}"; do
            candidates+=("/etc/dpkg/dpkg.cfg.d/$name")
        done
    fi
    _sort_into_sorted "${candidates[@]}"
    candidates=("${SORTED[@]}")
    for path in "${candidates[@]}"; do
        [[ -e "$path" || -L "$path" ]] || continue
        _printable "$path" || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_FILE_TYPE "$path"
        [[ -f "$path" && ! -L "$path" ]] || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_FILE_TYPE "$path"
        st=$(_x "$T_STAT" -c '%u %a' -- "$path") || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_FILE_TYPE "$path"
        uid=${st%% *}
        mode=${st#* }
        if [[ "$uid" != 0 ]] || (( (8#$mode & 8#022) != 0 )); then
            _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_FILE_TYPE "$path"
        fi
        _read_file "$path" || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MALFORMED "NUL:$path"
        data=$REPLY
        PH=()
        _ph_files "$path"
        DPKG_PATHS+=("$path")
        DPKG_FILE_SHA[$path]=${PH[$path]}
        DPKG_SER+=("F$TAB$path$TAB${PH[$path]}")
        DPKG_FILE_OPTS[$path]=""
        local number=0
        while IFS= read -r line || [[ -n "$line" ]]; do
            number=$((number + 1))
            _strip_blank "$line"
            stripped=$REPLY
            [[ -z "$stripped" || "$stripped" == \#* ]] && continue
            [[ "$line" =~ $RE_DPKG_LINE ]] || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MALFORMED "$path:$number"
            lname=${BASH_REMATCH[2],,}
            if [[ "${BASH_REMATCH[3]}" == =* ]]; then
                value="=${BASH_REMATCH[4]}"
            elif [[ -n "${BASH_REMATCH[3]}" ]]; then
                # DPKG_OPTION_SYNTAX_V1 separator form: unquoted value, trailing blanks removed.
                sep_value=${BASH_REMATCH[5]}
                sep_value=${sep_value%"${sep_value##*[![:blank:]]}"}
                if [[ -z "$sep_value" || "$sep_value" == [=\"\'[:blank:]]* ]]; then
                    _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MALFORMED "$path:$number"
                fi
                value="=$sep_value"
            else
                value="-"
            fi
            DPKG_SER+=("O$TAB$lname$TAB$value")
            DPKG_FILE_OPTS[$path]+="$lname$TAB$value$NL"
        done <<< "$data"
    done
    DPKG_DIV=()
    if [[ -e /var/lib/dpkg/diversions ]]; then
        _read_file /var/lib/dpkg/diversions || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MALFORMED DIVERSIONS_NUL
        data=${REPLY%"$NL"}
        if [[ -n "$REPLY" ]]; then
            mapfile -t file_lines <<< "$data"
        else
            file_lines=()
        fi
        (( ${#file_lines[@]} % 3 == 0 )) || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MALFORMED /var/lib/dpkg/diversions
        rows=()
        local i
        for (( i = 0; i < ${#file_lines[@]}; i += 3 )); do
            if [[ "${file_lines[$i]}${file_lines[$i+1]}${file_lines[$i+2]}" == *"$TAB"* ]]; then
                _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MALFORMED /var/lib/dpkg/diversions
            fi
            rows+=("${file_lines[$i]}$TAB${file_lines[$i+1]}$TAB${file_lines[$i+2]}")
        done
        _sort_stable_key1_into_sorted "${rows[@]}"
        DPKG_DIV=("${SORTED[@]}")
    fi
    DPKG_STAT=()
    if [[ -e /var/lib/dpkg/statoverride ]]; then
        _read_file /var/lib/dpkg/statoverride || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MALFORMED STATOVERRIDE_NUL
        rows=()
        local re_four='^([^ ]+) ([^ ]+) ([^ ]+) ([^ ]+)$'
        while IFS= read -r line; do
            [[ -n "$line" ]] || continue
            [[ "$line" =~ $re_four ]] || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MALFORMED /var/lib/dpkg/statoverride
            rows+=("${BASH_REMATCH[4]}$TAB$line")
        done <<< "$REPLY"
        _sort_stable_key1_into_sorted "${rows[@]}"
        for line in "${SORTED[@]}"; do
            DPKG_STAT+=("${line#*"$TAB"}")
        done
    fi
    if [[ -e /usr/sbin/policy-rc.d || -L /usr/sbin/policy-rc.d ]]; then
        PH=()
        _ph_files /usr/sbin/policy-rc.d
        DPKG_POLICY="/usr/sbin/policy-rc.d$TAB${PH[/usr/sbin/policy-rc.d]}"
    else
        DPKG_POLICY="/usr/sbin/policy-rc.d${TAB}ABSENT"
    fi
}

# DPKG_CONFIG_CHECK_V1 comparison, NO_DEBSIG_EXACT_ADMISSION_V1 order.
_check_dpkg_record() {
    local path token line index name value expected
    local -a approved_paths=() approved_ser=() approved_div=() approved_stat=() opts=() approved_opts=()
    local approved_policy
    mapfile -t approved_paths < "$N/x0/dpkg_paths.txt"
    [[ "${approved_paths[0]-}" == "" && ${#approved_paths[@]} -eq 1 ]] && approved_paths=()
    if [[ "${DPKG_PATHS[*]}" != "${approved_paths[*]}" || ${#DPKG_PATHS[@]} -ne ${#approved_paths[@]} ]]; then
        _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_FILE_SET FILE_SET
    fi
    for path in "${DPKG_PATHS[@]}"; do
        mapfile -t opts <<< "${DPKG_FILE_OPTS[$path]%"$NL"}"
        [[ -z "${DPKG_FILE_OPTS[$path]}" ]] && opts=()
        for line in "${opts[@]}"; do
            name=${line%%"$TAB"*}
            for token in "${DPKG_NEVER_APPROVABLE[@]}"; do
                if [[ "$name" == "$token" || "$name" == "$token"* ]]; then
                    _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_NEVER_APPROVABLE "$path:$name"
                fi
            done
        done
    done
    for path in "${DPKG_PATHS[@]}"; do
        mapfile -t opts <<< "${DPKG_FILE_OPTS[$path]%"$NL"}"
        [[ -z "${DPKG_FILE_OPTS[$path]}" ]] && opts=()
        mapfile -t approved_opts < "$N/x0/dpkg_opts.$(_path_key "$path")"
        [[ "${approved_opts[0]-}" == "" && ${#approved_opts[@]} -eq 1 ]] && approved_opts=()
        expected=$(<"$N/x0/dpkg_sha.$(_path_key "$path")")
        for index in "${!opts[@]}"; do
            line=${opts[$index]}
            name=${line%%"$TAB"*}
            value=${line#*"$TAB"}
            [[ "$name" == no-debsig* ]] || continue
            if [[ "$name" != no-debsig || "$value" != "-" || "${DPKG_FILE_SHA[$path]}" != "$expected" \
                  || "${approved_opts[$index]-}" != "no-debsig$TAB-" ]]; then
                _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_NO_DEBSIG_UNAPPROVED "$path:$index"
            fi
        done
    done
    mapfile -t approved_ser < "$N/x0/dpkg_files.txt"
    [[ "${approved_ser[0]-}" == "" && ${#approved_ser[@]} -eq 1 ]] && approved_ser=()
    if (( ${#approved_ser[@]} != ${#DPKG_SER[@]} )); then
        _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MISMATCH FILES
    fi
    for index in "${!approved_ser[@]}"; do
        [[ "${approved_ser[$index]}" == "${DPKG_SER[$index]}" ]] || _abort APT_CONFIG_UNAPPROVED DPKG_CONFIG_MISMATCH FILES
    done
    mapfile -t approved_div < "$N/x0/dpkg_diversions.tsv"
    [[ "${approved_div[0]-}" == "" && ${#approved_div[@]} -eq 1 ]] && approved_div=()
    if [[ "${approved_div[*]}" != "${DPKG_DIV[*]}" || ${#approved_div[@]} -ne ${#DPKG_DIV[@]} ]]; then
        _abort APT_CONFIG_UNAPPROVED DPKG_DIVERSION DIVERSIONS
    fi
    mapfile -t approved_stat < "$N/x0/dpkg_statoverride.txt"
    [[ "${approved_stat[0]-}" == "" && ${#approved_stat[@]} -eq 1 ]] && approved_stat=()
    if [[ "${approved_stat[*]}" != "${DPKG_STAT[*]}" || ${#approved_stat[@]} -ne ${#DPKG_STAT[@]} ]]; then
        _abort APT_CONFIG_UNAPPROVED DPKG_STATOVERRIDE STATOVERRIDE
    fi
    approved_policy=$(<"$N/x0/dpkg_policy_rc_d.tsv")
    [[ "$approved_policy" == "$DPKG_POLICY" ]] || _abort APT_CONFIG_UNAPPROVED DPKG_POLICY_RC POLICY_RC_D
}

_path_key() {
    local key=${1//\//_}
    printf '%s' "$key"
}

_dpkg_state() {
    local out
    out=$(_x "$T_DPKG_QUERY" -W -f '${Package}\t${Architecture}\t${Version}\t${Status}\n') \
        || _abort APT_UNEXPECTED_CHANGE APT_UNEXPECTED_CHANGE DPKG_QUERY_FAILED
    local -a rows=()
    local line
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        if [[ "$line" != *"$TAB"*"$TAB"*"$TAB"* || "$line" == *"$TAB"*"$TAB"*"$TAB"*"$TAB"* || "$line" == *"|"* ]]; then
            _abort APT_UNEXPECTED_CHANGE APT_UNEXPECTED_CHANGE DPKG_QUERY_MALFORMED
        fi
        rows+=("$line")
    done <<< "$out"
    _sort_into_sorted "${rows[@]}"
    STATE=("${SORTED[@]}")
}

_identity_critical_set() {
    local out line pkgs item rc i
    local -a paths=() chunk=()
    declare -gA IDENTITY_CRITICAL=([libc6]=1)
    paths=("${!NC_FILES[@]}" "${!NC_LOADED_PATHS[@]}" "${LOADER_INPUT_PATHS[@]}" "${STDLIB_FILES[@]}" "${PIP_FILES[@]}")
    for (( i = 0; i < ${#paths[@]}; i += 256 )); do
        chunk=("${paths[@]:i:256}")
        out=$(_x "$T_DPKG_QUERY" -S "${chunk[@]}" 2>/dev/null)
        rc=$?
        (( rc <= 1 )) || _abort APT_UNEXPECTED_CHANGE APT_UNEXPECTED_CHANGE DPKG_QUERY_OWNERS
        while IFS= read -r line; do
            [[ "$line" == "diversion by "* || "$line" != *": /"* ]] && continue
            pkgs=${line%%": /"*}
            while [[ -n "$pkgs" ]]; do
                item=${pkgs%%, *}
                [[ "$pkgs" == *", "* ]] && pkgs=${pkgs#*, } || pkgs=""
                IDENTITY_CRITICAL[${item%%:*}]=1
            done
        done <<< "$out"
    done
    for item in "${HT_OWNERS[@]}"; do
        [[ "$item" == UNOWNED ]] && continue
        local -a owners=()
        IFS=, read -r -a owners <<< "$item"
        for pkgs in "${owners[@]}"; do
            IDENTITY_CRITICAL[$pkgs]=1
        done
    done
    _evidence identity_critical_packages "$(printf '%s ' "${!IDENTITY_CRITICAL[@]}")"
}

_policy_origins() {
    local package=$1 arch=$2 version=$3 query out line current=""
    local re_version='^ (\*\*\*|   ) ([^ ]+) (-?[0-9]+)$'
    local re_origin='^[[:space:]]+-?[0-9]+ ([^ ]+) ([^/[:space:]]+)/([^ ]+) [^ ]+ Packages$'
    if [[ "$arch" == "$NATIVE_ARCH" || "$arch" == all ]]; then
        query=$package
    else
        query="$package:$arch"
    fi
    out=$(_x "$T_APT_CACHE" policy "$query") || _abort ENV_UNVERIFIED APT_ORIGIN "POLICY:$package"
    ORIGINS=()
    while IFS= read -r line; do
        if [[ "$line" =~ $re_version ]]; then
            current=${BASH_REMATCH[2]}
            continue
        fi
        if [[ "$current" == "$version" && "$line" =~ $re_origin ]]; then
            ORIGINS+=("${BASH_REMATCH[1]}$TAB${BASH_REMATCH[2]}$TAB${BASH_REMATCH[3]}")
        fi
    done <<< "$out"
}

_origin_approved() {
    local origin=$1 tuple u s c au as ac rest
    u=${origin%%"$TAB"*}
    rest=${origin#*"$TAB"}
    s=${rest%%"$TAB"*}
    c=${rest#*"$TAB"}
    for tuple in "${APPROVED_TUPLES[@]}"; do
        rest=${tuple#*"$TAB"}
        au=${rest%%"$TAB"*}
        rest=${rest#*"$TAB"}
        as=${rest%%"$TAB"*}
        rest=${rest#*"$TAB"}
        ac=${rest%%"$TAB"*}
        if [[ "${au%/}" == "${u%/}" && "$as" == "$s" && "$ac" == "$c" ]]; then
            return 0
        fi
    done
    return 1
}

# APT_SEQUENCE_V1 F and G.
_apt_delta_and_checks() {
    local -A before=() after=()
    local line key rest pkg arch ver change vb va o
    local -a keys=() delta=()
    for line in "${SNAPSHOT_STATE[@]}"; do
        key=${line%"$TAB"*}
        key=${key%"$TAB"*}
        before[$key]=${line#"$key$TAB"}
    done
    for line in "${STATE[@]}"; do
        key=${line%"$TAB"*}
        key=${key%"$TAB"*}
        after[$key]=${line#"$key$TAB"}
    done
    _sort_unique_into_sorted "${!before[@]}" "${!after[@]}"
    keys=("${SORTED[@]}")
    for key in "${keys[@]}"; do
        pkg=${key%%"$TAB"*}
        arch=${key#*"$TAB"}
        if [[ -v before[$key] && -v after[$key] && "${before[$key]}" == "${after[$key]}" ]]; then
            continue
        fi
        vb=${before[$key]-}
        va=${after[$key]-}
        if [[ ! -v before[$key] ]]; then
            change=ADDED
        elif [[ ! -v after[$key] ]]; then
            change=REMOVED
        elif [[ "${vb%%"$TAB"*}" == "${va%%"$TAB"*}" ]]; then
            change=STATUS_CHANGED
        elif _x "$T_DPKG" --compare-versions "${va%%"$TAB"*}" gt "${vb%%"$TAB"*}"; then
            change=UPGRADED
        else
            change=DOWNGRADED
        fi
        delta+=("$pkg|$arch|$change|${vb%%"$TAB"*}|${va%%"$TAB"*}")
    done
    for line in "${delta[@]}"; do
        pkg=${line%%|*}
        if [[ -v IDENTITY_CRITICAL[$pkg] ]]; then
            _evidence apt_installed_delta "$line"
            _abort ENV_UNVERIFIED APT_UNEXPECTED_CHANGE "IDENTITY_CRITICAL:$pkg"
        fi
    done
    local -a origin_checks=()
    while IFS="$TAB" read -r pkg ver arch; do
        key="$pkg$TAB$arch"
        [[ "${after[$key]-}" == "$ver${TAB}install ok installed" ]] || _abort ENV_UNVERIFIED APT_PIN "$pkg"
        origin_checks+=("$pkg|$arch|$ver")
    done < "$N/x0/packages.tsv"
    for line in "${delta[@]}"; do
        IFS='|' read -r pkg arch change vb va <<< "$line"
        case "$change" in
            DOWNGRADED|REMOVED|STATUS_CHANGED)
                _evidence apt_installed_delta "$line"
                _abort ENV_UNVERIFIED APT_UNEXPECTED_CHANGE "$change:$pkg"
                ;;
            ADDED)
                [[ "${after[$pkg$TAB$arch]#*"$TAB"}" == "install ok installed" ]] \
                    || _abort ENV_UNVERIFIED APT_UNEXPECTED_CHANGE "ADDED_STATUS:$pkg"
                origin_checks+=("$pkg|$arch|$va")
                ;;
            UPGRADED)
                origin_checks+=("$pkg|$arch|$va")
                ;;
        esac
    done
    mapfile -t APPROVED_TUPLES < "$N/x0/sources.tsv"
    local -A checked=()
    for line in "${origin_checks[@]}"; do
        IFS='|' read -r pkg arch ver <<< "$line"
        [[ -v checked[$line] ]] && continue
        checked[$line]=1
        _policy_origins "$pkg" "$arch" "$ver"
        (( ${#ORIGINS[@]} )) || _abort ENV_UNVERIFIED APT_ORIGIN "$pkg"
        for o in "${ORIGINS[@]}"; do
            _origin_approved "$o" || _abort ENV_UNVERIFIED APT_ORIGIN "$pkg"
        done
        _evidence apt_origin "$pkg $arch $ver $(printf '%s;' "${ORIGINS[@]//$TAB/ }")"
    done
    for line in "${delta[@]}"; do
        _evidence apt_installed_delta "$line"
    done
    while IFS="$TAB" read -r key rest; do
        PH=()
        _ph_files "$key"
        [[ "${PH[$key]}" == "$rest" ]] || _abort ENV_UNVERIFIED APT_UNEXPECTED_CHANGE "KEYRING:$key"
    done < "$N/x0/keyrings.tsv"
}

# -- embedded governed Python (PROCESS_CREATION_DENY_V1 first, FINAL_DENIED_CHECK last) -----------

_load_embedded() {
    IFS= read -r -d '' HOOK_HEAD <<'PY_HOOK_HEAD'
#BEGIN HOOK_HEAD
# PROCESS_CREATION_DENY_V1 with PROCESS_CREATION_RECORD_V2: this single statement must stay the first statement of every governed execution.
__import__("sys").addaudithook((lambda denied, allowed, raised, events, counts, approved: (lambda event, args: ((lambda text: allowed.append([len(allowed) + 1, event, text]) if (len(allowed) < len(approved) and approved[len(allowed)] == [event, text]) else (denied.append([len(denied) + 1, event, ascii(args[0] if args else None)[:256]]), (_ for _ in ()).throw(raised(event))))(ascii(args)) if event in events else (counts.__setitem__(event, counts[event] + 1) if event in counts else None))))(DENIED_EVENTS := [], ALLOWED_EVENTS := [], ProcessCreationDenied := type("ProcessCreationDenied", (BaseException,), {}), frozenset(("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty", "pty.spawn", "_posixsubprocess.fork_exec")), RECORDED_COUNTS := {"ctypes.dlopen": 0, "ctypes.dlsym": 0, "ctypes.call_function": 0}, APPROVED_SEQUENCE := []))
#END HOOK_HEAD
PY_HOOK_HEAD
    IFS= read -r -d '' HOOK_HEAD_E2 <<'PY_HOOK_HEAD_E2'
#BEGIN HOOK_HEAD_E2
# PROCESS_CREATION_DENY_V1 with PROCESS_CREATION_RECORD_V2: this single statement must stay the first statement of every governed execution.
__import__("sys").addaudithook((lambda denied, allowed, raised, events, counts, approved: (lambda event, args: ((lambda text: allowed.append([len(allowed) + 1, event, text]) if (len(allowed) < len(approved) and approved[len(allowed)] == [event, text]) else (denied.append([len(denied) + 1, event, ascii(args[0] if args else None)[:256]]), (_ for _ in ()).throw(raised(event))))(ascii(args)) if event in events else (counts.__setitem__(event, counts[event] + 1) if event in counts else None))))(DENIED_EVENTS := [], ALLOWED_EVENTS := [], ProcessCreationDenied := type("ProcessCreationDenied", (BaseException,), {}), frozenset(("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty", "pty.spawn", "_posixsubprocess.fork_exec")), RECORDED_COUNTS := {"ctypes.dlopen": 0, "ctypes.dlsym": 0, "ctypes.call_function": 0}, APPROVED_SEQUENCE := [["subprocess.Popen", "('lsb_release', ['lsb_release', '-a'], None, None)"], ["_posixsubprocess.fork_exec", "((b'/usr/sbin/lsb_release', b'/usr/bin/lsb_release', b'/sbin/lsb_release', b'/bin/lsb_release'), ['lsb_release', '-a'], None)"], ["subprocess.Popen", "('uname', ['uname', '-rs'], None, None)"], ["_posixsubprocess.fork_exec", "((b'/usr/sbin/uname', b'/usr/bin/uname', b'/sbin/uname', b'/bin/uname'), ['uname', '-rs'], None)"]]))
#END HOOK_HEAD_E2
PY_HOOK_HEAD_E2
    IFS= read -r -d '' HOOK_TAIL <<'PY_HOOK_TAIL'
#BEGIN HOOK_TAIL
try:
    main()
finally:
    sys.stdout.write("CTYPES_EVENTS=" + json.dumps(RECORDED_COUNTS, sort_keys=True) + "\n")
    if DENIED_EVENTS:
        sys.stdout.write("PROVISIONING_ENV_VIOLATION PROCESS_CREATION " + json.dumps(DENIED_EVENTS) + "\n")
        sys.stdout.flush()
        os._exit(71)
    if len(ALLOWED_EVENTS) != len(APPROVED_SEQUENCE):
        sys.stdout.write("PROVISIONING_ENV_VIOLATION PROCESS_CREATION_SEQUENCE " + json.dumps(ALLOWED_EVENTS) + "\n")
        sys.stdout.flush()
        os._exit(71)
    sys.stdout.write("ALLOWED_EVENTS_RECORD=" + json.dumps(ALLOWED_EVENTS) + "\n")
    sys.stdout.write("DENIED_EVENTS=0\n")
    sys.stdout.write("ALLOWED_EVENTS=" + __import__("hashlib").sha256(json.dumps(
        ALLOWED_EVENTS, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest() + "\n")
    sys.stdout.flush()
#END HOOK_TAIL
PY_HOOK_TAIL
    IFS= read -r -d '' PROBE <<'PY_PROBE'
#BEGIN PROBE
import hashlib
import json
import os
import sys

NEUTRAL = os.path.dirname(sys.pycache_prefix or "/nonexistent/pycache")


def governed_abort(status, reason, detail=""):
    sys.stdout.write("GOVERNED_ABORT status=%s reason=%s detail=%s\n" % (status, reason, detail))
    sys.stdout.flush()
    raise SystemExit(3)


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key %r" % key)
            result[key] = value
        return result

    def constant(name):
        raise ValueError("non-finite number %s" % name)

    return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def read_plan(name):
    with open(os.path.join(NEUTRAL, "plan", name), "rb") as handle:
        return handle.read()


def child_env():
    return {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C", "HOME": NEUTRAL, "TMPDIR": NEUTRAL,
            "DEBIAN_FRONTEND": "noninteractive", "PIP_CONFIG_FILE": "/dev/null", "PYTHONDONTWRITEBYTECODE": "1"}


def in_process_probe(manifest, form):
    """IN_PROCESS_PROBE_V1, a consistency check by the interpreter about itself."""
    base = manifest["operator_base_interpreter"]
    checks = (
        ("VERSION_STRING", sys.version == base["version_string"]),
        ("IMPLEMENTATION", sys.implementation.name == base["implementation"]),
        ("PYTHON_VERSION", "%d.%d.%d" % sys.version_info[:3] == base["python_version"]),
        ("LIBC", os.confstr("CS_GNU_LIBC_VERSION") == base["libc"]),
        ("FLAGS", sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.dont_write_bytecode == 1
         and sys.flags.ignore_environment == 1 and sys.flags.no_user_site == 1),
        ("SITE", "site" not in sys.modules),
        ("PYCACHE_PREFIX", sys.pycache_prefix == os.path.join(NEUTRAL, "pycache")),
        ("EXECUTABLE", os.path.realpath(sys.executable) == os.path.realpath(base["path"])),
        ("ENVIRONMENT", dict(os.environ) == child_env()),
    )
    for name, passed in checks:
        if not passed:
            governed_abort("BASE_INTERPRETER_MISMATCH", "IN_PROCESS_PROBE", name)
    expected = base["sys_path_isolated"] if form == "BASE" else base["sys_path_isolated_prefix"]
    if sys.path != expected:
        governed_abort("BASE_INTERPRETER_MISMATCH", "SYS_PATH_UNBOUND", form)
    if form == "BASE":
        if sys.prefix != sys.base_prefix:
            governed_abort("BASE_INTERPRETER_MISMATCH", "IN_PROCESS_PROBE", "PREFIX")
    elif (os.path.realpath(sys.prefix) != os.path.realpath(manifest["operator_python_prefix"])
          or sys.base_prefix == sys.prefix):
        governed_abort("PROVISIONING_ENV_VIOLATION", "IN_PROCESS_PROBE", "PREFIX")


def derive_tags(tags_module, python_version):
    sequence, seen = [], set()
    for tag in tags_module.sys_tags():
        text = str(tag)
        if text not in seen:
            seen.add(text)
            sequence.append(text)
    platforms, seen = [], set()
    for text in sequence:
        platform = text.split("-", 2)[2]
        if platform not in seen:
            seen.add(platform)
            platforms.append(platform)
    major, minor = (int(item) for item in python_version.split(".")[:2])
    own = "cp%d%d" % (major, minor)
    abi = next(text.split("-")[1] for text in sequence if text.split("-")[0] == own)
    cpython_platforms = [item for item in platforms if item != "any"]
    generated = list(tags_module.cpython_tags(python_version=(major, minor), abis=[abi], platforms=list(cpython_platforms)))
    generated += list(tags_module.compatible_tags(python_version=(major, minor), interpreter=own,
                                                  platforms=list(cpython_platforms)))
    regenerated, seen = [], set()
    for tag in generated:
        text = str(tag)
        if text not in seen:
            seen.add(text)
            regenerated.append(text)
    if regenerated != sequence:
        governed_abort("BASE_INTERPRETER_MISMATCH", "TAG_GENERATOR")
    return {"tag_sequence": sequence, "platform_sequence": platforms, "abi_tag": abi,
            "platform_tags": sorted(set(platforms))}


def check_tags(manifest, fields, members):
    base = manifest["operator_base_interpreter"]
    targets = [item for item in manifest["artifact_targets"] if item.get("id") == "OPERATOR"]
    if len(targets) != 1:
        governed_abort("BASE_INTERPRETER_MISMATCH", "TARGET", "OPERATOR")
    for member in members:
        if fields[member] != targets[0][member] or (member in base and fields[member] != base[member]):
            governed_abort("BASE_INTERPRETER_MISMATCH", "TARGET", member)
    for member in ("implementation", "python_version", "libc"):
        if base[member] != targets[0][member]:
            governed_abort("BASE_INTERPRETER_MISMATCH", "TARGET", member)


def audit_modules(stdlib_real, pipcopy):
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        real = os.path.realpath(filename)
        if not (real.startswith(stdlib_real.rstrip("/") + "/") or real.startswith(pipcopy + "/")):
            governed_abort("PIP_MISMATCH", "UNBUNDLED_PIP", name)


def import_pip_copy(manifest):
    pipcopy = os.path.join(NEUTRAL, "pipcopy")
    sys.path.append(pipcopy)
    try:
        import pip
    except ImportError:
        governed_abort("PIP_UNAVAILABLE", "PIP_UNAVAILABLE", "IMPORT")
    if pip.__version__ != manifest["installer_pip_version"]:
        governed_abort("PIP_MISMATCH", "PIP_MISMATCH", "VERSION")
    if not os.path.realpath(pip.__file__).startswith(pipcopy + "/"):
        governed_abort("PIP_MISMATCH", "PIP_MISMATCH", "LOCATION")
    import importlib
    return pipcopy, importlib.import_module("pip._vendor.packaging.tags")
#END PROBE
PY_PROBE
    IFS= read -r -d '' X0_BODY <<'PY_X0'
#BEGIN X0
PRE_KEYS = (
    "annotation_record_spec_id", "apt_plan", "artifact_targets", "bubblewrap_version", "dependency_lock_review",
    "dependency_model", "docx_limits", "extraction_spec", "font_inventory_record_spec_id", "geometry_spec_id",
    "installer_pip_package_path", "installer_pip_package_tree_digest", "installer_pip_version",
    "libreoffice_version", "locale", "lock_artifacts", "lock_review_digest", "operator_base_interpreter",
    "operator_python_prefix", "pdf_export_filter", "pdfminer_six_version", "provisioning_script_path",
    "provisioning_script_sha256", "pypdf_version", "quantization_spec_id", "sandbox_capability_mechanism",
    "sandbox_flags", "sandbox_forbidden_canary_paths", "sandbox_tmpfs_paths", "sandbox_tmpfs_size_bytes",
    "source_date_epoch", "temp_root_policy", "text_normalization_spec_id", "text_overlap_ratio_denominator",
    "text_overlap_ratio_numerator", "timeout_seconds", "timezone", "verifier_path", "verifier_sha256",
)
INSTALL_FLAGS = ["--yes", "--no-install-recommends", "--no-remove"]


def read_tsv(path):
    values = {}
    with open(path, "r", encoding="utf-8", newline="\n") as handle:
        for line in handle.read().split("\n"):
            if line:
                key, _, value = line.partition("\t")
                values[key] = value
    return values


def write_lines(name, lines):
    for line in lines:
        if "\n" in line:
            governed_abort("PLAN_DIGEST", "PLAN_VALUE", name)
    with open(os.path.join(NEUTRAL, "x0", name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(line + "\n" for line in lines))


def approved_sequence(head_text):
    import ast
    found = [node.value for node in ast.walk(ast.parse(head_text))
             if isinstance(node, ast.NamedExpr) and node.target.id == "APPROVED_SEQUENCE"]
    if len(found) != 1:
        governed_abort("PLAN_DIGEST", "E2_HELPER_CHAIN", "APPROVED_SEQUENCE_LITERAL")
    return ast.literal_eval(found[0])


def chain_rows(chain):
    entries = list(chain["helpers"]) + [chain["interpreter"]] + list(chain["descendants"]) + list(chain["data_files"])
    return [[entry["invoked_path"], entry["realpath"], entry["sha256"], ",".join(entry["owner_packages"]),
             ",".join(entry["owner_versions"]), entry["link_string"]] for entry in entries]


def verify_e2_helper_chain(base, proven, head_text):
    """E2_HELPER_CHAIN_V1: the manifest record must equal the approved sequence embedded in this script and
    the helper records the script took from the live host at step 1 (HOST_TOOL_RECORD_V1)."""
    chain = base.get("e2_helper_chain")
    if not isinstance(chain, dict):
        governed_abort("PLAN_DIGEST", "PLAN_INCOMPLETE", "e2_helper_chain")
    approved_events = approved_sequence(head_text)
    if chain.get("sequence") != approved_events:
        governed_abort("PLAN_DIGEST", "E2_HELPER_CHAIN", "SEQUENCE")
    if digest([[index + 1, item[0], item[1]] for index, item in enumerate(approved_events)]) != proven["e2_allowed_sha256"] \
            or digest([]) != proven["empty_allowed_sha256"]:
        governed_abort("PLAN_DIGEST", "E2_HELPER_CHAIN", "ALLOWED_DIGEST")
    if chain_rows(chain) != json.loads(proven["e2_chain_rows"]):
        governed_abort("BASE_INTERPRETER_MISMATCH", "E2_HELPER_CHAIN", "TOOL_RECORD")
    if chain.get("absent_candidates") != json.loads(proven["e2_chain_absent"]):
        governed_abort("BASE_INTERPRETER_MISMATCH", "E2_HELPER_CHAIN", "ABSENT_CANDIDATES")


def safe_path(value):
    return isinstance(value, str) and value.startswith("/") and all(" " <= ch <= "~" for ch in value) \
        and '"' not in value and "\\" not in value


def main():
    approved = read_tsv(os.path.join(NEUTRAL, "approved.tsv"))
    proven = read_tsv(os.path.join(NEUTRAL, "proven.tsv"))
    manifest = strict_json(read_plan("manifest.json"))
    in_process_probe(manifest, "BASE")
    requirements_in = read_plan("requirements.in")
    requirements_lock = read_plan("requirements-lock.txt")
    missing = [key for key in PRE_KEYS if key not in manifest]
    if missing:
        governed_abort("PLAN_DIGEST", "MANIFEST_KEYS", ",".join(missing))
    pre = digest({"spec": "PRE_PROVISION_PLAN_V1", "fields": {key: manifest[key] for key in PRE_KEYS}})
    plan = digest({
        "spec": "PROVISIONING_PLAN_V1",
        "lock_review_digest": manifest["lock_review_digest"],
        "requirements_in_sha256": hashlib.sha256(requirements_in).hexdigest(),
        "requirements_lock_sha256": hashlib.sha256(requirements_lock).hexdigest(),
        "pre_provision_plan_digest": pre,
    })
    if plan != approved["plan_digest"]:
        governed_abort("PLAN_DIGEST", "PLAN_DIGEST", plan)
    review = digest({"spec": "LOCK_REVIEW_RECORD_V1", "records": manifest["dependency_lock_review"],
                     "artifact_targets": manifest["artifact_targets"], "lock_artifacts": manifest["lock_artifacts"]})
    if review != manifest["lock_review_digest"]:
        governed_abort("PLAN_DIGEST", "LOCK_REVIEW_DIGEST")
    if hashlib.sha256(requirements_in).hexdigest() != proven["requirements_in_sha256"] or \
            hashlib.sha256(requirements_lock).hexdigest() != proven["requirements_lock_sha256"]:
        governed_abort("PLAN_DIGEST", "PLAN_FILE_COPY")
    base = manifest["operator_base_interpreter"]
    members = {
        "executable_sha256": base["executable_sha256"],
        "interpreter_path": base["path"],
        "stdlib_path": base["stdlib_path"],
        "stdlib_tree_digest": base["stdlib_tree_digest"],
        "native_closure_digest": base["native_closure_digest"],
        "installer_pip_package_path": manifest["installer_pip_package_path"],
        "installer_pip_package_tree_digest": manifest["installer_pip_package_tree_digest"],
        "provisioning_script_sha256": manifest["provisioning_script_sha256"],
        "verifier_sha256": manifest["verifier_sha256"],
    }
    for name, value in members.items():
        if proven.get(name) != value:
            governed_abort("BASE_INTERPRETER_MISMATCH", "IDENTITY_MEMBER", name)
    if json.loads(proven["sys_path_isolated"]) != base["sys_path_isolated"]:
        governed_abort("BASE_INTERPRETER_MISMATCH", "SYS_PATH_UNBOUND", "MANIFEST_LIST")
    with open(os.path.join(NEUTRAL, "e2_hook_head.py"), "r", encoding="utf-8") as handle:
        verify_e2_helper_chain(base, proven, handle.read())
    pipcopy, tags_module = import_pip_copy(manifest)
    fields = derive_tags(tags_module, base["python_version"])
    check_tags(manifest, fields, ("abi_tag", "platform_tags", "platform_sequence", "tag_sequence"))
    audit_modules(os.path.realpath(base["stdlib_path"]), pipcopy)

    prefix = manifest["operator_python_prefix"]
    if not safe_path(prefix) or ":" in prefix or prefix.endswith("/") or prefix.startswith("/tmp/"):
        governed_abort("PLAN_DIGEST", "PLAN_VALUE", "operator_python_prefix")
    for entry in base["sys_path_isolated"] + base["sys_path_isolated_prefix"]:
        if not safe_path(entry):
            governed_abort("PLAN_DIGEST", "PLAN_VALUE", "sys_path")
    apt = manifest["apt_plan"]
    if apt["install_flags"] != INSTALL_FLAGS:
        governed_abort("PLAN_DIGEST", "PLAN_VALUE", "install_flags")
    os.mkdir(os.path.join(NEUTRAL, "x0"), 0o700)
    write_lines("prefix.txt", [prefix])
    write_lines("python_version.txt", [base["python_version"]])
    write_lines("sys_path_prefix.txt", base["sys_path_isolated_prefix"])
    write_lines("os_release.tsv", ["%s\t%s" % (key, apt["os_release"][key])
                                   for key in ("ID", "VERSION_ID", "VERSION_CODENAME")])
    tuples, pairs, keyrings = [], [], {}
    for stanza in apt["sources"]:
        signed = stanza["signed_by"]
        keyrings[signed["keyring_path"]] = signed["keyring_sha256"]
        for uri in stanza["uris"]:
            for suite in stanza["suites"]:
                pairs.append("%s\t%s" % (uri, suite))
                for component in stanza["components"]:
                    tuples.append("\t".join((stanza["type"], uri, suite, component, signed["keyring_path"],
                                             signed["keyring_sha256"])))
    write_lines("sources.tsv", tuples)
    write_lines("update_pairs.tsv", sorted(set(pairs)))
    write_lines("keyrings.tsv", ["%s\t%s" % item for item in sorted(keyrings.items())])
    config = []
    for key, value in apt["approved_apt_config"]:
        if "\t" in key:
            governed_abort("PLAN_DIGEST", "PLAN_VALUE", "approved_apt_config")
        config.append("".join(chr(ord(ch) + 32) if "A" <= ch <= "Z" else ch for ch in key) + "\t" + value)
    write_lines("apt_config.tsv", config)
    dpkg = apt["approved_dpkg_config"]
    if dpkg is None or dpkg.get("diversions") is None or dpkg.get("statoverride") is None:
        governed_abort("PLAN_DIGEST", "PLAN_INCOMPLETE", "approved_dpkg_config")
    serialized, paths = [], []
    for item in dpkg["files"]:
        paths.append(item["path"])
        serialized.append("F\t%s\t%s" % (item["path"], item["sha256"]))
        options = []
        for name, value in item["options"]:
            options.append("%s\t%s" % (name, "-" if value is None else "=" + value))
        serialized += ["O\t" + line for line in options]
        key = item["path"].replace("/", "_")
        write_lines("dpkg_opts." + key, options)
        write_lines("dpkg_sha." + key, [item["sha256"]])
    write_lines("dpkg_files.txt", serialized)
    write_lines("dpkg_paths.txt", paths)
    for row in dpkg["diversions"] + dpkg["statoverride"]:
        if any("\t" in field or "\n" in field for field in row):
            governed_abort("PLAN_DIGEST", "PLAN_VALUE", "approved_dpkg_config")
    write_lines("dpkg_diversions.tsv", ["\t".join(row) for row in dpkg["diversions"]])
    write_lines("dpkg_statoverride.txt", [" ".join(row) for row in dpkg["statoverride"]])
    write_lines("dpkg_policy_rc_d.tsv", ["%s\t%s" % (dpkg["policy_rc_d"]["path"], dpkg["policy_rc_d"]["sha256"])])
    packages = []
    for item in apt["packages"]:
        for field in (item["name"], item["version"], item["architecture"]):
            if not field or any(not (ch.isascii() and (ch.isalnum() or ch in ".+:~_-")) for ch in field):
                governed_abort("PLAN_DIGEST", "PLAN_VALUE", "packages")
        packages.append("%s\t%s\t%s" % (item["name"], item["version"], item["architecture"]))
    write_lines("packages.tsv", packages)
    sys.stdout.write("X0_PLAN_DIGEST_VERIFIED=%s\n" % plan)
#END X0
PY_X0
    IFS= read -r -d '' E1_BODY <<'PY_E1'
#BEGIN E1
def main():
    manifest = strict_json(read_plan("manifest.json"))
    in_process_probe(manifest, "BASE")
    prefix = sys.argv[1]
    if len(sys.argv) != 2 or prefix != manifest["operator_python_prefix"]:
        governed_abort("PROVISIONING_ENV_VIOLATION", "E1_ARGV")
    if os.path.lexists(prefix) and (os.path.islink(prefix) or not os.path.isdir(prefix) or os.listdir(prefix)):
        governed_abort("PROVISIONING_ENV_VIOLATION", "PREFIX_NOT_EMPTY")
    import venv
    venv.EnvBuilder(system_site_packages=False, clear=False, symlinks=True, with_pip=False).create(prefix)
    sys.stdout.write("E1_PREFIX_CREATED=%s\n" % prefix)
#END E1
PY_E1
    IFS= read -r -d '' E2_BODY <<'PY_E2'
#BEGIN E2
def main():
    manifest = strict_json(read_plan("manifest.json"))
    in_process_probe(manifest, "PREFIX")
    base = manifest["operator_base_interpreter"]
    lock_path = os.path.join(NEUTRAL, "plan", "requirements-lock.txt")
    arguments = ["--isolated", "install", "--require-hashes", "--only-binary=:all:", "--no-deps", "--no-compile",
                 "--disable-pip-version-check", "-r", lock_path]
    if sys.argv[1:] != arguments:
        governed_abort("PROVISIONING_ENV_VIOLATION", "PIP_ARGV")
    pipcopy, tags_module = import_pip_copy(manifest)
    fields = derive_tags(tags_module, base["python_version"])
    check_tags(manifest, fields, ("abi_tag", "platform_tags", "tag_sequence"))
    stdlib_real = os.path.realpath(base["stdlib_path"])
    audit_modules(stdlib_real, pipcopy)
    import runpy
    sys.argv = ["pip"] + arguments
    status = 0
    try:
        runpy.run_module("pip", run_name="__main__", alter_sys=True)
    except SystemExit as exit_request:
        status = exit_request.code
    audit_modules(stdlib_real, pipcopy)
    if status not in (0, None):
        governed_abort("PROVISIONING_ENV_VIOLATION", "PIP_INSTALL_FAILED", str(status))
    sys.stdout.write("E2_PIP_STATUS=0\n")
#END E2
PY_E2
    X0_CODE="$HOOK_HEAD$PROBE$X0_BODY$HOOK_TAIL"
    E1_CODE="$HOOK_HEAD$PROBE$E1_BODY$HOOK_TAIL"
    E2_CODE="$HOOK_HEAD_E2$PROBE$E2_BODY$HOOK_TAIL"
}

# -- OPERATOR_PYTHON_INSTALL_V1 steps 1-8 ----------------------------------------------------------

_manifest_string() {
    local text=$1 key=$2 re rest
    re="\"$key\"[[:space:]]*:[[:space:]]*\"([^\"]*)\""
    [[ "$text" =~ $re ]] || _abort PROVISIONING_ENV_VIOLATION SELF_HASH "MANIFEST:$key"
    REPLY=${BASH_REMATCH[1]}
    rest=${text#*"\"$key\""}
    [[ "$rest" != *"\"$key\""* ]] || _abort PROVISIONING_ENV_VIOLATION SELF_HASH "MANIFEST_DUPLICATE:$key"
}

_manifest_string_list() {
    local text=$1 key=$2 re body item matched
    re="\"$key\"[[:space:]]*:[[:space:]]*\\[([^]]*)\\]"
    [[ "$text" =~ $re ]] || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "MANIFEST:$key"
    body=${BASH_REMATCH[1]}
    local rest=${text#*"\"$key\""}
    [[ "$rest" != *"\"$key\""* ]] || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "MANIFEST_DUPLICATE:$key"
    LIST=()
    local re_item='^[[:space:]]*"([^"]*)"[[:space:]]*(,|$)'
    while :; do
        _strip_space "$body"
        body=$REPLY
        [[ -z "$body" ]] && break
        [[ "$body" =~ $re_item ]] || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "MANIFEST_LIST:$key"
        item=${BASH_REMATCH[1]}
        matched=${#BASH_REMATCH[0]}
        _printable "$item" || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND "MANIFEST_LIST:$key"
        LIST+=("$item")
        body=${body:matched}
    done
}

_parse_arguments() {
    (( $# == 10 )) || _abort PROVISIONING_ENV_VIOLATION INVOCATION ARGUMENT_COUNT
    [[ "$1" == --approved-plan-digest && "$3" == --approved-interpreter-sha256 && "$5" == --approved-identity-digest \
       && "$7" == --identity-paths && "$9" == --checkout-root ]] || _abort PROVISIONING_ENV_VIOLATION INVOCATION ARGUMENT_ORDER
    [[ "$2" =~ $RE_HEX64 && "$4" =~ $RE_HEX64 && "$6" =~ $RE_HEX64 ]] || _abort PROVISIONING_ENV_VIOLATION INVOCATION DIGEST_FORMAT
    APPROVED_PLAN_DIGEST=$2
    APPROVED_INTERPRETER_SHA256=$4
    APPROVED_IDENTITY_DIGEST=$6
    _split_colon "$8"
    (( ${#SPLIT[@]} == 3 )) || _abort PROVISIONING_ENV_VIOLATION INVOCATION IDENTITY_PATHS
    local p
    for p in "${SPLIT[@]}"; do
        [[ "$p" == /* ]] && _printable "$p" || _abort PROVISIONING_ENV_VIOLATION INVOCATION IDENTITY_PATHS
    done
    ID_INTERP=${SPLIT[0]}
    ID_STDLIB=${SPLIT[1]}
    ID_PIP=${SPLIT[2]}
    CHECKOUT=${10}
    [[ "$CHECKOUT" == /* ]] && _printable "$CHECKOUT" || _abort PROVISIONING_ENV_VIOLATION INVOCATION CHECKOUT_ROOT
}

_step1() {
    local out self_sha verifier_sha manifest_text
    (( EUID == 0 )) || _abort PROVISIONING_ENV_VIOLATION NOT_ROOT
    [[ "$0" == "$STAGING_PARENT"/stage-*/provision_document_rendering_env.sh ]] \
        || _abort PROVISIONING_ENV_VIOLATION INVOCATION STAGED_PATH
    _evidence entry_assertions "PASS umask=0022 cwd=/ stdin=/dev/null privileged=1 environ=8 functions=0 fds=0,1,2,255"
    _evidence entry_ulimit_a "$(printf '%s' "$__entry_ulimit_a" | while IFS= read -r line; do printf '%s; ' "$line"; done)"
    local -a cmdline=()
    mapfile -d '' -t cmdline < "/proc/$$/cmdline"
    _evidence cmdline "$(printf '%q ' "${cmdline[@]}")"
    N=$(_x "$T_MKTEMP" -d /tmp/career-os-render-provision.XXXXXXXXXX) || _abort PROVISIONING_ENV_VIOLATION NEUTRAL_DIRECTORY
    [[ "$N" == /tmp/career-os-render-provision.* && -d "$N" && ! -L "$N" && -O "$N" ]] \
        || _abort PROVISIONING_ENV_VIOLATION NEUTRAL_DIRECTORY "$N"
    out=$(_x "$T_STAT" -c '%a %u' -- "$N") || _abort PROVISIONING_ENV_VIOLATION NEUTRAL_DIRECTORY STAT
    [[ "$out" == "700 0" ]] || _abort PROVISIONING_ENV_VIOLATION NEUTRAL_DIRECTORY "$out"
    _evidence fd1 "$(_x "$T_READLINK" -- "/proc/$$/fd/1")"
    _evidence fd2 "$(_x "$T_READLINK" -- "/proc/$$/fd/2")"
    [[ "$PWD" == / ]] || _abort PROVISIONING_ENV_VIOLATION ENTRY_CWD
    cd "$N" || _abort PROVISIONING_ENV_VIOLATION NEUTRAL_DIRECTORY CD
    _set_child_home "$N"
    _x "$T_MKDIR" -m 0700 -- "$N/plan" "$N/pycache" || _abort PROVISIONING_ENV_VIOLATION NEUTRAL_DIRECTORY MKDIR
    out=$(_x "$T_REALPATH" -e -- "$CHECKOUT") || _abort PROVISIONING_ENV_VIOLATION CHECKOUT_ROOT
    [[ "$out" == "$CHECKOUT" ]] || _abort PROVISIONING_ENV_VIOLATION CHECKOUT_ROOT REALPATH
    _x "$T_CP" -- "$CHECKOUT/docs/rendering/RENDERING_ENVIRONMENT_V1.json" "$N/plan/manifest.json" \
        && _x "$T_CP" -- "$CHECKOUT/requirements.in" "$N/plan/requirements.in" \
        && _x "$T_CP" -- "$CHECKOUT/requirements-lock.txt" "$N/plan/requirements-lock.txt" \
        && _x "$T_CP" -- "$CHECKOUT/scripts/verify_document_rendering_environment.py" "$N/plan/verifier.py" \
        || _abort PROVISIONING_ENV_VIOLATION PLAN_COPY
    self_sha=$(_x "$T_SHA256SUM" -- "$0") || _abort PROVISIONING_ENV_VIOLATION SELF_HASH SCRIPT
    self_sha=${self_sha:0:64}
    verifier_sha=$(_x "$T_SHA256SUM" -- "$N/plan/verifier.py") || _abort PROVISIONING_ENV_VIOLATION SELF_HASH VERIFIER
    verifier_sha=${verifier_sha:0:64}
    _read_file "$N/plan/manifest.json" || _abort PROVISIONING_ENV_VIOLATION SELF_HASH MANIFEST_NUL
    manifest_text=$REPLY
    MANIFEST_TEXT=$manifest_text
    _manifest_string "$manifest_text" provisioning_script_sha256
    [[ "$REPLY" == "$self_sha" ]] || _abort PROVISIONING_ENV_VIOLATION SELF_HASH SCRIPT
    [[ "$0" == "$STAGING_PARENT/stage-$self_sha/provision_document_rendering_env.sh" ]] \
        || _abort PROVISIONING_ENV_VIOLATION INVOCATION STAGED_PATH
    _manifest_string "$manifest_text" verifier_sha256
    [[ "$REPLY" == "$verifier_sha" ]] || _abort PROVISIONING_ENV_VIOLATION SELF_HASH VERIFIER
    SELF_SHA=$self_sha
    VERIFIER_SHA=$verifier_sha
    _evidence staged_script "$0 $self_sha $(_x "$T_STAT" -c '%u:%g %a %s %Y' -- "$0")"
    _evidence verifier_copy "$verifier_sha"
    _host_tool_record
    _chain_record
    _create_private_tool
    _evidence private_hash_tool "$PRIV PASS"
}

_step2() {
    local entries
    _identity_external PRE_APT
    _manifest_string_list "$MANIFEST_TEXT" sys_path_isolated
    BASE_SYS_PATH=("${LIST[@]}")
    entries=$(printf '%s\n' "${BASE_SYS_PATH[@]}")
    _sys_path_rule1 "$entries"
    STARTUP_ABSENT=()
    _startup_path_inputs "$ID_INTERP" "$INTERP_REAL"
    _pip_copy
    PH=()
    _ph_files "$N/plan/requirements.in" "$N/plan/requirements-lock.txt"
    REQ_IN_SHA=${PH[$N/plan/requirements.in]}
    REQ_LOCK_SHA=${PH[$N/plan/requirements-lock.txt]}
    local sys_path_json sep="" e
    sys_path_json="["
    for e in "${BASE_SYS_PATH[@]}"; do
        sys_path_json+="$sep\"$e\""
        sep=", "
    done
    sys_path_json+="]"
    printf '%s' "$HOOK_HEAD_E2" > "$N/e2_hook_head.py"
    _chain_rows_json
    local chain_rows=$REPLY
    _chain_absent_json
    local chain_absent=$REPLY
    printf 'plan_digest\t%s\n' "$APPROVED_PLAN_DIGEST" > "$N/approved.tsv"
    {
        printf 'executable_sha256\t%s\n' "$APPROVED_INTERPRETER_SHA256"
        printf 'interpreter_path\t%s\n' "$ID_INTERP"
        printf 'stdlib_path\t%s\n' "$ID_STDLIB"
        printf 'stdlib_tree_digest\t%s\n' "$PROVEN_STDLIB_DIGEST"
        printf 'native_closure_digest\t%s\n' "$PROVEN_CLOSURE_DIGEST"
        printf 'installer_pip_package_path\t%s\n' "$ID_PIP"
        printf 'installer_pip_package_tree_digest\t%s\n' "$PROVEN_PIP_DIGEST"
        printf 'provisioning_script_sha256\t%s\n' "$SELF_SHA"
        printf 'verifier_sha256\t%s\n' "$VERIFIER_SHA"
        printf 'requirements_in_sha256\t%s\n' "$REQ_IN_SHA"
        printf 'requirements_lock_sha256\t%s\n' "$REQ_LOCK_SHA"
        printf 'sys_path_isolated\t%s\n' "$sys_path_json"
        printf 'e2_allowed_sha256\t%s\n' "$E2_ALLOWED_SHA256"
        printf 'empty_allowed_sha256\t%s\n' "$EMPTY_ALLOWED_SHA256"
        printf 'e2_chain_rows\t%s\n' "$chain_rows"
        printf 'e2_chain_absent\t%s\n' "$chain_absent"
    } > "$N/proven.tsv"
    _governed X0 "$ID_INTERP" -I -S -B -X "pycache_prefix=$N/pycache" -c "$X0_CODE"
    PREFIX=$(<"$N/x0/prefix.txt")
    PYTHON_VERSION=$(<"$N/x0/python_version.txt")
    _evidence plan_digest_verified "$APPROVED_PLAN_DIGEST"
}

_step3_apt() {
    local out rc line u s found name path
    # A
    _identity_critical_set
    _dpkg_state
    SNAPSHOT_STATE=("${STATE[@]}")
    for line in "${SNAPSHOT_STATE[@]}"; do
        name=${line%%"$TAB"*}
        if [[ -v IDENTITY_CRITICAL[$name] ]]; then
            _evidence apt_preinstall_snapshot "$line${TAB}1"
        else
            _evidence apt_preinstall_snapshot "$line${TAB}0"
        fi
    done
    NATIVE_ARCH=$(_x "$T_DPKG" --print-architecture) || _abort APT_CONFIG_UNAPPROVED APT_CONFIG_UNAPPROVED ARCHITECTURE
    # B
    _os_release_check
    _apt_config_shell
    _check_sources
    _check_apt_config
    _check_pins
    _dpkg_record
    _check_dpkg_record
    DPKG_SER_B=("${DPKG_SER[@]}")
    for line in "${DPKG_SER[@]}" "${DPKG_DIV[@]}" "${DPKG_STAT[@]}" "$DPKG_POLICY"; do
        _evidence dpkg_config_record "$line"
    done
    # C
    out=$(_x "$T_APT_GET" update --error-on=any 2>&1)
    rc=$?
    printf '%s\n' "$out" | while IFS= read -r line; do printf 'APT_UPDATE %s\n' "$line"; done
    (( rc == 0 )) || _abort APT_UPDATE_FAILED APT_UPDATE_FAILED "EXIT:$rc"
    while IFS= read -r line; do
        [[ "$line" == Err:* || "$line" == E:* || "$line" == W:* ]] && _abort APT_UPDATE_FAILED APT_UPDATE_FAILED UPDATE_ERROR
    done <<< "$out"
    local -a hits=()
    while IFS="$TAB" read -r u s; do
        found=0
        while IFS= read -r line; do
            if [[ "$line" =~ ^(Hit|Get):[0-9]+\ (.*)$ ]]; then
                local rest=${BASH_REMATCH[2]}
                if [[ "$rest" == "${u%/} $s InRelease" || "$rest" == "${u%/} $s InRelease "* \
                      || "$rest" == "${u%/}/ $s InRelease" || "$rest" == "${u%/}/ $s InRelease "* ]]; then
                    found=1
                    hits+=("$line")
                fi
            fi
        done <<< "$out"
        (( found )) || _abort APT_UPDATE_FAILED APT_UPDATE_FAILED "INRELEASE_NOT_FETCHED:$u $s"
    done < "$N/x0/update_pairs.tsv"
    _evidence no_debsig_admission "COMPLETE (sources, keyrings, configuration and update passed)"
    # D
    while IFS="$TAB" read -r u s; do
        name=${u#*://}
        name=${name%/}
        name="${name//\//_}_dists_${s//\//_}_InRelease"
        path="${APT_PATHS[LISTS]}/$name"
        [[ -f "$path" ]] || _abort APT_UPDATE_FAILED APT_UPDATE_FAILED "INRELEASE_MISSING:$path"
        PH=()
        _ph_files "$path"
        _evidence apt_inrelease "$u $s $path ${PH[$path]}"
    done < "$N/x0/update_pairs.tsv"
    for line in "${hits[@]}"; do
        _evidence apt_update_line "$line"
    done
    # E
    local -a argv=("$T_APT_GET" install --yes --no-install-recommends --no-remove)
    local pkg ver arch
    while IFS="$TAB" read -r pkg ver arch; do
        argv+=("$pkg=$ver")
    done < "$N/x0/packages.tsv"
    _evidence apt_get_version "$(_x "$T_APT_GET" --version | { IFS= read -r first; printf '%s' "$first"; })"
    _evidence apt_install_argv "$(printf '%q ' "${argv[@]}")"
    _ph_string "$(printf '%q ' "${argv[@]}")"
    APT_TRANSACTION_SHA256=$REPLY
    out=$(_x "${argv[@]}" 2>&1)
    rc=$?
    APT_INSTALL_OUTPUT=$out
    # F0: hash-first guard before any other command.
    _tool_recheck F0
    _dpkg_record
    if [[ "${DPKG_SER[*]}" != "${DPKG_SER_B[*]}" || ${#DPKG_SER[@]} -ne ${#DPKG_SER_B[@]} ]]; then
        _abort APT_UNEXPECTED_CHANGE APT_UNEXPECTED_CHANGE DPKG_CONFIG_CHANGED
    fi
    for line in "${DPKG_DIV[@]}" "${DPKG_STAT[@]}" "$DPKG_POLICY"; do
        _evidence dpkg_config_record_f0 "$line"
    done
    printf '%s\n' "$out" | while IFS= read -r line; do printf 'APT_INSTALL %s\n' "$line"; done
    (( rc == 0 )) || _abort APT_INSTALL_FAILED APT_INSTALL_FAILED "EXIT:$rc"
    while IFS= read -r line; do
        [[ "$line" == *"Do you want to continue"* || "$line" == Abort.* ]] && _abort APT_INSTALL_FAILED APT_INSTALL_FAILED PROMPT
    done <<< "$out"
    # F and G
    _dpkg_state
    _apt_delta_and_checks
    # POST_APT_LD_SO_CACHE_V1 prerequisites: the apt phase with every package and plan check has completed (an
    # identity_critical delta or any plan deviation aborted above), and the libc-bin trigger of this exact transaction
    # is recorded from its captured output.
    _libc_bin_trigger_check
    APT_PHASE_COMPLETE=1
}

_identity_recheck() {
    local label=$1 entries
    _tool_recheck "$label"
    _identity_external "$label"
    entries=$(printf '%s\n' "${BASE_SYS_PATH[@]}")
    _sys_path_rule1 "$entries"
    STARTUP_ABSENT=()
    _startup_path_inputs "$ID_INTERP" "$INTERP_REAL"
    _pip_copy
}

_step5_e1() {
    local out
    if [[ -e "$PREFIX" || -L "$PREFIX" ]]; then
        [[ -d "$PREFIX" && ! -L "$PREFIX" ]] || _abort PROVISIONING_ENV_VIOLATION PREFIX_NOT_EMPTY "$PREFIX"
        out=$(_x "$T_FIND" "$PREFIX" -mindepth 1 -maxdepth 1 -printf '%p\n') || _abort PROVISIONING_ENV_VIOLATION PREFIX_NOT_EMPTY
        [[ -z "$out" ]] || _abort PROVISIONING_ENV_VIOLATION PREFIX_NOT_EMPTY "$PREFIX"
    fi
    _governed E1 "$ID_INTERP" -I -S -B -X "pycache_prefix=$N/pycache" -c "$E1_CODE" "$PREFIX"
}

_step6_audit() {
    local cfg expected out site minor ancestor st prefix_entries
    minor=${PYTHON_VERSION%.*}
    site="$PREFIX/lib/python$minor/site-packages"
    _read_file "$PREFIX/pyvenv.cfg" || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT PYVENV_NUL
    cfg=$REPLY
    _dirname "$ID_INTERP"
    expected="home = $REPLY${NL}include-system-site-packages = false${NL}version = $PYTHON_VERSION${NL}executable = $INTERP_REAL${NL}command = $ID_INTERP -m venv --without-pip --without-scm-ignore-files $PREFIX$NL"
    [[ "$cfg" == "$expected" ]] || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT PYVENV_CFG
    [[ -d "$site" && ! -L "$site" ]] || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT SITE_PACKAGES
    out=$(_x "$T_FIND" "$site" -mindepth 1 -printf '%p\n') || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT SITE_PACKAGES
    [[ -z "$out" ]] || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT SITE_PACKAGES_NOT_EMPTY
    out=$(_x "$T_FIND" "$PREFIX" \( -name sitecustomize.py -o -name usercustomize.py -o -name '*.pth' -o -name '*.pyc' \
          -o -name __pycache__ \) -printf '%p\n') || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT STARTUP_HOOK
    [[ -z "$out" ]] || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT "STARTUP_HOOK:$out"
    out=$(_x "$T_FIND" "$PREFIX" ! -type l \( ! -uid 0 -o -perm /022 \) -printf '%p\n') \
        || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT OWNERSHIP
    [[ -z "$out" ]] || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT "OWNERSHIP:$out"
    _dirname "$PREFIX"
    ancestor=$REPLY
    while :; do
        st=$(_x "$T_STAT" -c '%u %a' -- "$ancestor") || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT "ANCESTOR:$ancestor"
        if [[ "${st%% *}" != 0 ]] || (( (8#${st#* } & 8#022) != 0 )); then
            _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT "ANCESTOR:$ancestor"
        fi
        [[ "$ancestor" == / ]] && break
        _dirname "$ancestor"
        ancestor=$REPLY
    done
    PH=()
    _ph_files "$N/plan/requirements-lock.txt"
    [[ "${PH[$N/plan/requirements-lock.txt]}" == "$REQ_LOCK_SHA" ]] || _abort PROVISIONING_ENV_VIOLATION PREFIX_AUDIT LOCK_COPY
    _identity_recheck STEP6
    prefix_entries=$(<"$N/x0/sys_path_prefix.txt")
    _sys_path_rule1 "$prefix_entries" "$PREFIX/lib"
    STARTUP_ABSENT=()
    _startup_path_inputs "$ID_INTERP" "$INTERP_REAL"
    local prefix_python="$PREFIX/bin/python" prefix_real
    prefix_real=$(_x "$T_REALPATH" -e -- "$prefix_python") || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND PREFIX_PYTHON
    [[ "$prefix_real" == "$INTERP_REAL" ]] || _abort BASE_INTERPRETER_MISMATCH SYS_PATH_UNBOUND PREFIX_PYTHON
    _startup_path_inputs "$prefix_python" "$prefix_real" "$PREFIX/pyvenv.cfg"
    local c
    for c in "${STARTUP_ABSENT[@]}"; do
        _evidence startup_path_absent "$c"
    done
}

_step7_e2() {
    E2_LAUNCH="$PREFIX/bin/python"
    _governed E2 "$E2_LAUNCH" -I -S -B -X "pycache_prefix=$N/pycache" -c "$E2_CODE" --isolated install --require-hashes \
        --only-binary=:all: --no-deps --no-compile --disable-pip-version-check -r "$N/plan/requirements-lock.txt"
    E2_LAUNCH=""
}

_step8_evidence() {
    local minor site out
    local -a dists=()
    minor=${PYTHON_VERSION%.*}
    site="$PREFIX/lib/python$minor/site-packages"
    _x "$T_FIND" "$site" -mindepth 1 -maxdepth 1 -name '*.dist-info' -printf '%f\0' > "$N/dists.lst" \
        || _abort PROVISIONING_ENV_VIOLATION EVIDENCE DISTRIBUTIONS
    mapfile -d '' -t dists < "$N/dists.lst"
    _sort_into_sorted "${dists[@]}"
    for out in "${SORTED[@]}"; do
        _evidence installed_distribution "$out"
    done
    out=$(_x "$T_FIND" "$PREFIX" \( -name '*.pyc' -o -name __pycache__ \) -printf '%p\n') \
        || _abort PROVISIONING_ENV_VIOLATION EVIDENCE BYTECODE
    [[ -z "$out" ]] || _abort PROVISIONING_ENV_VIOLATION EVIDENCE "BYTECODE:$out"
    _evidence governed_execution_count "$GOVERNED_COUNT"
    _evidence result "PROVISIONED prefix=$PREFIX plan_digest=$APPROVED_PLAN_DIGEST (the verifier decides; the script grants no authority)"
}

provision_main() {
    trap _cleanup EXIT
    trap _on_term TERM
    GOVERNED_COUNT=0
    _parse_arguments "$@"
    _load_embedded
    _step1
    _step2
    _step3_apt
    _identity_recheck STEP4
    _step5_e1
    _step6_audit
    _step7_e2
    _step8_evidence
    return 0
}
#END FUNCTIONS

provision_main "$@"
exit $?
