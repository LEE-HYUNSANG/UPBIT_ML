# 로그 디렉터리 구조

모든 로그 파일은 `logs/` 폴더 아래에 저장됩니다. 개발 중에는 다음과 같은
하위 디렉터리가 사용됩니다:

```
logs/
  debug/
  info/
  warning/
  error/
  critical/
  f1/
  f2/
  f3/
  f4/
  f5/
  f6/
  etc/
```

각 기능 모듈은 해당되는 `f1`~`f6` 디렉터리에 로그를 기록합니다. `web.log`나
`events.jsonl` 같은 일반 애플리케이션 로그는 `logs/etc`에 저장됩니다. 레벨별
디렉터리(`debug`, `info`, `warning`, `error`, `critical`)는 추후 사용을 위해
예약되어 있습니다.

`python logs/relog.py` 명령을 실행하면 기존 로그를 모두 삭제하고 디렉터리 구조를
다시 생성합니다. 업데이트 후 새 로그를 확인할 때 유용합니다.
