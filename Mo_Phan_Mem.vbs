Set WshShell = CreateObject("WScript.Shell")
' Tự động lấy đường dẫn thư mục hiện tại
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

' Chạy bằng pythonw.exe để mở thẳng giao diện mà không hiện bảng đen CMD
If CreateObject("Scripting.FileSystemObject").FileExists(strPath & "\.venv\Scripts\pythonw.exe") Then
    WshShell.Run """" & strPath & "\.venv\Scripts\pythonw.exe"" main.py", 0, False
Else
    WshShell.Run "pythonw main.py", 0, False
End If