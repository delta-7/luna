from collections import OrderedDict
from functools import reduce
from operator import xor

from migen import *

# from Liteeth: https://github.com/enjoy-digital/liteeth/blob/95849a0fed26c2f7e88e731e8ba7cb6b95d873e8/liteeth/core/mac/crc.py
class CRCEngine(Module):
    """Cyclic Redundancy Check Engine

    Compute next CRC value from last CRC value and data input using
    an optimized asynchronous LFSR.

    Parameters
    ----------
    data_width : int
        Width of the data bus.
    width : int
        Width of the CRC.
    polynom : int
        Polynom of the CRC (ex: 0x04C11DB7 for IEEE 802.3 CRC)

    Attributes
    ----------
    data : in
        Data input.
    last : in
        last CRC value.
    next :
        next CRC value.
    """
    def __init__(self, data_width, width, polynom):
        self.data = Signal(data_width)
        self.last = Signal(width)
        self.next = Signal(width)

        # # #

        def _optimize_eq(l):
            """
            remove an even numbers of XORs with the same bit
            replace an odd number of XORs with a single XOR
            """
            d = OrderedDict()
            for e in l:
                if e in d:
                    d[e] += 1
                else:
                    d[e] = 1
            r = []
            for key, value in d.items():
                if value%2 != 0:
                    r.append(key)
            return r

        # compute and optimize the parallel implementation of the CRC's LFSR
        taps = [x for x in range(width) if (1 << x) & polynom]
        curval = [[("state", i)] for i in range(width)]
        for i in range(data_width):
            feedback = curval.pop() + [("din", i)]
            for j in range(width-1):
                if j+1 in taps:
                    curval[j] += feedback
                curval[j] = _optimize_eq(curval[j])
            curval.insert(0, feedback)

        # implement logic
        for i in range(width):
            xors = []
            for t, n in curval[i]:
                if t == "state":
                    xors += [self.last[n]]
                elif t == "din":
                    xors += [self.data[n]]
            self.comb += self.next[i].eq(reduce(xor, xors))


@ResetInserter()
@CEInserter()
class LuxCRC(Module):
    width = 32
    polynom = 0x04C11DB7
    init = 2**width - 1

    def __init__(self, data_width):
        self.data = Signal(data_width)
        self.value = Signal(self.width)

        ###

        self.submodules.engine = CRCEngine(data_width, self.width, self.polynom)

        reg = Signal(self.width, reset=self.init)

        self.sync += reg.eq(self.engine.next)

        self.comb += [
            self.engine.data.eq(self.data),
            self.engine.last.eq(reg),

            self.value.eq(~reg[::-1]), # reverse and invert
        ]
