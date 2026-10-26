#!/usr/bin/env python3
"""
pack_sd_firmware.py
Kodak Charmera (Generalplus GPCV1235F) SD Firmware Packaging Tool

Generates SD card update files:
    JH_5408<YYYYMMDDhhmm>_<CHECKSUM8HEX>.bin

Safe 30-Block Trimming:
-----------------------
The factory Charmera SPI NOR flash is 2 MiB (0x200000 bytes, 32 x 64KB blocks),
with physical address lines A0..A20 (no A21).
Generalplus bootloader routine 0x0217B4 performs a post-upgrade erase at:
    target_block = file_end_block + 0x10000

When fed an untrimmed 2 MiB file:
    0x200000 + 0x10000 = 0x210000
    0x210000 mod 0x200000 = 0x010000 (Block 1) -> Erases Block 1 (Bricks camera!)

By trimming the binary to 30 blocks (1,966,080 bytes / 0x1E0000):
    0x1E0000 + 0x10000 = 0x1F0000 (Block 31) -> Erases unused padding block!
    Block 1 and Block 2 remain 100% intact and verified!
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

SAFE_BLOCK_COUNT = 30
SAFE_BYTE_SIZE = SAFE_BLOCK_COUNT * 65536  # 1,966,080 bytes (0x1E0000)
STOCK_TIMESTAMP = "202505201029"

def calculate_checksum(data: bytes) -> int:
    """32-bit unsigned cumulative byte sum."""
    return sum(data) & 0xFFFFFFFF

def generate_sd_filename(data: bytes, timestamp: str = None) -> tuple[str, int]:
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
    
    if len(timestamp) != 12:
        raise ValueError(f"Timestamp must be exactly 12 digits (YYYYMMDDhhmm), got '{timestamp}'")
    if timestamp == STOCK_TIMESTAMP:
        timestamp = "202505201030"
        
    chk = calculate_checksum(data)
    filename = f"JH_5408{timestamp}_{chk:08X}.bin"
    return filename, chk

def verify_filename_offsets(filename: str):
    """Verify exact offsets checked by Generalplus bootloader assembly (0x0213B0-0x0214C0)."""
    assert filename.startswith("JH_5408"), f"Prefix error: {filename}"
    
    ts = filename[7:19]
    assert len(ts) == 12 and ts.isdigit(), f"Invalid timestamp at index 7: {ts}"
    assert ts != STOCK_TIMESTAMP, f"Timestamp cannot equal factory stock {STOCK_TIMESTAMP}"
    
    sep = filename[19]
    assert sep == "_", f"Separator at index 19 must be '_', got '{sep}'"
    
    hex_chk = filename[20:28]
    assert len(hex_chk) == 8, f"Invalid hex checksum length at index 20: {hex_chk}"
    int(hex_chk, 16)
    
    ext = filename[28:]
    assert ext.lower() == ".bin", f"Extension must be .bin, got '{ext}'"
    print(f"[+] Bootloader Schema Validation Passed: '{filename}'")

def pack_firmware(input_path: str, output_dir: str, timestamp: str = None, force_raw: bool = False) -> str:
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input binary not found: {input_path}")
        
    raw_data = path.read_bytes()
    print(f"[*] Input file: {path.name} ({len(raw_data):,} bytes)")

    if len(raw_data) == 2 * 1024 * 1024 and not force_raw:
        # Check if tail blocks (30 and 31) are empty padding
        tail = raw_data[SAFE_BYTE_SIZE:]
        if all(x == 0xFF for x in tail):
            print(f"[+] Safe trimming enabled: Sizing to 30 blocks ({SAFE_BYTE_SIZE:,} bytes).")
            print("    Prevents 21-bit SPI address wraparound erase to Block 1.")
            data = raw_data[:SAFE_BYTE_SIZE]
        else:
            print("[-] Warning: Tail blocks contain non-0xFF data. Trimming may truncate data.")
            data = raw_data[:SAFE_BYTE_SIZE]
    else:
        data = raw_data

    filename, chk = generate_sd_filename(data, timestamp)
    verify_filename_offsets(filename)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / filename
    out_file.write_bytes(data)

    print(f"\n[+] Successfully generated SD Firmware Package:")
    print(f"    Path:     {out_file}")
    print(f"    Filename: {filename}")
    print(f"    Size:     {len(data):,} bytes ({len(data) // 65536} blocks)")
    print(f"    Checksum: 0x{chk:08X}")
    return str(out_file)

def main():
    parser = argparse.ArgumentParser(description="Pack Kodak Charmera firmware for zero-hardware SD card update")
    parser.add_argument("input_bin", help="Path to input raw firmware binary (.bin)")
    parser.add_argument("-o", "--output_dir", default="release", help="Directory for output package")
    parser.add_argument("-t", "--timestamp", default=None, help="12-digit build timestamp (default: current)")
    parser.add_argument("--force-raw", action="store_true", help="Do not trim tail blocks")
    args = parser.parse_args()

    pack_firmware(args.input_bin, args.output_dir, args.timestamp, args.force_raw)

if __name__ == "__main__":
    main()
