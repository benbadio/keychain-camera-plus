# Kodak Charmera Reverse Engineering & Custom Firmware Toolkit 📸✨

A complete reverse engineering, firmware analysis, and custom firmware toolkit for the **Kodak Charmera** keychain digital camera, featuring:
* **UVC Webcam Mode**: Plug in via USB-C to stream live 30 FPS vintage video to macOS (FaceTime, Photo Booth, Zoom, OBS, Discord) and Windows/Linux.
* **Real-Time Hardware Video Filters**: Live color filter cycling (Normal, B&W, Sepia, Negative) using the camera buttons.
* **Zero-Hardware SD Card Delivery**: Community members can upgrade their cameras simply by dragging a `.bin` file onto a FAT32 MicroSD card—**no CH341A programmer, no opening the camera, no soldering**.

---

## Hardware Architecture

- **SoC**: Generalplus GPCV1235F / CBB3 (ARMv5TE core)
- **Onboard Flash**: 2 MiB (2,097,152 bytes) SPI NOR Flash (SFDP compliant, SOIC-8)
- **Display**: 1.5" Color TFT LCD (Slide-lock drawer ZIF connector)
- **USB Interface**: USB-C (Enumerates as standard USB Video Class `GENERAL - UVC` at 30 FPS in custom firmware)
- **Removable Storage**: MicroSD FAT32 (`C:\` in Generalplus RTOS)

---

## ⚡ Quick Start: Zero-Hardware Upgrade (For Community)

To upgrade your Kodak Charmera without opening the case or buying hardware tools:

1. Format a MicroSD card as **FAT32** (MBR).
2. Copy [`release/webcam/JH_5408202610201900_0F065EB9.bin`](release/webcam/JH_5408202610201900_0F065EB9.bin) to the **root** of the SD card.
3. Insert the card into the Charmera and turn it on.
4. Watch the LCD display `Upgrade 0%` $\rightarrow$ `100%`.
5. Eject the MicroSD card when complete. The camera chimes and reboots into custom firmware!
6. Connect via USB-C and launch Photo Booth, FaceTime, Zoom, or OBS.

*For detailed instructions and rollback packages, see [release/COMMUNITY_UPGRADE_GUIDE.md](release/COMMUNITY_UPGRADE_GUIDE.md).*

---

## Repository Structure

```text
charmera-rea-tooling/
├── dumps/
│   ├── charmera_stock_latest.bin  # Verified factory stock 2 MiB backup (SHA-256: cc3b4b...)
│   ├── charmera_webcam.bin        # Patched UVC webcam firmware
│   └── charmera_super.bin         # Webcam + Real-Time Hardware Video Filters
├── release/
│   ├── COMMUNITY_UPGRADE_GUIDE.md # Drag-and-drop SD card flashing instructions
│   ├── webcam/                    # Zero-hardware UVC webcam SD update package
│   ├── super/                     # Zero-hardware Webcam + Filters SD update package
│   └── stock/                     # Zero-hardware Factory Stock rollback package
├── scripts/
│   ├── pack_sd_firmware.py        # Generates bootloader-validated, safely-trimmed SD update files
│   ├── patch_firmware_webcam.py   # Patches UVC fallback instruction (0x022124)
│   ├── patch_firmware_super.py    # Injects hardware CDSP filter hooks into unused padding
│   ├── flash_custom_firmware.sh   # Direct CH341A SPI flashing utility via flashrom
│   └── watch_and_restore_camera2.py # Automated live SPI monitor & restore tool
└── README.md
```

---

## Deep Technical Insights & Discoveries

### 1. UVC Webcam Mode Patch (`0x022124`)
The factory firmware includes full USB Video Class (UVC) camera drivers (`PC_CAM.GPZ`), but USB enumeration defaults to mass storage mode unless an internal flag is set.
* **Original (`0x022124`)**: `03 00 00 1A` (`bne #0x22138` $\rightarrow$ jump to mass storage setup).
* **Patched**: `00 00 A0 E1` (`mov r0, r0` / NOP $\rightarrow$ fallthrough directly into `PC_CAM` UVC initialization with `r4 = 1`).

### 2. Bootloader SD Update Protocol
The Generalplus bootloader scans for `C:\JH_5408*.bin` on cold boot:
* **Timestamp (`0x0213B0`)**: 12-digit build date at characters 7–18 (`YYYYMMDDhhmm`). If different from factory `202505201029`, it initiates upgrade mode.
* **Checksum (`0x02144C`)**: 8-character hex string at characters 20–27. Must match the cumulative 32-bit unsigned byte sum: $\sum \text{byte} \pmod{2^{32}}$.
* **Eject Trigger (`0x0217DC`)**: Debounces the SD Card Detect (CD) pin. Once the card is physically removed, it plays a chime and soft-resets to prevent an infinite update loop.

### 3. The 21-Bit SPI NOR Flash Wraparound Bug Fix
The Generalplus SDK updater (`0x0217B4`) issues a post-upgrade block erase at `end_block + 0x10000` to clear factory settings.
When given an unpadded 2 MiB file:
$$\text{Offset} = 0\text{x}200000 + 0\text{x}10000 = 0\text{x}210000$$
Because the 2 MiB SPI flash chip has only 21 address lines ($A_0$–$A_{20}$), address bit 21 does not exist, causing the erase to wrap around to **Block 1 (`0x010000`)**, corrupting the camera firmware!
**The Solution**: Sizing release binaries to **30 blocks ($1,966,080$ bytes / $0\text{x}1E0000$)**:
$$0\text{x}1E0000 + 0\text{x}10000 = 0\text{x}1F0000 \quad (\text{Block 31})$$
Block 31 is the physical end of the flash (which is already empty padding). The erase cleanly clears Block 31, preventing wraparound and leaving all operational code 100% intact!
