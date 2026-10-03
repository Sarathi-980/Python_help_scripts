""" 
   Modbus RTU master script file
   Implemented direclty from the Modbus specification, depends only on pyserial

"""

import argparse
import struct 
import time
import serial

# Modbus maximum frame limit is 256 bytes, and we determine maximum quantity per read request based on function code.
# Overhead like slave address, function code, parity and CRC consumes 5 bytes.
MAX_READ_COUNT = {1 : 2000, 2 : 2000, 3 : 125, 4 : 125}

def modbus_rtu_crc16(data: bytes) -> int:
    crc = 0xFFFF
    # Iterating all bytes in data
    for byte in data:
        crc ^= byte
        # Iterating all 8 bits in byte
        for _ in range(8):
            # Checking whether LSB is 1
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
 
    return crc

def build_read_pdu(function: int, address: int, count: int) -> bytes:
    if function not in MAX_READ_COUNT:
        raise ValueError(f"function {function} is not a read function")
    if not 0 <= address <= 0xFFFF:
        raise ValueError(f"address {address} out of range 0-65535")
    if not 1 <= count <= MAX_READ_COUNT[function]:
        raise ValueError(f"count {count} out of range 1-{MAX_READ_COUNT[function]}")
    if address + count > 0x10000:
        raise ValueError("address + count goes past 65535")
    return struct.pack('>BHH', function, address, count)

def build_rtu_frame(slave: int, pdu: bytes) -> bytes:
    if not 1 <= slave <= 247:
        raise ValueError(f"slave {slave} out of range 1-247")
    frame = struct.pack('>B', slave) + pdu
    return frame + struct.pack('<H', modbus_rtu_crc16(frame))

# 3.5 times of char times is required or 1.75 ms is the minimum interval
def silent_interval(baud: int) -> float:
    if baud > 19200:
        return 0.00175
    return 3.5 * 11 / baud

def open_port(port: str, baud: int, parity: str, stopbits: int, timeout: float) -> serial.Serial:
    return serial.Serial(
        port=port,
        baudrate=baud,
        bytesize=serial.EIGHTBITS,
        parity=parity,
        stopbits=stopbits,
        timeout=timeout,
    )

def read_exact(ser: serial.Serial, n: int) -> bytes:
    data = ser.read(n)
    if len(data) != n:
        raise TimeoutError(f"expected {n} bytes, got {len(data)}: {data.hex(' ')}")
    return data

def transmit(ser: serial.Serial, frame: bytes) -> bytes:
    ser.reset_input_buffer()
    time.sleep(silent_interval(ser.baudrate))

    ser.write(frame)
    ser.flush()

    header = read_exact(ser, 3)
    if header[1] & 0x80:
        rest = read_exact(ser, 2)
    else:
        rest = read_exact(ser, header[2] + 2)

    response = header + rest

    if modbus_rtu_crc16(response) != 0:
        raise ValueError(f"CRC error: {response.hex(' ')}")
    if response[0] != frame[0]:
        raise ValueError(f"wrong slave {response[0]}, expected {frame[0]}")
    if response[1] & 0x7F != frame[1]:
        raise ValueError(f"wrong function 0x{response[1]:02X}, expected 0x{frame[1]:02X}")
    
    return response


def parse_args():
    parser = argparse.ArgumentParser(description="Modbus RTU master over RS-485")
 
    # Serial port settings
    parser.add_argument("-p", "--port", required=True,
                        help="serial port, e.g. COM3 or /dev/ttyUSB0")
    parser.add_argument("-b", "--baud", type=int, default=9600,
                        help="baud rate (default: 9600)")
    parser.add_argument("--parity", choices=["N", "E", "O"], default="N",
                        help="parity: N=none, E=even, O=odd (default: N)")
    parser.add_argument("--stopbits", type=int, choices=[1, 2], default=1,
                        help="stop bits (default: 1)")
    parser.add_argument("-t", "--timeout", type=float, default=1.0,
                        help="response timeout in seconds (default: 1.0)")
 
    # Modbus request settings
    parser.add_argument("-s", "--slave", type=lambda x: int(x, 0), required=True,
                        help="slave address 1-247, decimal or hex")
    parser.add_argument("-f", "--function", type=lambda x: int(x, 0), choices=[1, 2, 3, 4, 5, 6, 15, 16], required=True,
                        help="function code 1-4, decimal or hex.")
    parser.add_argument("-a", "--address", type=lambda x: int(x, 0), required=True,
                        help="start address, decimal or hex like 0x6B.")
    parser.add_argument("-c", "--count", type=int, default=1,
                        help="number of coils/registers to read.")
    parser.add_argument("-v", "--values", type=lambda x: int(x, 0), nargs="+",
                        help="value(s) to write, decimal or hex")
    return parser.parse_args()
 

