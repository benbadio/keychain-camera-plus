#!/usr/bin/env python3
"""
firmware_asset_tool.py
Analyzes, extracts, and modifies embedded assets in Kodak Charmera (Generalplus CBB3) firmware dumps.
- Scans for embedded JPEG splash screens / UI frames
- Scans for embedded RIFF/WAVE audio cues (shutter click, startup chime, button beeps)
- Scans for relevant configuration strings (SD update filenames, boot parameters)
- Replaces assets cleanly with custom files, maintaining byte alignment
"""

import os
import sys
import re
import argparse
from pathlib import Path
from PIL import Image

def find_jpegs(data: bytes):
    """Locate all JPEG images by SOI (FF D8) and EOI (FF D9)."""
    jpegs = []
    soi_pattern = re.compile(b'\xFF\xD8\xFF')
    for match in soi_pattern.finditer(data):
        start = match.start()
        # Search forward for EOI marker
        eoi = data.find(b'\xFF\xD9', start + 2)
        if eoi != -1:
            end = eoi + 2
            size = end - start
            # Filter out tiny spurious matches (real camera splash screens are > 1KB)
            if size > 1024:
                jpegs.append((start, end, size))
    return jpegs

def find_waves(data: bytes):
    """Locate RIFF WAVE audio files."""
    waves = []
    riff_pattern = re.compile(b'RIFF....WAVE', re.DOTALL)
    for match in riff_pattern.finditer(data):
        start = match.start()
        # Read the 4-byte little-endian chunk size at offset 4
        if start + 8 <= len(data):
            chunk_size = int.from_bytes(data[start + 4:start + 8], 'little')
            end = start + 8 + chunk_size
            if end <= len(data) and chunk_size > 100:
                waves.append((start, end, end - start))
    return waves

def find_interesting_strings(data: bytes):
    """Extract strings matching firmware filenames, version banners, etc."""
    pattern = re.compile(rb'[A-Za-z0-9_\-\.\/]{4,60}')
    matches = []
    keywords = [b'.bin', b'.BIN', b'GPCV', b'GENERALPLUS', b'CBB', b'DCIM', b'SPIDCIM', b'FAT', b'SD', b'FW']
    for m in pattern.finditer(data):
        s = m.group(0)
        if any(k.lower() in s.lower() for k in keywords):
            matches.append((m.start(), s.decode('ascii', errors='ignore')))
    return matches

def cmd_inspect(args):
    fw_path = Path(args.firmware)
    if not fw_path.exists():
        print(f"Error: {fw_path} not found.")
        sys.exit(1)
    
    data = fw_path.read_bytes()
    print("=" * 65)
    print(f"Firmware Inspection: {fw_path.name}")
    print(f"Total Size: {len(data)} bytes ({len(data) / 1024:.2f} KiB)")
    print("=" * 65)

    jpegs = find_jpegs(data)
    print(f"\n[+] Embedded JPEGs found: {len(jpegs)}")
    for i, (start, end, size) in enumerate(jpegs):
        # Attempt to parse dimensions
        try:
            import io
            img = Image.open(io.BytesIO(data[start:end]))
            dim = f"{img.width}x{img.height} ({img.mode})"
        except Exception:
            dim = "Unknown dimensions"
        print(f"  [{i}] Offset 0x{start:06X} - 0x{end:06X} | Size: {size:6d} bytes | {dim}")

    waves = find_waves(data)
    print(f"\n[+] Embedded WAV Audio found: {len(waves)}")
    for i, (start, end, size) in enumerate(waves):
        print(f"  [{i}] Offset 0x{start:06X} - 0x{end:06X} | Size: {size:6d} bytes")

    strings = find_interesting_strings(data)
    print(f"\n[+] Notable Strings / File References: {len(strings)}")
    for offset, s in strings[:30]:
        print(f"  0x{offset:06X}: {s}")
    if len(strings) > 30:
        print(f"  ... and {len(strings) - 30} more.")

def cmd_extract(args):
    fw_path = Path(args.firmware)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = fw_path.read_bytes()

    print(f"Extracting assets from {fw_path.name} to {out_dir} ...")
    
    # Extract JPEGs
    jpegs = find_jpegs(data)
    for i, (start, end, size) in enumerate(jpegs):
        fname = out_dir / f"image_{i:02d}_offset_0x{start:06X}.jpg"
        fname.write_bytes(data[start:end])
        print(f"Saved JPEG: {fname.name} ({size} bytes)")

    # Extract WAVs
    waves = find_waves(data)
    for i, (start, end, size) in enumerate(waves):
        fname = out_dir / f"audio_{i:02d}_offset_0x{start:06X}.wav"
        fname.write_bytes(data[start:end])
        print(f"Saved WAV:  {fname.name} ({size} bytes)")

    # Dump strings
    strings = find_interesting_strings(data)
    str_file = out_dir / "firmware_strings.txt"
    with open(str_file, "w") as f:
        for offset, s in strings:
            f.write(f"0x{offset:06X}: {s}\n")
    print(f"Saved Strings: {str_file.name}")
    print("\nExtraction complete.")

def cmd_replace_image(args):
    fw_path = Path(args.firmware)
    new_img_path = Path(args.new_image)
    out_path = Path(args.output)
    offset = int(args.offset, 16) if args.offset.startswith("0x") or args.offset.startswith("0X") else int(args.offset)

    fw_data = bytearray(fw_path.read_bytes())
    new_img_data = new_img_path.read_bytes()

    if not new_img_data.startswith(b'\xFF\xD8'):
        print("Error: New image is not a valid JPEG (missing SOI FF D8).")
        sys.exit(1)

    # Find the end of the existing image at this offset
    eoi = fw_data.find(b'\xFF\xD9', offset + 2)
    if eoi == -1:
        print(f"Error: Could not locate original JPEG EOI at offset 0x{offset:06X}.")
        sys.exit(1)
    orig_end = eoi + 2
    orig_size = orig_end - offset

    print(f"Original image size: {orig_size} bytes (0x{offset:06X} - 0x{orig_end:06X})")
    print(f"Replacement size   : {len(new_img_data)} bytes")

    if len(new_img_data) > orig_size:
        print(f"Error: New image ({len(new_img_data)} bytes) exceeds allocated slot ({orig_size} bytes)!")
        print("Please compress the JPEG further (e.g. reduce quality or re-encode with Pillow).")
        sys.exit(1)

    # Pad with 0xFF to preserve boundary alignment
    padded_replacement = new_img_data + (b'\xFF' * (orig_size - len(new_img_data)))
    fw_data[offset:orig_end] = padded_replacement

    out_path.write_bytes(fw_data)
    print(f"✓ Successfully wrote modified firmware to: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Kodak Charmera / Generalplus Firmware Asset Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Inspect
    inspect_p = subparsers.add_parser("inspect", help="Inspect firmware binary for assets and strings")
    inspect_p.add_argument("firmware", help="Path to firmware .bin file")

    # Extract
    extract_p = subparsers.add_parser("extract", help="Extract all JPEGs, WAVs, and strings")
    extract_p.add_argument("firmware", help="Path to firmware .bin file")
    extract_p.add_argument("output_dir", help="Directory to save extracted assets")

    # Replace image
    replace_img_p = subparsers.add_parser("replace-image", help="Replace an embedded JPEG splash screen")
    replace_img_p.add_argument("firmware", help="Path to input stock firmware .bin")
    replace_img_p.add_argument("offset", help="Hex offset of the target image (e.g. 0x054000)")
    replace_img_p.add_argument("new_image", help="Path to replacement JPEG image")
    replace_img_p.add_argument("output", help="Path to write customized firmware .bin")

    args = parser.parse_args()
    if args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "extract":
        cmd_extract(args)
    elif args.command == "replace-image":
        cmd_replace_image(args)

if __name__ == "__main__":
    main()
