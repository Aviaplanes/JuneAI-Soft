:: Post-install cleanup script
:: Removes files and folders that are no longer needed after setup:
@echo off
rmdir /s /q icons 2>nul
del /f /q install_browser.bat 2>nul
del /f /q requirements.txt 2>nul
del /f /q install.bat 2>nul
del /f /q CHANGELOG.md 2>nul
del /f /q README.md 2>nul
