"""纯 host 正反例。fixture 是符号化输入，不是 VM 事件捕获。"""
import struct
import unittest

from adapter import ContractRejected, inspect_movie_core, translate_host_subsets


class AdapterTests(unittest.TestCase):
    def test_poweron_reuses_pinned_contract(self):
        source = struct.pack("<III", 0x1026, 0x87654321, 0)
        self.assertEqual(translate_host_subsets("poweron", source),
                         struct.pack("<III", 0x102d, 0x87654321, 0))

    def test_timer_reuses_pinned_record_subset(self):
        source = bytearray(60)
        struct.pack_into("<I", source, 0, 0x1022)
        source[4] = 1
        struct.pack_into("<III", source, 8, 250000, 250000, 123)
        self.assertEqual(translate_host_subsets("timer_record", bytes(source))[:4],
                         struct.pack("<I", 0x1029))

    def test_movie_core_write_is_parsed_but_not_callable(self):
        source = struct.pack("<IIIIQQ", 0x1009, 1, 2, 3, 0x11223344, 0x55667788)
        core = inspect_movie_core("movie_write_finished", source)
        self.assertEqual((core.fx6_event, core.userdata_fx6_offset), (0x1009, 0x778))
        self.assertEqual((core.userdata_qword_0, core.userdata_qword_1), (0x11223344, 0x55667788))
        with self.assertRaises(ContractRejected):
            translate_host_subsets("movie_write_finished", source)

    def test_movie_core_auto_requires_zero_and_rejects_native_call(self):
        source = struct.pack("<IIIIQQ", 0x1030, 1, 2, 0, 3, 4)
        core = inspect_movie_core("movie_auto_divided", source)
        self.assertEqual((core.fx6_event, core.userdata_fx6_offset), (0x1037, 0x770))
        with self.assertRaises(ContractRejected):
            translate_host_subsets("movie_auto_divided", source)
        with self.assertRaises(ContractRejected):
            inspect_movie_core("movie_auto_divided", source[:12] + b"\x01" + source[13:])

    def test_negative_lengths_types_ids_and_nonzero_result(self):
        valid = struct.pack("<IIIIQQ", 0x1009, 1, 2, 3, 4, 5)
        for raw in (valid[:-1], valid + b"\x00", bytearray(valid),
                    struct.pack("<I", 0x1037) + valid[4:]):
            with self.assertRaises(ContractRejected):
                inspect_movie_core("movie_write_finished", raw)
        with self.assertRaises(ContractRejected):
            translate_host_subsets("poweron", struct.pack("<III", 0x1026, 1, 1))
        with self.assertRaises(ContractRejected):
            translate_host_subsets("unknown", b"")


if __name__ == "__main__":
    unittest.main()
