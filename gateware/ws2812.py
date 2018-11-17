from migen import *
from migen.genlib.fifo import AsyncFIFO

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

# class WS2812Controller(Module):
#     def __init__(self, pads, n_leds, freq_base):
#         self.writeout = Signal()

#         ###

#         self.submodules.phy = WS2812PHY(pads, 24, freq_base)
#         self.submodules.data = SyncFIFO(24, n_leds) # TODO: ugh should this be AsyncFIFO

#         self.submodules.framing_fsm = FSM()
#         self.framing_fsm.act('IDLE',
#             If(self.writeout, NextState('TXING')))

#         # self.framing_fsm.act('TXING',
#         #     If(self.data.))

if __name__ == '__main__':
    from migen.build.platforms import icestick
    def tb(dut):
        yield dut.data.eq(0xaaaaaa)
        yield dut.tx_ready.eq(1)
        yield
        yield dut.tx_ready.eq(0)
        for _ in range(3000): yield

    class PhysCore(Module):
        def __init__(self, plat):
            from migen.build.generic_platform import Subsignal, IOStandard, Pins
            neopixel_gpio = [
                ('neopixel', 0,
                    Subsignal('tx', Pins('PMOD:0')),
                    IOStandard('LVCMOS33')
                )
            ]

            plat.add_extension(neopixel_gpio)
            neopixel_pads = plat.request('neopixel')

            # self.submodules.controller = WS2812Controller(neopixel_pads, 8, 12000000)

            self.submodules.phy = WS2812PHY(neopixel_pads, 24, freq_base=12000000, freq_tx=8e5)
            self.comb += self.phy.data.eq(0xd6afd2)

            self.submodules.framing_fsm = FSM()
            self.framing_fsm.act('IDLE',
                NextValue(self.phy.tx_ready, 1),
                NextState('TX_DAT'),
            )

            self.framing_fsm.act('TX_DAT',
                If(self.phy.tx_ack == 1,
                    NextValue(self.phy.tx_ready, 0),
                    NextValue(self.phy.tx_latch, 1),
                    NextState('TX_LATCH'),
                )
            )

            self.framing_fsm.act('TX_LATCH',
                If(self.phy.tx_ack == 1,
                    NextState('IDLE')
                )
            )

    class _TestPads:
        tx = Signal()
        dbg = Signal()

    plat = icestick.Platform()
    plat.build(PhysCore(plat), run=True, build_dir="build", build_name="top")
    plat.create_programmer().flash(0, "build/top.bin")

    # pads = _TestPads()
    # dut = WS2812PHY(pads, 24, freq_base=20, freq_tx=1, latch_length=1)
    # run_simulation(dut, tb(dut), vcd_name='ws2812.vcd')
