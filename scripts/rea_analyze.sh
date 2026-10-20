#!/usr/bin/env bash
# ==============================================================================
# rea_analyze.sh
# Performs region analysis and extraction on Kodak Charmera firmware using Binwalk & REA
# ==============================================================================

set -euo pipefail

FIRMWARE="${1:-}"
if [ -z "${FIRMWARE}" ] || [ ! -f "${FIRMWARE}" ]; then
    echo "Usage: $0 <path_to_firmware.bin>"
    exit 1
fi

BINWALK_CMD="$(which binwalk || echo /opt/homebrew/bin/binwalk)"
OUTPUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/extracted_fw"
VENV_PYTHON="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.venv/bin/python3"
TOOL_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/firmware_asset_tool.py"

mkdir -p "${OUTPUT_DIR}"

echo "=========================================================="
echo "Analyzing Kodak Charmera Firmware: ${FIRMWARE}"
echo "Using Binwalk: ${BINWALK_CMD}"
echo "Output Directory: ${OUTPUT_DIR}"
echo "=========================================================="

echo -e "\n[1/3] Running Binwalk signature scan..."
"${BINWALK_CMD}" "${FIRMWARE}"

echo -e "\n[2/3] Running REA-compatible Asset Extraction..."
"${VENV_PYTHON}" "${TOOL_PY}" extract "${FIRMWARE}" "${OUTPUT_DIR}"

echo -e "\n[3/3] Inspecting notable strings and boot parameters..."
"${VENV_PYTHON}" "${TOOL_PY}" inspect "${FIRMWARE}"

echo "=========================================================="
echo "Analysis complete! Check ${OUTPUT_DIR} for extracted assets."
echo "=========================================================="
