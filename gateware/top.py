from migen import *
from migen.build.platforms import icestick
from .uart import UART


class TopModule(Module):
    def __init__(self, plat):
        serial_pads = plat.request('serial')
        self.submodules.uart = UART(serial_pads, baud_rate=115200, clk_freq=12000000)

        empty = Signal(reset=1)
        data = Signal(8)
        rx_strobe = Signal()
        tx_strobe = Signal()
        self.comb += [
            rx_strobe.eq(self.uart.rx_ready & empty),
            tx_strobe.eq(self.uart.tx_ack & ~empty),
            self.uart.rx_ack.eq(rx_strobe),
            self.uart.tx_data.eq(data),
            self.uart.tx_ready.eq(tx_strobe)
        ]
        self.sync += [
            If(rx_strobe,
                data.eq(self.uart.rx_data),
                empty.eq(0)
            ),
            If(tx_strobe,
                empty.eq(1)
            )
        ]


if __name__ == '__main__':
    plat = icestick.Platform()
    top = TopModule(plat)
    plat.build(top, run=True, build_dir="build")
    plat.create_programmer().flash(0, "build/top.bin")
