#!/usr/bin/env bash
# ==============================================================================
# CARINA .deb Installer Builder
# Builds a self-contained .deb package using Docker as a sterile environment.
#
# Usage:
#   chmod +x build_installer.sh
#   ./build_installer.sh
#
# Output:
#   ./dist/carina_1.0.0_amd64.deb
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="carina-builder"
DEB_NAME="carina_1.0.0_amd64.deb"
OUTPUT_DIR="${SCRIPT_DIR}/dist"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║       CARINA .deb Installer Builder                 ║"
echo "║       Docker + PyInstaller + dpkg-deb               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[0/4] Pre-flight checks...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker não encontrado. Instale com: sudo apt install docker.io${NC}"
    exit 1
fi

if ! docker info &> /dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker daemon não está rodando ou sem permissão.${NC}"
    echo -e "${YELLOW}Tente: sudo systemctl start docker${NC}"
    echo -e "${YELLOW}   ou: sudo usermod -aG docker \$USER (e re-faça login)${NC}"
    exit 1
fi

# Check required files
for f in carina.py carina.spec build-requirements.txt Dockerfile.build; do
    if [ ! -f "${SCRIPT_DIR}/${f}" ]; then
        echo -e "${RED}ERROR: Arquivo necessário não encontrado: ${f}${NC}"
        exit 1
    fi
done

for d in src proto ui config debian Model_Vault; do
    if [ ! -d "${SCRIPT_DIR}/${d}" ]; then
        echo -e "${RED}ERROR: Diretório necessário não encontrado: ${d}/${NC}"
        exit 1
    fi
done

echo -e "${GREEN}  ✓ Docker disponível${NC}"
echo -e "${GREEN}  ✓ Todos os arquivos e diretórios necessários presentes${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Build Docker image
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[1/4] Construindo imagem Docker (isso pode levar 15-30 min na primeira vez)...${NC}"
echo ""

docker build \
    -f "${SCRIPT_DIR}/Dockerfile.build" \
    -t "${IMAGE_NAME}" \
    "${SCRIPT_DIR}"

echo ""
echo -e "${GREEN}  ✓ Imagem Docker construída com sucesso${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Run container and extract .deb
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/4] Extraindo .deb do container...${NC}"

mkdir -p "${OUTPUT_DIR}"

docker run --rm \
    -v "${OUTPUT_DIR}:/output" \
    "${IMAGE_NAME}"

echo -e "${GREEN}  ✓ .deb extraído para ${OUTPUT_DIR}/${DEB_NAME}${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Verify .deb
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/4] Verificando o pacote .deb...${NC}"

DEB_PATH="${OUTPUT_DIR}/${DEB_NAME}"

if [ ! -f "${DEB_PATH}" ]; then
    echo -e "${RED}ERROR: .deb não foi gerado em ${DEB_PATH}${NC}"
    exit 1
fi

# Size
DEB_SIZE=$(du -sh "${DEB_PATH}" | cut -f1)
echo -e "  Tamanho: ${CYAN}${DEB_SIZE}${NC}"

# Package info
echo ""
echo -e "  ${CYAN}--- Informações do Pacote ---${NC}"
dpkg-deb --info "${DEB_PATH}" 2>/dev/null || true

# Verify key files exist in the .deb
echo ""
echo -e "  ${CYAN}--- Verificação de Arquivos Críticos ---${NC}"

CRITICAL_PATHS=(
    "./opt/carina/carina"
    "./usr/share/applications/carina.desktop"
    "./usr/share/icons/hicolor/256x256/apps/carina.png"
    "./usr/local/bin/carina"
)

ALL_OK=true
for cpath in "${CRITICAL_PATHS[@]}"; do
    if dpkg-deb --contents "${DEB_PATH}" 2>/dev/null | grep -q "${cpath}"; then
        echo -e "    ${GREEN}✓${NC} ${cpath}"
    else
        echo -e "    ${RED}✗ MISSING: ${cpath}${NC}"
        ALL_OK=false
    fi
done

# Verify no NVIDIA kernel drivers (CUDA runtime libs are OK)
if dpkg-deb --contents "${DEB_PATH}" 2>/dev/null | grep -qi "nvidia-driver\|nvidia.*\.ko"; then
    echo -e "    ${RED}✗ WARNING: NVIDIA kernel drivers found in .deb!${NC}"
else
    echo -e "    ${GREEN}✓${NC} No NVIDIA kernel drivers (CUDA runtime libs present — OK)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[4/4] Resultado${NC}"
echo ""

if [ "${ALL_OK}" = true ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  BUILD CONCLUÍDO COM SUCESSO!                       ║${NC}"
    echo -e "${GREEN}║                                                     ║${NC}"
    echo -e "${GREEN}║  Pacote: ${DEB_PATH}${NC}"
    echo -e "${GREEN}║  Tamanho: ${DEB_SIZE}${NC}"
    echo -e "${GREEN}║                                                     ║${NC}"
    echo -e "${GREEN}║  Instalar:                                          ║${NC}"
    echo -e "${GREEN}║    sudo dpkg -i ${DEB_PATH}${NC}"
    echo -e "${GREEN}║                                                     ║${NC}"
    echo -e "${GREEN}║  Desinstalar:                                       ║${NC}"
    echo -e "${GREEN}║    sudo dpkg -r carina                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  BUILD COM AVISOS — verifique os erros acima        ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
