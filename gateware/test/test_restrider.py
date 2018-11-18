from unittest import TestCase
from migen import *
from .util import simulation_test
from ..restrider import Restrider

class RestriderTestbench(Module):
    def __init__(self):
        self.submodules.restrider = Restrider(from_n=8, to_n=24)

    def write_in(self, val):
        yield self.restrider.data_in.eq(val)
        yield self.restrider.latch_data.eq(1)
        yield
        yield self.restrider.latch_data.eq(0)

class RestriderTestCase(TestCase):
    def setUp(self):
        self.tb = RestriderTestbench()

    def assertSignal(self, signal, value):
        self.assertEqual((yield signal), value)

    @simulation_test
    def test_basic_restride(self, tb):
        yield from self.assertSignal(self.tb.restrider.done, 0)
        yield from self.tb.write_in(0x80)
        yield from self.tb.write_in(0x40)
        yield from self.tb.write_in(0x20)
        yield
        yield from self.assertSignal(self.tb.restrider.done, 1)
        yield from self.assertSignal(self.tb.restrider.data_out, 0x804020)


        yield from self.tb.write_in(0xaa)
        yield
        yield from self.assertSignal(self.tb.restrider.done, 0)
        yield
        yield from self.tb.write_in(0xbb)
        yield from self.tb.write_in(0xcc)
        yield
        yield from self.assertSignal(self.tb.restrider.done, 1)
