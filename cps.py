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
    
    # 바이옴별 최다 구간일 때의 CPS 목록 수집용 Dict
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

        # 1. 해당 구간(표본)에서 최다 비율/수량을 차지한 바이옴 추출
        if biomes:
            max_count = max(count for _, count in biomes)
            # 수량이 동일하게 최대인 바이옴이 여럿일 경우 모두 포함 (보통 1개)
            for biome, count in biomes:
                if count == max_count and count > 0:
                    dominant_biome_cps[biome].append(rate)

        # 2. 불일치 검증
        if biome_count != rate:
            mismatches.append(
                f"{line_number}행: Rate {rate} cps, 바이옴 합계 {biome_count} chunks"
            )

    return rates, biome_totals, mismatches, dominant_biome_cps


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
    for biome, cps_list in sorted(dominant_biome_cps.items(), key=lambda x: len(x[1]), reverse=True):
        avg_cps = sum(cps_list) / len(cps_list)
    
        if (avg_cps < sum(rates)/len(rates)*0.70) :print(f"- {biome}: 평균 {avg_cps:.2f} CPS❌ (최다 차지 구간: {len(cps_list)}초)")
        elif (avg_cps < sum(rates)/len(rates)*0.9):print(f"- {biome}: 평균 {avg_cps:.2f} CPS⚠️ (최다 차지 구간: {len(cps_list)}초)")
        else:print(f"- {biome}: 평균 {avg_cps:.2f} CPS✅ (최다 차지 구간: {len(cps_list)}초)")

    if mismatches:
        print(f"\n불일치: {len(mismatches)}개")
        print("\n".join(mismatches))
    else:
        print("\n모든 표본에서 바이옴별 합계와 CPS가 일치합니다.")


def plot_chunks_per_minute(rates: list[int]) -> None:
    per_minute = [sum(rates[index:index + 60]) for index in range(0, len(rates), 60)]
    plt.title("Chunks per minute")
    plt.plot(per_minute, marker="*", color="blue", label="measured")
    plt.axhline(sum(rates) / len(rates) * 60, color="red", linestyle="--", label="average")
    plt.xlabel("minute sample")
    plt.ylabel("chunks")
    plt.grid(True)
    plt.legend()
    plt.show()


if __name__ == "__main__":
    rates, biome_totals, mismatches, dominant_biome_cps = parse_log(LOG_PATH)
    print_summary(rates, biome_totals, mismatches, dominant_biome_cps)
    if rates:
        plot_chunks_per_minute(rates)