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
| `-f`, `--function` | Function code 1-4, 6, 16 (decimal or hex)    | required|
| `-a`, `--address`  | Start address (decimal or hex like `0x6B`)   | required|
| `-c`, `--count`    | Number of coils / registers to read          | 1       |
| `-v`, `--values`   | Values to write, decimal or hex              |         |

- Count (-c) used for reading registers and Values (-v) used for writing registers
- Address is the **0 based** address sent in the frame.
- Read functions: **0x01** Read Coils, **0x02** Read Discrete Inputs, **0x03** Read Holding Registers, **0x04** Read Input Registers
- Write functions: **0x06** Write Single Register, **0x10** Write Multiple Registers

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

Write value 3 to register 1 of slave 1 (0x06):

```
$ python3 modbus_rtu.py -p /dev/ttyUSB0 -s 1 -f 6 -a 1 -v 3
TX: 01 06 00 01 00 03 98 0b
```

Write values 10 and 0x102 to registers 1 and 2 of slave 1 (0x10):

```
$ python3 modbus_rtu.py -p /dev/ttyUSB0 -s 1 -f 16 -a 1 -v 10 0x102
TX: 01 10 00 01 00 02 04 00 0a 01 02 92 30
```

