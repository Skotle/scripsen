import re
import math
from collections import Counter
from datetime import datetime

def analyze_ranking_from_file(file_path, start_date_str, end_date_str):
    """
    텍스트 파일에서 데이터를 읽어 특정 기간 내 활동 상위 4% 사용자만 출력합니다.
    """
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str + " 23:59:59", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print("날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 입력해주세요.")
        return

    counts = Counter()
    pattern = re.compile(r"\[(.+?)\]\s\[(.+?)\]\s\[(.+?)\]")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    name, identifier, date_str = match.groups()
                    try:
                        current_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        if start_dt <= current_dt <= end_dt:
                            user_key = f"[{name}] [{identifier}]"
                            counts[user_key] += 1
                    except ValueError:
                        continue

        # 1. 활동한 전체 사용자 수 계산
        all_users = counts.most_common()
        total_user_count = len(all_users)
        
        if total_user_count == 0:
            print("해당 기간 내에 데이터가 존재하지 않습니다.")
            return

        # 2. 상위 4% 인원수 계산 (최소 1명 보장)
        top_4_percent_count = max(1, math.ceil(total_user_count * 0.04))

        # 3. 결과 출력
        print(f"\n===== {start_date_str} ~ {end_date_str} 활동 순위 =====")
        print(f"(전체 사용자 {total_user_count}명 중 상위 4%인 {top_4_percent_count}명 출력)\n")

        for rank, (user, count) in enumerate(all_users[:top_4_percent_count], 1):
            print(f"{rank}위: {user} - {count}회")
            
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")

# --- 실행부 ---
file_name = 'daily-data.txt'
start = input("시작 날짜 입력 (YYYY-MM-DD): ")
end = input("종료 날짜 입력 (YYYY-MM-DD): ")

analyze_ranking_from_file(file_name, start, end)