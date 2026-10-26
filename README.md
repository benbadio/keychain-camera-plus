# Keychain Camera Plus 📸✨

> **Turn your Kodak Charmera into a vintage USB-C UVC Webcam via a zero-hardware MicroSD card update.**

[![CI](https://github.com/benbadio/keychain-camera-plus/actions/workflows/ci.yml/badge.svg)](https://github.com/benbadio/keychain-camera-plus/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/benbadio/keychain-camera-plus)](https://github.com/benbadio/keychain-camera-plus/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Keychain Camera Plus** is an open-source custom firmware toolkit for the **Kodak Charmera** keychain digital camera (Generalplus GPCV1235F SoC). 

* **Plug-and-Play USB-C Webcam**: Connect via USB-C to stream live 30 FPS vintage video to macOS (Photo Booth, FaceTime, Zoom, OBS, Discord, QuickTime) and Windows/Linux as `GENERAL- UVC`.
* **Zero-Hardware Installation**: Simply copy one `.bin` file to an ordinary FAT32 MicroSD card—**no opening the camera, no soldering, no external programmer required**.
* **Retains Standalone Camera Operation**: Unplug from USB, and the camera functions normally for taking photos and videos on battery.

---

## ⚡ Quick Start: 3-Step Community Upgrade

### 1. Format MicroSD Card
Format any MicroSD card (up to 32 GB) as **FAT32** (Master Boot Record / MBR).
* **macOS**: Disk Utility $\rightarrow$ Format: `MS-DOS (FAT)` | Scheme: `Master Boot Record`.
* **Windows**: Right-click drive $\rightarrow$ Format $\rightarrow$ `FAT32`.

### 2. Copy Firmware Update
Download the latest release package from [GitHub Releases](https://github.com/benbadio/keychain-camera-plus/releases).
Copy the `JH_5408*.bin` file directly to the **ROOT** of your MicroSD card.
> *Note: Do NOT rename the file! The camera's bootloader cryptographically validates the timestamp and checksum in the filename.*

### 3. Upgrade in Camera
1. Insert the MicroSD card into your powered-off Kodak Charmera.
2. Press the **Power** button. The screen will display:
   ```text
   Upgrade   0%  --->  Upgrade 100%
   ```
3. When the upgrade completes, **eject the MicroSD card**. The camera will safely power down.
4. Turn the camera back **ON** and plug it into your Mac or PC via USB-C.
5. Launch **Photo Booth**, **QuickTime Player** (New Movie Recording), or **Zoom**, select **`GENERAL- UVC`**, and enjoy your retro webcam!

---

## 🗺️ Iterative Feature Roadmap

We prioritize new features iteratively based on technical complexity and risk:

| Milestone | Feature | Difficulty | Risk | Status | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **v1.0.0 (MVP)** | **USB-C UVC Webcam Streaming** | **Solved** | **Low** | **Shipped** | Hardware-verified 30 FPS video streaming via `GENERAL- UVC`. |
| **v1.0.0 (MVP)** | **GitHub Actions CI/CD** | **Solved** | **Low** | **Shipped** | Automated pytest suite & release artifact publishing. |
| **v1.1.0** | **Factory Rollback Package** | **1 / 10** | **Low** | Planned | Official 1-click SD card restore to 100% factory behavior. |
| **v1.1.0** | **Custom Boot/Shutdown Splash** | **2 / 10** | **Low** | Planned | Custom splash bitmaps at known flash sector offsets. |
| **v1.1.0** | **Custom Audio UI Chimes** | **3 / 10** | **Low** | Planned | Replace shutter click and power-on/off audio chunks. |
| **v1.2.0** | **Live Hardware Color Filters** | **5 / 10** | **Med** | In Review | Real-time B&W, Sepia, and Negative cycling via Left/Right buttons. |
| **v1.2.0** | **UI String Customization** | **4 / 10** | **Low** | Planned | Custom menu labels and string localization. |
| **v2.0.0** | **Web-Based Drag-and-Drop Patcher** | **5 / 10** | **Low** | Planned | In-browser Web-SD flasher (no CLI or Python needed). |
| **v2.0.0** | **Sensor Exposure & Gain Tuning** | **8 / 10** | **High** | Research | Sensor driver register overrides for low-light tuning. |

---

## 🔬 Reverse Engineering Discoveries

### 1. UVC Mode Selection (`0x022124`)
The factory firmware includes the full Generalplus USB Video Class stack (`PC_CAM.GPZ`), but USB enumeration defaults to mass storage unless an internal flag is passed.
* **Factory instruction at `0x022124`**: `03 00 00 1A` (`bne #0x22138` $\rightarrow$ setup mass storage MSDC).
* **Custom Patch**: `00 00 A0 E1` (`mov r0, r0` / NOP $\rightarrow$ fallthrough directly into `PC_CAM` initialization with `r4 = 1`).

### 2. Bootloader SD Update Protocol
On boot, the Generalplus bootloader parses FAT32 root for `C:\JH_5408*.bin`:
* **Timestamp (`0x0213B0`)**: Characters 7–18 must be 12 numeric digits (`YYYYMMDDhhmm`). If different from factory `202505201029`, it initiates upgrade mode.
* **32-Bit Checksum (`0x02144C`)**: Characters 20–27 must match the unsigned 32-bit cumulative byte sum $\sum \text{byte} \pmod{2^{32}}$.
* **Card Ejection Detection (`0x0217DC`)**: Polls the Card Detect (CD) pin. Once removed, it triggers a clean power-off sequence to prevent re-flashing loops.

### 3. The 21-Bit SPI NOR Flash Wraparound Fix
The Generalplus updater routine (`0x0217B4`) issues a block erase at `end_block + 0x10000`.
When fed an untrimmed 2 MiB file:
$$\text{Offset} = 0\text{x}200000 + 0\text{x}10000 = 0\text{x}210000$$
Because the 2 MiB SPI flash chip has only 21 address lines ($A_0$–$A_{20}$), address bit 21 does not exist, wrapping the erase to **Block 1 (`0x010000`)**, corrupting the firmware!

**Our Solution**: Sizing release binaries to **30 blocks ($1,966,080$ bytes / $0\text{x}1E0000$)**:
$$0\text{x}1E0000 + 0\text{x}10000 = 0\text{x}1F0000 \quad (\text{Block 31})$$
Block 31 is the physical end of the flash (which is empty padding). The erase cleanly clears Block 31, preventing wraparound and leaving all operational code 100% intact!

---

## 🛠️ Development & Building

```bash
# Clone the repository
git clone https://github.com/benbadio/keychain-camera-plus.git
cd keychain-camera-plus

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run automated tests
pytest -v tests/

# Build a release package locally
python scripts/build_release.py --tag v1.0.0
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
All reverse engineering was performed for interoperability purposes. Kodak and Charmera are trademarks of their respective owners.
