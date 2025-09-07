@echo off
setlocal enabledelayedexpansion

set /p userInput="是否删除 build（缓存）文件夹？（默认为Y）(Y/N): "

:: 默认 Y
if "%userInput%"=="" set userInput=Y

:: 删除 build 文件夹
if /I "%userInput%"=="Y" (
    if exist build (
        rmdir /s /q build
        echo build 已删除
    )
) else (
    echo 删除 build 文件夹失败
)


set filesToCheck[0]=.venv\Lib\site-packages\cv2\opencv_videoio_ffmpeg4110_64.dll
set filesToCheck[1]=.venv\Lib\site-packages\selenium\webdriver\common\linux\selenium-manager
set filesToCheck[2]=.venv\Lib\site-packages\selenium\webdriver\common\macos\selenium-manager
set filesToCheck[3]=.venv\Lib\site-packages\chromedriver_binary\chromedriver.exe

for /L %%i in (0,1,2,3) do (
    call set "file=%%filesToCheck[%%i]%%"
    if exist "!file!" (
        set /p delInput="是否删除 !file! （减少打包大小，默认为Y） (Y/N): "
        if "!delInput!"=="" set delInput=Y
        if /I "!delInput!"=="Y" (
            del /f /q "!file!" >nul 2>nul
            if exist "!file!" (
                rd /s /q "!file!" >nul 2>nul
            )
            echo !file! 已删除
        ) else (
            echo 不删除 !file!
        )
    )
)

.\.venv\Scripts\pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo 未安装 pyinstaller 是否安装？
    .\.venv\Scripts\pip install pyinstaller
) else (
    echo pyinstaller 已安装
)

call .\.venv\Scripts\activate.bat
.\.venv\Scripts\pyinstaller main.spec
echo 打包完成，请查看dist文件夹  
pause