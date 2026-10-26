#!/usr/bin/env python3
"""
tests/test_webcam_patch.py
Automated regression tests for the Keychain Camera Plus (Kodak Charmera) UVC Webcam patch.
"""

import sys
import hashlib
from pathlib import Path
import pytest
import capstone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STOCK_FW_PATH = PROJECT_ROOT / "dumps" / "charmera_stock_latest.bin"
EXPECTED_STOCK_SHA256 = "cc3b4b2fd7eb71ba5a441decdc86984261fac8418ee3e105d7e2b3c38b7ea42f"

PATCH_OFFSET = 0x022124
ORIGINAL_BYTES = b"\x03\x00\x00\x1a"  # bne #0x22138
PATCHED_BYTES = b"\x00\x00\xa0\xe1"   # mov r0, r0 / nop
WATCHDOG_OFFSET = 0x006D10
WATCHDOG_SAFE_BYTES = b"\xe8\x69\x00\x00"  # Factory 0x000069E8 exit stub

def test_stock_firmware_integrity():
    """Verify stock firmware hash against the known hardware reference dump."""
    if not STOCK_FW_PATH.exists():
        pytest.skip(f"Stock firmware not present at {STOCK_FW_PATH} (may be skipped in external CI)")
    
    data = STOCK_FW_PATH.read_bytes()
    assert len(data) == 2 * 1024 * 1024, f"Stock firmware size must be 2 MiB, got {len(data)}"
    assert hashlib.sha256(data).hexdigest() == EXPECTED_STOCK_SHA256, "Stock SHA-256 mismatch!"

def test_watchdog_loop_prevention_at_0x006d10():
    """Ensure experimental 0x006D10 patch is NOT present, preventing 3.5s WDT reboot loop."""
    if not STOCK_FW_PATH.exists():
        pytest.skip("Stock firmware not present")
        
    data = STOCK_FW_PATH.read_bytes()
    cur_bytes = data[WATCHDOG_OFFSET:WATCHDOG_OFFSET + 4]
    assert cur_bytes == WATCHDOG_SAFE_BYTES, (
        f"CRITICAL: Address 0x006D10 must remain factory safe {WATCHDOG_SAFE_BYTES.hex()}, "
        f"got {cur_bytes.hex()}. Modifying this triggers a 100% CPU WDT reboot loop!"
    )

def test_uvc_webcam_patch_logic():
    """Verify webcam patch modifies strictly the target instruction and disassembles to mov r0, r0."""
    if not STOCK_FW_PATH.exists():
        pytest.skip("Stock firmware not present")

    stock_data = bytearray(STOCK_FW_PATH.read_bytes())
    assert stock_data[PATCH_OFFSET:PATCH_OFFSET + 4] == ORIGINAL_BYTES, (
        f"Original instruction mismatch at 0x{PATCH_OFFSET:06X}"
    )

    # Apply patch
    patched_data = bytearray(stock_data)
    patched_data[PATCH_OFFSET:PATCH_OFFSET + 4] = PATCHED_BYTES

    # Check byte differences
    diffs = [i for i in range(len(stock_data)) if patched_data[i] != stock_data[i]]
    assert len(diffs) == 3, f"Expected exactly 3 modified bytes, got {len(diffs)}: {diffs}"
    assert all(PATCH_OFFSET <= i < PATCH_OFFSET + 4 for i in diffs), (
        f"Diff leaked outside patch range! Diffs at: {diffs}"
    )

    # Disassembly verification with Capstone
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    disasm = list(md.disasm(bytes(patched_data[PATCH_OFFSET:PATCH_OFFSET + 4]), PATCH_OFFSET))
    assert len(disasm) == 1, "Expected single 32-bit ARM instruction"
    insn = disasm[0]
    assert insn.mnemonic == "mov"
    assert insn.op_str == "r0, r0", f"Expected 'mov r0, r0', got '{insn.op_str}'"
