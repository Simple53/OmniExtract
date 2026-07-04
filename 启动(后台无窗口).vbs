Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

venvPython = currentDir & "\.venv\Scripts\python.exe"

If Not fso.FileExists(venvPython) Then
    ' Run start.bat in visible window to set up environment and install dependencies
    WshShell.Run "cmd.exe /c """ & currentDir & "\start.bat""", 1, false
Else
    ' Clean port 8000 first using the stop script to prevent conflicts
    WshShell.Run "cmd.exe /c """ & currentDir & "\停止(关闭后台).bat""", 0, true
    ' Start the system tray app (runs python.exe in background, which will manage console visibility)
    WshShell.Run """" & venvPython & """ """ & currentDir & "\tray_icon.py""", 0, false
End If
