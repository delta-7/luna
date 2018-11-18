from migen import *
from migen.build.platforms import icestick
from migen.genlib.fsm import FSM, NextValue, NextState
from migen.genlib.fifo import SyncFIFO
from .uart import UART
from .restrider import Restrider


class TopModule(Module):
    def __init__(self, plat):
        serial_pads = plat.request('serial')

        self.submodules.uart = UART(serial_pads, baud_rate=115200, clk_freq=12000000)

        N_PIXELS = 8
        fifo = SyncFIFO(24, N_PIXELS)

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

if __name__ == '__main__':
    plat = icestick.Platform()
    top = TopModule(plat)
    plat.build(top, run=True, build_dir="build")
    plat.create_programmer().flash(0, "build/top.bin")
