# 自动弹琴脚本打包

```b
OverField_Auto_Piano
├─ release
│    ├─ README.md
│    ├─ build_single.bat
│    ├─ build_multi.bat
│    ├─ dist_single
│    │    └─ PianoSingle.exe  # 生成的可执行文件
│    └─ upx-5.0.0-win64       # 在打包压缩时需要的依赖
└─ ...
```

## 使用方法

激活当前项目的虚拟环境，确保在当前环境中能正确运行本项目且安装了`pyinstaller`。否则打包出来的exe会出现缺少对应依赖的问题

进入到release目录下：

```bash
(base) E:\OverField_Auto_Piano>conda activate overfield
(overfield) E:\OverField_Auto_Piano>cd release
(overfield) E:\OverField_Auto_Piano\release>
```

运行脚本：

```bash
(overfield) E:\NRB\OverField_Auto_Piano\release>build_single.bat
...
19037 INFO: Fixing EXE headers
19134 INFO: Building EXE from EXE-00.toc completed successfully.
打包完成!
可执行文件位于 dist_single 文件夹中
Press any key to continue . . .
```

实际打包测试过程发现：使用`pyautogui`标准库会占用较大程序体积，而后调整为使用`pynput.keyboard`标准库进行按键发送，以下为打包的exe体积对比

```bash
overfield_auto_piano_single.exe  # 若使用pyautogui，且不用UPX压缩，体积为：36.4M
overfield_auto_piano_single.exe  # 若使用pyautogui，且使用UPX压缩，体积为：28.8M
overfield_auto_piano_single.exe  # 若使用keyboard ，且不用UPX压缩，体积为：12.2M
overfield_auto_piano_single.exe  # 若使用keyboard ，且使用UPX压缩，体积为：10.7M(采用)
```

当前单人与多人弹琴的打包脚本分开写，虽然里面内容基本一致，但考虑到后续可能对多人弹琴有优化等改动，打包脚本就不写在同一个文件里