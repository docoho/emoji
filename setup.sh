#!/usr/bin/env bash
# =============================================================================
# Emoji Showcase Platform — Dependency Setup Script
# Supports: macOS, Linux (Debian/Ubuntu, Fedora/RHEL, Arch)
# Usage:    chmod +x setup.sh && ./setup.sh [--backend-only | --frontend-only]
# =============================================================================

set -euo pipefail

# ── Version requirements ──────────────────────────────────────────────────────
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=9
NODE_MIN_MAJOR=16

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

info()  { printf "${CYAN}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
fail()  { printf "${RED}[ERROR]${NC} %s\n" "$*"; exit 1; }

# ── Resolve project root (directory this script lives in) ─────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# =============================================================================
# Usage
# =============================================================================
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --backend-only   Set up only the Python backend (venv + pip)
  --frontend-only  Set up only the Node.js frontend (npm install)
  --help           Show this help message and exit

Without options both backend and frontend are set up.
EOF
    exit 0
}

# =============================================================================
# Parse arguments
# =============================================================================
DO_BACKEND=true
DO_FRONTEND=true

for arg in "$@"; do
    case "$arg" in
        --backend-only)  DO_FRONTEND=false ;;
        --frontend-only) DO_BACKEND=false  ;;
        --help|-h)       usage             ;;
        *) fail "Unknown option: $arg  (try --help)" ;;
    esac
done

# =============================================================================
# 1. Detect OS
# =============================================================================
detect_os() {
    case "$(uname -s)" in
        Darwin) OS="macos" ;;
        Linux)  OS="linux" ;;
        *) fail "Unsupported OS: $(uname -s). This script supports macOS and Linux." ;;
    esac
    info "Detected OS: $OS"
}

# =============================================================================
# 2. Version comparison helpers
# Returns 0 (true) when the installed version >= the required minimum.
# Uses plain integer arithmetic to avoid depending on GNU sort -V.
# =============================================================================

# Extract the major component from a "major.minor[.patch]" string.
_major() { echo "${1%%.*}"; }

# Extract the minor component from a "major.minor[.patch]" string.
_minor() {
    local rest="${1#*.}"   # strip leading "major."
    echo "${rest%%.*}"     # strip trailing ".patch" if present
}

# version_gte INSTALLED REQUIRED_MAJOR REQUIRED_MINOR
# Returns 0 when INSTALLED >= REQUIRED_MAJOR.REQUIRED_MINOR
version_gte() {
    local installed="$1"
    local req_major="$2"
    local req_minor="$3"

    local inst_major inst_minor
    inst_major="$(_major "$installed")"
    inst_minor="$(_minor "$installed")"

    if   [ "$inst_major" -gt "$req_major" ]; then return 0
    elif [ "$inst_major" -lt "$req_major" ]; then return 1
    elif [ "$inst_minor" -ge "$req_minor" ]; then return 0
    else return 1
    fi
}

# =============================================================================
# 3. Check / install Python
# =============================================================================
check_python() {
    info "Checking Python >= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR} …"

    PYTHON_CMD=""
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done

    if [ -n "$PYTHON_CMD" ]; then
        PY_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        if version_gte "$PY_VER" "$PYTHON_MIN_MAJOR" "$PYTHON_MIN_MINOR"; then
            ok "Python $PY_VER found ($PYTHON_CMD)"
            return
        fi
        warn "Python $PY_VER found but >= ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR} is required"
    fi

    info "Attempting to install Python …"
    install_python
}

install_python() {
    case "$OS" in
        macos)
            if command -v brew &>/dev/null; then
                brew install python@3
            else
                fail "Homebrew not found. Install it from https://brew.sh and retry, or install Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ manually."
            fi
            ;;
        linux)
            if   command -v apt-get &>/dev/null; then
                sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip python3-venv
            elif command -v dnf     &>/dev/null; then
                sudo dnf install -y python3 python3-pip
            elif command -v pacman  &>/dev/null; then
                sudo pacman -Sy --noconfirm python python-pip
            else
                fail "No supported package manager found. Install Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ manually."
            fi
            ;;
    esac

    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    else
        fail "Python installation failed. Please install Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ manually."
    fi
    ok "Python installed: $($PYTHON_CMD --version)"
}

# =============================================================================
# 4. Check / install Node.js
# =============================================================================
check_node() {
    info "Checking Node.js >= ${NODE_MIN_MAJOR} …"

    if command -v node &>/dev/null; then
        NODE_VER=$(node -v | sed 's/^v//')
        NODE_MAJOR="$(_major "$NODE_VER")"
        if [ "$NODE_MAJOR" -ge "$NODE_MIN_MAJOR" ]; then
            ok "Node.js v${NODE_VER} found"
            return
        fi
        warn "Node.js v${NODE_VER} found but >= ${NODE_MIN_MAJOR} is required"
    fi

    info "Attempting to install Node.js …"
    install_node
}

install_node() {
    case "$OS" in
        macos)
            if command -v brew &>/dev/null; then
                brew install node
            else
                fail "Homebrew not found. Install it from https://brew.sh and retry, or install Node.js ${NODE_MIN_MAJOR}+ manually."
            fi
            ;;
        linux)
            if   command -v apt-get &>/dev/null; then
                sudo apt-get update -qq && sudo apt-get install -y nodejs npm
            elif command -v dnf     &>/dev/null; then
                sudo dnf install -y nodejs npm
            elif command -v pacman  &>/dev/null; then
                sudo pacman -Sy --noconfirm nodejs npm
            else
                fail "No supported package manager found. Install Node.js ${NODE_MIN_MAJOR}+ manually."
            fi
            ;;
    esac

    if ! command -v node &>/dev/null; then
        fail "Node.js installation failed. Please install Node.js ${NODE_MIN_MAJOR}+ manually."
    fi
    ok "Node.js installed: $(node -v)"
}

# =============================================================================
# 5a. Remove packages that were replaced (to avoid import conflicts)
#     Add entries to STALE_PACKAGES when swapping a dependency.
#     e.g. python-jose was replaced by PyJWT.
# =============================================================================
STALE_PACKAGES=("python-jose")

cleanup_stale_packages() {
    local venv_pip="${PROJECT_ROOT}/backend/venv/bin/pip"
    for pkg in "${STALE_PACKAGES[@]}"; do
        if "$venv_pip" show "$pkg" &>/dev/null; then
            warn "Removing stale package: $pkg"
            "$venv_pip" uninstall -y "$pkg" --quiet
        fi
    done
}

# =============================================================================
# 5b. Set up backend — Python venv + pip install + .env
# =============================================================================
setup_backend() {
    info "Setting up backend …"
    local backend_dir="${PROJECT_ROOT}/backend"
    local venv_dir="${backend_dir}/venv"

    # Create virtual environment
    if [ ! -d "$venv_dir" ]; then
        info "Creating Python virtual environment …"
        "$PYTHON_CMD" -m venv "$venv_dir"
        ok "Virtual environment created at backend/venv"
    else
        ok "Virtual environment already exists — skipping creation"
    fi

    # Upgrade pip silently
    info "Upgrading pip …"
    "${venv_dir}/bin/pip" install --quiet --upgrade pip

    # Install project dependencies (including [dev] extras for pytest/ruff)
    info "Installing backend dependencies …"
    "${venv_dir}/bin/pip" install --quiet -e "${backend_dir}[dev]"
    ok "Backend dependencies installed"

    # Remove any packages replaced by newer alternatives
    cleanup_stale_packages

    # Generate .env from .env.example when no .env exists yet
    if [ ! -f "${backend_dir}/.env" ]; then
        if [ -f "${backend_dir}/.env.example" ]; then
            info "Copying .env.example → backend/.env …"
            cp "${backend_dir}/.env.example" "${backend_dir}/.env"
            ok "Created backend/.env — please fill in your secrets before use"
        else
            # Fallback: write a minimal template inline
            info "Creating backend/.env from built-in template …"
            cat > "${backend_dir}/.env" <<'ENVFILE'
# ── Emoji Showcase — Backend Configuration ──────────────────────────────────
# Generate a secure key:
#   python3 -c "import secrets; print(secrets.token_urlsafe(32))"

SECRET_KEY=change-me-to-a-random-secret
OAUTH_STATE_SECRET=change-me-to-another-random-secret

# Google OAuth2 (optional — required for Google sign-in)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/oauth/google/callback
FRONTEND_URL=http://localhost:5173

# MailerSend (optional — required for password-reset emails)
MAILERSEND_API_KEY=
MAIL_FROM=
ENVFILE
            ok "Created backend/.env — please update the secrets before production use"
        fi
    else
        ok "backend/.env already exists — skipping"
    fi
}

# =============================================================================
# 6. Set up frontend — npm install
# =============================================================================
setup_frontend() {
    info "Setting up frontend …"
    local frontend_dir="${PROJECT_ROOT}/frontend"

    if ! command -v npm &>/dev/null; then
        fail "npm not found. It should have been installed with Node.js."
    fi

    info "Installing frontend dependencies …"
    (cd "$frontend_dir" && npm install --silent)
    ok "Frontend dependencies installed"
}

# =============================================================================
# 7. Verify the installation
# =============================================================================
verify() {
    info "Verifying installation …"
    local all_ok=true

    # ── Backend ──────────────────────────────────────────────────────────────
    if $DO_BACKEND; then
        local venv_python="${PROJECT_ROOT}/backend/venv/bin/python"

        # Core packages required at runtime (redis is optional — skip it here)
        if "$venv_python" -c \
            "import fastapi, sqlmodel, bcrypt, jwt, uvicorn, authlib" \
            2>/dev/null; then
            ok "Backend Python packages verified"
        else
            warn "Some backend packages failed to import — re-run or check the error above"
            all_ok=false
        fi
    fi

    # ── Frontend ─────────────────────────────────────────────────────────────
    if $DO_FRONTEND; then
        if [ -d "${PROJECT_ROOT}/frontend/node_modules/vue" ]; then
            ok "Frontend node_modules verified"
        else
            warn "Frontend node_modules missing or incomplete"
            all_ok=false
        fi
    fi

    # ── Summary ──────────────────────────────────────────────────────────────
    echo ""
    if $all_ok; then
        printf "${GREEN}%s${NC}\n" "══════════════════════════════════════════════════════"
        printf "${GREEN}%s${NC}\n" "  ✅  Setup complete! All dependencies are installed."
        printf "${GREEN}%s${NC}\n" "══════════════════════════════════════════════════════"
        echo ""
        info "Next steps:"
        echo "  1. Edit  backend/.env  and fill in your secrets"
        echo "  2. Start both servers:    make run-bg"
        echo "  3. Or start individually:"
        echo "       make backend      # API at http://localhost:8000"
        echo "       make frontend     # UI  at http://localhost:5173"
        echo "  4. Run tests:   make backend-test"
        echo "  5. Lint:        make lint"
    else
        warn "Setup completed with warnings — review the messages above."
    fi
    echo ""
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    printf "${CYAN}%s${NC}\n" "🎨 Emoji Showcase Platform — Dependency Setup"
    printf "${CYAN}%s${NC}\n" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    detect_os

    if $DO_BACKEND;  then check_python; fi
    if $DO_FRONTEND; then check_node;   fi
    if $DO_BACKEND;  then setup_backend;  fi
    if $DO_FRONTEND; then setup_frontend; fi

    verify
}

main "$@"
