from migen import *

from util import closest_divisor


class WS2812PHY(Module):
    def __init__(self, pads, data_width, freq_base, freq_tx=8e5, latch_length=5.41e-5):
        self.pads = pads

        self.tx_ack = Signal()
        self.tx_ready = Signal()
        self.tx_latch = Signal()
        self.data = Signal(data_width)


        ###

        self.reg = Signal(data_width)
        self.pwm_strobe = Signal()

        ###

        divisor = closest_divisor(freq_base, freq_tx * 3, max_ppm=50000)
        self.pwm_counter = Signal(max=divisor)

        self.sync += If(self.pwm_counter == 0,
            self.pwm_strobe.eq(1),
            self.pwm_counter.eq(divisor - 1)
        ).Else(
            self.pwm_strobe.eq(0),
            self.pwm_counter.eq(self.pwm_counter - 1)
        )


        self.submodules.tx_fsm = FSM(reset_state='IDLE')

        self.tx_fsm.act('IDLE',
            self.tx_ack.eq(1),
            If(self.tx_ready,
                NextValue(self.reg, self.data),
                NextState('WRITE')
            ).Elif(self.tx_latch,
                NextState('LATCH')
            ),
        )

        self.bitno = Signal(max=data_width+10)
        self.modulation_counter = Signal(max=3)
        self.tx_fsm.act('WRITE',
            If(self.pwm_strobe,
                Case(self.modulation_counter, {
                    0: NextValue(self.pads.tx, 1),
                    1: NextValue(self.pads.tx, self.reg[-1]),
                    2: NextValue(self.pads.tx, 0)
                }),

                NextValue(self.modulation_counter, self.modulation_counter + 1),
                If(self.modulation_counter == 2,
                    NextValue(self.modulation_counter, 0),
                    NextValue(self.reg, Cat(0, self.reg[0:-1])),
                    NextValue(self.bitno, self.bitno + 1),
                    If(self.bitno == data_width-1,
                        NextState('IDLE'),
                        NextValue(self.bitno, 0),
                    )
                )
            )
        )

        latch_cycles = int(freq_base * latch_length)
        self.latch_counter = Signal(max=latch_cycles, reset=0)
        self.tx_fsm.act('LATCH',
            If(self.latch_counter == latch_cycles,
                NextValue(self.latch_counter, 0),
                NextState('IDLE'),
            ).Else(
                NextValue(self.latch_counter, self.latch_counter + 1),
                NextState('LATCH'),
            )
        )
