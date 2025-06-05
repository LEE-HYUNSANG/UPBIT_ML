# 공통 유틸리티 함수

`common_utils.py` 모듈은 F2~F4 패키지 전반에서 사용되는 보조 함수를 모아둔 곳입니다.

## 함수 목록

| 함수 | 설명 |
| --- | --- |
| `load_json(path, default=None)` | *path*에서 JSON을 읽어 실패 시 *default*를 반환합니다. |
| `save_json(path, data)` | 필요한 디렉터리를 생성하고 *data*를 JSON으로 *path*에 저장합니다. |
| `now_kst()` | 현재 KST 기준 시각을 ISO 문자열로 반환합니다. |
| `now()` | 현재 epoch 시간을 실수형으로 반환합니다. |
| `setup_logging(tag, log_files, level=logging.INFO, force=True)` | 회전 파일 로그와 콘솔 로그 핸들러를 설정합니다. |

