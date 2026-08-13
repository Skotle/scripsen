import pandas as pd
import re
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from datetime import datetime

# 한글 폰트 설정
def set_korean_font():
    candidates = [
        "Malgun Gothic", "AppleGothic", "NanumGothic",
        "NanumBarunGothic", "Gulim", "Dotum"
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams['font.family'] = font
            break
    plt.rcParams['axes.unicode_minus'] = False

set_korean_font()

# === 가중치 설정 ===
POST_WEIGHT    = 0.56
COMMENT_WEIGHT = 0.18
MAX_TOP_N = 28
LOW_PERIOD_AVERAGE_RATIO = 0.05
ILLEGAL_EXCEL_CHAR_RE = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]')
DAILY_DATA_PATTERN = re.compile(
    r"^\[(?P<nick>.*?)\]\s+\[(?P<uid>.*?)\]\s+\[(?P<date>.*?)\]"
    r"(?:\s+\[(?P<view>[^\]]*)\]\s+\[(?P<recom>[^\]]*)\]\s+\[(?P<reple>[^\]]*)\])?\s*$"
)

# === 블랙리스트 설정 ===
BLACK_LIST = ["운영자", "테스트계정"] 

def safe_input(prompt, default):
    try:
        value = input(prompt).strip()
    except EOFError:
        return default
    return value or default

def ask_options():
    mode = safe_input("분석 단위 선택 (D: 일간, W: 주간, M: 월간) [D]: ", "D").upper()
    if mode not in ['D', 'W', 'M']: mode = 'D'

    graph_type = safe_input("그래프 종류 선택 (C: 누적, A: 기간별 집계, B: 둘 다) [B]: ", "B").upper()
    if graph_type not in ['C', 'A', 'B']: graph_type = 'B'

    top_n = parse_top_n(safe_input("표시할 사용자 수 N [10]: ", "10"))

    # 막대 스타일 옵션 세분화 안내
    print("\n[막대 스타일 안내]")
    print(" - S: 일반 쌓기 (전체 점수 볼륨 + 유저별 크기)")
    print(" - G: N개 분리 (유저별 막대를 가로로 개별 나열)")
    print(" - P: 100% 비율 쌓기 (전체 높이를 100%로 고정하여 점유율 비교)")
    print(" - R: 순위별 쌓기 (밑바닥부터 1위, 2위... 순서대로 정렬하여 쌓기)")
    bar_style = safe_input("집계 막대 스타일 선택 (S, G, P, R) [G]: ", "G").upper()
    if bar_style not in ['S', 'G', 'P', 'R']: bar_style = 'G'
        
    start_date = safe_input("\n분석 시작일 입력 (YYYY-MM-DD) [제한없음]: ", "")
    end_date = safe_input("분석 종료일 입력 (YYYY-MM-DD) [제한없음]: ", "")

    return mode, graph_type, top_n, bar_style, start_date, end_date

def parse_top_n(value):
    try:
        top_n = int(value)
        if top_n > MAX_TOP_N:
            print(f"N은 최대 {MAX_TOP_N}명까지 표시합니다. {MAX_TOP_N}로 실행합니다.")
        return max(1, min(MAX_TOP_N, top_n))
    except ValueError:
        return 10

def clean_excel_text(value):
    if isinstance(value, str):
        return ILLEGAL_EXCEL_CHAR_RE.sub('', value)
    return value

def clean_excel_frame(df):
    safe_df = df.copy()
    safe_df.index = safe_df.index.map(clean_excel_text)
    safe_df.columns = [clean_excel_text(column) for column in safe_df.columns]
    for column in safe_df.select_dtypes(include=['object']).columns:
        safe_df[column] = safe_df[column].map(clean_excel_text)
    return safe_df

def safe_to_excel(df, writer, **kwargs):
    clean_excel_frame(df).to_excel(writer, **kwargs)

def parse_daily_metric(value):
    if value is None:
        return 0
    value = re.sub(r"^(?:조회수|추천|리플)\s*:\s*", "", value.strip())
    try:
        return int(value)
    except ValueError:
        return 0

def parse_daily_line(line, pattern=DAILY_DATA_PATTERN):
    """구형 3필드와 신규 6필드 daily-data 행을 모두 파싱한다."""
    match = pattern.match(line.strip())
    if not match:
        return None
    values = match.groupdict()
    return {
        'nick': clean_excel_text(values['nick']),
        'uid': clean_excel_text(values['uid']),
        'date': values['date'],
        'Views': parse_daily_metric(values.get('view')),
        'Recommendations': parse_daily_metric(values.get('recom')),
        'Replies': parse_daily_metric(values.get('reple')),
    }

def build_mapping(files, pattern):
    id_to_nick = {}
    nick_usage = {}
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError: continue
        for line in lines:
            entry = parse_daily_line(line, pattern)
            if entry:
                nick, uid = entry['nick'], entry['uid']
                if uid not in id_to_nick:
                    id_to_nick[uid] = nick
                    nick_usage[nick] = nick_usage.get(nick, 0) + 1

    final_mapping  = {}
    current_counts = {}
    for uid, nick in id_to_nick.items():
        display_uid = uid if uid else "no-id"
        if nick_usage.get(nick, 0) > 1:
            current_counts[nick] = current_counts.get(nick, 0) + 1
            final_mapping[uid] = f"{nick}({current_counts[nick]})({display_uid})"
        else:
            final_mapping[uid] = f"{nick}({display_uid})"
    return final_mapping

def load_file(file_path, weight, pattern, final_mapping, blacklisted_periods, now, mode,
              start_date="", end_date="", is_post=False):
    raw_data = []
    s_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    e_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    try:
        with open(file_path, 'r', encoding='utf-8') as f: lines = f.readlines()
    except FileNotFoundError: return raw_data

    for line in lines:
        entry = parse_daily_line(line, pattern)
        if entry:
            uid, date_str = entry['uid'], entry['date']
            try:
                dt = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
                p_month = dt.strftime("%Y-%m")
                
                if dt > now or p_month in blacklisted_periods: continue
                if s_dt and dt < s_dt: continue
                if e_dt and dt > e_dt: continue

                if mode == 'D':   p = dt.strftime("%Y-%m-%d")
                elif mode == 'W': p = (dt.date() - pd.Timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
                else:             p = p_month
                
                raw_data.append({
                    'Period': p,
                    'User':   final_mapping.get(uid, "Unknown"),
                    'Weight': weight,
                    'Posts': 1 if is_post else 0,
                    'Comments': 0 if is_post else 1,
                    'Views': entry['Views'] if is_post else 0,
                    'Recommendations': entry['Recommendations'] if is_post else 0,
                    'Replies': entry['Replies'] if is_post else 0,
                })
            except ValueError: continue
    return raw_data

def save_final_clean_report(post_file, comment_file, mode='D', graph_type='B', top_n=10, bar_style='G', start_date="", end_date="", black=[]):
    pattern = DAILY_DATA_PATTERN
    now = datetime.now()
    blacklisted_periods = []

    final_mapping = build_mapping([post_file, comment_file], pattern)
    raw_data = (
        load_file(post_file, POST_WEIGHT, pattern, final_mapping, blacklisted_periods, now,
                  mode, start_date, end_date, is_post=True) +
        load_file(comment_file, COMMENT_WEIGHT, pattern, final_mapping, blacklisted_periods, now,
                  mode, start_date, end_date, is_post=False)
    )

    if not raw_data:
        print("선택 시점 내에 유효한 데이터가 없습니다.")
        return

    df = pd.DataFrame(raw_data)
    pivot_df = df.groupby(['Period', 'User'])['Weight'].sum().unstack(fill_value=0).sort_index()
    
    if '기타(Others)' not in pivot_df.columns:
        pivot_df['기타(Others)'] = 0.0
        
    for user in list(pivot_df.columns):
        if user in black or any(b in user for b in black):
            if user != '기타(Others)':
                pivot_df['기타(Others)'] += pivot_df[user]
                pivot_df = pivot_df.drop(columns=[user])

    pivot_df = filter_low_activity_periods(pivot_df)
    if pivot_df.empty:
        print("전체기간 평균 5% 초과 기간이 없어 집계를 중단합니다.")
        return

    cumulative_scores = pivot_df.cumsum()
    selected_users = select_final_top_users(cumulative_scores, top_n)
    
    if not selected_users:
        print("순위 내 표시할 사용자가 없습니다.")
        return

    cumulative_plot_data = cumulative_scores[selected_users]
    aggregate_plot_data = build_period_top_n_data(pivot_df, selected_users, top_n)

    output_file = f'final_scores_{mode}.xlsx'
    selected_symbols = build_user_symbols(selected_users)
    selected_user_summary = pd.DataFrame({
        'Symbol': [selected_symbols[user] for user in selected_users],
        'User': selected_users,
        'FinalCumulativeScore': [cumulative_scores.iloc[-1].get(user, 0) for user in selected_users]
    })
    metric_columns = ['Posts', 'Comments', 'Views', 'Recommendations', 'Replies']
    user_metrics = df.groupby('User')[metric_columns].sum()
    for column in metric_columns:
        selected_user_summary[column] = [user_metrics.at[user, column] if user in user_metrics.index else 0 for user in selected_users]
    period_user_metrics = (
        df[df['User'].isin(selected_users)]
        .groupby(['Period', 'User'], as_index=False)[metric_columns]
        .sum()
    )
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        safe_to_excel(selected_user_summary, writer, sheet_name='selected_users', index=False)
        safe_to_excel(period_user_metrics, writer, sheet_name='period_user_metrics', index=False)
        safe_to_excel(cumulative_plot_data, writer, sheet_name='cumulative_selected')
        safe_to_excel(aggregate_plot_data, writer, sheet_name='period_top_n_only')
        safe_to_excel(cumulative_scores, writer, sheet_name='cumulative_all')
        safe_to_excel(pivot_df, writer, sheet_name='period_aggregate_all')
    print(f"파일 저장: {output_file}")

    if graph_type in ['C', 'B']:
        save_cumulative_chart(cumulative_plot_data, selected_users, mode, top_n)
    if graph_type in ['A', 'B']:
        save_aggregate_chart(pivot_df, selected_users, mode, bar_style, top_n)

def select_final_top_users(cumulative_scores, top_n):
    if cumulative_scores.empty: return []
    final_row = cumulative_scores.iloc[-1].copy()
    if '기타(Others)' in final_row.index:
        final_row = final_row.drop('기타(Others)')
    return final_row[final_row > 0].nlargest(top_n).index.tolist()

def build_period_top_n_data(pivot_df, selected_users, top_n):
    result = pd.DataFrame(0.0, index=pivot_df.index, columns=selected_users)
    for period, row in pivot_df.iterrows():
        row_clean = row.drop('기타(Others)') if '기타(Others)' in row.index else row
        top_series = row_clean[row_clean > 0].nlargest(top_n)
        for user, value in top_series.items():
            if user in result.columns:
                result.at[period, user] = value
    return result

def filter_low_activity_periods(pivot_df, threshold_ratio=LOW_PERIOD_AVERAGE_RATIO):
    if pivot_df.empty:
        return pivot_df

    period_totals = pivot_df.sum(axis=1)
    average = period_totals.mean()
    threshold = average * threshold_ratio
    keep_mask = period_totals > threshold
    removed = pivot_df.index[~keep_mask].tolist()

    if not keep_mask.any():
        max_period = period_totals.idxmax()
        print(f"저활동 기간 필터링: 모든 기간이 기준 이하라 총합 최대 기간 1개 유지 ({max_period})")
        return pivot_df.loc[[max_period]]

    if removed:
        print(f"저활동 기간 필터링: 전체기간 평균 {average:.2f}의 {threshold_ratio * 100:.1f}% 이하({threshold:.2f}) {len(removed)}개 제거")
        print("제거 기간:", ", ".join(map(str, removed[:20])) + (" ..." if len(removed) > 20 else ""))
    else:
        print(f"저활동 기간 필터링: 전체기간 평균 {average:.2f}의 {threshold_ratio * 100:.1f}% 이하({threshold:.2f}) 제거 없음")

    return pivot_df.loc[keep_mask]

def build_user_colors(users):
    cmap = plt.get_cmap('hsv', max(1, len(users) + 1))
    colors = {user: cmap(i) for i, user in enumerate(users)}
    colors['기타(Others)'] = '#d3d3d3'
    return colors

def rank_symbol(index):
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    index += 1
    symbol = ""
    while index > 0:
        index, remainder = divmod(index - 1, len(alphabet))
        symbol = alphabet[remainder] + symbol
    return symbol

def build_user_symbols(users):
    return {user: rank_symbol(i) for i, user in enumerate(users)}

def legend_label(user, symbols):
    return f"[{symbols[user]}] {user}"

def apply_legend(ax, users):
    columns = 2 if len(users) <= 14 else 3
    ax.legend(loc='upper left', fontsize=7, ncol=columns, framealpha=0.5)

def calculate_tick_step(n_periods):
    if n_periods <= 12: return 1
    if n_periods <= 36: return 2
    return max(1, n_periods // 18)

def save_cumulative_chart(plot_data, top_users, mode, top_n):
    periods, n_periods = plot_data.index.tolist(), len(plot_data)
    step = calculate_tick_step(n_periods)
    colors = build_user_colors(top_users)
    symbols = build_user_symbols(top_users)
    fig, ax = plt.subplots(figsize=(max(14, n_periods * 0.6), 7))

    for user in top_users:
        scores = plot_data[user].tolist()
        ax.plot(range(n_periods), scores, marker='o', markersize=4, linewidth=1.5,
                label=legend_label(user, symbols), color=colors[user])
        ax.text(n_periods - 1 + 0.1, scores[-1], f"{symbols[user]} {user} ({scores[-1]:.1f})",
                fontsize=8, va='center', color=colors[user])

    tick_positions = list(range(0, n_periods, step))
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([periods[i] for i in tick_positions], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("누적 점수")
    ax.set_title(f"누적 활동 수치 - 최종 Top {top_n} 추적", fontsize=13)
    apply_legend(ax, top_users)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    plt.savefig(f'score_chart_{mode}.png', dpi=150)
    plt.show()

def save_aggregate_chart(pivot_df, top_users, mode, bar_style='G', top_n=10):
    if bar_style == 'S':
        save_stacked_aggregate_chart(pivot_df, top_users, mode, top_n, percentage=False)
    elif bar_style == 'P':
        save_stacked_aggregate_chart(pivot_df, top_users, mode, top_n, percentage=True)
    elif bar_style == 'R':
        save_ranked_stacked_chart(pivot_df, top_users, mode, top_n)
    else:
        save_grouped_aggregate_chart(pivot_df, top_users, mode, top_n)

def save_stacked_aggregate_chart(pivot_df, top_users, mode, top_n, percentage=False):
    """ [S 옵션 / P 옵션] 일반 쌓기 및 100% 비율 쌓기 통합 제어 함수 """
    periods, n_periods = pivot_df.index.tolist(), len(pivot_df)
    step = calculate_tick_step(n_periods)
    x = range(n_periods)

    processed_data = {user: [] for user in top_users}
    processed_data['기타(Others)'] = []

    for period, row in pivot_df.iterrows():
        base_others = row.get('기타(Others)', 0.0)
        row_clean = row.drop('기타(Others)') if '기타(Others)' in row.index else row
        
        period_top = row_clean[row_clean > 0].nlargest(top_n)
        period_top_users = period_top.index.tolist()
        
        total_score = row_clean.sum()
        top_score_sum = period_top.sum()
        others_score = max(0.0, total_score - top_score_sum)
        
        # 실제 합산 처리
        p_total = row.sum() if percentage else 1.0
        if p_total == 0: p_total = 1.0 # 0 나누기 방지
        
        for user in top_users:
            val = row_clean[user] if user in period_top_users else 0.0
            processed_data[user].append(val / p_total)
                
        actual_others = base_others + others_score + sum([row_clean[u] for u in top_users if u not in period_top_users])
        processed_data['기타(Others)'].append(actual_others / p_total)

    fig, ax = plt.subplots(figsize=(max(14, n_periods * 0.6), 7))
    bottom = [0] * n_periods
    colors = build_user_colors(top_users)
    symbols = build_user_symbols(top_users)

    # 기타 우선 깔기
    ax.bar(x, processed_data['기타(Others)'], bottom=bottom, label='기타(Others)', color=colors['기타(Others)'], width=0.75)
    bottom = [b + v for b, v in zip(bottom, processed_data['기타(Others)'])]

    for user in top_users:
        values = processed_data[user]
        if sum(values) == 0: continue
        ax.bar(x, values, bottom=bottom, label=legend_label(user, symbols), color=colors[user], width=0.75)
        bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_xticks(list(range(0, n_periods, step)))
    ax.set_xticklabels([periods[i] for i in list(range(0, n_periods, step))], rotation=45, ha='right', fontsize=8)
    
    title_str = "100% 비율 점유율 쌓기" if percentage else "일반 누적 막대 쌓기"
    ax.set_ylabel("비중" if percentage else "기간별 점수")
    ax.set_title(f"{mode} 집계 - {title_str} (Top {top_n} 외 기타 통합)", fontsize=13)
    apply_legend(ax, top_users)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    output_style = 'P' if percentage else 'S'
    plt.savefig(f'score_chart_aggregate_{output_style}_{mode}.png', dpi=150)
    plt.show()

def save_ranked_stacked_chart(pivot_df, top_users, mode, top_n):
    """ [R 옵션] 순위별 정렬 쌓기: 매 시점 1등이 가장 아래, 순위순 정렬 """
    periods, n_periods = pivot_df.index.tolist(), len(pivot_df)
    step = calculate_tick_step(n_periods)
    colors = build_user_colors(top_users)
    symbols = build_user_symbols(top_users)
    
    fig, ax = plt.subplots(figsize=(max(14, n_periods * 0.6), 7))
    
    # 순위 범례용 가짜 패치 핸들링
    seen_labels = set()

    for period_idx, period in enumerate(periods):
        row = pivot_df.loc[period]
        base_others = row.get('기타(Others)', 0.0)
        row_clean = row.drop('기타(Others)') if '기타(Others)' in row.index else row
        
        # 실시간 순위 정렬
        sorted_rank = row_clean[row_clean > 0].sort_values(ascending=False)
        top_part = sorted_rank.head(top_n)
        
        # 순위권 밖 점수 수집 -> 기타 통합
        others_part_score = base_others + sorted_rank.iloc[top_n:].sum()
        
        # 차트 드로잉 베이스 바닥 설정
        current_bottom = 0.0
        
        # 1. 기타(Others) 바닥에 배치
        if others_part_score > 0:
            lbl = '기타(Others)' if '기타(Others)' not in seen_labels else None
            seen_labels.add('기타(Others)')
            ax.bar(period_idx, others_part_score, bottom=current_bottom, color=colors['기타(Others)'], width=0.75, label=lbl)
            current_bottom += others_part_score
            
        # 2. 순위 역순(낮은 순위부터 위로 쌓아 최종 1등이 기타 바로 위에 오도록 구성)
        for user, score in reversed(list(top_part.items())):
            lbl = legend_label(user, symbols) if user not in seen_labels and user in symbols else None
            seen_labels.add(user)
            ax.bar(period_idx, score, bottom=current_bottom, color=colors.get(user, '#999999'), width=0.75, label=lbl)
            if user in symbols and score > 0:
                ax.text(period_idx, current_bottom + score / 2, symbols[user],
                        ha='center', va='center', fontsize=7, color='black')
            current_bottom += score

    ax.set_xticks(list(range(0, n_periods, step)))
    ax.set_xticklabels([periods[i] for i in list(range(0, n_periods, step))], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("기간별 점수")
    ax.set_title(f"{mode} 집계 - 순위순 정렬 쌓기 (아래에서부터 상위권 레이어)", fontsize=13)
    apply_legend(ax, top_users)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    plt.savefig(f'score_chart_ranked_stacked_{mode}.png', dpi=150)
    plt.show()

def save_grouped_aggregate_chart(pivot_df, top_users, mode, top_n):
    """ [G 옵션] 가로 분리 배열 막대 """
    periods, n_periods = pivot_df.index.tolist(), len(pivot_df)
    step = calculate_tick_step(n_periods)
    group_width = 0.82
    bar_width = min(0.22, group_width / max(1, top_n))
    x = list(range(n_periods))
    colors = build_user_colors(top_users)
    symbols = build_user_symbols(top_users)

    fig, ax = plt.subplots(figsize=(max(14, n_periods * max(0.75, top_n * 0.13)), 7))
    labeled_users, other_labeled = set(), False

    for period_index, period in enumerate(periods):
        row = pivot_df.loc[period]
        row_clean = row.drop('기타(Others)') if '기타(Others)' in row.index else row
        ranked = row_clean[row_clean > 0].sort_values(ascending=False).head(top_n)
        
        count = len(ranked)
        if count == 0: continue
        start_offset = -((count - 1) * bar_width) / 2
        
        for rank_index, (user, value) in enumerate(ranked.items()):
            offset = x[period_index] + start_offset + rank_index * bar_width
            if user in top_users:
                color = colors[user]
                label = legend_label(user, symbols) if user not in labeled_users else None
                labeled_users.add(user)
            else:
                color, label = colors['기타(Others)'], ('기타(Others)' if not other_labeled else None)
                other_labeled = True
            ax.bar(offset, value, width=bar_width, label=label, color=color)
            if user in symbols:
                ax.text(offset, value, symbols[user], ha='center', va='bottom', fontsize=7, color='black')

    ax.set_xticks(list(range(0, n_periods, step)))
    ax.set_xticklabels([periods[i] for i in list(range(0, n_periods, step))], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("기간별 점수")
    ax.set_title(f"{mode} 집계 개별 분리 막대 (순위 외 회색)", fontsize=13)
    apply_legend(ax, top_users)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    plt.tight_layout()
    plt.savefig(f'score_chart_aggregate_grouped_{mode}.png', dpi=150)
    plt.show()

# 실행
if __name__ == "__main__":
    selected_mode, selected_graph_type, selected_top_n, selected_bar_style, selected_start, selected_end = ask_options()
    save_final_clean_report(
        'daily-data.txt', 'daily-data-comment.txt',
        mode=selected_mode, graph_type=selected_graph_type, top_n=selected_top_n,
        bar_style=selected_bar_style, start_date=selected_start, end_date=selected_end,
        black=BLACK_LIST
    )

