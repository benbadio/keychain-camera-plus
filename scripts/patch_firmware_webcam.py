#!/usr/bin/env python3
"""
patch_firmware_webcam.py
Patches the Kodak Charmera (Generalplus GPCV1235F/CBB3) stock firmware to enable
USB Video Class (UVC) Webcam mode instead of Mass Storage when connected via USB.

Patch location:
  Address: 0x022124
  Original instruction: 03 00 00 1A (bne #0x22138 -> branches to U_DISK.GPZ)
  Patched instruction:  00 00 A0 E1 (mov r0, r0 / nop -> falls through to PC_CAM.GPZ)
"""

import sys
import hashlib
from pathlib import Path
import capstone

STOCK_FW_PATH = Path(__file__).resolve().parent.parent / "dumps" / "charmera_stock_latest.bin"
OUTPUT_FW_PATH = Path(__file__).resolve().parent.parent / "dumps" / "charmera_webcam.bin"

EXPECTED_STOCK_SHA256 = "cc3b4b2fd7eb71ba5a441decdc86984261fac8418ee3e105d7e2b3c38b7ea42f"
EXPECTED_SIZE = 2 * 1024 * 1024  # 2,097,152 bytes

PATCH_OFFSET = 0x022124
ORIGINAL_BYTES = b"\x03\x00\x00\x1a"  # bne #0x22138
PATCHED_BYTES = b"\x00\x00\xa0\xe1"   # nop (mov r0, r0)

def main():
    print(f"[*] Reading stock firmware: {STOCK_FW_PATH}")
    if not STOCK_FW_PATH.exists():
        print(f"[-] Error: File not found: {STOCK_FW_PATH}")
        sys.exit(1)

    data = bytearray(STOCK_FW_PATH.read_bytes())
    
    # 1. Size verification
    if len(data) != EXPECTED_SIZE:
        print(f"[-] Error: Unexpected size {len(data)}, expected {EXPECTED_SIZE}")
        sys.exit(1)
    print(f"[+] Firmware size verified: {len(data):,} bytes")

    # 2. SHA-256 verification
    stock_hash = hashlib.sha256(data).hexdigest()
    print(f"[*] Stock SHA-256: {stock_hash}")
    if stock_hash != EXPECTED_STOCK_SHA256:
        print(f"[-] Warning: Stock SHA-256 does not match known reference {EXPECTED_STOCK_SHA256}")
        # Allow proceeding only if original bytes at offset match
    else:
        print("[+] Stock SHA-256 verified against reference dump.")

    # 3. Check target bytes
    current_bytes = bytes(data[PATCH_OFFSET:PATCH_OFFSET + 4])
    if current_bytes != ORIGINAL_BYTES:
        print(f"[-] Error: Unexpected bytes at 0x{PATCH_OFFSET:06X}: {current_bytes.hex()}, expected {ORIGINAL_BYTES.hex()}")
        sys.exit(1)
    print(f"[+] Found original instruction at 0x{PATCH_OFFSET:06X}: {current_bytes.hex()}")

    # 4. Apply patch
    data[PATCH_OFFSET:PATCH_OFFSET + 4] = PATCHED_BYTES
    print(f"[+] Patched 0x{PATCH_OFFSET:06X} -> {PATCHED_BYTES.hex()}")

    # 5. Verify byte diff strictly falls within the 4-byte patch range
    original_data = STOCK_FW_PATH.read_bytes()
    diffs = [i for i in range(len(data)) if data[i] != original_data[i]]
    if not all(PATCH_OFFSET <= i < PATCH_OFFSET + 4 for i in diffs) or len(diffs) == 0:
        print(f"[-] Error: Diff anomaly detected! Changed indices: {diffs}")
        sys.exit(1)
    print(f"[+] Byte diff verification passed: changed bytes strictly within 0x{PATCH_OFFSET:06X}-0x{PATCH_OFFSET+3:06X} (modified {len(diffs)} bytes).")

    # 6. Disassemble patched context
    print("\n=== Disassembly Verification (0x022118 - 0x022148) ===")
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    verify_start = 0x022118
    verify_end = 0x022148
    for insn in md.disasm(data[verify_start:verify_end], verify_start):
        marker = "===> [PATCHED]" if insn.address == PATCH_OFFSET else "              "
        print(f"{marker} 0x{insn.address:06X}: {insn.bytes.hex():<10} {insn.mnemonic:<8} {insn.op_str}")

    # 7. Write output file
    OUTPUT_FW_PATH.write_bytes(data)
    patched_hash = hashlib.sha256(data).hexdigest()
    print(f"\n[+] Wrote patched firmware: {OUTPUT_FW_PATH}")
    print(f"[+] Patched firmware SHA-256: {patched_hash}")
    print("[+] Ready for flashing!")

if __name__ == "__main__":
    main()
