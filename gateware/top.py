from migen import *
from migen.build.platforms import icestick
from migen.genlib.fsm import FSM, NextValue, NextState
from migen.genlib.fifo import SyncFIFOBuffered
from migen.build.generic_platform import Subsignal, IOStandard, Pins
from .uart import UART
from .ws2812 import WS2812Controller
from .restrider import Restrider
from migen.genlib.io import CRG


class TopModule(Module):
    def __init__(self, plat):
        neopixel_gpio = [
            ('neopixel', 0,
                Subsignal('tx', Pins('PMOD:0')),
                IOStandard('LVCMOS33')
            )
        ]
        plat.add_extension(neopixel_gpio)

        neopixel_pads = plat.request('neopixel')
        leds = plat.request('user_led')
        serial_pads = plat.request('serial')

        self.submodules.uart = UART(serial_pads, baud_rate=115200, clk_freq=12000000)

        self.submodules.restrider = Restrider()

        data = Signal(8)
        self.submodules.uart_fsm = FSM()
        self.uart_fsm.act('RX',
            If(self.uart.rx_ready,
                self.uart.rx_ack.eq(1),
                NextValue(data, self.uart.rx_data),
                NextState('INGEST'),
            )
        )
        self.comb += self.restrider.data_in.eq(data)
        self.uart_fsm.act('INGEST',
            self.restrider.latch_data.eq(1),
            NextState('RX'),
        )

        N_PIXELS = 8
        self.submodules.fifo = SyncFIFOBuffered(24, N_PIXELS)
        pixel_data = Signal(24)

        self.submodules.slurp_fsm = FSM()
        self.slurp_fsm.act('IDLE',
            self.fifo.we.eq(0),
            If(self.restrider.done,
                self.restrider.out_read_ack.eq(1),
                NextValue(pixel_data, self.restrider.data_out),
                NextState('CHUNK'),
            )
        )
        self.comb += self.fifo.din.eq(pixel_data)
        self.slurp_fsm.act('CHUNK',
            If(self.fifo.writable,
                self.fifo.we.eq(1),
            ),
            NextState('IDLE'),
        )

        self.submodules.neopixels = WS2812Controller(neopixel_pads, self.fifo, 12000000)
        self.comb += self.neopixels.write_en.eq(self.fifo.level == N_PIXELS)

if __name__ == '__main__':
    plat = icestick.Platform()
    top = TopModule(plat)
    plat.build(top, run=True, build_dir="build")
    plat.create_programmer().flash(0, "build/top.bin")
