@echo off
:bot_reboot
	python3 main.py
	if errorlevel 1 (
   		goto :bot_shutdown
	)
	git pull
	goto :bot_reboot

:bot_shutdown
cmd /k