#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import pretty_midi

# General MIDI percussion channel is 9 (10th), but many MIDIs put drums on channel 9.
# 我们不强依赖通道，按常见打击乐音高映射到游戏按键名。

DRUM_NOTE_MAP = {
    # Hi-Hat
    42: "踩镲闭",  # Closed Hi-Hat
    44: "踩镲开",  # Pedal Hi-Hat（不少谱面用作开启/半开）
    46: "踩镲开",  # Open Hi-Hat（补充，映射到 踩镲开->Q）
    # Crash / Ride family
    49: "高音吊镲",  # Crash Cymbal 1
    57: "中音吊镲",  # Crash Cymbal 2
    55: "中音吊镲",  # Splash Cymbal（补充，归为中音吊镲以适配 T）
    51: "叮叮镲", 59: "叮叮镲",  # Ride Cymbal / Ride Cymbal 2 -> 叮叮镲
    # Snare / Kick
    38: "军鼓", 40: "军鼓",
    36: "底鼓", 35: "底鼓",
    # Toms
    48: "一嗵鼓", 50: "一嗵鼓",
    45: "二嗵鼓", 47: "二嗵鼓",
    41: "落地嗵鼓", 43: "落地嗵鼓",
}


def note_to_token(pitch: int):
    return DRUM_NOTE_MAP.get(pitch)


def midi_to_note_blocks(pm: pretty_midi.PrettyMIDI):
    blocks = []
    for inst in pm.instruments:
        for note in inst.notes:
            tok = note_to_token(note.pitch)
            if not tok:
                continue
            s = round(note.start, 3)
            e = round(note.end, 3)
            if e < s:
                e = s
            blocks.append((s, e, tok))
    return blocks


def group_blocks(blocks):
    groups = {}
    for s, e, tok in blocks:
        key = (s, e)
        groups.setdefault(key, []).append(tok)
    out = []
    for (s, e), toks in groups.items():
        toks.sort()
        out.append((s, e, toks))
    out.sort(key=lambda x: (x[0], x[1]))
    return out


def format_time(t: float) -> str:
    m = int(t // 60)
    s = t % 60
    return f"[{m:02d}:{s:06.3f}]"


def midi_to_lrcd(midi_path: str, lrcd_path: str):
    pm = pretty_midi.PrettyMIDI(midi_path)
    blocks = midi_to_note_blocks(pm)
    grouped = group_blocks(blocks)
    with open(lrcd_path, 'w', encoding='utf-8') as f:
        for s, e, toks in grouped:
            if abs(e - s) < 1e-6:
                line = f"{format_time(s)} {' '.join(toks)}\n"
            else:
                line = f"{format_time(s)}{format_time(e)} {' '.join(toks)}\n"
            f.write(line)
    print(f"已生成: {lrcd_path}")


def midi_to_lrcd_text(midi_path: str) -> str:
    pm = pretty_midi.PrettyMIDI(midi_path)
    blocks = midi_to_note_blocks(pm)
    grouped = group_blocks(blocks)
    lines = []
    for s, e, toks in grouped:
        if abs(e - s) < 1e-6:
            lines.append(f"{format_time(s)} {' '.join(toks)}")
        else:
            lines.append(f"{format_time(s)}{format_time(e)} {' '.join(toks)}")
    return ("\n".join(lines) + ("\n" if lines else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_midi', type=str, required=True, help='需要转换的mid文件路径')
    parser.add_argument('--output_lrcd', type=str, required=True, help='转换后保存的lrcd文件路径')
    args = parser.parse_args()
    midi_to_lrcd(args.input_midi, args.output_lrcd)
