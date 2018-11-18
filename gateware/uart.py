from migen import *
from migen.genlib.fsm import FSM, NextValue, NextState

from .util import closest_divisor


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
    rx_data : octet out
        Recieve buffer. Valid when rx_ready is high.

    rx_ready : out
        High when rx_data contains a full octet.

    rx_ack : in
        User should set high to signal that rx_data may be cleared and a new byte recieved.

    rx_error : out
        High when framing errors are encountered, or when a start bit occurs while rx_ready is asserted.

    tx_data : octet in
        Transmit buffer. Considered valid when tx_ready is set high.

    tx_ready : in
        User should set high to signal that tx_data is stable and TX should begin.

    tx_ack : out
        High when tx core is IDLE, low during transmit.
    """
    def __init__(self, pads, clk_freq, baud_rate):
        self.rx_data = Signal(8)
        self.rx_ready = Signal()
        self.rx_ack = Signal()
        self.rx_error = Signal()

        self.tx_data = Signal(8)
        self.tx_ready = Signal()
        self.tx_ack = Signal()

        ###

        divisor = closest_divisor(clk_freq, baud_rate, max_ppm=50000)

        ### RX CORE ###

        # divider counter for baud clock
        self.rx_counter = Signal(max=divisor)

        # when strobe goes high, we shift in a bit
        self.rx_strobe = Signal()

        # what bit are we on?
        self.rx_bitno = Signal(max=8)

        ###

        # the strobe goes high when the counter resets
        self.comb += self.rx_strobe.eq(self.rx_counter == 0)
        self.sync += If(self.rx_counter == 0,
            self.rx_counter.eq(divisor - 1), # wrap around when the counter hits zero
        ).Else(
            self.rx_counter.eq(self.rx_counter - 1),   # decrement the counter every clock
        )

        # FSM for the rx core
        self.submodules.rx_fsm = FSM(reset_state='IDLE')

        self.rx_fsm.act('IDLE',
            If(~pads.rx, # If we hit a start bit
                NextValue(self.rx_counter, divisor // 2 ), # shift halfway through the rx counter;
                                                          # this offsets our bit reads to the middle of the pulse, improving read stability
                NextState('START'),
            )
        )

        # START state just waits one half strobe.
        self.rx_fsm.act('START',
            If(self.rx_strobe, NextState('DATA')))

        self.rx_fsm.act('DATA',
            If(self.rx_strobe,
                NextValue(self.rx_data, Cat(self.rx_data[1:8], pads.rx)), # shift in a new bit
                NextValue(self.rx_bitno, self.rx_bitno + 1),
                If(self.rx_bitno == 7, # if we're done
                    NextState('STOP')  # go to the stop state
                )
            )
        )

        self.rx_fsm.act('STOP',
            If(self.rx_strobe,
                If(~pads.rx, # if we didn't get a stop bit
                    NextState('ERROR') # assert an error
                ).Else(
                    NextState('FULL')
                )
            )
        )

        self.rx_fsm.act('FULL',
            If(self.rx_ack,        # if read data was acknowledged
                NextState('IDLE')  # get ready for a new byte
            ).Elif(~pads.rx,
                NextState('ERROR') # if we see a start bit and we still are sitting on data, assert an error.
            )
        )

        # assert the error line when we're in the error state
        self.comb += self.rx_error.eq(self.rx_fsm.ongoing('ERROR'))

        # assert the ready line when we're in the full state
        self.comb += self.rx_ready.eq(self.rx_fsm.ongoing('FULL'))

        ### TX CORE ###

        # what bit number are we on?
        self.tx_bitno = Signal(max=8)

        # register which the tx data is shifted through
        self.tx_shift = Signal(8)

        # divider counter for baud clock
        self.tx_counter = Signal(max=divisor)

        # when strobe goes high, we shift out a bit
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
                    NextState('STOP'), # stop if we've reached the end of the data to transmit
                    NextValue(self.tx_bitno, 0),
                )
            )
        )

        self.tx_fsm.act('STOP',
            If(self.tx_strobe,
                NextValue(pads.tx, 1),  # TX := stop bit
                NextState('IDLE'),
            )
        )
