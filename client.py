import serial
import sys
import struct
import time

with serial.Serial(sys.argv[1], 115200) as ser:
    i = 0
    while True:
        i += 1
        pixels = [0]*8
        pixels[i%8] = 0xffffff
        for value in pixels:
            dat = struct.pack('>L', value)[1:]
            print(dat.hex())
            ser.write(dat)
        time.sleep(0.1)

