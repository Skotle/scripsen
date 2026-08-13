import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    import bar_chart_race as bcr
except ImportError:
    bcr = None


INPUT_FILE = Path("daily-data.txt")
OUTPUT_PREFIX = "activity_race"
TOP_N = 10


def set_korean_font():
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False


def load_daily_data(file_path):
    pattern = re.compile(r"\[(.+?)\]\s\[(.+?)\]\s\[(.+?)\]")
    data_list = []

    if not file_path.exists():
        print(f"{file_path} 파일을 찾을 수 없습니다.")
        return pd.DataFrame(columns=["date", "user", "count"])

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if not match:
                continue

            name, identifier, date_str = match.groups()
            user = f"{name}({identifier})" if identifier else name
            date = date_str.split(" ")[0]
            data_list.append({"date": date, "user": user, "count": 1})

    return pd.DataFrame(data_list)


def build_outputs(df):
    if df.empty:
        print("daily-data.txt에서 사용할 수 있는 데이터가 없습니다.")
        return None, None, None

    df_grouped = df.groupby(["date", "user"]).size().reset_index(name="count")
    df_pivot = df_grouped.pivot(index="date", columns="user", values="count").fillna(0)
    df_cumsum = df_pivot.cumsum()

    final_rank = (
        df_cumsum.iloc[-1]
        .sort_values(ascending=False)
        .head(TOP_N)
        .reset_index()
    )
    final_rank.columns = ["user", "cumulative_count"]

    df_grouped.to_csv(f"{OUTPUT_PREFIX}_daily_counts.csv", index=False, encoding="utf-8-sig")
    df_cumsum.to_csv(f"{OUTPUT_PREFIX}_cumulative.csv", encoding="utf-8-sig")

    with pd.ExcelWriter(f"{OUTPUT_PREFIX}_summary.xlsx", engine="openpyxl") as writer:
        df_grouped.to_excel(writer, sheet_name="daily_counts", index=False)
        df_cumsum.to_excel(writer, sheet_name="cumulative")
        final_rank.to_excel(writer, sheet_name="top10", index=False)

    return df_grouped, df_cumsum, final_rank


def save_snapshot(final_rank):
    if final_rank is None or final_rank.empty:
        return

    plot_data = final_rank.sort_values("cumulative_count", ascending=True)
    fig_height = max(5, len(plot_data) * 0.45)

    plt.figure(figsize=(11, fig_height))
    bars = plt.barh(plot_data["user"], plot_data["cumulative_count"], color="#4C78A8")
    plt.title("Activity Top 10 Snapshot")
    plt.xlabel("Cumulative Count")

    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.3, bar.get_y() + bar.get_height() / 2, f"{int(width)}", va="center")

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_PREFIX}_snapshot.png", dpi=150)
    plt.close()


def save_race(df_cumsum):
    if df_cumsum is None or df_cumsum.empty:
        return

    if bcr is None:
        print("bar_chart_race 패키지가 없어 MP4/HTML 애니메이션 생성을 건너뜁니다.")
        return

    race_options = dict(
        df=df_cumsum,
        title="daily graph",
        n_bars=TOP_N,
        period_length=700,
        steps_per_period=10,
        bar_label_size=10,
        tick_label_size=10,
        title_size=15,
    )

    try:
        bcr.bar_chart_race(filename=f"{OUTPUT_PREFIX}.mp4", **race_options)
        print(f"{OUTPUT_PREFIX}.mp4 저장 완료")
    except Exception as e:
        print(f"MP4 생성 실패: {e}")

    try:
        bcr.bar_chart_race(filename=f"{OUTPUT_PREFIX}.html", **race_options)
        print(f"{OUTPUT_PREFIX}.html 저장 완료")
    except Exception as e:
        print(f"HTML 생성 실패: {e}")


def main():
    set_korean_font()
    raw_df = load_daily_data(INPUT_FILE)
    _, df_cumsum, final_rank = build_outputs(raw_df)
    if df_cumsum is None:
        return

    save_snapshot(final_rank)
    save_race(df_cumsum)

    print("추가 산출물 저장 완료:")
    print(f"- {OUTPUT_PREFIX}_daily_counts.csv")
    print(f"- {OUTPUT_PREFIX}_cumulative.csv")
    print(f"- {OUTPUT_PREFIX}_summary.xlsx")
    print(f"- {OUTPUT_PREFIX}_snapshot.png")
    print(f"- {OUTPUT_PREFIX}.mp4 / {OUTPUT_PREFIX}.html (가능한 경우)")


if __name__ == "__main__":
    main()
