# ESP32 Provision Tools
This python scripts is used to provision **ESP32 S3** MCU, this tool generates key for secure features, efuse burning, and final secure deployment using "ESP-IDF" tool chain.

---

## Security workflow

This project splits into two operations build and flash, so it is easy to debug.

### 1. Firmware builder & encrypter
    * Automatically detect target chips and queries unique physical hardware **MAC addresses** via efuse registers.
    * Generates device unique **XTS-AES 128 bit** flash encryption keys and **Secure boot V2 RSA 3072** signing key pair and derives the public key digests.
    * configures custome target-specific `sdkconfig.defaults` profiles, here you can make changes based on requirement.
    * Automatically signs and encrypts the binary blocks (**Bootloader**, **Partition table**, and **Application binary**)

## 2. Efuse Provisioner & Flasher
    * Extracts device context and validates matching pre-generated cryptographic components in device secrets folder. 
    * Contains modules (currently commented for safety validation) to permanently program hardware eFuses using espefuse.py.
        * Burns `BLOCK_KEY0` with device unique flash encryption key.
        * Burns `BLOCK_KEY1` with project wide secure boot digest.
        * Configures `SPI_BOOT_CRYPT_COUNT` to `0x7` to scale hardware into release mode.
        * write protects security arrays like USB_JTAG, ICACHE to mitigate reverse engineering.
    * Flashes encrypted bin files to device.

## Getting started 
### Prerequisites

1. Install the official **ESP v5.x** toolchain environment on your host compiler.

2. Ensure environmental variable ESP_IDF path is set.
    Scripts rely on environmental variable to dynamically locate paths, configure compilation target and memory layout.
    **`IDF_PATH`** Root installation directory of the official ESP-IDF toolchain framework.
    **`target_chip`** Specifies the silicon chip target profile.
    **`bootloader_offset`** physical memory offset address in flash where the bootloader is written. 
    **`partition_table_offset`** memory address offset where the partition table layout is written.
    **`factory_app_offset`** flash memory location address where the primary firmware image begins.
    **`certificate_name`** Path string pointing to your project's custom TLS certificate bundle file.
    **`flash_bin_file`** Target base filename of your compiled application firmware binary asset.
    **`baud_rate`** Communication connection speed target for flashing devices over a serial link.

#### Linux Workspace Setup
```bash
export IDF_PATH="\$HOME/esp/esp-idf"
export target_chip="esp32s3"
export bootloader_offset="0x0"
export partition_table_offset="0x10000"
export factory_app_offset="0x20000"
export certificate_name="certs/server_certs.pem"
export flash_bin_file="Proj001"
export baud_rate="116200"
```
#### Windows PowerShell Workspace Setup
```powershell
\$env:IDF_PATH="C:\esp\esp-idf"
\$env:target_chip="esp32s3"
\$env:bootloader_offset="0x0"
\$env:partition_table_offset="0x10000"
\$env:factory_app_offset="0x20000"
\$env:certificate_name="certs\server_certs.pem"
\$env:flash_bin_file="Proj001"
\$env:baud_rate="116200"
```

3. Install script bindings:
    ```bash
        pip install esptool pyserial
    ```

### Export the your project configs in 'config_edits' in device_build_key.py file
### Connect your ESP32 S3 module via USB and execute the build_key.py file