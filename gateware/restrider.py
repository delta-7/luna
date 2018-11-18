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
        self.out_read_ack = Signal()

        ####

        assert to_n//from_n == to_n/from_n
        total_n_chunks = to_n//from_n

        chunk_counter = Signal(max=total_n_chunks)
        chunks = Array(Signal(from_n) for _ in range(total_n_chunks))

        self.comb += [
            self.data_out.eq(Cat(*reversed(chunks)))
        ]
        self.sync += [
            If(self.latch_data,
                chunks[chunk_counter].eq(self.data_in),
                If(chunk_counter == total_n_chunks - 1,
                    chunk_counter.eq(0),
                    self.done.eq(1),
                ).Else(
                    chunk_counter.eq(chunk_counter+1),
                    self.done.eq(0),
                )
            ),

            If(self.out_read_ack,
                self.done.eq(0),
            )
        ]
