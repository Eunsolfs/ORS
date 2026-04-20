@echo off
setlocal

cd /d "%~dp0.."

set "VERSION=%~1"
set "MESSAGE=%~2"

if "%VERSION%"=="" (
  echo === ORS 本地一键发版（BAT）===
  set /p VERSION=请输入版本号（例如 v1.3.7）:
)

if not defined VERSION (
  echo [ERROR] 版本号不能为空
  pause
  exit /b 1
)

echo %VERSION% | findstr /r "^v[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul
if errorlevel 1 (
  echo [ERROR] Version 格式必须为 vX.Y.Z，例如 v1.3.7
  pause
  exit /b 1
)

if "%MESSAGE%"=="" (
  set "MESSAGE=chore: release %VERSION%"
)

git status --short >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 当前目录不是 git 仓库或 git 不可用
  pause
  exit /b 1
)

for /f "delims=" %%i in ('git status --short') do set "HAS_CHANGES=1"
if not defined HAS_CHANGES (
  echo [ERROR] 没有可提交改动，请先修改代码再发版
  pause
  exit /b 1
)

for /f "delims=" %%i in ('git tag --list %VERSION%') do set "TAG_EXISTS=1"
if defined TAG_EXISTS (
  echo [ERROR] Tag 已存在：%VERSION%
  pause
  exit /b 1
)

set /p CONFIRM=确认发布 %VERSION% ? [y/N]:
if /i not "%CONFIRM%"=="y" (
  echo [INFO] 已取消发布
  pause
  exit /b 1
)

echo >> git add -A
git add -A || goto :fail
echo >> git commit -m "%MESSAGE%"
git commit -m "%MESSAGE%" || goto :fail
echo >> git push origin main
git push origin main || goto :fail
echo >> git tag -a %VERSION% -m "Release %VERSION%"
git tag -a %VERSION% -m "Release %VERSION%" || goto :fail
echo >> git push origin %VERSION%
git push origin %VERSION% || goto :fail

echo.
echo [OK] 发布完成：%VERSION%
pause
exit /b 0

:fail
echo.
echo [ERROR] 发版失败，请查看上方报错
pause
exit /b 1
