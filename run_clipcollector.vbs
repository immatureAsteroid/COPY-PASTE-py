' Double-click this file to start ClipCollector silently in the background.
' It runs fully independent of VS Code / any terminal — closing VS Code
' or any editor will NOT stop it.
'
' Requires: pythonw.exe (comes bundled with every Python install on Windows)

Set WshShell = CreateObject("WScript.Shell")
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir
WshShell.Run "pythonw clipcollector.py", 0, False
