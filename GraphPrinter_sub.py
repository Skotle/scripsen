from datetime import datetime
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt

# Java에서 저장한 파일 읽기
with open("date-data.txt", "r", encoding="utf-8") as f:
    raw_dates = [line.strip() for line in f if line.strip()]


now = datetime.now()
current_year = now.year

# 날짜 변환 함수
def parse_date(d):
    try:
        # YY.MM.DD 형식
        if len(d.split('.')) == 3 and len(d.split('.')[0]) == 2:
            return datetime.strptime(d, "%y.%m.%d")
        # MM.DD 형식
        elif len(d.split('.')) == 2:
            dt = datetime.strptime(d, "%m.%d").replace(year=current_year)
            if dt > now:
                dt = dt.replace(year=current_year - 1)
            return dt
        # 시간 문자열 등 처리 가능
        elif ":" in d:
            return now
    except:
        return None
    return None

# 날짜 처리
dates = list(filter(None, [parse_date(d) for d in raw_dates]))

if not dates:
    print("유효한 날짜가 없습니다.")
else:
    # 일별 카운트만 사용 (월별 전환 로직 제거)
    counter = Counter([d.strftime("%y.%m.%d") for d in dates])
    
    # 평균 계산
    counts_list = list(counter.values())
    
    # 예외 처리: 데이터가 없는 경우
    if not counts_list:
        print("집계된 데이터가 없습니다.")
        exit()

    # 일별 카운트의 항목 개수로 평균 계산
    average = sum(counts_list) / len(counts_list)
    
    # 평균 기반 필터
    # 평균의 10% 이상인 항목만 필터링
    filtered_counter = {k: v for k, v in counter.items() if v >= average * 0.1} 

    if filtered_counter:
        x_labels = sorted(filtered_counter)
        counts = [filtered_counter[d] for d in x_labels]
        cumulative_counts = np.cumsum(counts)

        fig, ax1 = plt.subplots(figsize=(12, 5))

        bars = ax1.bar(range(len(x_labels)), counts, color='skyblue', label='Count')
        ax1.set_ylabel("Count", color='skyblue')
        ax1.tick_params(axis='y', labelcolor='skyblue')
        ax1.axhline(y=average, color='red', linestyle='--', label=f'Average ({average:.1f})')

        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() * 0.3, height + 0.5, f'{int(height)}',
                     ha='center', va='bottom', fontsize=9, color='blue')

        ax2 = ax1.twinx()
        ax2.plot(range(len(x_labels)), cumulative_counts, marker='o', color='green', label='Cumulative Count')
        ax2.set_ylabel("Cumulative Count", color='green')
        ax2.tick_params(axis='y', labelcolor='green')

        # X축 라벨 표시 간격 설정 (데이터가 너무 많을 경우 생략)
        interval = max(1, len(x_labels) // 10)
        
        for i, y in enumerate(cumulative_counts):
            if i % interval == 0 or i == len(x_labels) - 1:
                offset = 0.35 if i == len(x_labels) - 1 else 0.15
                ax2.text(i + offset, y + 0.5, f'{int(y)}', ha='center', va='bottom', fontsize=9, color='green')

        ax1.set_xticks(range(len(x_labels)))
        # X축 라벨이 너무 많을 경우 interval에 따라 일부 생략
        xtick_labels = [label if i % interval == 0 else '' for i, label in enumerate(x_labels)]
        ax1.set_xticklabels(xtick_labels, rotation=45, ha='right', fontsize=8) # rotation을 45도로 변경하여 긴 일자 표시 개선

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        plt.title("Activity Count (Daily View)")
        plt.tight_layout()
        plt.show()
    else:
        print("평균의 10% 이상인 항목이 없습니다.")