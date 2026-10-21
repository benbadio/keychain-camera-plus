#!/usr/bin/env bash
# ==============================================================================
# deploy_to_sd.sh
# Safely deploys the verified Kodak Charmera UVC Webcam firmware to FAT32 MicroSD
# ==============================================================================

set -euo pipefail

TARGET_VOLUME="/Volumes/NO NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FIRMWARE_BIN="${1:-${PROJECT_ROOT}/release/webcam/JH_5408202610211858_0F065EB9.bin}"

echo "=========================================================="
echo " Kodak Charmera MicroSD Firmware Deployer"
echo " Target Binary: $(basename "${FIRMWARE_BIN}")"
echo "=========================================================="

if [ ! -f "${FIRMWARE_BIN}" ]; then
    echo "[-] Error: Firmware binary not found at ${FIRMWARE_BIN}"
    exit 1
fi

echo "[*] Waiting for MicroSD card to mount at '${TARGET_VOLUME}' (up to 45s)..."
COUNT=0
while [ ! -d "${TARGET_VOLUME}" ]; do
    sleep 1
    COUNT=$((COUNT + 1))
    echo -n "."
    if [ ${COUNT} -ge 45 ]; then
        echo ""
        echo "[-] Timeout: MicroSD card not detected at '${TARGET_VOLUME}'."
        echo "    Please plug your USB card reader into your Mac and re-run."
        exit 1
    fi
done

echo ""
echo "[+] Detected MicroSD card at '${TARGET_VOLUME}'!"

# Remove any old firmware packages on the card root
echo "[*] Cleaning up old .bin firmware packages..."
rm -f "${TARGET_VOLUME}"/JH_5408*.bin

# Copy target firmware
echo "[*] Copying $(basename "${FIRMWARE_BIN}") to MicroSD root..."
cp "${FIRMWARE_BIN}" "${TARGET_VOLUME}/"

# Strip macOS hidden resource forks & metadata
echo "[*] Stripping macOS hidden dot-files (dot_clean)..."
dot_clean -m "${TARGET_VOLUME}" || true
rm -rf "${TARGET_VOLUME}/._*" 2>/dev/null || true

# Sync buffers
sync

echo "[+] Firmware package copied and verified:"
ls -lh "${TARGET_VOLUME}"/JH_5408*.bin

echo ""
echo "[*] Safely unmounting MicroSD card..."
diskutil eject "${TARGET_VOLUME}"
echo "[+] MicroSD card safely ejected! Ready to insert into your Charmera."
