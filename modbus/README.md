# MODBUS RTU MASTER IN PYTHON
    
- Modbus RTU master for serial lines and implemented directly from modbus spec, depends only on **pyserial**. 
- Frame building, CRC-16 and response validation are written from scratch.
    
## Modbus 

- Modbus is a messaging protocol for master-slave based intellingent devices.
- It is independent of physical layers of RS485, RS232, RS422 or TCP on ethernet.
- The messages are sent in continuous stream of bytes.

## Why python script for modbus

- Since modbus in independent of the physical layer, we can use the generic python script to all modbus based devices. 
- If we can easily transform code for particular device by add extra features on it, because based on device features differ like Some devices use floating pointer representation from register values.
- We can make the device readings more readable in debugging the problem.
- We can add our error handling mechanisms for timeout and some devices **only accept multiple write registers (fc : 0x10)**, they won't accept single write if we try single write on those devices will cause timeout.

## Requirements

- Python 3.8 or newer
- pyserial

```
pip install pyserial
```

## Usage

```
python modbus_rtu.py -p <port> [options]
```

| Option             | Description                                  | Default |
|--------------------|----------------------------------------------|---------|
| `-p`, `--port`     | Serial port, e.g. `COM3` or `/dev/ttyUSB0`   | required|
| `-b`, `--baud`     | Baud rate                                    | 9600    |
| `--parity`         | `N` none, `E` even, `O` odd                  | N       |
| `--stopbits`       | 1 or 2                                       | required|
| `-t`, `--timeout`  | Response timeout in seconds                  | 1.0     |
| `-s`, `--slave`    | Slave address 1-247 (decimal or hex)         | required|
| `-f`, `--function` | Function code 1-4 (decimal or hex)           | required|
| `-a`, `--address`  | Start address (decimal or hex like `0x6B`)   | required|
| `-c`, `--count`    | Number of coils / registers to read          | 1       |

- Address is the **0 based** address sent in the frame.

## Scope

- This script is act like Modbus RTU master, using pyserial module.
- It doesn't support other ASCII, TCP based modbus communnication.

## Hardware setup

- USB to RS-485 adapter connected to the slave.
- Wiring: **A+ to A+**, **B- to B-** **(Here we must see the signal sign + and - not A or B)** and **GND to GND**. Some vendors swap the A/B naming, so if there is no response try swapping A and B.
- On long cables, put **120 ohm termination** resistor at both ends of the bus.
- Serial settings (baud, parity, stop bits) and slave address must match the device exactly.

## Example

Read 3 holding registers from slave 1, starting at address 0x6B:

```
$ python modbus_rtu.py -p COM3 -s 1 -f 3 -a 0x6B -c 3
TX: 01 03 00 6b 00 03 74 17
RX: 01 03 06 02 2b 00 00 00 64 05 7a
``` 
