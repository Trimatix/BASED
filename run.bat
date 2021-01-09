@echo off
if "%~1"=="-g" (
	set usegit=true
) else (
	set usegit=false
)
if %usegit%==false (
	if "%~2"=="-g" (
		set usegit=true
	)
)

if not "%~1"=="-g" (
	set cfg="%~1"
) else (
	set "cfg="
)
if not defined cfg (
	if not "%~2"=="-g" (
		if not "%~2"=="" (
			set cfg="%~2"
		)
	)
)

if defined cfg (
	set runbot=py main.py %cfg%
) else (
	set runbot=py main.py
)


:bot_reboot
	%runbot%

	if '%errorlevel%'=='1' (
   		goto :bot_shutdown
	) else if '%errorlevel%'=='0' (
		goto :bot_reboot
	)

	if %usegit%==true (
		echo update requested, pulling...
		git pull --no-commit --no-ff
		if not '%errorlevel%'=='1' (
			echo conflict occurred, aborting
			git merge --abort
		) else (
			echo no conflict, merging
			git commit
		)
	)
	goto :bot_reboot

:bot_shutdown
cmd /k