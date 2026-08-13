from collections import Counter, defaultdict
from pathlib import Path
import re

import matplotlib.pyplot as plt


LOG_PATH = Path(__file__).with_name("latest.log")
TASK_PATTERN = re.compile(
    r"Rate: (?P<rate>\d+) cps, Surface biomes: (?P<biomes>.*?), Current:"
)
BIOME_PATTERN = re.compile(r"(?P<biome>[\w:-]+) \((?P<count>\d+) chunks\)")


def parse_log(path: Path):
    rates: list[int] = []
    biome_totals: Counter[str] = Counter()
    mismatches: list[str] = []
    
    # 1초 단위의 (바이옴, 청크수) 데이터 리스트
    sample_biomes_list: list[list[tuple[str, int]]] = []
    dominant_biome_cps: dict[str, list[int]] = defaultdict(list)

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        task = TASK_PATTERN.search(line)
        if task is None:
            continue

        rate = int(task.group("rate"))
        biomes = [(match.group("biome"), int(match.group("count"))) for match in BIOME_PATTERN.finditer(task.group("biomes"))]
        biome_count = sum(count for _, count in biomes)

        rates.append(rate)
        biome_totals.update(dict(biomes))
        sample_biomes_list.append(biomes)

        # 1초 기준 최다 차지 바이옴 집계 (기존 로직 유지)
        if biomes:
            max_count = max(count for _, count in biomes)
            for biome, count in biomes:
                if count == max_count and count > 0:
                    dominant_biome_cps[biome].append(rate)

        # 불일치 검증
        if biome_count != rate:
            mismatches.append(
                f"{line_number}행: Rate {rate} cps, 바이옴 합계 {biome_count} chunks"
            )

    return rates, biome_totals, mismatches, dominant_biome_cps, sample_biomes_list


def print_summary(
    rates: list[int],
    biome_totals: Counter[str],
    mismatches: list[str],
    dominant_biome_cps: dict[str, list[int]],
) -> None:
    if not rates:
        print("진행 로그를 찾지 못했습니다.")
        return

    print("=== 바이옴별 누적 청크 ===")
    for biome, count in biome_totals.most_common():
        print(f"- {biome}: {count} chunks")
    print(f"총 바이옴 청크: {sum(biome_totals.values())}")
    print(f"CPS 표본: {len(rates)}개")
    print(f"전체 평균 CPS: {sum(rates) / len(rates):.2f}\n")

    print("=== 각 바이옴이 최다 구간일 때의 평균 CPS ===")
    avg_total = sum(rates) / len(rates)
    for biome, cps_list in sorted(dominant_biome_cps.items(), key=lambda x: len(x[1]), reverse=True):
        avg_cps = sum(cps_list) / len(cps_list)
        
        if avg_cps < avg_total * 0.75:
            icon = "❌"
        elif avg_cps < avg_total:
            icon = "⚠️"
        elif avg_cps > avg_total * 1.20:
            icon = "🟦"
        else:
            icon = "✅"
            
        print(f"- {biome}: 평균 {avg_cps:.2f} CPS{icon} (최다 차지 구간: {len(cps_list)}초)")

    if mismatches:
        print(f"\n불일치: {len(mismatches)}개")
        print("\n".join(mismatches))
    else:
        print("\n모든 표본에서 바이옴별 합계와 CPS가 일치합니다.")


def plot_chunks_per_minute(rates: list[int], sample_biomes_list: list[list[tuple[str, int]]]) -> None:
    per_minute: list[int] = []
    minute_biomes: list[str] = []

    # 60초(1분) 단위로 묶어서 구간별 바이옴 일괄 합산
    for index in range(0, len(rates), 60):
        minute_rates = rates[index:index + 60]
        minute_biomes_slice = sample_biomes_list[index:index + 60]

        # 1. 1분간의 총 청크 수
        per_minute.append(sum(minute_rates))

        # 2. 1분(60초) 범위 전체의 바이옴 청크 일괄 집계
        interval_counter: Counter[str] = Counter()
        for sample in minute_biomes_slice:
            interval_counter.update(dict(sample))

        if interval_counter:
            # 해당 1분 구간에서 합산 청크 수가 가장 많았던 바이옴
            top_biome = interval_counter.most_common(1)[0][0]
            # minecraft: 프리픽스 제거
            short_biome = top_biome.split(":")[-1]
            minute_biomes.append(short_biome)
        else:
            minute_biomes.append("N/A")

    plt.figure(figsize=(10, 6))
    plt.title("Chunks per minute (Dominant Biome Aggregated per Minute)")
    plt.plot(per_minute, marker="*", color="blue", label="measured")
    plt.axhline(sum(rates) / len(rates) * 60, color="red", linestyle="--", label="average")

    # 그래프 각 1분 포인트 상단에 일괄 집계된 최다 바이옴 표시
    for i, (val, biome) in enumerate(zip(per_minute, minute_biomes)):
        plt.annotate(
            biome,
            (i, val),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
            rotation=20,
            weight="bold"
        )

    plt.xlabel("minute sample")
    plt.ylabel("chunks")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    rates, biome_totals, mismatches, dominant_biome_cps, sample_biomes_list = parse_log(LOG_PATH)
    print_summary(rates, biome_totals, mismatches, dominant_biome_cps)
    if rates:
        plot_chunks_per_minute(rates, sample_biomes_list)