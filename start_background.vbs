Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

venvPython = currentDir & "\.venv\Scripts\pythonw.exe"

If Not fso.FileExists(venvPython) Then
    ' No venv found - run start.bat to set up environment first
    WshShell.Run "cmd.exe /c """ & currentDir & "\start.bat""", 1, False
Else
    ' Kill any existing process on port 8000
    WshShell.Run "cmd.exe /c netstat -aon | findstr /c:"":8000"" | findstr /c:""LISTENING"" > """ & currentDir & "\port_check.tmp"" 2>nul && for /f ""tokens=5"" %a in (""" & currentDir & "\port_check.tmp"") do taskkill /F /PID %a >nul 2>&1 & del """ & currentDir & "\port_check.tmp""", 0, True
    ' Start tray_icon.py with pythonw.exe (no console window)
    WshShell.Run """" & venvPython & """ """ & currentDir & "\tray_icon.py""", 0, False
End If
