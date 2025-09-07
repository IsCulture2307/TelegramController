@echo off
setlocal enabledelayedexpansion

set /p userInput="�Ƿ�ɾ�� build�����棩�ļ��У���Ĭ��ΪY��(Y/N): "

:: Ĭ�� Y
if "%userInput%"=="" set userInput=Y

:: ɾ�� build �ļ���
if /I "%userInput%"=="Y" (
    if exist build (
        rmdir /s /q build
        echo build ��ɾ��
    )
) else (
    echo ɾ�� build �ļ���ʧ��
)


set filesToCheck[0]=.venv\Lib\site-packages\cv2\opencv_videoio_ffmpeg4110_64.dll
set filesToCheck[1]=.venv\Lib\site-packages\selenium\webdriver\common\linux\selenium-manager
set filesToCheck[2]=.venv\Lib\site-packages\selenium\webdriver\common\macos\selenium-manager
set filesToCheck[3]=.venv\Lib\site-packages\chromedriver_binary\chromedriver.exe

for /L %%i in (0,1,2,3) do (
    call set "file=%%filesToCheck[%%i]%%"
    if exist "!file!" (
        set /p delInput="�Ƿ�ɾ�� !file! �����ٴ����С��Ĭ��ΪY�� (Y/N): "
        if "!delInput!"=="" set delInput=Y
        if /I "!delInput!"=="Y" (
            del /f /q "!file!" >nul 2>nul
            if exist "!file!" (
                rd /s /q "!file!" >nul 2>nul
            )
            echo !file! ��ɾ��
        ) else (
            echo ��ɾ�� !file!
        )
    )
)

.\.venv\Scripts\pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo δ��װ pyinstaller �Ƿ�װ��
    .\.venv\Scripts\pip install pyinstaller
) else (
    echo pyinstaller �Ѱ�װ
)

call .\.venv\Scripts\activate.bat
.\.venv\Scripts\pyinstaller main.spec
echo �����ɣ���鿴dist�ļ���  
pause