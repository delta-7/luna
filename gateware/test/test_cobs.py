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

    def unstuff(self, inbs):
        produced = []
        for inb in inbs:
            yield from self.input_byte(inb)
            yield
            if (yield self.cobs.outrdy) == 1:
                produced.append((yield self.cobs.dout))
            yield

        return produced


class COBSTestCase(TestCase):
    def setUp(self):
        self.tb = COBSTestbench()

    def assertSignal(self, signal, value):
        self.assertEqual((yield signal), value)

    @simulation_test
    def test_basic_cobs(self, tb):
        produced = yield from self.tb.unstuff([0x02, 0x66, 0x02, 0x6f])
        self.assertEqual(produced, [0x66, 0x00, 0x6f])

    @simulation_test
    def test_longer_cobs(self, tb):
        data = b'Lorem\0ipsum\0dolor\0sit\0amet,\0consectetur\0adipiscing\0elit,\0sed\0do\0eiusmod\0tempor\0incididunt'
        encoded = cobs_encode(data)

        produced = yield from self.tb.unstuff(encoded)
        self.assertEqual(bytes(produced), data)

    @simulation_test
    def test_more_than_one_block(self, tb):
        data = (
            b'Lorem\0ipsum\0dolor\0sit\0amet,\0consectetur\0adipiscing\0elit,\0sed\0do\0eiusmod\0tempor\0incididunt\0ut\0labore\0et\0dolore '
            b'magna\0aliqua.\0Ut\0enim\0ad\0minim\0veniam,\0quis\0nostrud\0exercitation\0ullamco\0laboris nisi ut aliquip ex ea commodo '
            b'consequat. Duis aute irure dolor in reprehenderit\0in\0voluptate\0velit\0esse\0cillum\0dolore\0eu\0fugiat\0nulla pariatur. '
            b'Excepteur sint occaecat cupidatat non proident, sunt\0in\0culpa\0qui\0officia\0deserunt\0mollit\0anim\0id\0est\0laborum.'
        )
        encoded = cobs_encode(data)

        produced = yield from self.tb.unstuff(encoded)
        print(bytes(produced))
        print(data)
        self.assertEqual(bytes(produced), data)


    @simulation_test
    def test_more_than_one_block_no_zeros(self, tb):
        data = (
            b'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore '
            b'magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo '
            b'consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. '
            b'Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'
        )
        encoded = cobs_encode(data)

        produced = yield from self.tb.unstuff(encoded)
        print(bytes(produced))
        print(data)
        self.assertEqual(bytes(produced), data)
