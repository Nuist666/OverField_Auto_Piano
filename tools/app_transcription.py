import os
import time
import torch
import librosa
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from libs.piano_transcription_inference import PianoTranscription, sample_rate


class PianoTranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MP3转录MID")
        self.root.geometry("500x260")

        self.var_cuda = tk.BooleanVar()
        self._create_widgets()

    def _create_widgets(self):
        # 音频文件输入
        tk.Label(self.root, text="音频文件:").pack(anchor='w', padx=5)
        frame_audio = tk.Frame(self.root)
        frame_audio.pack(fill='x', padx=5, pady=2)
        self.entry_audio = tk.Entry(frame_audio)
        self.entry_audio.pack(side=tk.LEFT, fill='x', expand=True)
        tk.Button(frame_audio, text="选择文件", command=self.open_file).pack(side=tk.LEFT, padx=2)

        # 输出 MIDI 文件路径
        tk.Label(self.root, text="输出MIDI文件:").pack(anchor='w', padx=5)
        frame_midi = tk.Frame(self.root)
        frame_midi.pack(fill='x', padx=5, pady=2)
        self.entry_midi = tk.Entry(frame_midi)
        self.entry_midi.pack(side=tk.LEFT, fill='x', expand=True)
        tk.Button(frame_midi, text="保存路径", command=self.save_file).pack(side=tk.LEFT, padx=2)

        # CUDA 选项
        tk.Checkbutton(self.root, text="尝试使用CUDA加速", variable=self.var_cuda).pack()
        self.label_device = tk.Label(self.root, text="当前设备：未检测", fg="green")
        self.label_device.pack(pady=2)

        # 状态显示（显示进度、耗时、预计剩余）
        self.label_status = tk.Label(self.root, text="", fg="blue")
        self.label_status.pack(pady=10)

        # 开始按钮
        self.btn_start = tk.Button(self.root, text="开始转录", command=self.start_transcription)
        self.btn_start.pack(pady=10)

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if path:
            self.entry_audio.delete(0, tk.END)
            self.entry_audio.insert(0, path)

            # 自动填充 MIDI 输出路径
            base, _ = os.path.splitext(path)  # 去掉原来的扩展名
            default_midi_path = base + ".mid"
            self.entry_midi.delete(0, tk.END)
            self.entry_midi.insert(0, default_midi_path)

    def save_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".mid", filetypes=[("MIDI files", "*.mid")])
        if path:
            self.entry_midi.delete(0, tk.END)
            self.entry_midi.insert(0, path)

    def start_transcription(self):
        audio_path = self.entry_audio.get()
        midi_path = self.entry_midi.get()
        use_cuda = self.var_cuda.get()

        if not audio_path or not os.path.exists(audio_path):
            messagebox.showerror("错误", "请选择一个有效的音频文件")
            return
        if not midi_path:
            messagebox.showerror("错误", "请设置输出 MIDI 文件路径")
            return

        # 检测设备
        device = 'cuda' if use_cuda and torch.cuda.is_available() else 'cpu'
        self.label_device.config(text=f"当前设备：{'GPU (CUDA)' if device == 'cuda' else 'CPU'}")

        # 禁用按钮并更新状态
        self.btn_start.config(state=tk.DISABLED)
        self.label_status.config(text="正在转录，请稍候...")

        # 使用线程避免 UI 卡死
        threading.Thread(target=self.run_inference,
                         args=(audio_path, midi_path, device),
                         daemon=True).start()

    def run_inference(self, audio_path, output_midi_path, device):
        try:
            self.root.after(0, lambda: self.label_status.config(text="正在加载音频..."))
            audio, _ = librosa.load(path=audio_path, sr=sample_rate, mono=True)

            self.root.after(0, lambda: self.label_status.config(text="正在推理..."))
            transcriptor = PianoTranscription(
                device=device,
                gui_callback=lambda msg: self.root.after(0, lambda: self.label_status.config(text=msg))
            )

            start_time = time.time()
            transcriptor.transcribe(audio, output_midi_path, gui_callback=self.update_progress)
            elapsed_time = time.time() - start_time

            self.root.after(0, lambda: self.on_inference_done(elapsed_time, output_midi_path))
        except Exception as e:
            # 捕获完整异常信息
            tb_str = traceback.format_exc()
            self.root.after(0, lambda err=tb_str: self.on_inference_error(err))

    def on_inference_done(self, elapsed_time, output_path):
        self.label_status.config(text="转录完成！")
        self.btn_start.config(state=tk.NORMAL)
        messagebox.showinfo("完成", f"转录完成！耗时 {elapsed_time:.2f} 秒\n输出: {output_path}")

    def on_inference_error(self, error):
        self.label_status.config(text="发生错误")
        self.btn_start.config(state=tk.NORMAL)
        messagebox.showerror("错误", f"推理时出错:\n{error}")

    def update_progress(self, current, total, elapsed, rate):
        percent = int((current / total) * 100)
        eta = (total - current) / rate if rate else 0
        self.root.after(0, lambda: self._update_progress_ui(percent, elapsed, eta))

    def _update_progress_ui(self, percent, elapsed, eta):
        self.label_status.config(
            text=f"进度: {percent}% | 已用时: {elapsed:.1f}s | 预计剩余: {eta:.1f}s"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = PianoTranscriptionApp(root)
    root.mainloop()
