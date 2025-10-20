$APP = 'D:\Programs\helpD-main'

# 0..180 минут (окно 07:00 → 10:00 МСК)
$delay = Get-Random -Minimum 0 -Maximum (180*60)
Start-Sleep -Seconds $delay

# Приветствие (hello_en) в #general
$env:AUTORUN = '1'
$env:AUTORUN_TASK = 'MESSAGE_SENDER'
$env:SENDER_GUILD_ID = '1392602898160025741'     # server mondana
$env:SENDER_CHANNEL_ID = '1397937063571099688'   # #general
$env:MESSAGE_FILE_OVERRIDE = 'hello_en'
& "$APP\run_helpd.bat"

# Пауза 10..20 минут
$gap = Get-Random -Minimum (10*60) -Maximum (20*60)
Start-Sleep -Seconds $gap

# Запуск AI в том же канале
$env:AUTORUN_TASK = 'AI_CHATTER'
$env:AI_GUILD_ID = '1392602898160025741'
$env:AI_CHANNEL_ID = '1397937063571099688'
$env:MESSAGE_FILE_OVERRIDE = ''
& "$APP\run_helpd.bat"
