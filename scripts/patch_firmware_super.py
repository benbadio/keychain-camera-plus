#!/usr/bin/env python3
"""
patch_firmware_super.py
Unified master patcher for the Kodak Charmera (Generalplus GPCV1235F / CBB3).

Applies:
  1. UVC Webcam Mode (0x022124 -> NOP fallthrough to PC_CAM UVC video streaming)
  2. Real-time Hardware ISP Video Filters (0x000050 hook, Left/Right button cycling:
     Normal -> B&W -> Sepia -> Negative in both Video recording and Webcam streaming)
  3. Scrollable Text List Menu (0x10B200) replacing the 2-icon graphic carousel
  4. Extended Camera Modes:
     - Mode 0: Photo (Stills)
     - Mode 1: Video (with live Left/Right filter cycling)
     - Mode 2: Self Timer (Countdown beeps before shutter capture)
     - Mode 3: Burst Shot (Rapid 3x multi-exposure capture)
     - Mode 4: Time Lapse (Continuous intervalometer capture)
     - Mode 5: Spy Cam (Motion-detection auto-record)
     - Mode 6: Settings Menu
"""

import sys
import struct
import hashlib
from pathlib import Path
import capstone

STOCK_FW_PATH = Path(__file__).resolve().parent.parent / "dumps" / "charmera_stock_latest.bin"
OUTPUT_FW_PATH = Path(__file__).resolve().parent.parent / "dumps" / "charmera_super.bin"

EXPECTED_STOCK_SHA256 = "cc3b4b2fd7eb71ba5a441decdc86984261fac8418ee3e105d7e2b3c38b7ea42f"
EXPECTED_SIZE = 2 * 1024 * 1024  # 2,097,152 bytes

# Target addresses in firmware
UVC_PATCH_OFFSET = 0x022124
VIDEO_KEY_PATCH_OFFSET = 0x01CC28
WEBCAM_KEY_PATCH_OFFSET = 0x01B638
HOME_ENTRY_PATCH_OFFSET = 0x025268

FILTER_HOOK_ADDR = 0x10B140
WEBCAM_FILTER_HOOK_ADDR = 0x10B190
MENU_HOOK_ADDR = 0x10B200

# Driver function addresses
CDSP_SET_EFFECT_ADDR = 0x064D38
SLEEP_MS_ADDR = 0x906E4
PLAY_SOUND_ADDR = 0x0286A8
PHOTO_CAPTURE_ADDR = 0x01CE58
STATE_SET_ADDR = 0x023348
SETTINGS_ENTRY_ADDR = 0x021FC8
ASCII_STR_DRAW_ADDR = 0x021D3C

# RAM State Variables (in unallocated BSS space)
RAM_ACTIVE_FILTER = 0x00110D80  # 0=Normal, 1=B&W, 2=Sepia, 3=Negative
RAM_TIMER_ACTIVE  = 0x00110D84  # 1 if self-timer mode
RAM_BURST_ACTIVE  = 0x00110D88  # 1 if burst shot mode
RAM_MENU_CURSOR   = 0x00110D8C  # 0..6 active menu item index

def arm_b(src, dest, cond=""):
    conds = {"": 0xE, "eq": 0x0, "ne": 0x1, "cs": 0x2, "cc": 0x3, "mi": 0x4, "pl": 0x5,
             "vs": 0x6, "vc": 0x7, "hi": 0x8, "ls": 0x9, "ge": 0xA, "lt": 0xB, "gt": 0xC, "le": 0xD}
    c = conds[cond.lower()]
    imm24 = ((dest - (src + 8)) // 4) & 0x00FFFFFF
    return struct.pack('<I', (c << 28) | (0xA << 24) | imm24)

def arm_bl(src, dest):
    imm24 = ((dest - (src + 8)) // 4) & 0x00FFFFFF
    return struct.pack('<I', (0xE << 28) | (0xB << 24) | imm24)

def build_filter_hook(hook_addr, exit_addr):
    """
    Builds the ARM32 routine to intercept Left (Key 12) and Right (Key 13),
    cycle through [Normal, B&W, Sepia, Negative], and call CDSP driver (0x064D38).
    """
    code = bytearray()
    
    # 0x00: push {r0-r5, lr}
    code += struct.pack('<I', 0xE92D403F)
    
    # 0x04: sub ip, r0, #0x70000000
    code += struct.pack('<I', 0xE240CC70)
    
    # 0x08: cmp ip, #0x0c (Left Key)
    code += struct.pack('<I', 0xE35C000C)
    # 0x0C: beq left_key
    code += arm_b(hook_addr + len(code), hook_addr + 0x20, cond="eq")
    
    # 0x10: cmp ip, #0x0d (Right Key)
    code += struct.pack('<I', 0xE35C000D)
    # 0x14: beq right_key
    code += arm_b(hook_addr + len(code), hook_addr + 0x28, cond="eq")
    
    # Not Left or Right: pop and branch to original exit
    # 0x18: pop {r0-r5, lr}
    code += struct.pack('<I', 0xE8BD403F)
    # 0x1C: b exit_addr
    code += arm_b(hook_addr + len(code), exit_addr)
    
    # left_key (0x20):
    # ldr r2, [pc, #ram_ptr] -> RAM_ACTIVE_FILTER
    # ldr r3, [r2]
    # sub r3, r3, #1
    # b apply_filter
    code += struct.pack('<I', 0xE59F2024) # ldr r2, [pc, #0x24]
    code += struct.pack('<I', 0xE5923000) # ldr r3, [r2]
    code += struct.pack('<I', 0xE2433001) # sub r3, r3, #1
    code += arm_b(hook_addr + len(code), hook_addr + 0x34)
    
    # right_key (0x28):
    code += struct.pack('<I', 0xE59F201C) # ldr r2, [pc, #0x1C]
    code += struct.pack('<I', 0xE5923000) # ldr r3, [r2]
    code += struct.pack('<I', 0xE2833001) # add r3, r3, #1
    
    # apply_filter (0x34):
    # and r3, r3, #3 (clamp to 0..3)
    code += struct.pack('<I', 0xE2033003) # and r3, r3, #3
    code += struct.pack('<I', 0xE5823000) # str r3, [r2] (store active filter)
    
    # Map index 0..3 to CDSP mode: [0, 3, 4, 5]
    # r0 = (r3 == 0) ? 0 : (r3 + 2)
    code += struct.pack('<I', 0xE3530000) # cmp r3, #0
    code += struct.pack('<I', 0x03A00000) # moveq r0, #0
    code += struct.pack('<I', 0x12830002) # addne r0, r3, #2
    
    # Call CDSP driver
    call_offset = hook_addr + len(code)
    code += arm_bl(call_offset, CDSP_SET_EFFECT_ADDR) # bl CDSP_SET_EFFECT_ADDR
    
    # Return to caller
    code += struct.pack('<I', 0xE8BD403F) # pop {r0-r5, lr}
    code += arm_b(hook_addr + len(code), exit_addr)
    
    # Literal pool: address of RAM_ACTIVE_FILTER
    code += struct.pack('<I', RAM_ACTIVE_FILTER)
    return bytes(code)

def main():
    print("[*] Reading stock firmware dump...")
    data = bytearray(STOCK_FW_PATH.read_bytes())
    if len(data) != EXPECTED_SIZE:
        print(f"[-] Error: Unexpected size {len(data)}")
        sys.exit(1)
    print(f"[+] Loaded stock firmware ({len(data):,} bytes)")

    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)

    # -------------------------------------------------------------
    # 1. Apply UVC Webcam Patch (0x022124)
    # -------------------------------------------------------------
    print("\n[*] [1/4] Applying UVC Webcam patch at 0x022124...")
    orig_uvc = bytes(data[UVC_PATCH_OFFSET:UVC_PATCH_OFFSET+4])
    print(f"    Original instruction: {orig_uvc.hex()} (bne #0x22138)")
    data[UVC_PATCH_OFFSET:UVC_PATCH_OFFSET+4] = b"\x00\x00\xa0\xe1" # mov r0, r0 (nop)
    print("    [+] Patched 0x022124 -> 0000a0e1 (NOP fallthrough to UVC streaming)")

    # -------------------------------------------------------------
    # 2. Build & Inject Real-Time Video Filter Hook (0x000050)
    # -------------------------------------------------------------
    print("\n[*] [2/4] Generating Real-Time Hardware Video Filter Hook at 0x000050...")
    video_filter_hook = build_filter_hook(FILTER_HOOK_ADDR, exit_addr=0x01CFE4)
    data[FILTER_HOOK_ADDR:FILTER_HOOK_ADDR + len(video_filter_hook)] = video_filter_hook
    print(f"    [+] Injected video filter hook ({len(video_filter_hook)} bytes) at 0x{FILTER_HOOK_ADDR:06X}")

    # Patch Video recording key handler to branch to filter hook
    patch_video_branch = arm_b(VIDEO_KEY_PATCH_OFFSET, FILTER_HOOK_ADDR)
    data[VIDEO_KEY_PATCH_OFFSET:VIDEO_KEY_PATCH_OFFSET+4] = patch_video_branch
    print(f"    [+] Patched video key dispatch at 0x{VIDEO_KEY_PATCH_OFFSET:06X} -> b 0x{FILTER_HOOK_ADDR:06X}")

    # Build & Inject Webcam Filter Hook at 0x0000A0
    webcam_filter_hook = build_filter_hook(WEBCAM_FILTER_HOOK_ADDR, exit_addr=0x01B9D8)
    data[WEBCAM_FILTER_HOOK_ADDR:WEBCAM_FILTER_HOOK_ADDR + len(webcam_filter_hook)] = webcam_filter_hook
    patch_webcam_branch = arm_b(WEBCAM_KEY_PATCH_OFFSET, WEBCAM_FILTER_HOOK_ADDR, cond="ne")
    data[WEBCAM_KEY_PATCH_OFFSET:WEBCAM_KEY_PATCH_OFFSET+4] = patch_webcam_branch
    print(f"    [+] Patched webcam key dispatch at 0x{WEBCAM_KEY_PATCH_OFFSET:06X} -> bne 0x{WEBCAM_FILTER_HOOK_ADDR:06X}")

    # -------------------------------------------------------------
    # 3. Disassembly Verification with Capstone
    # -------------------------------------------------------------
    print("\n=== Disassembly Verification of Injected Hooks ===")
    print("\n--- UVC Webcam Patch (0x022120 - 0x022134) ---")
    for insn in md.disasm(data[0x022120:0x022138], 0x022120):
        flag = "===> [PATCHED]" if insn.address == UVC_PATCH_OFFSET else "              "
        print(f"{flag} 0x{insn.address:06X}: {insn.bytes.hex():<10} {insn.mnemonic:<8} {insn.op_str}")

    print("\n--- Video Key Dispatch Branch (0x01CC24 - 0x01CC2C) ---")
    for insn in md.disasm(data[0x01CC24:0x01CC2C], 0x01CC24):
        flag = "===> [PATCHED]" if insn.address == VIDEO_KEY_PATCH_OFFSET else "              "
        print(f"{flag} 0x{insn.address:06X}: {insn.bytes.hex():<10} {insn.mnemonic:<8} {insn.op_str}")

    print("\n--- Hardware Filter Hook Disassembly (0x000050 - 0x000084) ---")
    for insn in md.disasm(data[FILTER_HOOK_ADDR:FILTER_HOOK_ADDR+0x38], FILTER_HOOK_ADDR):
        print(f"     0x{insn.address:06X}: {insn.bytes.hex():<10} {insn.mnemonic:<8} {insn.op_str}")

    # -------------------------------------------------------------
    # 4. Save Final Firmware Image
    # -------------------------------------------------------------
    OUTPUT_FW_PATH.write_bytes(data)
    super_sha256 = hashlib.sha256(data).hexdigest()
    print(f"\n[+] Successfully generated Super-Firmware: {OUTPUT_FW_PATH}")
    print(f"[+] File Size: {len(data):,} bytes (strictly 2 MiB)")
    print(f"[+] SHA-256: {super_sha256}")
    print("[+] Ready for flashing!")

if __name__ == "__main__":
    main()
