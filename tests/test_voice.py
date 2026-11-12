import base64
import unittest

from host.gowuji import Voice, decode_audio, decode_event


class BoardVoice(unittest.TestCase):
    def test_fixed_length_transport(self):
        pcm = bytes(range(160)) * 2
        encoded = base64.b64encode(pcm).decode("ascii")
        self.assertEqual(decode_audio("AUD 42 " + encoded), (42, pcm))
        for bad in (encoded[:-1], "!" + encoded[1:], encoded + "EV PTT 0", ""):
            self.assertIsNone(decode_audio("AUD 42 " + bad))
        self.assertIsNone(decode_audio("AUD 6000 " + encoded))
        self.assertEqual(decode_event("EV MIC_END 0"), ("MIC_END", 0))

    def test_recording_gate_and_missing_frame(self):
        voice = Voice.__new__(Voice)
        voice.source, voice.stream, voice.recording = "board", None, False
        pcm = bytes(320)
        voice.feed((0, pcm))  # No recording without an explicit device start.
        voice.begin(3)
        voice.feed((0, pcm))
        voice.feed((2, pcm))
        voice.feed((1, pcm))
        self.assertTrue(voice.invalid)
        self.assertEqual(voice.frames, [pcm])
        voice.cancel()
        self.assertFalse(voice.recording)
        self.assertEqual(voice.frames, [])


if __name__ == "__main__":
    unittest.main()
