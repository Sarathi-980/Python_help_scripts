

import subprocess
import os
import sys
import re
import esptool
import struct
import traceback 
import serial.tools.list_ports
import shutil

from esptool.util import FatalError
from esptool.cmds import detect_chip

""" 
    This function reads Esp-32 S3 MAC, returns 
"""
def esp_read_MAC_addr(esp):
    # Base eFuse register address where MAC is stored (ESP32-S3 specific)
    ESP32S3_MAC_EFUSE = 0x60007044  # MAC efuse address
 
    # MAC address is 48 bits (12 HEX numbers: each hex is 4 bits)
    # So MAC is stored in 2 registers, and yes esp32 reg size is 32 bits
    MAC0 = esp.read_reg(ESP32S3_MAC_EFUSE) 
    MAC1 = esp.read_reg(ESP32S3_MAC_EFUSE + 4)

    # packing as a string ">II" ==> big-endian (>) and two unsigned integers (I, I)
    bitstring = struct.pack(">II", MAC1, MAC0)

    # we skipping first two bytes because MAC1 last 2 bytes holds MAC value
    return tuple(bitstring)[2:]

current_directory = os.getcwd()

# ESP IDF should be present because we need esp python scripts
esp_idf_path = os.getenv('IDF_PATH')
if not esp_idf_path:
    sys.exit("Error: The 'IDF_PATH' environment variable didn't set, Please set before run this script")

idf_py_path = os.path.join(esp_idf_path, 'tools', 'idf.py') 
esptool_path = os.path.join(
    esp_idf_path, 'components', 'esptool_py', 'esptool', 'esptool.py'
) 
espfuse_path = os.path.join(
    esp_idf_path, 'components', 'esptool_py', 'esptool', 'espefuse.py'
) 
espsecure_path = os.path.join(
    esp_idf_path, 'components', 'esptool_py', 'esptool', 'espsecure.py'
) 
nvs_partition_gen_path = os.path.join(
    esp_idf_path, 'components', 'nvs_flash',
    'nvs_partition_generator', 'nvs_partition_gen.py'
)

# Get the target chip type (e.g., esp32, esp32s3) from environment variables
target_chip = os.environ.get("target_chip")

# Offset address in flash memory where the bootloader will be written
bootloader_offset = os.environ.get("bootloader_offset")

# Offset address for the partition table in flash
partition_table_offset = os.environ.get("partition_table_offset")

# Offset address where the factory application (main firmware) is stored
factory_app_offset = os.environ.get("factory_app_offset")

# Name of the certificate bundle (used for security features like TLS)
certificate_bundle_name = os.environ.get("certificate_name")

# The executable image built to flash name
flash_file = os.environ.get("flash_bin_file")
if not flash_bin_file.endswith(".bin"):
    flash_file = f"{flash_file}.bin"

# Path to the compiled bootloader binary inside the build directory
plain_bootloader_path = os.path.join(
    current_directory, 'build', 'bootloader', 'bootloader.bin'
)

# Path to the generated partition table binary
plain_partition_table_path = os.path.join(
    current_directory, 'build', 'partition_table', 'partition-table.bin'
)

# Path to the main application firmware binary
plain_app_path = os.path.join(
    current_directory, 'build', flash_file
)

# Normalize certificate path by replacing backslashes with forward  
# because while using in windows, i got error for '//' file separation, the Cmake didn't work for me
certificate_bundle_name_path = certificate_bundle_name.replace("\\", "/")

# Get a list of all available serial ports connected to the system
ports = serial.tools.list_ports.comports()

def main():
    device_detected = False 
    for port in ports: 
        try:
            print(f"Trying to connect {target_chip} via {port}")
            with detect_chip(port.device) as esp:
                try:
                    python_exec = sys.executable
 
                    des = esp.get_chip_description()
                    print(f"ESP detected on {port.device}: {des}") 
                    device_detected = True
                    MAC = esp_read_MAC_addr(esp)
                    MAC_str = ''.join(f"{b:02X}" for b in MAC) 
                    print(f"Device MAC: {MAC_str}.")

                    #device secrets folder to store security requirements like keys and digest.
                    device_secrets_folder_path = os.path.join(current_directory, "device_secrets")
                    if not os.path.isdir(device_secrets_folder_path):
                        os.makedirs(device_secrets_folder_path)
                    
                    #Folder to store flash encryption key for each device
                    flash_encryption_keys_folder = os.path.join(device_secrets_folder_path, "flash_encryption_keys")  
                    if not os.path.isdir(flash_encryption_keys_folder):
                        os.makedirs(flash_encryption_keys_folder)  

                    #flash encryption key generation
                    flash_encryption_key_file_name = "flash_encryption_key_" + MAC_str + ".bin"
                    flash_encryption_key_file = os.path.join(flash_encryption_keys_folder, flash_encryption_key_file_name)
                    if not os.path.exists(flash_encryption_key_file):
                        subprocess.run([ python_exec, espsecure_path, "generate_flash_encryption_key", flash_encryption_key_file ], check=True)  
                    
                    #secure boot key generation and the same key used for all device
                    secureboot_key_file = os.path.join(device_secrets_folder_path, "secureboot_encryption_key.pem")  
                    if not os.path.exists(secureboot_key_file):
                        subprocess.run([ python_exec, espsecure_path, "generate_signing_key",
                        "--version", "2", "--scheme", "rsa3072", secureboot_key_file ], check=True) 

                    #secure boot digest generation using the secure boot key
                    digest_file = os.path.join(device_secrets_folder_path, "secureboot_digest.bin")  
                    if not os.path.exists(digest_file):
                        subprocess.run([ python_exec, espsecure_path, "digest_sbv2_public_key",
                        "--keyfile", secureboot_key_file , "--output", digest_file ], check=True)

                    #forcing ESP-IDF rebuild dependencies
                    components_folder = os.path.join(current_directory, "managed_components")
                    if os.path.exists(components_folder) and os.path.isdir(components_folder):
                        shutil.rmtree(components_folder)

                    #Forcing ESP-IDF to build with new configurations
                    sdkconfig_path = os.path.join(current_directory, "sdkconfig")
                    if (os.path.exists(sdkconfig_path)):
                        os.remove(sdkconfig_path)

                    #Rebuilding configs using sdkconfig.defaults
                    config_defaults_file = os.path.join(current_directory, "sdkconfig.defaults") 
                    config_edits = [
                        f'CONFIG_IDF_TARGET={target_chip}',
                        "CONFIG_BT_ENABLED=y",
                        "CONFIG_BTDM_CTRL_MODE_BLE_ONLY=y",
                        "CONFIG_BTDM_CTRL_MODE_BR_EDR_ONLY=n",
                        "CONFIG_BTDM_CTRL_MODE_BTDM=n",
                        "CONFIG_BT_NIMBLE_ENABLED=y",
                        "CONFIG_BT_GATTS_PPCP_CHAR_GAP=y",
                        f'CONFIG_PARTITION_TABLE_OFFSET={partition_table_offset}',
                        "CONFIG_PARTITION_TABLE_CUSTOM=y",
                        'CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions.csv"',
                        'CONFIG_PARTITION_TABLE_FILENAME="partitions.csv"',
                        "CONFIG_PARTITION_TABLE_MD5=y",
                        "CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y",  

                        "CONFIG_ESP_HTTPS_OTA_ALLOW_HTTP=n", 
                        "CONFIG_MBEDTLS_CERTIFICATE_BUNDLE=y",
                        "CONFIG_MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_FULL=y",
                        "CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE=y",
                        f'CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE_PATH="{certificate_bundle_name_path}"',
                        
                        "CONFIG_SECURE_FLASH_ENC_ENABLED=y", 
                        "CONFIG_SECURE_BOOT=y",
                        "CONFIG_SECURE_BOOT_V2_ENABLED=y",
                        "CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=n", 
                        "CONFIG_BTN_NVS_RESET=y",
                        "CONFIG_DEVICE_INCLUDE_SPI=y",  
                    ]
                    
                    #Open the sdkconfig.defaults file and write configs
                    with open(config_defaults_file, 'w') as f: 
                        f.write('\n'.join(config_edits)) 

                    #Building firmware using idf build command  
                    result = subprocess.run([ python_exec, idf_py_path, "build", "-D", f"IDF_TARGET={target_chip}" ], check=True)
                    if result.returncode != 0 :
                        raise Exception("Build failed.")

                    #Creating folder to store signed firmware
                    device_firmware_path = os.path.join(current_directory, "device_firmware")
                    if not os.path.isdir(device_firmware_path):
                        os.makedirs(device_firmware_path)
                        
                    #generating signed firmware
                    signed_firmware = "firmware_signed_" + MAC_str
                    signed_firmware_path = os.path.join(device_firmware_path, signed_firmware)  

                    if not os.path.isdir(signed_firmware_path):
                        os.makedirs(signed_firmware_path)

                    signed_bootloader_file = os.path.join(signed_firmware_path, "signed_bootloader.bin")  
                    if os.path.exists(signed_bootloader_file):
                        os.remove(signed_bootloader_file)
                    subprocess.run([ python_exec, espsecure_path, "sign_data", "--version", "2",
                        "--keyfile", secureboot_key_file, "--output", signed_bootloader_file,
                        plain_bootloader_path ], check=True)
                        
                    signed_app_file = os.path.join(signed_firmware_path, "signed_app.bin") 
                    if os.path.exists(signed_app_file):
                        os.remove(signed_app_file)
                    subprocess.run([ python_exec, espsecure_path, "sign_data", "--version", "2",
                        "--keyfile", secureboot_key_file, "--output", signed_app_file,
                        plain_app_path ], check=True)

                    flash_encrypted_firmware = "encrypted_flash_firmware_" + MAC_str
                    flash_encrypted_firmware_path = os.path.join(device_firmware_path, flash_encrypted_firmware)
                    if not os.path.isdir(flash_encrypted_firmware_path):
                        os.makedirs(flash_encrypted_firmware_path) 

                    flash_encrypted_bootloader_file = os.path.join(flash_encrypted_firmware_path, "bootloader_encrypted.bin")
                    if os.path.exists(flash_encrypted_bootloader_file):
                        os.remove(flash_encrypted_bootloader_file)
                    #encrypting the bootloader using flash encryption key
                    subprocess.run([ python_exec, espsecure_path, "encrypt_flash_data", "--aes_xts", "--keyfile",
                        flash_encryption_key_file, "--address", bootloader_offset, "--output", flash_encrypted_bootloader_file, 
                        signed_bootloader_file ], check=True)
                    
                    flash_encrypted_partition_file = os.path.join(flash_encrypted_firmware_path, "partition_table_encrypted.bin") 
                    if os.path.exists(flash_encrypted_partition_file):
                        os.remove(flash_encrypted_partition_file)
                    #encrypting the partition table using flash enc key
                    subprocess.run([ python_exec, espsecure_path, "encrypt_flash_data", "--aes_xts", "--keyfile",
                        flash_encryption_key_file, "--address", partition_table_offset, "--output", flash_encrypted_partition_file, 
                        plain_partition_table_path ], check=True)
                    
                    flash_encrypted_app_file = os.path.join(flash_encrypted_firmware_path, "app_encrypted.bin")
                    if os.path.exists(flash_encrypted_app_file):
                        os.remove(flash_encrypted_app_file)          
                    #encrypting the app using flash enc key
                    subprocess.run([ python_exec, espsecure_path, "encrypt_flash_data", "--aes_xts", "--keyfile",
                        flash_encryption_key_file, "--address", factory_app_offset, "--output", flash_encrypted_app_file, 
                        signed_app_file ], check=True)
                        
                    #verify signature
                    subprocess.run([ python_exec, espsecure_path, "signature_info_v2", signed_bootloader_file ], check=True)
                    subprocess.run([ python_exec, espsecure_path, "signature_info_v2", signed_app_file ], check=True)
                    esp._port.close()
                    sys.exit(0)
                except subprocess.CalledProcessError as e:
                        print(f"[{port.device}] Error: Subprocess failed with return code {e.returncode}")
                        print(f"STDOUT: {e.stdout}")
                        print(f"STDERR: {e.stderr}")
                        esp._port.close()
                        sys.exit(1)
                except Exception as e:
                    print(f"[{port.device}] An unexpected exception occurred: {type(e).__name__} - {e}")
                    traceback.print_exc() 
                    esp._port.close()
                    sys.exit(1)
        except (serial.SerialException, FatalError) as e:
            print(f"[WARN] Could not open port {port.device}: {e}") 
        except Exception as e:
            print(f"[ERROR] Unexpected error on port {port.device}: {e}")  
    if not device_detected:
        print("No esp device detected on below given ports:")
        for p in ports:
            print(f"- {p.device}")
        sys.exit(1)

if __name__ == "__main__":
    main()  
