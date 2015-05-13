@echo off
setlocal
set this_dir=%~dp0
set PATH=%this_dir%\..\python;%PATH%
set PYTHONPATH=%this_dir%\..;%PYTHONPATH%
python "%this_dir%\..\src\main.py" %*
endlocal
