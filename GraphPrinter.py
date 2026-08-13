from datetime import datetime, timedelta
from collections import Counter, defaultdict
import numpy as np
import matplotlib.pyplot as plt

# === 모드 설정 ===
# 선택: "daily", "weekly", "monthly"
MODE = "weekly"

# === 가중치 설정 ===
POST_WEIGHT    = 0.56  # 글
COMMENT_WEIGHT = 0.18  # 댓글

# === 파일 읽기 ===
def load_dates(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            raw_lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"{filename} 파일을 찾을 수 없습니다.")
        return []

    result = []
    for line in raw_lines:
        try:
            dt = datetime.strptime(line, "%Y-%m-%d %H:%M:%S")
            result.append(dt)
        except:
            pass
    return result

post_dates    = load_dates("date-data.txt")
comment_dates = load_dates("date-data-comment.txt")

if not post_dates and not comment_dates:
    print("데이터 없음")
    exit()

# 시간대 통계용 (가중치 적용)
hours_weighted = defaultdict(float)
for dt in post_dates:
    hours_weighted[dt.hour] += POST_WEIGHT
for dt in comment_dates:
    hours_weighted[dt.hour] += COMMENT_WEIGHT

now = datetime.now()
current_year = now.year

# === 날짜 라벨 함수 ===
def date_label(dt):
    if dt.year < current_year:
        return dt.strftime("%y-%m-%d")
    return dt.strftime("%m-%d")

def format_standard_week_label(dt):
    start_of_week_date = dt.date() - timedelta(days=dt.weekday())
    end_of_week_date   = start_of_week_date + timedelta(days=6)
    if start_of_week_date.year < current_year or end_of_week_date.year < current_year:
        start_label = start_of_week_date.strftime("%y.%m.%d")
        end_label   = end_of_week_date.strftime("%y.%m.%d")
    else:
        start_label = start_of_week_date.strftime("%m.%d")
        end_label   = end_of_week_date.strftime("%m.%d")
    return start_of_week_date, f"{start_label} ~ {end_label}"

def get_week_sort_key(start_of_week_date):
    today_date        = now.date()
    current_week_start = today_date - timedelta(days=today_date.weekday())
    return (start_of_week_date - current_week_start).total_seconds()

# ============================================================
# 1) 가중치 적용 집계
# ============================================================
def aggregate(dates, weight, mode):
    result    = defaultdict(float)
    label_map = {}

    for dt in dates:
        if mode == "daily":
            key = date_label(dt)
            result[key] += weight

        elif mode == "weekly":
            start_date, week_label = format_standard_week_label(dt)
            sort_key = get_week_sort_key(start_date)
            result[sort_key]    += weight
            label_map[sort_key]  = week_label

        elif mode == "monthly":
            key = dt.strftime("%y-%m") if dt.year < current_year else dt.strftime("%m")
            result[key] += weight

    return result, label_map

post_scores,    label_map_p = aggregate(post_dates,    POST_WEIGHT,    MODE)
comment_scores, label_map_c = aggregate(comment_dates, COMMENT_WEIGHT, MODE)

# label_map 병합 (weekly 전용)
label_map = {**label_map_p, **label_map_c}

# 두 딕셔너리 합산
all_keys = set(post_scores.keys()) | set(comment_scores.keys())
counter  = {k: round(post_scores.get(k, 0) + comment_scores.get(k, 0), 4) for k in all_keys}

print(f"📌 {MODE} 모드 | 글 ×{POST_WEIGHT} + 댓글 ×{COMMENT_WEIGHT} 가중 합산")

# ============================================================
# 2) 이상값 제거
# ============================================================
counts = list(counter.values())

if counts:
    initial_average = sum(counts) / len(counts)
    threshold       = initial_average * 0.1

    print(f"평균: {initial_average:.2f}, 이상값 임계치 (10%): {threshold:.2f}")

    keys_to_remove = [k for k, v in counter.items() if v < threshold]
    for k in keys_to_remove:
        display = label_map.get(k, k) if MODE == "weekly" else k
        print(f"  - 제외: {display} ({counter[k]}점)")
        del counter[k]

    counts  = list(counter.values())
    average = sum(counts) / len(counts) if counts else 0
else:
    print("집계된 데이터 없음.")
    exit()

# ============================================================
# 3) 그래프 생성
# ============================================================
sorted_keys = sorted(counter.keys())

if MODE == "weekly":
    x = [label_map[k] for k in sorted_keys]
else:
    x = sorted_keys

c          = [counter[k] for k in sorted_keys]
cumulative = np.cumsum(c)

fig, ax1 = plt.subplots(figsize=(12, 5))
bars = ax1.bar(range(len(x)), c, color='skyblue', alpha=0.8)
ax1.axhline(y=average, color='red', linestyle='--', linewidth=1, label=f"Average: {average:.1f}")

for i, v in enumerate(c):
    ax1.text(i, v + 0.1, f"{v:.1f}", ha='center', fontsize=8)

ax2 = ax1.twinx()
ax2.plot(range(len(x)), cumulative, marker="o", color='orange', label="Cumulative")

ax1.set_xticks(range(len(x)))
ax1.set_xticklabels(x, rotation=45, ha="right", fontsize=9)
ax1.set_ylabel(f"Weighted Score (post×{POST_WEIGHT} + comment×{COMMENT_WEIGHT})")

plt.title(f"Activity Statistics ({MODE}) - Weighted")
plt.tight_layout()
plt.show()

# ============================================================
# 4) 콘솔 출력
# ============================================================
print(f"\n===== 📌 {MODE} 통계 (가중치 적용, 이상값 제거 후) =====")
if MODE == "weekly":
    for k in sorted_keys:
        print(f"{label_map[k]:<25} → {counter[k]:.2f}점")
else:
    for k in sorted_keys:
        print(f"{k:<25} → {counter[k]:.2f}점")

print("\n===== 📌 시간대별 통계 (가중치 적용, 전체 데이터 기준) =====")
total_w = sum(hours_weighted.values())
for h in range(24):
    v = hours_weighted.get(h, 0)
    p = (v / total_w * 100) if total_w else 0
    print(f"{str(h).zfill(2)}시 → {p:.1f}% ({v:.2f}점)")