$APP = 'D:\Programs\helpD-main'

$delay = Get-Random -Minimum 0 -Maximum (180*60)
Start-Sleep -Seconds $delay

$env:AUTORUN = '1'
$env:AUTORUN_TASK = 'MESSAGE_SENDER'
$env:SENDER_GUILD_ID = '1293892201973157928'     # server gover
$env:SENDER_CHANNEL_ID = '1321887203051438184'   # #general
$env:MESSAGE_FILE_OVERRIDE = 'hello_en'
& "$APP\run_helpd.bat"

$gap = Get-Random -Minimum (10*60) -Maximum (20*60)
Start-Sleep -Seconds $gap

$env:AUTORUN_TASK = 'AI_CHATTER'
$env:AI_GUILD_ID = '1293892201973157928'
$env:AI_CHANNEL_ID = '1321887203051438184'
$env:MESSAGE_FILE_OVERRIDE = ''
& "$APP\run_helpd.bat"
