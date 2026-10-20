#!/usr/bin/env bash
# ==============================================================================
# dump_firmware.sh
# Safely dumps SPI NOR Flash from the Kodak Charmera via flashrom (CH341A programmer)
# Performs two consecutive reads and verifies checksum match before proceeding.
# ==============================================================================

set -euo pipefail

PROGRAMMER="${1:-ch341a_spi}"
CHIP="${2:-}"
OUTPUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/dumps"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_FILE="${OUTPUT_DIR}/charmera_stock_${TIMESTAMP}.bin"

mkdir -p "${OUTPUT_DIR}"

echo "=========================================================="
echo "Kodak Charmera Firmware Dumper"
echo "Programmer : ${PROGRAMMER}"
if [ -n "${CHIP}" ]; then
  echo "Target Chip: ${CHIP}"
  CHIP_ARG=(-c "${CHIP}")
else
  echo "Target Chip: Auto-detect"
  CHIP_ARG=()
fi
echo "Output Path: ${TARGET_FILE}"
echo "=========================================================="

DUMP1="${OUTPUT_DIR}/temp_read1.bin"
DUMP2="${OUTPUT_DIR}/temp_read2.bin"

echo "[1/3] Reading flash pass 1..."
flashrom -p "${PROGRAMMER}" "${CHIP_ARG[@]}" -r "${DUMP1}"

echo "[2/3] Reading flash pass 2..."
flashrom -p "${PROGRAMMER}" "${CHIP_ARG[@]}" -r "${DUMP2}"

echo "[3/3] Verifying read integrity (diffing pass 1 and pass 2)..."
if cmp -s "${DUMP1}" "${DUMP2}"; then
    echo "✓ Checksum verification SUCCESSFUL! Both reads match bit-for-bit."
    mv "${DUMP1}" "${TARGET_FILE}"
    rm -f "${DUMP2}"
    cp "${TARGET_FILE}" "${OUTPUT_DIR}/charmera_stock_latest.bin"
    
    SHA=$(shasum -a 256 "${TARGET_FILE}" | awk '{print $1}')
    SIZE=$(stat -f%z "${TARGET_FILE}")
    echo "=========================================================="
    echo "Firmware saved successfully!"
    echo "Path   : ${TARGET_FILE}"
    echo "Size   : ${SIZE} bytes"
    echo "SHA-256: ${SHA}"
    echo "Latest symlink/copy: ${OUTPUT_DIR}/charmera_stock_latest.bin"
    echo "=========================================================="
else
    echo "✗ ERROR: Read 1 and Read 2 differ! Flash connection is unstable."
    echo "Please check SOIC clip alignment, pin contacts, and 3.3V power."
    exit 1
fi
