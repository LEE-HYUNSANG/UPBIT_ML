# 텔레그램 원격 제어

`f6_setting.remote_control` 모듈은 거래 루프를 원격으로 시작하고 중지할 수 있는
간단한 텔레그램 봇을 제공합니다. `pyTelegramBotAPI` 패키지를 사용합니다.

1. `@BotFather`로 봇을 생성하고 토큰을 확인합니다.
2. `TELEGRAM_TOKEN` 환경 변수에 토큰을 설정합니다.
3. `f6_setting.remote_control.start_bot()`을 실행하여 폴링을 시작합니다.

채팅에서 `/on` 또는 `/off`를 사용합니다. 봇은 기본적으로 `remote_control.py`와 같은
위치에 `server_status.txt` 파일을 만들고 `ON` 또는 `OFF`를 기록합니다.
`signal_loop.main_loop`는 매 사이클 이 파일을 읽어 상태가 `ON`인 경우에만 동작합니
다. 파일 경로를 변경하려면 `SERVER_STATUS_FILE` 환경 변수를 설정합니다.
