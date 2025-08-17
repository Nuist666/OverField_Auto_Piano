import os
import sys
import pretty_midi

# 音符到lrcp映射表
NOTE_MAP = {
    # 低音区
    48: 'L1', 50: 'L2', 52: 'L3', 53: 'L4', 55: 'L5', 57: 'L6', 59: 'L7',
    # 中音区
    60: 'M1', 62: 'M2', 64: 'M3', 65: 'M4', 67: 'M5', 69: 'M6', 71: 'M7',
    # 高音区
    72: 'H1', 74: 'H2', 76: 'H3', 77: 'H4', 79: 'H5', 81: 'H6', 83: 'H7',
}

# 可选：和弦名映射（如需自动识别和弦，可扩展）
CHORDS = {
    # (根音, 类型): 和弦名
    (60, 'major'): 'C',
    (62, 'minor'): 'Dm',
    (64, 'minor'): 'Em',
    (65, 'major'): 'F',
    (67, 'major'): 'G',
    (69, 'minor'): 'Am',
    (67, 'dominant'): 'G7',
}

def note_to_token(note):
    return NOTE_MAP.get(note, None)

def midi_to_events(pm):
    """将MIDI转换为事件列表，格式：(时间, [token, ...])"""
    events = []
    # 收集所有音符事件
    for inst in pm.instruments:
        for note in inst.notes:
            start = round(note.start, 3)
            token = note_to_token(note.pitch)
            if token:
                events.append((start, token))
    # 按时间分组
    time_dict = {}
    for t, token in events:
        time_dict.setdefault(t, []).append(token)
    # 排序
    return sorted(time_dict.items())

def format_time(t):
    m = int(t // 60)
    s = t % 60
    return f"[{m:02d}:{s:06.3f}]"

def midi_to_lrcp(midi_path, lrcp_path):
    pm = pretty_midi.PrettyMIDI(midi_path)
    events = midi_to_events(pm)
    with open(lrcp_path, 'w', encoding='utf-8') as f:
        for t, tokens in events:
            line = f"{format_time(t)} {' '.join(tokens)}\n"
            f.write(line)
    print(f"已生成: {lrcp_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python midi2lrcp.py <midi文件>")
        sys.exit(1)
    midi_file = sys.argv[1]
    if not os.path.isfile(midi_file):
        print("文件不存在:", midi_file)
        sys.exit(1)
    name, _ = os.path.splitext(os.path.basename(midi_file))
    lrcp_file = name + ".lrcp"
    midi_to_lrcp(midi_file, lrcp_file)