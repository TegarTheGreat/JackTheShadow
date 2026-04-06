#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
#  Jack The Shadow — Installer
#  Installs jshadow from GitHub: https://github.com/TegarTheGreat/JackTheShadow
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO="https://github.com/TegarTheGreat/JackTheShadow.git"
BRANCH="main"
INSTALL_DIR="${JSHADOW_INSTALL_DIR:-$HOME/.jshadow-src}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

banner() {
    echo -e "${RED}"
    echo "     ██╗ █████╗  ██████╗██╗  ██╗"
    echo "     ██║██╔══██╗██╔════╝██║ ██╔╝"
    echo "     ██║███████║██║     █████╔╝ "
    echo "██   ██║██╔══██║██║     ██╔═██╗ "
    echo "╚█████╔╝██║  ██║╚██████╗██║  ██╗"
    echo " ╚════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${CYAN}  T H E   S H A D O W${NC}"
    echo ""
}

info()  { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
error() { echo -e "  ${RED}✖${NC} $1"; exit 1; }

check_python() {
    local py=""
    if command -v python3 &>/dev/null; then
        py="python3"
    elif command -v python &>/dev/null; then
        py="python"
    else
        error "Python 3.10+ is required but not found. Install Python first."
    fi

    local version
    version=$($py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 10 ]; }; then
        error "Python 3.10+ required, found $version"
    fi

    info "Python $version found ($py)"
    echo "$py"
}

check_pip() {
    local py="$1"
    if ! $py -m pip --version &>/dev/null; then
        warn "pip not found, attempting to install..."
        $py -m ensurepip --upgrade 2>/dev/null || error "Failed to install pip"
    fi
    info "pip available"
}

install_from_git() {
    local py="$1"
    info "Installing jshadow from GitHub..."

    if [ -d "$INSTALL_DIR" ]; then
        info "Updating existing source in $INSTALL_DIR..."
        cd "$INSTALL_DIR"
        git pull --quiet origin "$BRANCH" 2>/dev/null || {
            warn "Git pull failed, re-cloning..."
            cd ..
            rm -rf "$INSTALL_DIR"
            git clone --quiet --depth 1 -b "$BRANCH" "$REPO" "$INSTALL_DIR"
            cd "$INSTALL_DIR"
        }
    else
        git clone --quiet --depth 1 -b "$BRANCH" "$REPO" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi

    $py -m pip install --quiet --upgrade pip setuptools wheel
    $py -m pip install --quiet .
    info "jshadow installed successfully!"
}

install_from_pip() {
    local py="$1"
    info "Installing jshadow from PyPI..."
    $py -m pip install --quiet --upgrade jshadow
    info "jshadow installed from PyPI!"
}

setup_session_dir() {
    mkdir -p "$HOME/.jshadow/sessions"
    info "Session directory: ~/.jshadow/"
}

main() {
    banner
    echo -e "  ${CYAN}Installing Jack The Shadow...${NC}"
    echo ""

    # Check prerequisites
    local py
    py=$(check_python)
    check_pip "$py"

    # Check if git is available
    if ! command -v git &>/dev/null; then
        error "git is required. Install git first."
    fi
    info "git available"

    echo ""

    # Install method
    if [ "${1:-}" = "--pip" ]; then
        install_from_pip "$py"
    else
        install_from_git "$py"
    fi

    # Setup session directory
    setup_session_dir

    echo ""
    echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${GREEN}Installation complete!${NC}"
    echo ""
    echo -e "  ${CYAN}Get started:${NC}"
    echo -e "    1. ${YELLOW}jshadow${NC}                — Launch Jack The Shadow"
    echo -e "    2. Use ${YELLOW}/login${NC} in chat      — Connect Cloudflare credentials"
    echo ""
    echo -e "  ${CYAN}Quick commands:${NC}"
    echo -e "    jshadow                           # start agent, set target in chat"
    echo -e "    jshadow --target 192.168.1.0/24   # start with target preset"
    echo -e "    jshadow -t example.com --lang id  # use Indonesian language"
    echo ""
    echo -e "  ${CYAN}Docs:${NC} https://github.com/TegarTheGreat/JackTheShadow"
    echo -e "  ${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

main "$@"
