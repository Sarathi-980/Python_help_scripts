# MODBUS COMMUNICATION

## Modbus communication

- Modbus protocol is messaging structure, widely used to establish master-slave communication between intelligent devices.
- Modbus message sent from master to slave and it contains
    - Slave address (1 to 247)
    - command or function code (Read or Write)
    - data 
    - checksum.
- It is **Independent of the physical layer**. It is used in RS-485, RS-232 or RS-422. (Modbus TCP runs over Ethernet.)

## Modbus Request and Response

- Request: The message starts with address of the node it wants to communicate, function code is what kind of action, it wants to perform on the device and data bytes contains any additional information that slave will need to perform the action.
- Response: The slave makes response after it receives a valid request addressed to it. The function code in the response is same as request message if the action is success. If an error occurs, the function code is modified to indicate the error response and the data bytes contain a code that describes the error. 
- Only the master starts communication. Slave never talks unless master asks.
- Address 0 is **broadcast**. All slaves perform the action but nobody sends response. (Used only for write functions.)
- Controllers can be setup to communicate on standard modbus networks using either ASCII or RTU (Remote Terminal Unit). Modbus RTU is used mostly because it uses compact binary encoding with CRC error checking.
- RTU coding system is **8 bit binary**

## RTU FRAME
 ```
+----------------+-------------+------------+----------------+------------+------------------+
|      START     |   ADDRESS   |  FUNCTION  |     DATA       |    CRC     |       END        |
| 3.5 char times |  (8 BITS)   |  (8 BITS)  |  (N * 8 BITS)  | (16 BITS)  |  3.5 char times  |
+----------------+-------------+------------+----------------+------------+------------------+
```
- The RTU message starts with silent interval of at least 3.5 char times. 
- The first field is address, so each receiving device check whether the message is intended for them.
- The function indicates what kind of action, it need to perform in request and in response it returns same as request's function code if request is successful.
- The data field contains the data based on request or in response it contains requested action value if request is success. If error is response, this field contains error code.
- The CRC field is used to check integrity of the data received. All other fields are High, then Low byte while trasfer, But **CRC is Low byte then High byte**.
- The RTU message ends with silent interval of at least 3.5 char times.
- Maximum RTU frame size is **256 bytes**.

### Silent interval (3.5 char times)

- One character on the line is 11 bits (1 start + 8 data + parity or 2nd stop + 1 stop).
- At 9600 baud: 1 char = 11 / 9600 = ~1.15 ms, so 3.5 char = **~4 ms**.
- Above 19200 baud the spec uses fixed value of **1.75 ms**.
- If the line is silent more than 1.5 char times in middle of frame, receiver treats the frame as broken.

### Address field

- The address field contains 8 bits. The individual slave devices are assigned addresses in the range of 1 to 247
- 0 is broadcast address. 248 to 255 are reserved.

### Function code field

| Function code | Hex value | Function description     |
|---------------|-----------|--------------------------|
|        1      |   0x01    | Read Coils               |
|        2      |   0x02    | Read discrete inputs     |
|        3      |   0x03    | Read Holding registers   |
|        4      |   0x04    | Read input registers     |
|        5      |   0x05    | Write single coil        |
|        6      |   0x06    | Write single register    |
|        8      |   0x08    | Diagnostics              |
|        11     |   0x0B    | Get comm event counter   |
|        15     |   0x0F    | Write multiple coils     |
|        16     |   0x10    | Write multiple registers |
|        17     |   0x11    | Report server ID         |
|        22     |   0x16    | Mask write register      |
|        23     |   0x17    | Read/Write multiple regs |
|        43     |   0x2B    | Read device ID           |

### Byte order and addressing

- Address, quantity and register values in data field are sent **big endian** (high byte first).
- CRC is the only field sent **little endian** (low byte first).
- Address in the frame is **0 based**. Many manuals write "40001" for holding register, but in frame it is sent as 0x0000.

## MESSAGE FRAMES FOR EACH FUNCTION

- All examples below use slave address 0x01.
- All hex values are what actually goes on the wire, CRC included.

### 0x01 Read Coils

- Reads ON/OFF status of 1 to 2000 coils.

Request:

| Field             | Size    | Example |
|-------------------|---------|---------|
| Slave address     | 1 byte  | 01      |
| Function code     | 1 byte  | 01      |
| Starting address  | 2 bytes | 00 13   |
| Quantity of coils | 2 bytes | 00 13   |
| CRC               | 2 bytes | 8C 02   |

Response:

| Field          | Size    | Example  |
|----------------|---------|----------|
| Slave address  | 1 byte  | 01       |
| Function code  | 1 byte  | 01       |
| Byte count     | 1 byte  | 03       |
| Coil status    | N bytes | CD 6B 05 |
| CRC            | 2 bytes | 42 82    |

```
Request : 01 01 00 13 00 13 8C 02
Response: 01 01 03 CD 6B 05 42 82
```

- Coils are packed **8 per byte**, first coil in the **LSB** of first byte.
- Byte count = quantity / 8, rounded up. 19 coils needs 3 bytes.
- Unused bits in last byte are filled with 0.

### 0x02 Read Discrete Inputs

- Same frame as 0x01, only function code changes. Inputs are read-only.

```
Request : 01 02 00 C4 00 16 B8 39
Response: 01 02 03 AC DB 35 22 88
```

- 0x16 = 22 inputs, so byte count = 3.

### 0x03 Read Holding Registers

- Reads 1 to 125 registers. Each register is 16 bit.

Request:

| Field                 | Size    | Example |
|-----------------------|---------|---------|
| Slave address         | 1 byte  | 01      |
| Function code         | 1 byte  | 03      |
| Starting address      | 2 bytes | 00 6B   |
| Quantity of registers | 2 bytes | 00 03   |
| CRC                   | 2 bytes | 74 17   |

Response:

| Field           | Size        | Example           |
|-----------------|-------------|-------------------|
| Slave address   | 1 byte      | 01                |
| Function code   | 1 byte      | 03                |
| Byte count      | 1 byte      | 06                |
| Register values | N * 2 bytes | 02 2B 00 00 00 64 |
| CRC             | 2 bytes     | 05 7A             |

```
Request : 01 03 00 6B 00 03 74 17
Response: 01 03 06 02 2B 00 00 00 64 05 7A
```

- Byte count = quantity * 2.
- In this example register 0x6B = 0x022B (555), 0x6C = 0 and 0x6D = 0x0064 (100).

### 0x04 Read Input Registers

- Same frame as 0x03, only function code changes. Input registers are read-only.

```
Request : 01 04 00 08 00 01 B0 08
Response: 01 04 02 00 0A 39 37
```

- Register 0x08 = 0x000A (10).

### 0x05 Write Single Coil

| Field          | Size    | Example |
|----------------|---------|---------|
| Slave address  | 1 byte  | 01      |
| Function code  | 1 byte  | 05      |
| Coil address   | 2 bytes | 00 AC   |
| Value          | 2 bytes | FF 00   |
| CRC            | 2 bytes | 4C 1B   |

```
Request : 01 05 00 AC FF 00 4C 1B
Response: 01 05 00 AC FF 00 4C 1B
```

- Value must be **FF 00 for ON** and **00 00 for OFF**. Any other value is error.
- Response is **echo of request** (exact same bytes).

### 0x06 Write Single Register

| Field            | Size    | Example |
|------------------|---------|---------|
| Slave address    | 1 byte  | 01      |
| Function code    | 1 byte  | 06      |
| Register address | 2 bytes | 00 01   |
| Register value   | 2 bytes | 00 03   |
| CRC              | 2 bytes | 98 0B   |

```
Request : 01 06 00 01 00 03 98 0B
Response: 01 06 00 01 00 03 98 0B
```

- Response is also **echo of request**.

### 0x0F Write Multiple Coils

Request:

| Field             | Size    | Example |
|-------------------|---------|---------|
| Slave address     | 1 byte  | 01      |
| Function code     | 1 byte  | 0F      |
| Starting address  | 2 bytes | 00 13   |
| Quantity of coils | 2 bytes | 00 0A   |
| Byte count        | 1 byte  | 02      |
| Coil values       | N bytes | CD 01   |
| CRC               | 2 bytes | 72 CB   |

Response:

| Field             | Size    | Example |
|-------------------|---------|---------|
| Slave address     | 1 byte  | 01      |
| Function code     | 1 byte  | 0F      |
| Starting address  | 2 bytes | 00 13   |
| Quantity of coils | 2 bytes | 00 0A   |
| CRC               | 2 bytes | 24 09   |

```
Request : 01 0F 00 13 00 0A 02 CD 01 72 CB
Response: 01 0F 00 13 00 0A 24 09
```

- Coil values are packed same way as 0x01 (LSB first).
- Response does not echo the values, only address and quantity.

### 0x10 Write Multiple Registers

Request:

| Field                 | Size        | Example     |
|-----------------------|-------------|-------------|
| Slave address         | 1 byte      | 01          |
| Function code         | 1 byte      | 10          |
| Starting address      | 2 bytes     | 00 01       |
| Quantity of registers | 2 bytes     | 00 02       |
| Byte count            | 1 byte      | 04          |
| Register values       | N * 2 bytes | 00 0A 01 02 |
| CRC                   | 2 bytes     | 92 30       |

Response:

| Field                 | Size    | Example |
|-----------------------|---------|---------|
| Slave address         | 1 byte  | 01      |
| Function code         | 1 byte  | 10      |
| Starting address      | 2 bytes | 00 01   |
| Quantity of registers | 2 bytes | 00 02   |
| CRC                   | 2 bytes | 10 08   |

```
Request : 01 10 00 01 00 02 04 00 0A 01 02 92 30
Response: 01 10 00 01 00 02 10 08
```

- Writes 1 to 123 registers in one frame.
- Byte count = quantity * 2.

### Exception (error) response

- If slave cannot do the action, it sets the **MSB of function code** (function code + 0x80) and sends 1 byte exception code.

| Field          | Size    | Example |
|----------------|---------|---------|
| Slave address  | 1 byte  | 01      |
| Function code  | 1 byte  | 83      |
| Exception code | 1 byte  | 02      |
| CRC            | 2 bytes | C0 F1   |

```
Response: 01 83 02 C0 F1    (0x03 request failed, illegal data address)
```

| Exception code | Name                  | Meaning                                       |
|----------------|-----------------------|-----------------------------------------------|
|      0x01      | Illegal function      | Slave does not support this function code     |
|      0x02      | Illegal data address  | Address or address + quantity is out of range |
|      0x03      | Illegal data value    | Value in data field is not allowed            |
|      0x04      | Slave device failure  | Error happened inside slave while doing action|
|      0x05      | Acknowledge           | Accepted, but needs long time to finish       |
|      0x06      | Slave device busy     | Slave is busy, master should retry later      |

- If slave receives frame with **wrong CRC**, it sends **no response**. Master only sees timeout.

## CRC calculation for Modbus RTU

1. Initialize the 16 bit register with 0xFFFF
2. for each data byte follow:
    - XOR the data byte with the lower byte of the 16 bit CRC register. store back in CRC register.
    - repeat below **8 times** (once for each bit):
        - examine the LSB **before** shifting
        - shift the CRC register right by 1
        - if LSB was 1, XOR the CRC register with the value 0xA001.
        - if LSB was 0, do not XOR
3. Repeat for all bytes in the frame (address + function + data). CRC field itself is not included.
4. Result of this is 16 bit CRC value is appended to the message frame with lower byte first then upper byte.

- Check example: `01 03 00 00 00 02` gives CRC 0x0BC4, sent as **C4 0B**.
- On receive side, calculating CRC over the whole frame including CRC bytes gives **0x0000** if frame is correct.
