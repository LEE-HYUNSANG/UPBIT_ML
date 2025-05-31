# F6 알림 및 원격 설정

`f6_setting` 모듈은 시스템 알림과 원격 제어, 기본 매수 설정을 관리합니다.
웹 UI의 **환경설정** 메뉴와 연동되며 텔레그램 메시지도 이 모듈을 통해
발송됩니다.

## 역할

- 알림 카테고리별 사용 여부를 JSON 파일로 저장하고 조회합니다.
- 텔레그램 봇을 이용해 서버 ON/OFF 상태를 원격에서 변경할 수 있습니다.
- 매수 금액, 동시 매수 코인 수와 같은 기본값을 로컬 설정 파일에 보관합니다.

## 사용되는 관련 파일

| 파일 | 설명 |
| --- | --- |
| `f6_setting/alarm_control.py` | 알림 설정을 읽고 저장하는 함수 제공 |
| `f6_setting/remote_control.py` | 텔레그램 명령으로 서버 상태를 조절 |
| `f6_setting/buy_config.py` | 매수 관련 기본값 로딩 및 저장 |
| `f6_setting/01_alarm_control/alarm_config.json` | 알림 ON/OFF와 템플릿 저장 |
| `config/f6_buy_settings.json` | 매수 금액 등 사용자가 저장한 설정 |

## 사용되는 함수

- `load_config(path)` – 알림 설정 파일을 읽어 딕셔너리로 반환합니다.【F:f6_setting/alarm_control.py†L20-L25】
- `save_config(cfg, path)` – 수정된 알림 설정을 파일에 저장합니다.【F:f6_setting/alarm_control.py†L28-L31】
- `is_enabled(category)` – 카테고리별 알림 활성화 여부를 확인합니다.【F:f6_setting/alarm_control.py†L34-L36】
- `get_template(key)` – 매수·매도 알림 메시지 형식을 가져옵니다.【F:f6_setting/alarm_control.py†L39-L41】
- `start_bot()` – 텔레그램 토큰이 설정되어 있으면 명령을 수신합니다.【F:f6_setting/remote_control.py†L30-L49】
- `load_buy_config(path)` – 매수 설정 파일을 불러 기본값과 병합합니다.【F:f6_setting/buy_config.py†L11-L21】
- `save_buy_config(cfg, path)` – 주어진 값만 업데이트하여 저장합니다.【F:f6_setting/buy_config.py†L24-L29】

## 동작 흐름

1. 서버 시작 시 `alarm_control.load_config()`를 호출해 각 알림의 기본값을 불러옵니다.
2. 사용자가 웹 UI에서 설정을 변경하면 `save_config()`를 통해 JSON 파일이 갱신됩니다.
3. `remote_control.start_bot()`을 실행하면 텔레그램에서 `/on` 또는 `/off` 명령을
   받을 수 있으며, 상태는 `remote_control.py`와 같은 폴더의 `server_status.txt`에 기록됩니다.
   경로를 바꾸려면 `SERVER_STATUS_FILE` 환경 변수를 설정합니다.
4. 매수 로직은 `buy_config.load_buy_config()`로 초기 설정을 가져오고,
   필요 시 `save_buy_config()`로 값을 갱신합니다.

## 로그 위치 및 설명

- 별도 로그 파일은 없으며, 텔레그램 알림은 `ExceptionHandler`에서 전송됩니다.
- 원격 제어 봇이 동작 중이면 명령 사용 시 텔레그램 채팅창에 즉시 응답합니다.

알림 설정을 통해 시스템 이벤트나 매매 체결 알림을 손쉽게 관리할 수 있으며,
원격 제어 기능으로 서버를 종료하지 않고도 매매 루프를 중단시킬 수 있습니다.
