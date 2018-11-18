from migen import *
from migen.genlib.fsm import FSM, NextValue, NextState

class COBS(Module):
    """
    Implements streaming consistent-overhead byte stuffing.
    """

    def __init__(self):
        self.din = Signal(8)
        self.inclk = Signal()

        self.dout = Signal(8)
        self.outrdy = Signal()

        ctr = Signal(8)
        dumpzero = Signal()

        self.submodules.fsm = FSM()
        self.fsm.act('IDLE',
            If(self.inclk,
                NextValue(ctr, self.din),
                NextState('DECODING'),
                If(dumpzero,
                    NextValue(self.dout, 0),
                    NextValue(self.outrdy, 1),
                ),
            )
        )

        bits_out_count = Signal(9)
        self.fsm.act('DECODING',
            If(bits_out_count < ctr - 1, # if we haven't finished with this block yet
                If(self.inclk, # wait for next data bit
                    NextValue(self.dout, self.din),
                    NextValue(self.outrdy, 1),
                    NextValue(bits_out_count, bits_out_count + 1),
                ).Else(
                    NextValue(self.outrdy, 0),
                )
            ).Else( # done with block?
                # append trailing 0x0 to block if it's shorter than 255 bytes
                NextValue(dumpzero, ctr < 255),
                NextValue(bits_out_count, 0),
                NextValue(self.outrdy, 0),
                NextState('IDLE'),
            )
        )
