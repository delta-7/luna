from migen import *

class COBS(Module):
    """
    Implements streaming consistent-overhead byte stuffing.
    """

    def __init__(self)
        self.specials.cobs_buffer = Memory(8, 256)
