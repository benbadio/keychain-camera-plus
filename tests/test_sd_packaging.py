#!/usr/bin/env python3
"""
tests/test_sd_packaging.py
Automated regression tests for the Keychain Camera Plus MicroSD packaging tool and bootloader validator.
"""

import sys
import tempfile
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from pack_sd_firmware import (
    SAFE_BLOCK_COUNT,
    SAFE_BYTE_SIZE,
    STOCK_TIMESTAMP,
    calculate_checksum,
    generate_sd_filename,
    verify_filename_offsets,
    pack_firmware
)

def test_30_block_trimming_constants():
    """Verify safe 30-block constants prevent SPI NOR 21-bit address wraparound erase."""
    assert SAFE_BLOCK_COUNT == 30
    assert SAFE_BYTE_SIZE == 30 * 65536  # 1,966,080 bytes / 0x1E0000

    # Bootloader routine 0x0217B4 formula: target_erase_block = file_end_block + 0x10000
    erase_target = SAFE_BYTE_SIZE + 0x10000
    assert erase_target == 0x1F0000  # Block 31 (safe empty padding block)
    assert (erase_target & 0x1FFFFF) != 0x010000  # CANNOT equal Block 1!

def test_checksum_calculation():
    """Verify 32-bit unsigned cumulative byte sum."""
    test_data = b"\x01\x02\x03\x04"
    assert calculate_checksum(test_data) == 10

    # Test overflow wraps at 32 bits
    overflow_data = b"\xFF" * 17000000
    chk = calculate_checksum(overflow_data)
    assert 0 <= chk <= 0xFFFFFFFF

def test_bootloader_filename_schema():
    """Verify filename adheres to Generalplus bootloader parsing logic (0x0213B0-0x0214C0)."""
    valid_name, chk = generate_sd_filename(b"\x00" * 100, timestamp="202610261200")
    assert valid_name == "JH_5408202610261200_00000000.bin"
    verify_filename_offsets(valid_name)

    # Invalid timestamp (must be 12 digits)
    with pytest.raises(ValueError):
        generate_sd_filename(b"\x00", timestamp="2026")

    # Invalid stock timestamp (bootloader ignores update if timestamp == stock)
    with pytest.raises(AssertionError):
        verify_filename_offsets(f"JH_5408{STOCK_TIMESTAMP}_00000000.bin")

    # Invalid prefix
    with pytest.raises(AssertionError):
        verify_filename_offsets("FW_5408202610261200_00000000.bin")

def test_pack_firmware_safe_trimming():
    """Verify pack_firmware trims 2 MiB image with 0xFF padding down to 30 blocks."""
    # Create synthetic 2 MiB binary with 0xFF in tail blocks
    synthetic_fw = bytearray(b"\xAA" * SAFE_BYTE_SIZE + b"\xFF" * (2 * 1024 * 1024 - SAFE_BYTE_SIZE))
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test_fw.bin"
        input_file.write_bytes(synthetic_fw)
        
        output_dir = Path(tmpdir) / "output"
        packed_file_path = pack_firmware(str(input_file), str(output_dir), timestamp="202610261400")
        
        packed_data = Path(packed_file_path).read_bytes()
        assert len(packed_data) == SAFE_BYTE_SIZE
        assert Path(packed_file_path).name == "JH_5408202610261400_13EC0000.bin"
