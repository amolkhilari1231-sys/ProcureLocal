' ============================================================================
'  ProcureLocal - Automated Desktop Application Launcher
'  Auto-starts Node.js backend silently on launch, waits for health check,
'  and opens isolated app window seamlessly.
' ============================================================================
Option Explicit

Dim sh, fs, d, f, txt, reg, m, port, http, i, serverReady, localApp, profileDir, edgePath, appCmd

Set sh = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
d = fs.GetParentFolderName(WScript.ScriptFullName)
If fs.FileExists(fs.GetParentFolderName(d) & "\server.js") Then
  d = fs.GetParentFolderName(d)
End If
sh.CurrentDirectory = d

' 1. Check if config.json exists
If Not fs.FileExists(d & "\config.json") Then
  MsgBox "First-time setup: a window will open to choose your data folder.", 64, "ProcureLocal"
  sh.Run """" & d & "\start.bat""", 1, False
  WScript.Quit
End If

' 2. Read configured port from config.json (default 3002)
port = "3002"
On Error Resume Next
Set f = fs.OpenTextFile(d & "\config.json", 1)
If Err.Number = 0 Then
  txt = f.ReadAll
  f.Close
  Set reg = New RegExp
  reg.Pattern = """port""\s*:\s*(\d+)"
  reg.IgnoreCase = True
  Set m = reg.Execute(txt)
  If m.Count > 0 Then port = m(0).SubMatches(0)
End If
On Error Goto 0

' 3. Check if server is already running and healthy
Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
serverReady = False
On Error Resume Next
http.Open "GET", "http://127.0.0.1:" & port & "/api/health", False
http.Send
If Err.Number = 0 Then
  If http.Status = 200 Then serverReady = True
End If
On Error Goto 0

' 4. If server is NOT running, start it silently in background
If Not serverReady Then
  sh.Run "cmd.exe /c node server.js >> server.log 2>&1", 0, False

  ' Wait up to 10 seconds for backend to become ready
  For i = 1 To 20
    WScript.Sleep 500
    Err.Clear
    On Error Resume Next
    http.Open "GET", "http://127.0.0.1:" & port & "/api/health", False
    http.Send
    If Err.Number = 0 Then
      If http.Status = 200 Then
        serverReady = True
        Exit For
      End If
    End If
    On Error Goto 0
  Next
End If

' If invoked with 'server' argument (headless server only), exit here
If WScript.Arguments.Count > 0 Then
  If LCase(WScript.Arguments(0)) = "server" Then WScript.Quit
End If

' 5. Prepare Microsoft Edge in standalone App Mode
localApp = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%")
profileDir = localApp & "\ProcureLocal\AppProfile"

edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
If Not fs.FileExists(edgePath) Then
  edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
End If

If fs.FileExists(edgePath) Then
  appCmd = """" & edgePath & """ --app=http://127.0.0.1:" & port & " --user-data-dir=""" & profileDir & """ --no-first-run --no-default-browser-check"
Else
  appCmd = "cmd.exe /c start http://127.0.0.1:" & port
End If

' 6. Open the app window
sh.Run appCmd, 1, False
