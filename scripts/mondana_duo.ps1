$APP = 'D:\Programs\helpD-main'

# 1-й пост: сразу при запуске задачи
$env:AUTORUN = '1'
$env:AUTORUN_TASK = 'MESSAGE_SENDER'
$env:SENDER_GUILD_ID   = '1392602898160025741'   # server mondana
$env:SENDER_CHANNEL_ID = '1397943371330228334'   # #mondana
$env:MESSAGE_FILE_OVERRIDE = 'mondana'
& "$APP\run_helpd.bat"

# 2-й пост: через случайные 6..8 часов
$gap = Get-Random -Minimum (6*3600) -Maximum (8*3600)
Start-Sleep -Seconds $gap

# повторный вызов (переменные уже установлены выше)
& "$APP\run_helpd.bat"
