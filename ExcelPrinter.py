import pandas as pd
import re
import os
from datetime import datetime, timedelta

DAILY_DATA_PATTERN = re.compile(
    r"^\[(.*?)\]\s+\[(.*?)\]\s+\[(.*?)\]"
    r"(?:\s+\[([^\]]*)\]\s+\[([^\]]*)\]\s+\[([^\]]*)\])?\s*$"
)

# --- Excel에서 문제되는 제어 문자 제거 ---
def clean_illegal_chars(text):
    if isinstance(text, str):
        # 엑셀 저장 시 오류를 일으킬 수 있는 비인쇄 문자 제거
        return re.sub(r'[\x00-\x1F\x7F]', '', text)
    return text

def parse_daily_metric(value):
    if value is None:
        return None
    value = re.sub(r"^(?:조회수|추천|리플)\s*:\s*", "", value.strip())
    try:
        return int(value)
    except ValueError:
        return None

def load_daily_rows(path):
    """3필드 구형 로그와 6필드 게시글 로그를 모두 읽는다."""
    if not os.path.exists(path):
        return []

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            match = DAILY_DATA_PATTERN.match(line.strip())
            if not match:
                continue
            name, identifier, date, view, recom, reple = match.groups()
            try:
                parsed_date = datetime.strptime(date.strip(), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            rows.append({
                "name": clean_illegal_chars(name),
                "id_or_ip": clean_illegal_chars(identifier),
                "date": parsed_date,
                "view": parse_daily_metric(view),
                "recom": parse_daily_metric(recom),
                "reple": parse_daily_metric(reple),
            })
    return rows

def read_date_range():
    try:
        start_text = input("포함 시작일 (YYYY-MM-DD, 전체는 Enter): ").strip()
        end_text = input("포함 종료일 (YYYY-MM-DD, 전체는 Enter): ").strip()
    except EOFError:
        return None, None

    try:
        start = datetime.strptime(start_text, "%Y-%m-%d") if start_text else None
        end = datetime.strptime(end_text, "%Y-%m-%d") + timedelta(days=1) if end_text else None
    except ValueError:
        raise SystemExit("❌ 날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력하세요.")

    if start and end and start >= end:
        raise SystemExit("❌ 시작일은 종료일보다 늦을 수 없습니다.")
    return start, end

def filter_daily_rows(rows, start, end):
    return [
        row for row in rows
        if (start is None or row["date"] >= start) and (end is None or row["date"] < end)
    ]

def aggregate_range_records(post_rows, comment_rows):
    """선택 날짜 범위의 게시글/댓글 로그로 사용자 집계를 다시 계산한다."""
    aggregated = {}

    def get_record(row):
        identifier = row["id_or_ip"]
        if identifier not in aggregated:
            aggregated[identifier] = {
                "name": row["name"],
                "id_or_ip": identifier,
                "nicktype": "",
                "num": 0, "view": 0, "recom": 0, "reple": 0, "comm": 0,
            }
        return aggregated[identifier]

    for row in post_rows:
        record = get_record(row)
        record["num"] += 1
        record["view"] += row["view"] or 0
        record["recom"] += row["recom"] or 0
        record["reple"] += row["reple"] or 0

    for row in comment_rows:
        get_record(row)["comm"] += 1

    return sorted(aggregated.values(), key=lambda record: record["num"], reverse=True)

def daily_posts_frame(post_rows):
    return pd.DataFrame([
        {
            "이름": row["name"], "ID/IP": row["id_or_ip"], "날짜": row["date"],
            "조회수": row["view"], "추천": row["recom"], "리플": row["reple"],
        }
        for row in post_rows
    ], columns=["이름", "ID/IP", "날짜", "조회수", "추천", "리플"])

black_list_file = "ip-black.txt"

start_date, end_date = read_date_range()
post_rows = filter_daily_rows(load_daily_rows("daily-data.txt"), start_date, end_date)
comment_rows = filter_daily_rows(load_daily_rows("daily-data-comment.txt"), start_date, end_date)
records = aggregate_range_records(post_rows, comment_rows)

if not records:
    print("❌ 선택한 날짜 범위에 데이터가 없습니다.")
    exit()

# ============================================================
# 🔥 필터(블랙리스트) 파일 읽기
# ============================================================
filter_values = []
if os.path.exists(black_list_file):
    with open(black_list_file, "r", encoding="utf-8") as f:
        readip = f.read().splitlines()
    filter_values = [re.sub(r"\[.*?\]", "", line).strip() for line in readip if line.strip()]


# ============================================================
# 🔥 1회차: 전체 통계 계산 (필터링 전 원본 기준)
# ============================================================
sum_posts = 0
sum_view = 0
sum_reco = 0
sum_reply = 0
sum_comment = 0

for record in records:
    sum_posts   += record["num"]
    sum_view    += record["view"]
    sum_reco    += record["recom"]
    sum_reply   += record["reple"]
    sum_comment += record["comm"]

start_label = start_date.strftime("%Y-%m-%d") if start_date else "제한 없음"
end_label = (end_date - timedelta(days=1)).strftime("%Y-%m-%d") if end_date else "제한 없음"
print(f"\n===== 📊 일간 데이터 집계 ({start_label} ~ {end_label}) =====")
print(f"총 게시글 수  = {sum_posts}")
print(f"총 조회수     = {sum_view}")
print(f"총 추천수     = {sum_reco}")
print(f"총 리플수     = {sum_reply}")
print(f"총 댓글수     = {sum_comment}")


# ============================================================
# 🔥 2회차: 데이터프레임 생성 및 계산
# ============================================================
rows = []

for record in records:
    parts = [
        record["name"], record["id_or_ip"], record["nicktype"],
        record["num"], record["view"], record["recom"],
        record["reple"], record["comm"],
    ]

    # 블랙리스트 필터링 (ID/IP 기준)
    if any(v in parts[1] for v in filter_values):
        continue

    # 평균치 계산 (parts[3] = 글 수)
    if parts[3] > 0:
        avg_view  = round(parts[4] / parts[3], 2)
        avg_reco  = round(parts[5] / parts[3], 2)
        avg_reply = round(parts[6] / parts[3], 2)
    else:
        avg_view = avg_reco = avg_reply = 0

    # 가중값 계산 (글 수 * 0.56 + 댓글 수 * 0.18)
    calc = round((parts[3] * 0.56 + parts[7] * 0.18), 2)
    if parts[2]=="비고정" or parts[2]=="비회원":
        parts[0] = parts[0]+'('+parts[1]+')'
    if parts[2]=="비회원" and parts[1]=="":
        parts[1]="익명"
    # 데이터 행 구성
    rows.append([
        parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7],
        avg_view, avg_reco, avg_reply, calc
    ])

# DataFrame 생성
df = pd.DataFrame(rows, columns=[
    "이름", "ID/IP", "타입", "글", "조회수", "추천", "리플", "댓글",
    "평균 조회수", "평균 추천 수", "평균 리플 수", "가중값"
])

# 편차율 계산을 위한 전체 평균 산출
total_avg_view  = df["평균 조회수"].mean()
total_avg_reco  = df["평균 추천 수"].mean()
total_avg_reply = df["평균 리플 수"].mean()

# 편차율 계산
df["조회수 편차율"] = round((df["평균 조회수"] - total_avg_view) / total_avg_view * 100, 2) if total_avg_view != 0 else 0
df["추천 편차율"] = round((df["평균 추천 수"] - total_avg_reco) / total_avg_reco * 100, 2) if total_avg_reco != 0 else 0
df["리플 편차율"] = round((df["평균 리플 수"] - total_avg_reply) / total_avg_reply * 100, 2) if total_avg_reply != 0 else 0

# 최종 컬럼 순서 정리
df_final = df[[
    "이름", "ID/IP", "타입", "글", "조회수", "추천", "리플", "댓글",
    "평균 조회수", "조회수 편차율",
    "평균 추천 수", "추천 편차율",
    "평균 리플 수", "리플 편차율",
    "가중값"
]]

# 파일 저장
try:
    daily_posts = daily_posts_frame(post_rows)
    with pd.ExcelWriter(
        "user-data.xlsx", engine='openpyxl', datetime_format="yyyy-mm-dd hh:mm:ss"
    ) as writer:
        df_final.to_excel(writer, sheet_name="사용자 집계", index=False, freeze_panes=(1, 0))
        if not daily_posts.empty:
            daily_posts.to_excel(writer, sheet_name="게시글 상세", index=False, freeze_panes=(1, 0))
    df_final.to_csv("user-data.csv", index=False, encoding="utf-8-sig")
    print("\n✅ user-data.xlsx / user-data.csv 저장 완료!")
except Exception as e:
    print(f"\n❌ 저장 실패: {e}")
