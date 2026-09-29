' ==============================================================================
' launch_dashboard.vbs
' 백업시스템 스마트 런처 (Smart Dashboard Launcher)
'
' 1. 백업 서버(http://127.0.0.1:8765) 동작 여부 확인 (MSXML2.ServerXMLHTTP)
' 2. 서버가 꺼져 있을 경우 start_silent.vbs를 무창(SW_HIDE)으로 자동 기동
' 3. 서버가 준비될 때까지 대기 (최대 3초, 300ms 간격)
' 4. 기본 브라우저로 대시보드(http://127.0.0.1:8765) 오픈
' ==============================================================================
Option Explicit

Const DASHBOARD_URL = "http://127.0.0.1:8765"
Const PING_URL      = "http://127.0.0.1:8765/api/system/release-info"

Dim objShell, objFSO, appDir, startVbs
Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

appDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
objShell.CurrentDirectory = appDir
startVbs = appDir & "\start_silent.vbs"

' 1. Check if server is alive
If Not IsServerAlive() Then
    ' Start server silently if start_silent.vbs exists
    If objFSO.FileExists(startVbs) Then
        objShell.Run "wscript.exe """ & startVbs & """", 0, False
    End If
    
    ' Wait up to 3 seconds for server to respond
    Dim i
    For i = 1 To 10
        WScript.Sleep 300
        If IsServerAlive() Then Exit For
    Next
End If

' 2. Launch default web browser
objShell.Run "cmd.exe /c start """" """ & DASHBOARD_URL & """", 0, False

Function IsServerAlive()
    On Error Resume Next
    Dim http
    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    If Err.Number <> 0 Then
        Err.Clear
        Set http = CreateObject("MSXML2.ServerXMLHTTP")
    End If
    
    http.setTimeouts 500, 500, 500, 500
    http.open "GET", PING_URL, False
    http.send
    
    If Err.Number = 0 And (http.status = 200 Or http.status = 401) Then
        IsServerAlive = True
    Else
        IsServerAlive = False
    End If
    On Error Goto 0
    Set http = Nothing
End Function
