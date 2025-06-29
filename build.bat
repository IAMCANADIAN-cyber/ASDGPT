@echo off
REM Batch script to build the ACR application using PyInstaller on Windows

REM Get App Name from config.py (simple parsing - might need python in PATH)
FOR /F "tokens=* USEBACKQ" %%F IN (`python -c "import config; print(config.APP_NAME)"`) DO (
  SET APP_NAME=%%F
)
IF "%APP_NAME%"=="" (
  SET APP_NAME=ACR
  echo Warning: Could not determine APP_NAME from config.py, using fallback: %APP_NAME%
)

REM Icon file - .ico is preferred for Windows. .png might work or be ignored.
SET ICON_FILE=assets\icons\default_icon.png
REM For a proper Windows icon, convert default_icon.png to default_icon.ico and use:
REM SET ICON_FILE=assets\icons\default_icon.ico

echo Starting PyInstaller build for %APP_NAME%...
echo Output will be in dist\%APP_NAME%.exe

REM Clean previous builds
IF EXIST build RMDIR /S /Q build
IF EXIST dist RMDIR /S /Q dist
IF EXIST "%APP_NAME%.spec" DEL /F /Q "%APP_NAME%.spec"

REM PyInstaller command
REM --add-data: Format on Windows for PyInstaller is typically "SOURCE;DESTINATION_IN_BUNDLE"
REM             However, PyInstaller often correctly interprets ":" as well.
REM             Let's use ":" for consistency with the .sh script, as PyInstaller usually handles it.
REM             'assets:assets' should copy the 'assets' folder into the bundle's 'assets' folder.
REM --hidden-import: May be needed for libraries like sounddevice or pystray backends.
REM                  e.g. --hidden-import=sounddevice._ffi --hidden-import=pystray.backend.win32
REM                  These are added if runtime errors occur.

echo Using icon: %ICON_FILE%

pyinstaller --name "%APP_NAME%" ^
    --onefile ^
    --windowed ^
    --icon="%ICON_FILE%" ^
    --add-data "assets:assets" ^
    --noconfirm ^
    --log-level INFO ^
    main.py

REM Check if build was successful
IF %ERRORLEVEL% EQU 0 (
    echo Build successful!
    echo Executable created in dist\
    DIR dist /B
) ELSE (
    echo Build failed. See output above for details.
    exit /b 1
)

echo Build script finished.
