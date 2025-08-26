import os
import numpy as np
import time
import librosa
from pathlib import Path
import urllib.request
import torch

from .utilities import (create_folder, get_filename, RegressionPostProcessor, write_events_to_midi)
from .models import Regress_onset_offset_frame_velocity_CRNN, Note_pedal
from .pytorch_utils import move_data_to_device, forward
from . import config



def download_with_progress(url, filename, progress_callback=None):
    def hook(count, block_size, total_size):
        if total_size > 0 and progress_callback:
            downloaded = count * block_size
            percent = min(downloaded / total_size, 1.0)
            progress_callback(downloaded, total_size, percent)
    urllib.request.urlretrieve(url, filename, reporthook=hook)


class PianoTranscription(object):
    def __init__old(self, model_type='Note_pedal', checkpoint_path=None, segment_samples=16000*10, device=torch.device('cuda')):
        """Class for transcribing piano solo recording.

        Args:
          model_type: str
          checkpoint_path: str
          segment_samples: int
          device: 'cuda' | 'cpu'
        """
        if not checkpoint_path: 
            checkpoint_path='{}/piano_transcription_inference_data/note_F1=0.9677_pedal_F1=0.9186.pth'.format(os.getcwd())
        print('Checkpoint path: {}'.format(checkpoint_path))

        # if not os.path.exists(checkpoint_path) or os.path.getsize(checkpoint_path) < 1.6e8:
        #     create_folder(os.path.dirname(checkpoint_path))
        #     print('Total size: ~165 MB')
        #     zenodo_path = 'https://zenodo.org/record/4034264/files/CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1'
        #     os.system('wget -O "{}" "{}"'.format(checkpoint_path, zenodo_path))
        if not os.path.exists(checkpoint_path) or os.path.getsize(checkpoint_path) < 1.6e8:
            create_folder(os.path.dirname(checkpoint_path))
            print('Total size: ~165 MB')
            zenodo_path = 'https://zenodo.org/record/4034264/files/CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1'

            try:
                print('正在下载模型...')
                urllib.request.urlretrieve(zenodo_path, checkpoint_path)
                print('下载完成!')
            except Exception as e:
                print(f'下载失败: {e}')
                print(f'请手动下载: {zenodo_path}')
                print(f'并保存到指定路径: {checkpoint_path}')
        print('Using {} for inference.'.format(device))

        self.segment_samples = segment_samples
        self.frames_per_second = config.frames_per_second
        self.classes_num = config.classes_num
        self.onset_threshold = 0.3
        self.offset_threshod = 0.3
        self.frame_threshold = 0.1
        self.pedal_offset_threshold = 0.2

        # Build model
        Model = eval(model_type)
        self.model = Model(frames_per_second=self.frames_per_second, 
            classes_num=self.classes_num)

        # Load model
        checkpoint = torch.load(checkpoint_path, map_location=device)
        self.model.load_state_dict(checkpoint['model'], strict=False)

        # Parallel
        if 'cuda' in str(device):
            self.model.to(device)
            print('GPU number: {}'.format(torch.cuda.device_count()))
            self.model = torch.nn.DataParallel(self.model)
        else:
            print('Using CPU.')

    def __init__(self, model_type='Note_pedal', checkpoint_path=None, segment_samples=16000*10, device=torch.device('cuda'), gui_callback=None):
        """Class for transcribing piano solo recording.

        Args:
          model_type: str
          checkpoint_path: str
          segment_samples: int
          device: 'cuda' | 'cpu'
        """
        if not checkpoint_path:
            # checkpoint_path = os.path.join(os.getcwd(), 'piano_transcription_inference_data', 'note_F1=0.9677_pedal_F1=0.9186.pth')
            checkpoint_path = os.path.join(os.getcwd(), 'models', 'note_F13D0.9186.pth')

        # zenodo_path = 'https://zenodo.org/record/4034264/files/CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1'
        download_path = 'https://mirror-huggingface.nuist666.top/note_F13D0.9186.pth'

        if not os.path.exists(checkpoint_path) or os.path.getsize(checkpoint_path) < 1.6e8:
            create_folder(os.path.dirname(checkpoint_path))
            if gui_callback:
                gui_callback("正在下载模型...")
            try:
                download_with_progress(
                    download_path, checkpoint_path,
                    progress_callback=lambda d, t, p: gui_callback(
                        f"下载模型: {p * 100:.1f}% ({d / 1e6:.1f}/{t / 1e6:.1f} MB)")
                )
                if gui_callback:
                    gui_callback("模型下载完成！")
            except Exception as e:
                if gui_callback:
                    gui_callback(f"下载失败: {e}\n请手动下载到 {checkpoint_path}")
                raise e

        if gui_callback:
            gui_callback("正在加载模型...")

        print('Using {} for inference.'.format(device))

        self.segment_samples = segment_samples
        self.frames_per_second = config.frames_per_second
        self.classes_num = config.classes_num
        self.onset_threshold = 0.3
        self.offset_threshod = 0.3
        self.frame_threshold = 0.1
        self.pedal_offset_threshold = 0.2

        # Build model
        Model = eval(model_type)
        self.model = Model(frames_per_second=self.frames_per_second,
            classes_num=self.classes_num)

        # Load model
        checkpoint = torch.load(checkpoint_path, map_location=device)
        self.model.load_state_dict(checkpoint['model'], strict=False)

        # Parallel
        if 'cuda' in str(device):
            self.model.to(device)
            print('GPU number: {}'.format(torch.cuda.device_count()))
            self.model = torch.nn.DataParallel(self.model)
        else:
            print('Using CPU.')

    def transcribe(self, audio, midi_path, gui_callback=None):
        """Transcribe an audio recording.

        Args:
          audio: (audio_samples,)
          midi_path: str, path to write out the transcribed MIDI.

        Returns:
          transcribed_dict, dict: {'output_dict':, ..., 'est_note_events': ...}

        """
        audio = audio[None, :]  # (1, audio_samples)

        # Pad audio to be evenly divided by segment_samples
        audio_len = audio.shape[1]
        pad_len = int(np.ceil(audio_len / self.segment_samples))\
            * self.segment_samples - audio_len

        audio = np.concatenate((audio, np.zeros((1, pad_len))), axis=1)

        # Enframe to segments
        segments = self.enframe(audio, self.segment_samples)
        """(N, segment_samples)"""

        # Forward
        # output_dict = forward(self.model, segments, batch_size=1)
        output_dict = forward(self.model, segments, batch_size=1, progress_callback=gui_callback)

        """{'reg_onset_output': (N, segment_frames, classes_num), ...}"""

        # Deframe to original length
        for key in output_dict.keys():
            output_dict[key] = self.deframe(output_dict[key])[0 : audio_len]
        """output_dict: {
          'reg_onset_output': (N, segment_frames, classes_num), 
          'reg_offset_output': (N, segment_frames, classes_num), 
          'frame_output': (N, segment_frames, classes_num), 
          'velocity_output': (N, segment_frames, classes_num)}"""

        # Post processor
        post_processor = RegressionPostProcessor(self.frames_per_second, 
            classes_num=self.classes_num, onset_threshold=self.onset_threshold, 
            offset_threshold=self.offset_threshod, 
            frame_threshold=self.frame_threshold, 
            pedal_offset_threshold=self.pedal_offset_threshold)

        # Post process output_dict to MIDI events
        (est_note_events, est_pedal_events) = \
            post_processor.output_dict_to_midi_events(output_dict)

        # Write MIDI events to file
        if midi_path:
            write_events_to_midi(start_time=0, note_events=est_note_events, 
                pedal_events=est_pedal_events, midi_path=midi_path)
            print('Write out to {}'.format(midi_path))

        transcribed_dict = {
            'output_dict': output_dict, 
            'est_note_events': est_note_events,
            'est_pedal_events': est_pedal_events}

        return transcribed_dict

    def enframe(self, x, segment_samples):
        """Enframe long sequence to short segments.

        Args:
          x: (1, audio_samples)
          segment_samples: int

        Returns:
          batch: (N, segment_samples)
        """
        assert x.shape[1] % segment_samples == 0
        batch = []

        pointer = 0
        while pointer + segment_samples <= x.shape[1]:
            batch.append(x[:, pointer : pointer + segment_samples])
            pointer += segment_samples // 2

        batch = np.concatenate(batch, axis=0)
        return batch

    def deframe(self, x):
        """Deframe predicted segments to original sequence.

        Args:
          x: (N, segment_frames, classes_num)

        Returns:
          y: (audio_frames, classes_num)
        """
        if x.shape[0] == 1:
            return x[0]

        else:
            x = x[:, 0 : -1, :]
            """Remove an extra frame in the end of each segment caused by the
            'center=True' argument when calculating spectrogram."""
            (N, segment_samples, classes_num) = x.shape
            assert segment_samples % 4 == 0

            y = []
            y.append(x[0, 0 : int(segment_samples * 0.75)])
            for i in range(1, N - 1):
                y.append(x[i, int(segment_samples * 0.25) : int(segment_samples * 0.75)])
            y.append(x[-1, int(segment_samples * 0.25) :])
            y = np.concatenate(y, axis=0)
            return y