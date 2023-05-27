@echo off
for /r %%i in (*.txt) do (
    del "%%i"
)
echo All .txt files have been deleted in the current directory and its subdirectories.
pause