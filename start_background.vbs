Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

venvPython = currentDir & "\.venv\Scripts\pythonw.exe"

If Not fso.FileExists(venvPython) Then
    ' 未检测到虚拟环境：弹窗提示并以显示窗口方式运行 start.bat，让用户看到配置依赖的进度
    MsgBox "未检测到 Python 虚拟环境，系统将打开控制台自动进行环境配置，请稍候...", 64, "OmniExtract"
    WshShell.Run "cmd.exe /c """ & currentDir & "\start.bat""", 1, True
Else
    ' 已有虚拟环境：直接无窗口后台运行
    ' 1. 调用 stop_server.bat 释放占用端口 (无窗口运行，等待其完成)
    WshShell.Run "cmd.exe /c """ & currentDir & "\stop_server.bat""", 0, True
    ' 2. 运行托盘程序 (无窗口运行)
    WshShell.Run """" & venvPython & """ """ & currentDir & "\tray_icon.py""", 0, False
End If
