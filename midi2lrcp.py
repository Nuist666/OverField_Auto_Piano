import os
import sys
import pretty_midi

# 音符到lrcp映射表（使用 C4=60 基准）
NOTE_MAP = {
    # 低音区
    48: 'L1', 50: 'L2', 52: 'L3', 53: 'L4', 55: 'L5', 57: 'L6', 59: 'L7',
    # 中音区
    60: 'M1', 62: 'M2', 64: 'M3', 65: 'M4', 67: 'M5', 69: 'M6', 71: 'M7',
    # 高音区
    72: 'H1', 74: 'H2', 76: 'H3', 77: 'H4', 79: 'H5', 81: 'H6', 83: 'H7',
}

# 可选：和弦识别略（保留接口）

def note_to_token(note):
    return NOTE_MAP.get(note, None)

def midi_to_note_blocks(pm):
    """返回 (start, end, token) 列表，保留延音."""
    blocks = []
    for inst in pm.instruments:
        for note in inst.notes:
            token = note_to_token(note.pitch)
            if not token:
                continue
            start = round(note.start, 3)
            end = round(note.end, 3)
            if end < start:
                end = start
            blocks.append((start, end, token))
    return blocks

def group_blocks(blocks):
    """将相同 (start,end) 的多个 token 合并为一行."""
    groups = {}
    for start, end, token in blocks:
        key = (start, end)
        groups.setdefault(key, []).append(token)
    out = []
    for (s, e), tokens in groups.items():
        tokens.sort()
        out.append((s, e, tokens))
    out.sort(key=lambda x: (x[0], x[1]))
    return out

def format_time(t):
    m = int(t // 60)
    s = t % 60
    return f"[{m:02d}:{s:06.3f}]"

def midi_to_lrcp(midi_path, lrcp_path):
    pm = pretty_midi.PrettyMIDI(midi_path)
    blocks = midi_to_note_blocks(pm)
    grouped = group_blocks(blocks)
    with open(lrcp_path, 'w', encoding='utf-8') as f:
        for start, end, tokens in grouped:
            if abs(end - start) < 1e-6:
                # 短音仍写单时间戳
                line = f"{format_time(start)} {' '.join(tokens)}\n"
            else:
                line = f"{format_time(start)}{format_time(end)} {' '.join(tokens)}\n"
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