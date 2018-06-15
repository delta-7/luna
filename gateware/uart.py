from migen import *
from migen.genlib.fsm import FSM, NextValue, NextState


def closest_divisor(freq_base, freq_target, max_ppm=None):
    divisor = round(freq_base / freq_target)

    if divisor <= 0:
        raise ArgumentError("Output frequency is too high")

    ppm = 1000000 * ((freq_base / divisor) - freq_target) / freq_target
    if max_ppm is not None and ppm > max_ppm:
        raise ArgumentError("Output frequency deviation is too high ({} ppm)".format(ppm))

    return divisor

@ResetInserter()
class UART(Module):
    """
    8N1 UART gatecore

    Parameters
    ----------
    pads : {rx, tx}

    clk_freq : int
        Base clock domain frequency.

    baud_rate : int
        Target baud rate.

    Attributes
    ----------
    tx_data : octet in
        Transmit buffer. Considered valid when tx_ready is set high.

    tx_ready : in
        User should set high to signal that tx_data is stable and TX should begin.

    tx_ack : out
        High when tx core is IDLE, low during transmit.
    """
    def __init__(self, pads, clk_freq, baud_rate):
        self.tx_data = Signal(8)
        self.tx_ready = Signal()
        self.tx_ack = Signal()

        ###

        divisor = closest_divisor(clk_freq, baud_rate, max_ppm=50000)

        # what bit number are we on?
        self.tx_bitno = Signal(max=8)

        # register which the tx data is shifted through
        self.tx_shift = Signal(8)

        # divider counter for baud clock
        self.tx_counter = Signal(max=divisor)

        # tx_strobe synchronizes our tx pulse edges
        self.tx_strobe = Signal()

        ###

        # the TX line should reset high
        pads.tx.reset = 1

        # the strobe goes high when the counter resets
        self.comb += self.tx_strobe.eq(self.tx_counter == 0)

        self.sync += If(self.tx_counter == 0,
            self.tx_counter.eq(divisor - 1), # wrap around when the counter hits zero
        ).Else(
            self.tx_counter.eq(self.tx_counter - 1),   # decrement the counter every clock
        )

        # FSM for the tx core
        self.submodules.tx_fsm = FSM(reset_state='IDLE')

        self.comb += self.tx_ack.eq(self.tx_fsm.ongoing('IDLE')) # TX_ACK is high when we're IDLE.

        self.tx_fsm.act('IDLE',
            If(self.tx_ready,                            # If transmit should begin:
                NextValue(self.tx_counter, divisor - 1), # reset the counter right before switching states (keeps TX high for a single bit)
                NextValue(self.tx_shift, self.tx_data),  # latch the tx data into the tx shift register
                NextState('START'),                      # Switch to START state
            ).Else(
                NextValue(pads.tx, 1)                    # TX line IDLEs high
            )
        )

        self.tx_fsm.act('START',
            If(self.tx_strobe,          # if it's time to TX
                NextValue(pads.tx, 0),  # TX := start bit
                NextState('DATA'),      # time to transmit data!
            )
        )

        self.tx_fsm.act('DATA',
            If(self.tx_strobe,
                NextValue(pads.tx, self.tx_shift[0]), # set the TX line to our current out bit
                NextValue(self.tx_shift, Cat(self.tx_shift[1:8], 0)), # shift the data through the register
                NextValue(self.tx_bitno, self.tx_bitno + 1),
                If(self.tx_bitno == 7,
                    NextState('STOP')  # stop if we've reached the end of the data to transmit
                )
            )
        )

        self.tx_fsm.act('STOP',
            If(self.tx_strobe,
                NextValue(pads.tx, 1),  # TX := stop bit
                NextState('IDLE'),
            )
        )

def _test_tx(tx, dut):
    def wait_bit():
        yield; yield; yield; yield

    def wait_half_bit():
        yield; yield

    def assert_start(octet):
        # check initial states
        assert (yield tx) == 1 # TX is high
        assert (yield dut.tx_ack) == 1 # we're idle

        # set up data and latch it
        yield dut.tx_data.eq(octet)
        yield dut.tx_ready.eq(1)

        # wait for start bit
        while (yield tx) == 1:
            yield

        # bring tx latch low again
        yield dut.tx_ready.eq(0)

        # should be on start bit
        assert (yield tx) == 0
        # shouldn't be idle
        assert (yield dut.tx_ack) == 0

        yield from wait_half_bit()

    def assert_databit(bit):
        assert (yield dut.tx_ack) == 0 # we're not idle
        yield from wait_bit()
        assert (yield tx) == bit

    def assert_stop():
        assert (yield dut.tx_ack) == 0 # we're still not idle
        yield from assert_databit(1) # stop bit
        yield from wait_half_bit()
        assert (yield dut.tx_ack) == 1 # now we're idle

    def assert_transmits(octet, bitstream):
        yield from assert_start(octet)
        for bit in bitstream:
            yield from assert_databit(bit)
        yield from assert_stop()

    yield from assert_transmits(0x55, [1, 0, 1, 0, 1, 0, 1, 0])
    yield from assert_transmits(0x81, [1, 0, 0, 0, 0, 0, 0, 1])
    yield from assert_transmits(0xff, [1, 1, 1, 1, 1, 1, 1, 1])
    yield from assert_transmits(0x00, [0, 0, 0, 0, 0, 0, 0, 0])

def _test_uart(pads, dut):
    yield from _test_tx(pads.tx, dut)

class _TestPads:
    tx = Signal(reset=1)
    rx = Signal()

if __name__ == '__main__':
    pads = _TestPads()
    dut = UART(pads, clk_freq=4800, baud_rate=1200)
    run_simulation(dut, _test_uart(pads, dut), vcd_name="uart.vcd")
