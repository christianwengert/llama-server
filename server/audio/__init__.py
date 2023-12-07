import wave
import torch
import numpy as np


SAMPLING_RATE = 16000


def convert_float32_to_wave(raw_audio, filename, sample_rate, num_channels):
    # Ensure the audio data is in the correct format
    assert raw_audio.dtype == np.float32, "Audio data must be in float32 format"

    # Open a new wave file in write mode
    with wave.open(filename, 'wb') as wave_file:
        # Set the audio parameters
        wave_file.setnchannels(num_channels)
        wave_file.setsampwidth(2)  # 2 bytes for 'int16' format
        wave_file.setframerate(sample_rate)

        # Convert float32 data to int16
        int16_audio = (raw_audio * 32767).astype(np.int16)

        # Write the frames to the wave file
        wave_file.writeframes(int16_audio.tobytes())


class VoiceActivityDetector:
    def __init__(self):
        model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                      model='silero_vad',
                                      force_reload=False,
                                      onnx=False)
        self.model = model
        self.utils = utils

        (get_speech_timestamps,
         save_audio,
         read_audio,
         VADIterator,
         collect_chunks) = utils
        self.vad_iterator = VADIterator(model)
        self.get_speech_timestamps = get_speech_timestamps
        self.collect_chunks = collect_chunks

    def get_timestamps(self, audio: np.ndarray, ):
        # number of samples in a single audio chunk
        timestamps = self.get_speech_timestamps(audio, self.model, sampling_rate=SAMPLING_RATE)
        return timestamps


if __name__ == '__main__':

    audio = np.fromfile('/Users/christianwengert/src/llama-server/server/temp.raw', np.float32)

    audio_processor = VoiceActivityDetector()
    timestamps = audio_processor.get_timestamps(audio)
    convert_float32_to_wave(audio, '/Users/christianwengert/src/llama-server/server/sanity.wav', 16000, 1)
    for i, ts in enumerate(timestamps):
        print(ts)
        convert_float32_to_wave(audio[ts['start']:ts['end']], f'/Users/christianwengert/src/llama-server/server/sanity_{i}.wav', 16000, 1)
