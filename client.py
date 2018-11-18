import serial
import sys
import struct

with serial.Serial(sys.argv[1], 115200) as ser:
    values = [0x00ffff,
              0xff00ff,
              ]
    for value in values:
        dat = struct.pack('>L', value)[1:]
        print(dat.hex())
        ser.write(dat)

