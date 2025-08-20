@echo off
:: set the terminal encode with UTF-8
chcp 65001 >nul

:: Set the EXE file name
set EXE_NAME=overfield_auto_piano_single

:: Set the working directory
set WORK_DIR=%~dp0
cd /d %WORK_DIR%

:: Clean up previous builds
if exist dist_single rmdir /s /q dist_single
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__
if exist %EXE_NAME%.spec del /f /q %EXE_NAME%.spec

:: Use PyInstaller to generate the .spec file
pyinstaller --onefile --windowed --icon=logo.ico --name "%EXE_NAME%" ../main_single.py

:: Modify the .spec file to include additional files and hiddenimports
powershell -Command "(Get-Content %EXE_NAME%.spec) -replace 'datas=\[', 'datas=[(''../src'', ''src''), (''../utils'', ''utils'')' | Set-Content %EXE_NAME%.spec"
:: powershell -Command "(Get-Content %EXE_NAME%.spec) -replace 'hiddenimports=\[', 'hiddenimports=[''os'',''tkinter'',''tkinter.filedialog'',''tkinter.messagebox'',''re'',''dataclasses'',''pyautogui'',''time'',''threading'',''argparse'',''pretty_midi'',''sys'',''ctypes'',''typing'',''packaging''' | Set-Content %EXE_NAME%.spec"
powershell -Command "(Get-Content %EXE_NAME%.spec) -replace 'hiddenimports=\[', 'hiddenimports=[''os'',''tkinter'',''tkinter.filedialog'',''tkinter.messagebox'',''re'',''dataclasses'',''pynput.keyboard'',''time'',''threading'',''argparse'',''pretty_midi'',''sys'',''ctypes'',''typing'',''packaging''' | Set-Content %EXE_NAME%.spec"

:: Build again using the modified .spec file
pyinstaller "%EXE_NAME%.spec" --distpath "dist_single" --upx-dir=upx-5.0.0-win64
:: pyinstaller "%EXE_NAME%.spec" --distpath "dist_single"

if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist %EXE_NAME%.spec del /f /q %EXE_NAME%.spec
echo 打包完成!
echo 可执行文件位于 dist_single 文件夹中
pause