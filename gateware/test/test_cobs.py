from unittest import TestCase
from migen import *
from .util import simulation_test
from ..cobs import COBS

def cobs_encode(data):
    output = b''
    data += b'\0'
    ptr = 0
    while ptr < len(data):
        next_zero = data.index(b'\0', ptr)
        if next_zero - ptr >= 254:
            output += b'\xFF' + data[ptr:ptr+254]
            ptr += 254
        else:
            output += bytearray((next_zero - ptr + 1,)) + data[ptr:next_zero]
            ptr = next_zero + 1
    return output

def cobs_decode(data):
    output = b''
    ptr = 0
    while ptr < len(data):
        ctr = data[ptr]
        if ptr + ctr > len(data):
            raise DecodeError("COBS decoding failed", repr(data))
        output += data[ptr + 1:ptr + ctr]
        if ctr < 255:
            output += b'\0'
        ptr += ctr
    if ptr != len(data):
        raise DecodeError("COBS decoding failed", repr(data))
    return output[0:-1]

class COBSTestbench(Module):
    def __init__(self):
        self.submodules.cobs = COBS()

    def input_byte(self, x):
        yield self.cobs.din.eq(x)
        yield self.cobs.inclk.eq(1)
        yield
        yield self.cobs.inclk.eq(0)
        # yield

    def assert_inout(self, inbs, outbs):
        yield from self.input_byte(inbs[0])
        yield; yield
        for (inb, outb) in zip(inbs[1:], outbs):
            print(hex(inb), hex(outb))
            yield from self.input_byte(inb)
            assert (yield self.cobs.outrdy) == 1
            assert (yield self.cobs.dout) == outb
            yield
            assert (yield self.cobs.outrdy) == 0
            yield


class COBSTestCase(TestCase):
    def setUp(self):
        self.tb = COBSTestbench()

    def assertSignal(self, signal, value):
        self.assertEqual((yield signal), value)

    @simulation_test
    def test_basic_cobs(self, tb):
        yield from self.tb.assert_inout([0x02, 0x66, 0x02, 0x6f],
            [0x66, 0x00, 0x6f])

    @simulation_test
    def test_longer_cobs(self, tb):
        data = b'Lorem\0ipsum\0dolor\0sit\0amet,\0consectetur\0adipiscing\0elit,\0sed\0do\0eiusmod\0tempor\0incididunt'
        encoded = cobs_encode(data)

        yield from self.tb.assert_inout(encoded, data)
