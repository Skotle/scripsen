#from PIL import Image
from collections import Counter

# 이미지 로드
img = Image.open('worldmap_river.jpg').convert('RGB')

# 픽셀 데이터 추출 및 색상별 개수 집계
pixels = list(img.getdata())
color_counts = Counter(pixels)

# 전체 픽셀 수 및 주요 색상 출력
print(f"전체 픽셀 수: {len(pixels):,}개\n")
print("=== 주요 색상별 픽셀 수 (RGB) ===")
for color, count in color_counts.most_common(10): # 상위 10개 색상
    percentage = (count / len(pixels)) * 100
    print(f"RGB {color}: {count:,}개 ({percentage:.2f}%)")
