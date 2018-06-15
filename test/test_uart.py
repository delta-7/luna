from migen import *
from gateware.uart import UART

def _test_rx(rx, dut):
    def wait_bit():
        yield; yield; yield; yield

    def send_bit(bit):
        yield rx.eq(bit)
        yield from wait_bit()

    def assert_start():
        yield from send_bit(0)
        assert (yield dut.rx_error) == 0
        assert (yield dut.rx_ready) == 0

    def assert_end():
        yield from send_bit(1)
        assert (yield dut.rx_error == 0)

    def assert_listening(bitstream):
        yield from assert_start()
        for bit in bitstream:
            yield from send_bit(bit)
        yield from assert_end()

    def assert_recieved(octet):
        yield from wait_bit()
        assert (yield dut.rx_data) == octet

        yield dut.rx_ack.eq(1)
        while (yield dut.rx_ready == 1): yield
        yield dut.rx_ack.eq(0)

    def assert_error():
        yield from wait_bit()
        assert (yield dut.rx_error) == 1
        yield rx.eq(1)

        yield dut.reset.eq(1)
        yield
        yield
        yield dut.reset.eq(0)
        yield
        yield

        assert (yield dut.rx_error) == 0

    ## good & pure bit patterns
    yield from assert_listening([1, 0, 1, 0, 1, 0, 1, 0])
    yield from assert_recieved(0x55)
    yield from assert_listening([1, 1, 0, 0, 0, 0, 1, 1])
    yield from assert_recieved(0xC3)
    yield from assert_listening([1, 0, 0, 0, 0, 0, 0, 1])
    yield from assert_recieved(0x81)
    yield from assert_listening([1, 0, 1, 0, 0, 1, 0, 1])
    yield from assert_recieved(0xA5)
    yield from assert_listening([1, 1, 1, 1, 1, 1, 1, 1])
    yield from assert_recieved(0xFF)

    ## the Bad Boys
    # framing error
    yield from assert_start()
    for bit in [1]*8:
        yield from send_bit(bit)
    yield from assert_start()
    yield from assert_error()

    # overflow error
    yield from assert_listening([1]*9)
    yield from send_bit(0)
    yield from assert_error()

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

    def assert_end():
        assert (yield dut.tx_ack) == 0 # we're still not idle
        yield from assert_databit(1) # stop bit
        yield from wait_half_bit()
        assert (yield dut.tx_ack) == 1 # now we're idle

    def assert_transmits(octet, bitstream):
        yield from assert_start(octet)
        for bit in bitstream:
            yield from assert_databit(bit)
        yield from assert_end()

    yield from assert_transmits(0x55, [1, 0, 1, 0, 1, 0, 1, 0])
    yield from assert_transmits(0x81, [1, 0, 0, 0, 0, 0, 0, 1])
    yield from assert_transmits(0xff, [1, 1, 1, 1, 1, 1, 1, 1])
    yield from assert_transmits(0x00, [0, 0, 0, 0, 0, 0, 0, 0])

class _TestPads:
    tx = Signal()
    rx = Signal(reset=1)

def test_rx():
    pads = _TestPads()
    dut = UART(pads, clk_freq=4800, baud_rate=1200)
    run_simulation(dut, _test_rx(pads.rx, dut), vcd_name="uart_rx.vcd")

def test_tx():
    pads = _TestPads()
    dut = UART(pads, clk_freq=4800, baud_rate=1200)
    run_simulation(dut, _test_tx(pads.tx, dut), vcd_name="uart_tx.vcd")
