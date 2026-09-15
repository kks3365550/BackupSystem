Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Dim currentDir, pyExe, userProfile
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

userProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
pyExe = "python"

If fso.FileExists(currentDir & "\.venv\Scripts\python.exe") Then
    pyExe = """" & currentDir & "\.venv\Scripts\python.exe"""
ElseIf fso.FileExists(userProfile & "\AppData\Local\Python\pythoncore-3.14-64\python.exe") Then
    pyExe = """" & userProfile & "\AppData\Local\Python\pythoncore-3.14-64\python.exe"""
ElseIf fso.FileExists(userProfile & "\AppData\Local\Python\bin\python.exe") Then
    pyExe = """" & userProfile & "\AppData\Local\Python\bin\python.exe"""
Else
    pyExe = "python"
End If

WshShell.Run pyExe & " """ & currentDir & "\run.py""", 0, False
