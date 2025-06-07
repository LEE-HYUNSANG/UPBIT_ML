# 공통 유틸리티 함수

`common_utils.py` 모듈에는 여러 패키스에서 공통으로 사용하는 보조 함수들이 모여
있습니다.

## 제공 함수

| 함수 | 설명 |
| --- | --- |
| `load_json(path, default=None)` | JSON 파일을 읽어 실패 시 기본값을 반환합니다. |
| `save_json(path, data)` | 필요한 폴더를 생성한 뒤 JSON을 저장합니다. |
| `now_kst()` | KST 기준 현재 시각을 ISO 문자열로 반환합니다. |
| `now()` | 현재 epoch 시간을 `float` 값으로 반환합니다. |
| `setup_logging(tag, log_files, level=logging.INFO, force=True)` | 로테이팅 파일
및 콘솔 로그를 설정합니다. |
