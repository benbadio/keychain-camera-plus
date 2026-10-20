# Kodak Charmera Custom Firmware: Community Zero-Hardware Upgrade Guide 📸✨

Turn your **Kodak Charmera** into a vintage, lo-fi **USB-C UVC Webcam** (compatible with macOS FaceTime, Photo Booth, Zoom, OBS, Discord, and QuickTime) while retaining full standard digital camera capabilities when unplugged.

**Zero Hardware Required**: No screwdrivers, no soldering, no CH341A programmer, no opening the camera case. Just a standard MicroSD card.

---

## 🚀 Features

* **Instant USB-C Webcam**: Connect to any Mac, PC, or Linux machine via USB-C to stream live 30 FPS vintage video as `GENERAL - UVC`.
* **Retains Standalone Camera Functions**: Unplug the USB cable, and the camera functions normally for taking photos and videos on battery.
* **Zero-Hardware SD Delivery**: Safe, in-camera firmware update using the factory Generalplus bootloader.

---

## 📦 Download Packages

| Package | Filename | Description |
| :--- | :--- | :--- |
| **UVC Webcam Edition** (Recommended) | `JH_5408202610201900_0F065EB9.bin` | Clean, 100% verified UVC webcam mod. |
| **Super Edition** (Webcam + Filters) | `JH_5408202610201900_0F069EA4.bin` | UVC webcam mod + live Left/Right button color filters (Normal, B&W, Sepia, Negative). |

---

## 🛠️ Step-by-Step Installation Guide

### Prerequisites
* 1x Kodak Charmera camera (fully charged).
* 1x MicroSD card (any size up to 32 GB, formatted as **FAT32**).
* 1x USB-C data cable.

---

### Step 1: Prepare the MicroSD Card
1. Format your MicroSD card as **FAT32** (Master Boot Record / MBR).
   * **macOS Disk Utility**: Format $\rightarrow$ MS-DOS (FAT), Scheme $\rightarrow$ Master Boot Record.
   * **Windows**: Right-click drive $\rightarrow$ Format $\rightarrow$ FAT32.
2. Ensure the MicroSD card is completely empty.

### Step 2: Copy the Firmware Update
1. Copy **ONE** firmware file (e.g. `JH_5408202610201900_0F065EB9.bin`) directly to the **ROOT directory** of your MicroSD card.
   * *Do NOT rename the file! The camera's bootloader cryptographically validates the timestamp and checksum in the filename.*
2. Safely eject the MicroSD card from your computer.

### Step 3: Run the In-Camera Upgrade
1. Ensure the Charmera is **powered OFF**.
2. Insert the MicroSD card into the camera's card slot.
3. Turn the camera **ON** by pressing the Power button.
4. The camera LCD will light up and display:
   ```text
   Upgrade   0%  --->  Upgrade 100%
   ```
   *(The upgrade process takes approximately 15–20 seconds. Do not touch any buttons or remove the battery during this step.)*
5. Once the upgrade reaches **100%**, the camera will pause and wait for you to eject the card.

### Step 4: Eject Card & Reboot
1. **Push and eject the MicroSD card** from the camera.
2. The camera will instantly detect that the card was removed, play a completion chime, and reboot automatically into custom firmware!
3. Format or delete the update file from your MicroSD card so the camera doesn't ask to re-flash every time you turn it on.

### Step 5: Test Your New Webcam!
1. Connect your Charmera to your Mac or PC using a standard USB-C cable.
2. The Charmera will automatically initialize in UVC mode.
3. Open **Photo Booth**, **FaceTime**, **QuickTime Player** (New Movie Recording), **OBS Studio**, or **Zoom**.
4. Select `GENERAL - UVC` as your camera input and enjoy the retro Kodak aesthetic!

---

## 🔬 Under the Hood: How It Works

### 1. The Generalplus GPCV1235F Bootloader Protocol
The Kodak Charmera runs on a Generalplus GPCV1235F / CBB3 multimedia SoC with a 2 MiB SPI NOR flash memory chip. During cold boot, the bootloader searches the root of the FAT32 filesystem for files matching `C:\JH_5408*.bin`:
* **Timestamp Check (`0x0213B0`)**: Parses characters 7–18 as a 12-digit build timestamp (`YYYYMMDDhhmm`). If different from the factory build timestamp (`202505201029`), it triggers the update.
* **32-Bit Byte Sum Validation (`0x02144C`)**: Computes the cumulative unsigned 32-bit sum of all bytes in the file and compares it to the 8-character uppercase hex string in the filename.
* **SD Card Removal Debounce (`0x0217DC`)**: Polls the Card Detect (CD) pin. Once the card is physically removed, it plays a chime and soft-resets the SoC to prevent an infinite update loop.

### 2. The 21-Bit SPI Flash Wraparound Bug (And How We Fixed It)
Standard Generalplus SDK updater code (`0x0217B4`) issues a post-upgrade block erase at `end_block + 0x10000` to wipe factory NVRAM settings.
When fed an unpadded 2 MiB file:
$$\text{Offset} = 0\text{x}200000 + 0\text{x}10000 = 0\text{x}210000$$
Because the 2 MiB SPI flash chip has only 21 address lines ($A_0$–$A_{20}$), address bit 21 does not exist on the die, causing the address to wrap around:
$$0\text{x}210000 \pmod{0\text{x}200000} = \mathbf{0\text{x}010000 \quad (\text{Block 1})}$$
This caused factory updaters to erase their own code in Block 1.
Our packaging tool safely sizes the release binary to **30 blocks ($1,966,080$ bytes / $0\text{x}1E0000$)**:
$$0\text{x}1E0000 + 0\text{x}10000 = 0\text{x}1F0000 \quad (\text{Block 31})$$
Block 31 is the physical end of the flash (which is already empty padding). The erase cleanly clears Block 31, preventing wraparound and leaving all operational code 100% intact!

---

## 🛡️ Recovery & Rollback

If you ever wish to restore your camera to 100% factory original state:
1. Copy the factory stock SD update package `JH_5408202610202000_0F065D55.bin` onto your MicroSD card.
2. Boot the camera to run the update, eject card, and reboot.
3. Your camera is returned to factory stock condition.
