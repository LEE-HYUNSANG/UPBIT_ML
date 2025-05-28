"""02_data_cleaning 단계 스크립트."""
from pathlib import Path
from utils import ensure_dir


def main():
    """실행 엔트리 포인트."""
    ensure_dir("ml_data")
    print(f"Running {__file__}")


if __name__ == "__main__":
    main()
