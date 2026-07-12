"""FrameRingBuffer 冒烟测试。"""

from src.service.replay_module.ring_buffer import FrameRingBuffer


class TestFrameRingBuffer:
    def test_push_and_dump(self):
        buf = FrameRingBuffer(max_seconds=1, fps=10)  # capacity = 10
        for i in range(5):
            buf.push(f"frame_{i}".encode())
        dump = buf.dump_all()
        assert len(dump) == 5
        assert dump[0] == b"frame_0"

    def test_overflow_drops_old(self):
        buf = FrameRingBuffer(max_seconds=1, fps=10)  # capacity = 10
        for i in range(15):
            buf.push(f"frame_{i}".encode())
        dump = buf.dump_all()
        assert len(dump) == 10
        # Oldest 5 were dropped
        assert dump[0] == b"frame_5"
        assert dump[-1] == b"frame_14"

    def test_clear(self):
        buf = FrameRingBuffer(max_seconds=1, fps=10)
        buf.push(b"data")
        buf.clear()
        assert len(buf) == 0

    def test_dump_does_not_clear(self):
        buf = FrameRingBuffer(max_seconds=1, fps=10)
        buf.push(b"data")
        dump1 = buf.dump_all()
        dump2 = buf.dump_all()
        assert len(dump1) == 1
        assert len(dump2) == 1
