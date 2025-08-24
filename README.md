# 🎹 Python 自动弹琴/架子鼓脚本

<p align="center">
  <img src="https://github.com/user-attachments/assets/18963a74-329e-42a4-9014-8b454a114203" width="200" height="200" />
</p>


## 📖 功能介绍
本脚本由 AI 辅助编写，适用于 《开放空间》 Windows 平台，可以根据指定的乐谱文件，自动模拟键盘输入，在游戏中实现“自动演奏（钢琴/架子鼓）”。
- 支持乐器
  - 钢琴（.lrcp / .mid）
  - 架子鼓（.lrcd / .mid）

- 钢琴音域/和弦键位
  - 低音 1~7 → `asdfghj`  
  - 中音 1~7 → `qwertyu`  
  - 高音 1~7 → `1234567`  
  - 和弦（C, Dm, Em, F, G, Am, G7） → `zxcvbnm`  

- 架子鼓键位（drum_map）
  - 踩镲闭 `1`，高音吊镲 `2`，一嗵鼓 `3`，二嗵鼓 `4`，叮叮镲 `5`
  - 踩镲开 `Q`，军鼓 `W`，底鼓 `E`，落地嗵鼓 `R`，中音吊镲 `T`

- 可视化功能  
  提供窗口内按键显示 + 可外置叠加层的“按键显示设置”。

- 自动演奏  
  根据乐谱时间轴自动模拟键盘按键。

- 延长音支持  
  通过双时间戳 `[开始][结束]` 表示按下保持到释放时间。

- MIDI 格式转换  
  钢琴：`utils/midi2lrcp.py`；架子鼓：`utils/midi2lrcd.py`。

- 多人模式  
  钢琴：去和弦 + 多音时间分散；架子鼓：无和弦，仍支持多击分散。

- 低延迟按键发送  
  通过设置实现毫秒级紧凑按键调度。

- 按键录制  
  支持录制动作，按所选乐器导出为 `.lrcp` 或 `.lrcd`。

---

## 📂 当前项目结构
```
OverField_Auto_Piano/
├─ main_single.py                      # 单人模式入口（含自动管理员检测）
├─ main_multi.py                       # 多人模式入口（去和弦 + 分散，含自动管理员检测）
├─ requirements.txt                    # 依赖（pretty_midi / pyautogui / pynput）
├─ README.md                           # 主 README（使用说明）
├─ README_Piano_Autoplayer_Tutorial.txt# 钢琴乐谱编写教程
├─ README_Drum_Autoplayer_Tutorial.txt # 架子鼓乐谱编写教程
├─ example/
│  ├─ lrcp/                            # 示例钢琴乐谱 (.lrcp)
│  └─ mid/                             # 示例 MIDI
├─ src/
│  ├─ app.py                           # 基础 GUI 框架与公共组件(BaseApp)
│  ├─ app_single.py                    # 单人模式 UI 与加载/播放逻辑
│  ├─ app_multi.py                     # 多人模式 UI 与偏移/去和弦逻辑
│  ├─ event.py                         # Event / SimpleEvent 数据结构
│  ├─ key_sender.py                    # 按键发送封装
│  ├─ key_sender_pyautogui.py
│  └─ player.py                        # 播放线程调度
├─ utils/
│  ├─ constant.py                      # 键位映射 & 正则（含 drum_map）
│  ├─ parse.py                         # 乐谱解析 + 多人预处理(preprocess)
│  ├─ midi2lrcp.py                     # MIDI -> LRCP 转换函数 & CLI
│  ├─ midi2lrcd.py                     # MIDI -> LRCD 转换函数 & CLI
│  ├─ util.py                          # admin_running 自动提权函数
│  ├─ lrcp_recorder.py                 # 录制实时演奏生成 .lrcp / .lrcd
│  └─ key_cast_overlay_demo.py         # 按键叠加层
└─ release/
```
> 说明：旧结构中的 `play_piano.py / play_piano_multi.py / main.py / (根) midi2lrcp.py` 已完全被以上模块化结构取代。

---

## 📝 乐谱文件格式说明（钢琴 .lrcp / 架子鼓 .lrcd）
两者的行写法相同，仅 token 不同：

- 短音行格式：
  ```
  [时间] 记号(可多个)
  ```

- 延长音行格式：
  ```
  [开始时间][结束时间] 记号(可多个)
  ```
  第一个时间戳表示按下，第二个表示释放。

- 多个独立重复短音：
  ```
  [00:01.000][00:01.500] 记号
  ```

- 钢琴 token：
  - 低音：`L1`~`L7`
  - 中音：`M1`~`M7`
  - 高音：`H1`~`H7`
  - 和弦：`C, Dm, Em, F, G, Am, G7`

- 架子鼓 token（中文名）：
  - `踩镲闭`、`高音吊镲`、`一嗵鼓`、`二嗵鼓`、`叮叮镲`、`踩镲开`、`军鼓`、`底鼓`、`落地嗵鼓`、`中音吊镲`

---

## ▶️ 使用方法（单人 / 原版）
1. 安装依赖
   ```bash
   pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
   ```
2. 直接运行（脚本会自动尝试管理员提权）：
   ```bash
   python main_single.py
   ```
3. 在窗口中：
   - 选择乐器：钢琴 或 架子鼓
   - 载入 `.lrcp/.lrcd` 或 `.mid` 文件（.mid 会自动转换）
   - 设置参数（速度 / 倒计时 / 全局延迟）  
   - 点击“开始演奏”
4. 切回游戏窗口保持焦点即可听到自动演奏。

5. MIDI 转换：
   - 钢琴：
     ```bash
     python utils/midi2lrcp.py --input_midi "your.mid" --output_lrcp "out.lrcp"
     ```
   - 架子鼓：
     ```bash
     python utils/midi2lrcd.py --input_midi "your.mid" --output_lrcd "out.lrcd"
     ```

---

## 🤝 多人模式说明 (main_multi.py)
- 钢琴：去除和弦，按“多音偏移”对同刻多音进行分散；延长音整体平移。
- 架子鼓：无和弦，同样按“多音偏移”对同刻多击进行分散。

使用：
```bash
python main_multi.py
```
步骤：
1. 选择乐器并载入谱（.lrcp/.lrcd 或 .mid）
2. 调整“多音偏移(ms)”（如 -15,0,15）
3. 点击开始

建议：若仍感觉漏音，可降低速度比例、增大偏移或简化谱面。

---

## ⚠️ 注意事项
- 需 管理员权限 运行（脚本已尝试自动提权，失败时请手动）。  
- 游戏可能存在反作弊机制，使用请自担风险。  
- 若无法识别按键可尝试：
  1. 以管理员身份运行 Python；
  2. 调整发送方式（可自行替换为其它库例如 `keyboard`、`pynput`）；
  3. 使用虚拟键盘驱动（vJoy 等）。

---

## 🎶 扩展建议
- 支持其他乐器：吉他、贝斯、架子鼓、麦克风
- MIDI 文件解析 → `.lrcp`/`.lrcd`
- 可视化键盘实时高亮
- 录制实时演奏生成 `.lrcp`/`.lrcd`
- 智能节流 / 自适应多人限速策略

---

## 📌 示例演奏
- 运行 `python main_single.py` 选择 `example/lrcp/一闪一闪亮晶晶.lrcp`  
- 或在多人模式下运行 `python main_multi.py` 体验分散后的主旋律  

祝使用愉快！  

## ▶️ 演示视频
- [钢琴](https://www.bilibili.com/video/BV11YYizGEVC)
- [架子鼓](https://www.bilibili.com/video/BV11YYizGEVC?&p=2)

<p align="center">
<img width="766" height="814" alt="image" src="https://github.com/user-attachments/assets/479bf15d-5839-4fca-80e0-23b559363b8a" />
</p>
<p align="center">
<img width="875" height="806" alt="image" src="https://github.com/user-attachments/assets/c699a800-61b4-4d84-af99-ac3a218a4687" />
</p>
<p align="center">
<img width="429" height="325" alt="image" src="https://github.com/user-attachments/assets/00f23b74-b1ba-4f1a-9c0e-bfd3ee1ad244" />
</p>
<p align="center">
<img width="583" height="594" alt="image" src="https://github.com/user-attachments/assets/7e09ef49-e24a-461b-a10a-b68fc0c5da7b" />
</p>


