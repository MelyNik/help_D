$APP = 'D:\Programs\helpD-main'

# 1-й пост: сразу при запуске задачи
$env:AUTORUN = '1'
$env:AUTORUN_TASK = 'MESSAGE_SENDER'
$env:SENDER_GUILD_ID   = '1293892201973157928'   # server gover
$env:SENDER_CHANNEL_ID = '1330320551587090464'   # #gover
$env:MESSAGE_FILE_OVERRIDE = 'gover'
& "$APP\run_helpd.bat"

# 2-й пост: через случайные 6..8 часов
$gap = Get-Random -Minimum (6*3600) -Maximum (8*3600)
Start-Sleep -Seconds $gap

# повторный вызов (переменные уже установлены выше)
& "$APP\run_helpd.bat"
