#!/usr/bin/env bash
#
# flash_custom_firmware.sh
# Safely flashes a firmware image (.bin) to the Kodak Charmera SPI flash
# via the CH341A programmer using flashrom with bit-for-bit verification.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
TARGET_IMAGE="${1:-"${PROJECT_ROOT}/dumps/charmera_webcam.bin"}"

echo "=========================================================="
echo " Kodak Charmera Firmware Flasher (CH341A / flashrom)"
echo "=========================================================="
echo "[*] Target image: ${TARGET_IMAGE}"

if [[ ! -f "${TARGET_IMAGE}" ]]; then
    echo "[-] Error: File not found: ${TARGET_IMAGE}"
    exit 1
fi

FILE_SIZE=$(wc -c < "${TARGET_IMAGE}" | tr -d ' ')
if [[ "${FILE_SIZE}" -ne 2097152 ]]; then
    echo "[-] Error: Target image is ${FILE_SIZE} bytes. Must be exactly 2,097,152 bytes (2 MiB)."
    exit 1
fi

SHA256_HASH=$(shasum -a 256 "${TARGET_IMAGE}" | awk '{print $1}')
echo "[*] Image size: ${FILE_SIZE} bytes (2 MiB)"
echo "[*] Image SHA-256: ${SHA256_HASH}"
echo ""

echo "[*] Step 1: Testing programmer and SPI flash connectivity..."
CHIP_NAME="SFDP-capable chip"
CHIP_ARG=(-c "${CHIP_NAME}")

DETECT_OUTPUT=$(flashrom -p ch341a_spi "${CHIP_ARG[@]}" 2>&1 || true)

if ! echo "${DETECT_OUTPUT}" | grep -q "SFDP-capable chip"; then
    echo "[-] Error: Could not detect SFDP-capable chip via CH341A!"
    echo "    Check that:"
    echo "      1. CH341A is firmly plugged into USB."
    echo "      2. The SOIC-8 clip is securely clamped to the flash chip."
    echo "      3. Pin 1 (red wire) is aligned with Pin 1 (dot on chip)."
    echo ""
    echo "flashrom output:"
    echo "${DETECT_OUTPUT}"
    exit 1
fi

echo "[+] Chip detected successfully: SFDP-capable chip (2048 kB, SPI)"
echo ""

echo "[*] Step 2: Writing and verifying firmware image..."
echo "    (Please DO NOT disconnect the programmer during this step!)"
echo ""

flashrom -p ch341a_spi "${CHIP_ARG[@]}" -w "${TARGET_IMAGE}"

echo ""
echo "=========================================================="
echo " [+] FLASHING AND VERIFICATION SUCCESSFUL!"
echo "=========================================================="
echo ""
echo "Next steps:"
echo " 1. Unplug the CH341A programmer from USB."
echo " 2. Carefully unclip the SOIC-8 spring clip from the camera board."
echo " 3. Connect the camera to your Mac using a USB-C cable."
echo " 4. Open Photo Booth, QuickTime, or FaceTime to test the webcam stream!"
