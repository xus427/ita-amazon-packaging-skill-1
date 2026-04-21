@echo off
chcp 65001 >nul
REM ============================================================================
REM 启动 AUTOMATIC1111 WebUI 并开启 API（供生成后端 sd 使用 txt2img / sdapi）
REM
REM 使用前请修改下一行为你本机「stable-diffusion-webui」解压目录（文件夹内有 webui-user.bat）
REM ============================================================================
set "WEBUI_HOME=C:\CHANGE_ME\stable-diffusion-webui"

if not exist "%WEBUI_HOME%\webui-user.bat" (
  echo [错误] 未找到 "%WEBUI_HOME%\webui-user.bat"
  echo 请编辑本脚本，将 WEBUI_HOME 改成你的 AUTOMATIC1111 安装路径。
  pause
  exit /b 1
)

REM 固定端口 7860，与本项目 .env 中 SD_API_URL=http://127.0.0.1:7860 对齐（若改端口请同步改 .env）
REM 若启动后自检脚本报 HTTP 502，多半是 7860 已被占用：换一个端口号并在 .env 里改掉 SD_API_URL。
set "COMMANDLINE_ARGS=--api --listen 127.0.0.1 --port 7860"

cd /d "%WEBUI_HOME%"
echo 启动 SD WebUI（API 已启用），请勿关闭本窗口...
call webui-user.bat
