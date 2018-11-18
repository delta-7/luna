from migen import *
from migen.build.platforms import icestick
from migen.genlib.fifo import SyncFIFO
from .uart import UART
from .restrider import Restrider


class TopModule(Module):
    def __init__(self, plat):
        serial_pads = plat.request('serial')
        self.submodules.uart = UART(serial_pads, baud_rate=115200, clk_freq=12000000)

        # N_PIXELS = 8
        # fifo = SyncFIFO(24, N_PIXELS)

        self.submodules.restrider = Restrider()

if __name__ == '__main__':
    plat = icestick.Platform()
    top = TopModule(plat)
    plat.build(top, run=True, build_dir="build")
    # plat.create_programmer().flash(0, "build/top.bin")
