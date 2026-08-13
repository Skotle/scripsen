import pandas as pd
df = pd.read_csv("user-data.csv")
df_a = df.drop(columns=["이름","ID/IP"])

# 기본 기술통계
print("===== 기본 기술통계(describe) =====")
print(df_a.describe(), '\n')

# 왜도/첨도
print("===== 왜도 (skew) =====")
print(df_a.skew(), '\n')

print("===== 첨도 (kurtosis) =====")
print(df_a.kurtosis(), '\n')

# 여러 형태의 상관계수
print("===== 피어슨 상관관계 (Pearson) =====")
print(df_a.corr(method='pearson'), '\n')

print("===== 스피어만 상관관계 (Spearman) =====")
print(df_a.corr(method='spearman'), '\n')

print("===== 켄달 타우 상관관계 (Kendall) =====")
print(df_a.corr(method='kendall'), '\n')
