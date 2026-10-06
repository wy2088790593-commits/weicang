@echo off
setlocal enabledelayedexpansion
title WorkBuddy Skills Installer

rem ---------------------------------------------------------------
rem  WorkBuddy skills installer (Windows)
rem
rem  usage: install.bat [copy^|link^|list]
rem
rem    copy  (default) - copy each skill into %USERPROFILE%\.workbuddy\skills\
rem    link            - directory junction (mklink /J), repo stays the live copy
rem    list            - only list skills in this repo, install nothing
rem
rem  NOTE: this file is intentionally plain ASCII only (GBK + CRLF safe).
rem        Do not add non-ASCII text here. Paths are taken from %%~dp0
rem        so a non-ASCII repo location still works.
rem ---------------------------------------------------------------

set "MODE=%~1"
if "%MODE%"=="" set "MODE=copy"

set "SRC=%~dp0skills"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"
set "DEST=%USERPROFILE%\.workbuddy\skills"

if /i "%MODE%"=="list" goto LIST
if /i "%MODE%"=="copy" goto RUN
if /i "%MODE%"=="link" goto RUN
echo [FAIL] unknown mode: %MODE%
echo        usage: install.bat [copy^|link^|list]
pause
exit /b 2

:RUN
if not exist "%SRC%" (
  echo [FAIL] skills folder not found next to this script.
  pause
  exit /b 2
)

echo Source : %SRC%
echo Target : %DEST%
echo Mode   : %MODE%
echo.

if not exist "%DEST%" md "%DEST%" >nul 2>&1

set /a OK=0
set /a BAD=0

for /d %%D in ("%SRC%\*") do (
  set "NAME=%%~nxD"
  if not "!NAME!"=="" (
    call :ONE "%%~fD" "!NAME!"
  )
)

echo.
echo Done. installed=%OK%  failed=%BAD%
echo Restart your WorkBuddy session for new skills to load.
echo.
pause
exit /b 0

rem ---------------------------------------------------------------
rem  :ONE  <source_dir>  <skill_name>
rem ---------------------------------------------------------------
:ONE
set "SDIR=%~1"
set "SN=%~2"
set "TDIR=%DEST%\%SN%"

if /i "%MODE%"=="link" goto ONE_LINK

if exist "%TDIR%" rd /s /q "%TDIR%"
xcopy "%SDIR%" "%TDIR%\" /E /I /Y /Q >nul 2>&1
if exist "%TDIR%\SKILL.md" (
  echo   [OK]   %SN%
  set /a OK+=1
) else (
  echo   [FAIL] %SN%
  set /a BAD+=1
)
exit /b 0

:ONE_LINK
if exist "%TDIR%" rd /s /q "%TDIR%"
mklink /J "%TDIR%" "%SDIR%" >nul 2>&1
if exist "%TDIR%\SKILL.md" (
  echo   [OK]   %SN%  (linked)
  set /a OK+=1
) else (
  echo   [FAIL] %SN%   -- junction failed, retry with: install.bat copy
  set /a BAD+=1
)
exit /b 0

:LIST
echo Skills in this repo:
for /d %%D in ("%SRC%\*") do (
  if exist "%%~fD\SKILL.md" (echo   [*] %%~nxD) else (echo   [-] %%~nxD  ^(no SKILL.md^))
)
echo.
pause
exit /b 0
