#!/usr/bin/env python3
"""
scripts/build_release.py
Automated release builder for Keychain Camera Plus (Kodak Charmera).
Builds the safe 30-block UVC Webcam SD update package, generates SHA256 checksums,
and bundles the distribution ZIP archive for GitHub Releases.
"""

import os
import sys
import argparse
import base64
import hashlib
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from pack_sd_firmware import pack_firmware

PATCH_UVC_MODE_OFFSET = 0x022124
ORIGINAL_UVC_MODE_BYTES = b"\x03\x00\x00\x1a"  # bne #0x22138
PATCHED_UVC_MODE_BYTES = b"\x00\x00\xa0\xe1"   # nop (mov r0, r0)
EXPECTED_STOCK_SHA256 = "cc3b4b2fd7eb71ba5a441decdc86984261fac8418ee3e105d7e2b3c38b7ea42f"

def get_or_restore_stock_rom(stock_path: Path) -> Path:
    if stock_path.exists():
        return stock_path
        
    b64_data = os.environ.get("STOCK_ROM_BASE64")
    if b64_data:
        print("[*] Reconstructing stock firmware from STOCK_ROM_BASE64 secret...")
        stock_path.parent.mkdir(parents=True, exist_ok=True)
        raw_bytes = base64.b64decode(b64_data)
        if hashlib.sha256(raw_bytes).hexdigest() != EXPECTED_STOCK_SHA256:
            raise ValueError("Reconstructed stock ROM SHA-256 does not match reference!")
        stock_path.write_bytes(raw_bytes)
        print(f"[+] Reconstructed stock ROM successfully at {stock_path}")
        return stock_path
        
    raise FileNotFoundError(
        f"Stock ROM not found at {stock_path} and STOCK_ROM_BASE64 environment variable not set."
    )

def patch_webcam(stock_path: Path, output_path: Path) -> Path:
    print(f"[*] Applying UVC Webcam patch to {stock_path}...")
    data = bytearray(stock_path.read_bytes())
    if len(data) != 2 * 1024 * 1024:
        raise ValueError(f"Invalid ROM size: {len(data)}")
        
    cur_bytes = bytes(data[PATCH_UVC_MODE_OFFSET:PATCH_UVC_MODE_OFFSET + 4])
    if cur_bytes != ORIGINAL_UVC_MODE_BYTES:
        raise ValueError(f"Unexpected bytes at 0x{PATCH_UVC_MODE_OFFSET:06X}: {cur_bytes.hex()}")
        
    data[PATCH_UVC_MODE_OFFSET:PATCH_UVC_MODE_OFFSET + 4] = PATCHED_UVC_MODE_BYTES
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    print(f"[+] Patched webcam image written to {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Keychain Camera Plus Release Builder")
    parser.add_argument("--stock", default=str(PROJECT_ROOT / "dumps" / "charmera_stock_latest.bin"))
    parser.add_argument("--outdir", default=str(PROJECT_ROOT / "dist"))
    parser.add_argument("--tag", default=os.environ.get("RELEASE_TAG", "v1.0.0"))
    parser.add_argument("--timestamp", default=None, help="12-digit build timestamp YYYYMMDDhhmm")
    args = parser.parse_args()

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stock_path = Path(args.stock)
    if stock_path.exists():
        # 1. Patch firmware
        temp_patched = out_dir / "charmera_webcam.bin"
        patch_webcam(stock_path, temp_patched)

        # 2. Package SD card update (30 blocks safe trimming)
        sd_bin_path = Path(pack_firmware(str(temp_patched), str(out_dir), timestamp=args.timestamp))
        sd_bin_name = sd_bin_path.name
        print(f"[+] Generated SD package from stock ROM: {sd_bin_path}")
        if temp_patched.exists():
            temp_patched.unlink()
    else:
        # Fallback to pre-packaged verified binary in release/webcam/
        release_webcam_dir = PROJECT_ROOT / "release" / "webcam"
        candidates = list(release_webcam_dir.glob("JH_5408*.bin"))
        if not candidates:
            raise FileNotFoundError(
                f"Neither stock ROM at {stock_path} nor pre-packaged release binary at {release_webcam_dir} found!"
            )
        candidate = sorted(candidates)[-1]
        print(f"[*] Stock ROM not present; using verified release package: {candidate.name}")
        from pack_sd_firmware import SAFE_BYTE_SIZE, verify_filename_offsets
        verify_filename_offsets(candidate.name)
        candidate_data = candidate.read_bytes()
        if len(candidate_data) != SAFE_BYTE_SIZE:
            raise ValueError(f"Candidate binary size {len(candidate_data)} does not match safe 30 blocks ({SAFE_BYTE_SIZE})")
        sd_bin_path = out_dir / candidate.name
        sd_bin_path.write_bytes(candidate_data)
        sd_bin_name = sd_bin_path.name
        print(f"[+] Verified and staged SD package: {sd_bin_path}")

    # 3. Create QUICKSTART.md in outdir
    quickstart_content = f"""# Keychain Camera Plus Quickstart 📸✨
Version: {args.tag}
File: {sd_bin_name}

## ⚡ 3-Step Zero-Hardware Upgrade

1. **Format MicroSD Card**:
   - Format a MicroSD card as **FAT32** (MBR).
   - Ensure the card is empty.

2. **Copy Firmware**:
   - Copy `{sd_bin_name}` directly to the **ROOT** of your MicroSD card.
   - *Do NOT rename the file (the camera bootloader verifies the filename checksum).*
   - Safely eject the card from your computer.

3. **In-Camera Upgrade**:
   - Insert the MicroSD card into the Kodak Charmera and turn it **ON**.
   - Watch the screen display `Upgrade 0%` -> `100%`.
   - When the upgrade reaches 100%, **eject the card**, then **manually power off the camera** by pressing and holding the Power button.
   - Turn the camera back **ON** and plug it into your Mac or PC via USB-C.
   - Open Photo Booth, QuickTime, Zoom, or FaceTime and select `GENERAL- UVC`!

*(Standalone photo and video shooting on battery remains 100% functional when unplugged!)*
"""
    quickstart_path = out_dir / "QUICKSTART.md"
    quickstart_path.write_text(quickstart_content)

    # 4. Generate SHA256SUMS.txt
    bin_sha = hashlib.sha256(sd_bin_path.read_bytes()).hexdigest()
    sums_path = out_dir / "SHA256SUMS.txt"
    sums_path.write_text(f"{bin_sha}  {sd_bin_name}\n")
    print(f"[+] Generated SHA256SUMS.txt ({bin_sha[:16]}...)")

    # 5. Bundle ZIP distribution
    clean_tag = args.tag.lstrip("v")
    zip_name = f"keychain-camera-plus-v{clean_tag}.zip"
    zip_path = out_dir / zip_name
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(sd_bin_path, arcname=sd_bin_name)
        z.write(quickstart_path, arcname="QUICKSTART.md")
        z.write(sums_path, arcname="SHA256SUMS.txt")
        
    print(f"\n==========================================================")
    print(f" [+] Release Bundle Successfully Created!")
    print(f"==========================================================")
    print(f" ZIP:        {zip_path} ({zip_path.stat().st_size:,} bytes)")
    print(f" BIN:        {sd_bin_path} ({sd_bin_path.stat().st_size:,} bytes)")
    print(f" SHA-256:    {bin_sha}")
    print(f" QUICKSTART: {quickstart_path}")

    # Remove temporary unpadded patched file
    if temp_patched.exists():
        temp_patched.unlink()

if __name__ == "__main__":
    main()
