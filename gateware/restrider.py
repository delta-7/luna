from migen import *
from migen.build.platforms import icestick


class Restrider(Module):
    def __init__(self, from_n=8, to_n=24):
        # in
        self.data_in = Signal(from_n)
        self.latch_data = Signal()

        # out
        self.data_out = Signal(to_n)
        self.done = Signal()

        ####

        assert to_n//from_n == to_n/from_n
        total_n_chunks = to_n//from_n

        chunk_counter = Signal(max=total_n_chunks)
        chunks = Array(Signal(from_n) for _ in range(total_n_chunks))

        self.comb += [
            self.done.eq(chunk_counter == total_n_chunks),
            self.data_out.eq(Cat(*reversed(chunks)))
        ]
        self.sync += [
            If(self.latch_data,
                chunks[chunk_counter].eq(self.data_in),
                chunk_counter.eq(chunk_counter+1),
            )
        ]
