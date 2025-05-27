# 2. 데이터 전처리/정제

import pandas as pd

# 파일 경로 지정
file_path = "./ml_data/01_raw/KRW-MTL_20250226_044900-20250527_114700.csv"

# CSV 읽기 (한글이 깨질 경우 encoding="utf-8" 또는 "cp949"로 시도)
df = pd.read_csv(file_path)

# 데이터 5행 미리보기
print(df.head())
print(df.columns)
print(df.info())
