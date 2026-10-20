#!/usr/bin/env python3
"""
watch_and_restore_camera2.py
Continuously monitors CH341A SPI connection for Camera 2.
As soon as solid contact is made:
1. Dumps the current flash state to dumps/camera2_sd_aftermath.bin for diagnostics.
2. Analyzes which blocks were written/erased by the SD updater.
3. Automatically flashes and verifies the working charmera_webcam.bin.
"""

import os
import sys
import time
import subprocess
import hashlib

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP_PATH = os.path.join(PROJECT_ROOT, "dumps", "camera2_sd_aftermath.bin")
WEBCAM_IMG = os.path.join(PROJECT_ROOT, "dumps", "charmera_webcam.bin")
STOCK_IMG = os.path.join(PROJECT_ROOT, "dumps", "charmera_stock_latest.bin")

def probe():
    res = subprocess.run(
        ["flashrom", "-p", "ch341a_spi", "-c", "SFDP-capable chip"],
        capture_output=True,
        text=True
    )
    return "SFDP-capable chip" in res.stdout or "SFDP-capable chip" in res.stderr

def main():
    print("==========================================================")
    print(" Camera 2 Auto-Detect, Diagnostic Dump & Restore Tool")
    print("==========================================================")
    print("[*] Monitoring CH341A clip connection (timeout: 180 seconds)...")
    print("    -> Position the clip so Pin 1 (red wire) is at bottom-left")
    print("    -> Apply steady downward finger pressure directly on the clip")
    print()

    start_time = time.time()
    detected = False

    while time.time() - start_time < 180:
        if probe():
            detected = True
            break
        print(".", end="", flush=True)
        time.sleep(0.7)

    print()
    if not detected:
        print("[-] Timeout: Chip not detected yet.")
        sys.exit(1)

    print("\n[+] SUCCESS! Flash chip detected firmly on CH341A!")
    print("\n[*] Step 1: Capturing diagnostic dump of Camera 2...")
    dump_res = subprocess.run(
        ["flashrom", "-p", "ch341a_spi", "-c", "SFDP-capable chip", "-r", DUMP_PATH],
        capture_output=True,
        text=True
    )
    if dump_res.returncode != 0:
        print("[-] First read attempt had jitter. Retrying dump once...")
        dump_res = subprocess.run(
            ["flashrom", "-p", "ch341a_spi", "-c", "SFDP-capable chip", "-r", DUMP_PATH],
            capture_output=True,
            text=True
        )

    if os.path.exists(DUMP_PATH) and os.path.getsize(DUMP_PATH) == 2097152:
        with open(DUMP_PATH, "rb") as f:
            dump_data = f.read()
        sha = hashlib.sha256(dump_data).hexdigest()
        print(f"[+] Dump captured successfully! Size: 2 MiB, SHA-256: {sha}")
        
        # Analyze blocks
        print("\n[*] Block-by-Block State Analysis (64 KB blocks):")
        with open(STOCK_IMG, "rb") as f:
            stock_data = f.read()

        for b in range(32):
            start = b * 65536
            end = start + 65536
            blk_d = dump_data[start:end]
            blk_s = stock_data[start:end]
            if blk_d == blk_s:
                st = "Matches Stock"
            elif all(x == 0xFF for x in blk_d):
                st = "ERASED (All 0xFF)"
            elif all(x == 0x00 for x in blk_d):
                st = "Zeroed (All 0x00)"
            else:
                st = "Modified / Written"
            print(f"    Block {b:02d} [0x{start:06X}-0x{end:06X}]: {st}")

    print("\n[*] Step 2: Flashing working custom firmware (charmera_webcam.bin)...")
    print("    (Writing and verifying bit-for-bit, takes ~30 seconds...)")
    flash_res = subprocess.run(
        ["flashrom", "-p", "ch341a_spi", "-c", "SFDP-capable chip", "-w", WEBCAM_IMG],
        capture_output=True,
        text=True
    )
    if flash_res.returncode == 0:
        print("\n==========================================================")
        print(" [+] CAMERA 2 RESTORED & UPGRADED TO UVC WEBCAM MODE!")
        print("==========================================================")
        print("Bit-for-bit verification successful.")
        sys.exit(0)
    else:
        print("[-] Flashing failed:")
        print(flash_res.stderr or flash_res.stdout)
        sys.exit(2)

if __name__ == "__main__":
    main()
