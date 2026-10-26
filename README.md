# Keychain Camera Plus 📸✨

> **Turn your Kodak Charmera into a vintage USB-C UVC Webcam via a zero-hardware MicroSD card update.**

[![CI](https://github.com/benbadio/keychain-camera-plus/actions/workflows/ci.yml/badge.svg)](https://github.com/benbadio/keychain-camera-plus/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/benbadio/keychain-camera-plus)](https://github.com/benbadio/keychain-camera-plus/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Keychain Camera Plus** is an open-source custom firmware toolkit for the **Kodak Charmera** keychain digital camera (Generalplus GPCV1235F SoC). 

* **Plug-and-Play USB-C Webcam**: Connect via USB-C to stream live 30 FPS vintage video to macOS (Photo Booth, FaceTime, Zoom, OBS, Discord, QuickTime) and Windows/Linux as `GENERAL- UVC`.
* **Zero-Hardware Installation**: Simply copy one `.bin` file to an ordinary FAT32 MicroSD card—**no opening the camera, no soldering, no external programmer required**.
* **Retains Standalone Camera Operation**: Unplug from USB, and the camera functions normally for taking photos and videos on battery.

> ⚠️ **Disclaimer**: Modifying device firmware carries inherent risks. While this procedure uses the manufacturer's built-in bootloader and has been tested on real hardware, you do this entirely at your own risk. The authors accept no responsibility for bricked devices, data loss, or hardware damage.

---

## Installation

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
3. When the upgrade reaches 100%, **eject the MicroSD card**, then **manually power off the camera** by pressing and holding the Power button.
4. **Delete the `.bin` file from your MicroSD card** (or reformat it) on your computer so the camera doesn't attempt to re-flash the next time the card is inserted.
5. Turn the camera back **ON** and plug it into your Mac or PC via USB-C.
6. Launch **Photo Booth**, **QuickTime Player** (New Movie Recording), or **Zoom**, select **`GENERAL- UVC`**, and enjoy your retro webcam!

---

## Restoring Original Factory Firmware

If you ever wish to revert your camera back to factory original behavior:

1. Download the original factory stock firmware update file (`JH_5408*_0F065D55.bin`) from [GitHub Releases](https://github.com/benbadio/keychain-camera-plus/releases).
2. Copy the file directly to the **ROOT** of your FAT32 MicroSD card.
3. Insert the card into your powered-off Kodak Charmera.
4. Turn the camera **ON** and wait for `Upgrade 0%` $\rightarrow$ `100%`.
5. When complete, **eject the MicroSD card**, then **manually power off the camera** by pressing and holding the Power button.
6. **Delete the `.bin` file from your MicroSD card** (or reformat it) on your computer so the camera doesn't attempt to re-flash the next time the card is inserted.
7. Turn the camera back **ON**. Your camera is now 100% restored to factory original firmware (standard USB mass storage).

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
