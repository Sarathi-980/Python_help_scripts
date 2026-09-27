import subprocess
import os
import sys
import re
import esptool
import traceback
import serial.tools.list_ports

from esptool.util import FatalError
from esptool.cmds import detect_chip

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

python_execution = sys.executable  
current_directory = os.getcwd()
MAC_str = ""

target_chip = os.environ.get("target_chip")
target_key = "burnkey"
target_efuse = "burnefuse"
target_efuse_write_protect = "write_protect"
baud_rate = os.environ.get("baud_rate") 
ports =  serial.tools.list_ports.comports()

## Enable below function and before make sure what efuses you going to burn
# def device_efuse_burn(port_value, target, efuse_burn_target, binary_file, key_purpose, efuse_value): 
#     efuse_burn_command = [python_execution, espfuse_path, "--port", port_value, "--chip", target_chip ]

#     # Case 1: Burn a key into eFuse (flash encryption key, secure boot key)
#     if target == target_key:
#         efuse_burn_command += ["burn_key", efuse_burn_target, binary_file, key_purpose ]
#     # Case 2: Burn a normal eFuse field 
#     elif target == target_efuse:  
#         efuse_burn_command.append("burn_efuse")
#         if efuse_burn_target is not None:
#             efuse_burn_command.append(efuse_burn_target)
#         if efuse_value is not None:
#             efuse_burn_command.append(efuse_value) 
#     elif target == target_efuse_write_protect:
#         efuse_burn_command += ["write_protect_efuse", efuse_burn_target ] 
#     else:   
#         raise ValueError(f"Invalid target: {target}. Expected 'key' or 'efuse'.")

#     try: 
#         burning_process = subprocess.Popen(
#             efuse_burn_command,
#             stdin = subprocess.PIPE,
#             stdout = subprocess.PIPE,
#             stderr = subprocess.STDOUT,
#             text = True,
#             bufsize = 1
#          )
 
#         while True:
#             line = burning_process.stdout.readline()
#             if not line:
#                 break  
#             print(line.strip())

#             # Before Efuse write it will ask to type "BURN", so we are using this.
#             if "Type 'BURN' (all capitals) to continue." in line:
#                 print("Sending BURN efuse command")
#                 burning_process.stdin.write("BURN\n")
#                 burning_process.stdin.flush()
 
#         #waiting for burning command returns
#         burning_process.wait() 
 
#         if burning_process.returncode != 0:
#             raise RuntimeError(f"BURN {target} command failed for {efuse_burn_target}.")
#     except Exception as e:
#         raise RuntimeError(f"Failed to burn efuse {efuse_burn_target}: {e}") 

def main(): 
    device_detected = False
    for port in ports: 
        try:
            print(f"Trying to connect {target_chip} via {port.device}")
            with detect_chip(port.device) as esp:
                try:
                    esp._port.close()
                    device_detected = True
                    result = subprocess.run(
                        [python_execution, espfuse_path, "--port", port.device, "--chip", target_chip, "summary"],
                        capture_output=True,
                        text=True,
                        check=True
                   )

                    efuse_summary = result.stdout 
                    #finding MAC in efuse, we can also use this type, but here I read all efuses and extracted MAC regex
                    MAC_pattern = r"MAC \(BLOCK1\).*?MAC address\s*\n\s*=\s*([0-9a-fA-F:]{17})"
                    device_MAC_match = re.search(MAC_pattern, efuse_summary)
                    if device_MAC_match:
                        read_MAC = device_MAC_match.group(1)
                        # MAC has : in output, AB:AB:AB:AB:AB:AB
                        MAC_str = read_MAC.replace(":", "")  

                    flash_encryption_key_file_name = "flash_encryption_key_" + MAC_str + ".bin"
                    device_secrets_folder = os.path.join(current_directory, "device_secrets")
                    if not os.path.isdir(device_secrets_folder):
                        raise Exception("device secrets folder not found.")
                    
                    flash_encryption_keys_folder = os.path.join(device_secrets_folder, "flash_encryption_keys")
                    if not os.path.isdir(flash_encryption_keys_folder):
                        raise Exception("flash encryption keys folder not found.")

                    current_device_flash_encryption_key = os.path.join(flash_encryption_keys_folder, flash_encryption_key_file_name)
                    if not os.path.exists(current_device_flash_encryption_key):
                        raise Exception(f"{MAC_str} flash encryption key not found.")

                    common_digest_file = os.path.join(device_secrets_folder, "secureboot_digest.bin")
                    if not os.path.exists(common_digest_file):
                        raise Exception(f"digest file not found.")

                    device_firmware_folder = os.path.join(current_directory, "device_firmware")
                    if not os.path.isdir(device_firmware_folder):
                        raise Exception(f"device firmware folder not found.")

                    encrypted_flash_folder_name = "encrypted_flash_firmware_" + MAC_str
                    encrypted_flash_encrypted_folder = os.path.join(device_firmware_folder, encrypted_flash_folder_name) 
                    if not os.path.isdir(encrypted_flash_encrypted_folder):
                        raise Exception(f"{MAC_str} encrypted flash firmware is not found.")

                    flash_encrypted_bootloader_file = os.path.join(encrypted_flash_encrypted_folder, "bootloader_encrypted.bin")
                    if not os.path.exists(flash_encrypted_bootloader_file):
                        raise Exception(f"{MAC_str} flash encrypted bootloader file not found.")
                    flash_encrypted_partition_file = os.path.join(encrypted_flash_encrypted_folder, "partition_table_encrypted.bin") 
                    if not os.path.exists(flash_encrypted_partition_file):
                        raise Exception(f"{MAC_str} flash encrypted partition file not found.")
                    flash_encrypted_app_file = os.path.join(encrypted_flash_encrypted_folder, "app_encrypted.bin")
                    if not os.path.exists(flash_encrypted_app_file):
                        raise Exception(f"{MAC_str} flash encrypted app file not found.") 
 
                    # SPI_BOOT_CRYPT_CNT indicates flash encryption state:
                    #   Enable  -> flash encryption active
                    #   Disable -> flash encryption not  active
                     flash_encryption_match = re.search(
                        r'SPI_BOOT_CRYPT_CNT.*?=\s*(Enable|Disable)\s*(R/W|-/W|R/-|-/-)\s*\((0b[01]+)\)',
                        efuse_summary
                    )

                    # Check flash encryption key block (Key0 in BLOCK_KEY0)
                    # "00" indicates empty/unprogrammed key
                    # "??" indicates already programmed, by default it is only readable by device that's why it is ??.
                    flash_key_match = re.search(
                        r'(Key0).*?=\s*([0\?]{2})',
                        efuse_summary,
                        re.DOTALL
                    )

                    # Handle flash encryption status
                    if flash_encryption_match:
                        print(
                            f'Flash encryption {flash_encryption_match.group(1)}d '
                            f'and value is {flash_encryption_match.group(3)} for Device {MAC_str}'
                        )

                        # Convert efuse state into boolean flag
                        flash_encryption_enabled = (
                            True if flash_encryption_match.group(1) == 'Enable'
                            else False if flash_encryption_match.group(1) == 'Disable'
                            else None
                        )

                        # Determine flash encryption mode based on SPI_BOOT_CRYPT_CNT value
                        # 0b111 -> Release (production secure mode)
                        # 0b001 -> Development mode (less secure, used for testing)
                        flash_encryption_mode = (
                            "Release mode" if flash_encryption_match.group(3) == '0b111'
                            else "Development mode" if flash_encryption_match.group(3) == '0b001'
                            else "currently Disabled mode"
                        )

                        # If flash encryption is already enabled
                        if flash_encryption_enabled:

                            if flash_encryption_mode == "Release mode":
                                print(f"Flash encryption for Device: {MAC_str} is enabled in production mode.")
                            else:
                                print(f"Flash encryption for Device: {MAC_str} is enabled in development mode.")

                                # Upgrade device from development mode to production mode
                                # by burning SPI_BOOT_CRYPT_CNT = 0x7
                                print("flash efuse burned to 0x07 after enable")

                                # device_efuse_burn(
                                #     port.device,
                                #     target_efuse,
                                #     efuse_burn_target="SPI_BOOT_CRYPT_CNT",
                                #     binary_file=None,
                                #     key_purpose=None,
                                #     efuse_value="0x7"
                                # )

                        # Flash encryption NOT enabled yet → provisioning flow
                        else:

                            # Check flash encryption key state (BLOCK_KEY0)
                            if flash_key_match:

                                # Case: Key slot is empty (00) → burn new key
                                if (flash_key_match.group(1) == "Key0" and flash_key_match.group(2) == "00"):

                                    # device_efuse_burn(
                                    #     port.device,
                                    #     target_key,
                                    #     efuse_burn_target="BLOCK_KEY0",
                                    #     binary_file=current_device_flash_encryption_key,
                                    #     key_purpose="XTS_AES_128_KEY",
                                    #     efuse_value=None
                                    # )

                                    print(f"Flash key burned for device: {MAC_str}")

                                # Case: Key already exists
                                elif (flash_key_match.group(1) == "Key0" and flash_key_match.group(2) == "??"):
                                    print(f"Flash key already burned for device: {MAC_str}")

                                # Unexpected state, likely corrupted or misread eFuse data
                                else:
                                    print("misconfigure data in efuse block key0.")
                                    raise ValueError("invalid data in key0.")

                            # Ensure SPI_BOOT_CRYPT_CNT is set correctly
                            if flash_encryption_match.group(3) != "0b111":

                                # Force production-safe flash encryption mode (0x7)
                                # device_efuse_burn(
                                #     port.device,
                                #     target_efuse,
                                #     efuse_burn_target="SPI_BOOT_CRYPT_CNT",
                                #     binary_file=None,
                                #     key_purpose=None,
                                #     efuse_value="0x7"
                                # )

                                print(f"Flash key efuse set to 0x7: {MAC_str}")

                            else:
                                print(f"Flash key efuse is already 0x7: {MAC_str}")

                    # Parse Secure Boot enable status from efuse summary output
                    # Example matched line:
                    # SECURE_BOOT_EN = True/False (R/W) (0b1)
                    secureboot_match = re.search(
                        r'SECURE_BOOT_EN.*?=\s*(True|False)\s*(R/W|R/-|-/W|-/-)\s*\((0b[01])\)',
                        efuse_summary
                    )

                    # Parse Secure Boot digest (BLOCK_KEY1 contains secure boot digest data)
                    # Extracts first 3 bytes from efuse dump for validation
                    secureboot_digest_match = re.search(
                        r'(BLOCK_KEY1).*?=\s*([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})',
                        efuse_summary,
                        re.DOTALL
                    ) 
                    if secureboot_digest_match:

                        # Extract first 3 bytes of BLOCK_KEY1
                        first_group = int(secureboot_digest_match.group(2), 16)
                        second_group = int(secureboot_digest_match.group(3), 16)
                        third_group = int(secureboot_digest_match.group(4), 16)

                        # If all extracted values are 0, digest is not yet burned
                        if first_group == 0 and second_group == 0:

                            if third_group == 0:
                                # Burn secure boot digest into BLOCK_KEY1
                                # Uses shared digest file (common_digest_file)
                                # device_efuse_burn(
                                #     port.device,
                                #     target_key,
                                #     efuse_burn_target="BLOCK_KEY1",
                                #     binary_file=common_digest_file,
                                #     key_purpose="SECURE_BOOT_DIGEST0",
                                #     efuse_value=None
                                # )

                                print(f"secure boot digest burned for: {MAC_str}")

                        else:
                            # Non-zero values indicate digest already exists (already provisioned)
                            print(f"secure boot digest already burned for: {MAC_str}")

                    if secureboot_match:

                        # Convert matched string into boolean state
                        secureboot_enabled = True if secureboot_match.group(1) == 'True' else False

                        print(
                            f"Secureboot is {'Enabled' if secureboot_enabled else 'Disabled'} "
                            f"with value of {secureboot_match.group(3)} for Device {MAC_str}"
                        )

                        # If already enabled, skip burning
                        if secureboot_enabled:
                            print("Secureboot already enabled")

                        else:
                            # Enable secure boot by burning SECURE_BOOT_EN eFuse bit
                            # device_efuse_burn(
                            #     port.device,
                            #     target_efuse,
                            #     efuse_burn_target="SECURE_BOOT_EN",
                            #     binary_file=None,
                            #     key_purpose=None,
                            #     efuse_value=None
                            # )

                            print(f"Secure boot enabled: {MAC_str}")

                    # SOFT_DIS_JTAG if odd bits then disabled else enabled
                    # RD_DIS disabled reading Block 4-10
                    # "DIS_DIRECT_BOOT", "DIS_DOWNLOAD_ICACHE", "DIS_DOWNLOAD_DCACHE","DIS_DOWNLOAD_MANUAL_ENCRYPT", "DIS_ICACHE",
                    production_disable_efuses = ["DIS_USB_JTAG", \
                                         "SOFT_DIS_JTAG", "SECURE_BOOT_AGGRESSIVE_REVOKE", "RD_DIS", "ENABLE_SECURITY_DOWNLOAD"] 
                    for efuse in production_disable_efuses:
                        pattern = fr"{efuse} \(BLOCK0\).*?=\s*(\d+|True|False).*?(R/-|W/-|R/W|-/-)\s*\((0b[01]+)\)"

                        match = re.search(pattern, efuse_summary)
                        if match:
                            efuse_status = match.group(1)
                            efuse_rw = match.group(2)
                            efuse_value = match.group(3)
                            if efuse == "RD_DIS" or efuse == "DIS_ICACHE":
                                if efuse_rw == 'R/-':
                                    print(f"{efuse} is already burned to write protect.")
                                elif efuse_rw == 'R/W':   
                                    print("efuse burn")
                                    #device_efuse_burn(port.device, target_efuse_write_protect, efuse, binary_file=None, key_purpose=None, efuse_value=None)
                                else:
                                    raise RuntimeError(f"Check {efuse} Read Write configuration.") 
                            else:
                                if efuse == "SOFT_DIS_JTAG":
                                    if efuse_status == '7' and efuse_value == '0b111':
                                        print(f"{efuse} is already burned to 0b111.")
                                    elif efuse_status == '0' and efuse_value == '0b000':
                                        print("efuse burn")
                                        #device_efuse_burn(port.device, target_efuse, efuse, binary_file=None, key_purpose=None, efuse_value="0x7")
                                    else:
                                        raise RuntimeError(f"The {efuse} have wrong efuse value")
                                else:
                                    if efuse_status == 'True' and efuse_value == '0b1':
                                        print(f"{efuse} is already burned to 0b1")
                                    elif efuse_status == 'False' and efuse_value == '0b0':
                                        print("efuse burn")
                                        #device_efuse_burn(port.device, target_efuse, efuse, binary_file=None, key_purpose=None, efuse_value="0x1")
                                    else:
                                        raise RuntimeError(f"The {efuse} have wrong efuse value")
                        else:
                            raise RuntimeError(f"The {efuse} not found in summary")

                    #Running flash command
                    subprocess.run([
                        python_execution,
                        esptool_path,
                        "--chip", target_chip,
                        "--port", port.device,
                        "--baud", baud_rate,
                        "--no-stub",
                        "write_flash", "--force",
                        "0x0", flash_encrypted_bootloader_file,
                        "0x10000", flash_encrypted_partition_file,
                        "0x20000", flash_encrypted_app_file
                    ], check=True)

                    esp._port.close()
                    sys.exit(0)
                
                except subprocess.CalledProcessError as e:
                    print(f"[{port.device}]Error: Subprocess failed with return code {e.returncode}")
                    print(f"STDOUT: {e.stdout}")
                    print(f"STDERR: {e.stderr}")
                    esp._port.close()
                    sys.exit(1) 
                except Exception as e:
                    print(f"[{port.device}]An unexpected exception occurred: {type(e).__name__} - {e}")
                    traceback.print_exc() 
                    esp._port.close()
                    sys.exit(1)
        except (serial.SerialException, FatalError) as e:
            print(f"[WARN] Could not open port {port.device}: {e}") 
        except Exception as e:
            print(f"[ERROR] Unexpected error on port {port.device}: {e}") 
    if not device_detected:
        print("No device detected to flash and given ports are:")
        for p in ports:
            print(f"- {p.device}")

if __name__ == "__main__":
    main()
