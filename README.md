# 🎹 Python 自动弹琴脚本

<p align="center">
  <img src="https://github.com/user-attachments/assets/18963a74-329e-42a4-9014-8b454a114203" width="200" height="200" />
</p>


## 📖 功能介绍
本脚本由 AI 辅助编写，适用于 《开放空间》 Windows 平台，可以根据指定的乐谱文件，自动模拟键盘输入，在游戏中实现“自动弹琴”。
- **支持乐器**
  - 键盘

- **支持音域**  
  - 低音 1~7 → `asdfghj`  
  - 中音 1~7 → `qwertyu`  
  - 高音 1~7 → `1234567`  
  - 和弦（C, Dm, Em, F, G, Am, G7） → `zxcvbnm`  

- **可视化功能**  
  提供简单的窗口界面，可以选择乐谱文件并启动演奏。

- **自动演奏**  
  根据乐谱的时间轴，自动模拟键盘按键，实现自动弹奏。

- **延长音支持**  
  通过双时间戳 `[开始][结束]` 实现按下保持到指定释放时间。

- **MIDI 格式转换**  
  根据 MIDI 文件自动转换为本程序支持的乐谱格式（会输出延长音）。

- **多人模式**  
  针对多人联机中“漏音 / 丢音”问题的降级方案：去除和弦 + 多音时间分散，降低同一瞬间按键密度。

- **低延迟按键发送**  
  通过关闭 `FAILSAFE` 与将 `PAUSE` 设为 0，实现毫秒级紧凑按键调度。

---

## 📂 当前项目结构
```
OverField_Auto_Piano/
├─ main_single.py                      # 单人模式入口（含自动管理员检测）
├─ main_multi.py                       # 多人模式入口（去和弦 + 分散，含自动管理员检测）
├─ requirements.txt                    # 依赖（pretty_midi / pyautogui）
├─ README.md                           # 主 README（使用说明）
├─ README_Piano_Autoplayer_Tutorial.txt# 乐谱编写进阶/格式教程
├─ example/
│  ├─ lrcp/                            # 示例乐谱 (.lrcp)
│  │  ├─ 一闪一闪亮晶晶.lrcp
│  │  └─ 卡农.lrcp
│  └─ mid/                             # 示例 MIDI
│     └─ 卡农.mid
├─ src/
│  ├─ app.py                           # 基础 GUI 框架与公共组件(BaseApp)
│  ├─ app_single.py                    # 单人模式 UI 与加载/播放逻辑
│  ├─ app_multi.py                     # 多人模式 UI 与偏移/去和弦逻辑
│  ├─ event.py                         # Event / SimpleEvent 数据结构
│  ├─ key_sender.py                    # 按键发送封装(FAILSAFE/Pause 设置)
│  ├─ key_sender_pyautogui.py
│  └─ player.py                        # 播放线程调度(排序 + 时间轴执行)
├─ utils/
│  ├─ constant.py                      # 键位映射 & 正则
│  ├─ parse.py                         # 乐谱解析 + 多人预处理(preprocess)
│  ├─ midi2lrcp.py                     # MIDI -> LRCP 转换函数 & CLI
│  └─ util.py                          # admin_running 自动提权函数
├─ release/
│  ├─ README.md                        # 打包脚本使用教程
│  ├─ build_multi.bat                  # 单人弹琴打包脚本
│  ├─ build_single.bat                 # 多人弹琴打包脚本
│  ├─ dist_multi                       # 多人弹琴打包生成的exe存放目录
│  ├─ dist_single                      # 单人弹琴打包生成的exe存放目录
│  ├─ logo.ico                         # 生成的exe的图标
│  └─ upx-5.0.0-win64                  # 打包压缩时所需的依赖
└─ (运行产物/缓存)                       # 未生成：本项目运行不写入缓存文件
```
> 说明：旧结构中的 `play_piano.py / play_piano_multi.py / main.py / (根) midi2lrcp.py` 已完全被以上模块化结构取代。

---

## 📝 乐谱文件格式说明
乐谱文件采用类似 LRC 的格式，扩展名建议使用 `.lrcp`。

- **短音行格式：**
  ```
  [时间] 音符(可多个)
  ```
  单时间戳表示点按（按下后立即释放）。

- **延长音行格式：**
  ```
  [开始时间][结束时间] 音符(可多个)
  ```
  第一个时间戳表示按下，第二个表示释放。适合需要 sustain 的音或和弦。

- **多个独立重复短音：**
  ```
  [00:01.000][00:01.500] C   # 两次短音 C（结束时间不大于开始时间不被视为延长）
  ```

- **音符映射表：**  
  - 低音：`L1`~`L7`  
  - 中音：`M1`~`M7`  
  - 高音：`H1`~`H7`  
  - 和弦：`C, Dm, Em, F, G, Am, G7`  

### 示例：《一闪一闪亮晶晶》（节选，加入延长演示）
```lrcp
[00:00.000][00:00.600] M1 C
[00:00.600] M1
[00:01.199] M5
[00:01.799] M5
[00:02.399][00:03.000] M6
[00:03.600] M5
```

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
   - 载入 `.lrcp` 乐谱或 `.mid` 文件
   - 设置参数（速度 / 倒计时 / 全局延迟）  
   - 点击“开始演奏”
4. 切回游戏窗口保持焦点即可听到自动演奏。

5. **MIDI 转换为 .lrcp：**
   当前 `utils/midi2lrcp.py` 为示例脚本，默认转换示例 `example/mid/卡农.mid`。
   - 方式 A：修改脚本末尾 `midi_file` / `lrcp_file` 变量后运行：
     ```bash
     python utils/midi2lrcp.py
     ```
   - 方式 B：在你自己的脚本中调用：
     ```python
     from utils.midi2lrcp import midi_to_lrcp
     midi_to_lrcp('your.mid', 'out.lrcp')
     ```
   - 方式 C：命令行：
     ```bash
     python utils/midi2lrcp.py --input_mid "your.mid" --output_lrcp "out.lrcp"
     ```
   - 基准：C4=60，支持音高 48~83（超出范围将被忽略）。

---

## 🤝 多人模式说明 (main_multi.py)
### 背景问题
多人联机里可能出现：
1. 同时按两键时，其他玩家只能听到一个，甚至副手和弦“挤掉”主旋律；
2. 极短时间内可被正确播放的按键数量受限（估计 ~ 每秒 3~4 个实际生效）。

### 策略
`main_multi.py` / `AppMulti` 运行时对已解析事件做退化预处理（不修改源谱文件）：
- 去除所有和弦（C, Dm, Em, F, G, Am, G7），避免宽音堆叠；
- 若同一时间戳包含多个单音，按顺序给予“时间偏移”分散（提前或延后若干毫秒）；
- 延长音整体平移（保持时长不变）。

### 多音偏移参数
输入示例：
```
-15,0,15
```
含义：
- 第1个音：提前15ms；第2个：不变；第3个：延后15ms；第4个再次使用第1个偏移，如此循环。

规则：
- 支持逗号 / 空格 / 分号分隔；
- 范围限制：每个值 -50 ~ 50 ms（超出将被裁剪）；
- 留空或全部非法 -> 默认为 [0]；
- 可尝试组合：`-20,0,20`、`-10,5,15` 等；
- 偏移仅运行期生效，不写回谱文件。

### 何时使用
- 原谱含大量和弦、密集装饰音，联机中主旋律不清晰；
- 经常出现“打一串但对方几乎没听见”情况。 

### 使用步骤
```bash
python main_multi.py
```
然后：
1. 载入 `.lrcp` 乐谱或 `.mid` 文件；
2. 调整“多音偏移(ms)”；
3. 点击开始；
4. 若仍感觉漏音，可：
   - 降低速度比例 (<1.0 放慢整体)；
   - 增大多音间隔（更大的正负偏移）；
   - 手动精简谱中过密修饰音。

### 效果与取舍
- 优点：主旋律清晰度提升；丢音概率降低。
- 代价：失去和弦丰满度，部分“同时”音会轻微错位。

---

## ⚠️ 注意事项
- 需 **管理员权限** 运行（脚本已尝试自动提权，失败时请手动）。  
- 游戏可能存在反作弊机制，使用请自担风险。  
- 若无法识别按键可尝试：
  1. 以管理员身份运行 Python；
  2. 调整发送方式（可自行替换为其它库例如 `keyboard`、`pynput`）；
  3. 使用虚拟键盘驱动（vJoy 等）。

---

## 🎶 扩展建议
- 支持其他乐器：吉他、贝斯、架子鼓、麦克风
- MIDI 文件解析 → `.lrcp`（已完成）
- 可视化键盘实时高亮
- 录制实时演奏生成 `.lrcp`
- 智能节流 / 自适应多人限速策略

---

## 📌 示例演奏
- 运行 `python main_single.py` 选择 `example/lrcp/一闪一闪亮晶晶.lrcp`  
- 或在多人模式下运行 `python main_multi.py` 体验分散后的主旋律  

祝使用愉快！  

## ▶️ 演示视频
- [bilibili](https://www.bilibili.com/video/BV11YYizGEVC)
<p align="center">
<img width="705" height="539" alt="image" src="https://github.com/user-attachments/assets/4e261f9a-4596-433e-b305-eaac4d21ff78" />
</p>
<p align="center">
<img width="751" height="418" alt="image" src="https://github.com/user-attachments/assets/1eb9ceb4-a710-4ddb-9e59-50930bd66f86" />
</p>