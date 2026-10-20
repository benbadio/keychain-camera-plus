#!/usr/bin/env bash
# ==============================================================================
# diagnose_flash.sh
# Reads current SPI flash from Charmera and compares against reference images.
# NEVER overwrites charmera_stock_latest.bin!
# ==============================================================================

set -euo pipefail

PROGRAMMER="ch341a_spi"
CHIP="SFDP-capable chip"
OUTPUT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/dumps"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DUMP_FILE="${OUTPUT_DIR}/diagnose_${TIMESTAMP}.bin"

echo "=========================================================="
echo "Kodak Charmera Flash Diagnostic"
echo "Programmer : ${PROGRAMMER}"
echo "Chip       : ${CHIP}"
echo "Dump target: ${DUMP_FILE}"
echo "=========================================================="

echo "[1/2] Reading current flash contents..."
flashrom -p "${PROGRAMMER}" -c "${CHIP}" -r "${DUMP_FILE}"

echo "[2/2] Comparing against reference binaries..."
SIZE=$(stat -f%z "${DUMP_FILE}")
SHA=$(shasum -a 256 "${DUMP_FILE}" | awk '{print $1}')
echo "Dump Size: ${SIZE} bytes"
echo "SHA-256  : ${SHA}"

python3 - << PYEOF
with open("${DUMP_FILE}", "rb") as f:
    dump = f.read()

import glob
for ref_path in sorted(glob.glob("${OUTPUT_DIR}/*.bin")):
    if "diagnose" in ref_path or "temp" in ref_path:
        continue
    with open(ref_path, "rb") as f:
        ref = f.read()
    if len(dump) != len(ref):
        continue
    diffs = sum(1 for a, b in zip(dump, ref) if a != b)
    print(f"  vs {ref_path.split('/')[-1]}: {diffs} different bytes")
    if diffs == 0:
        print(f"    ===> EXACT 100% BIT-FOR-BIT MATCH!")
PYEOF
echo "=========================================================="
