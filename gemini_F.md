# EarthShape × TFC (TerraFirmaCraft) 호환 패치 단계별 구체적 개발 지침서

본 지침서는 바닐라/NeoForge 파이프라인에 맞춰진 EarthShape의 생성 로직을 `tfc:overworld` 파이프라인으로 이식하기 위한 전 구체적 개발 순서 및 세부 구현 지침을 정리한 문서입니다.

---

## 1단계: 초기화, 프리셋 보존 및 오버월드 분기 (Initialization & Detection)

TFC 모드가 활성화된 환경에서 바닐라용 생성 파이프라인이 작동하지 않도록 차단하고 전용 분기를 신설합니다.

* **TFC 로드 여부 및 오버월드 감지**
* `tfc` 모드의 로드 여부와 현재 오버월드 월드 생성기가 `tfc:overworld`인지 확인합니다.
* TFC 월드일 경우 기존 바닐라/NeoForge용 `MultiNoiseBiomeSource` 처리 경로를 완전히 우회합니다.


* **세계 프리셋 및 설정 우회 차단**
* TFC의 기본 월드 프리셋인 `tfc:overworld`를 유지하며 EarthShape 로직을 적용합니다.
* EarthShape가 `minecraft:overworld` 프리셋이나 차원 설정을 강제로 덮어써 TFC 프리셋을 무효화하지 않도록 방지합니다.
* TFC의 `spawn_distance`, 암석층 설정, 기후 스케일과 EarthShape 설정 간의 우선순위를 정립합니다.


* **바이옴 태그 분류 체계 분리**
* 바닐라 태그 중심의 기존 `AdditionalBiomeRegistry`를 사용하는 대신 TFC 전용 태그(`tfc:is_ocean`, `tfc:is_river`, `tfc:is_lake` 등)와 `BiomeExtension` 기반의 새로운 분류를 작성합니다.
* TFC 월드 내에서 `minecraft` 바이옴 후보군을 강제로 반환하는 로직의 작동을 금지합니다.



---

## 2단계: 지형, 대륙 윤곽 및 대수층 보정 (Terrain & Aquifer Integration)

TFC 고유의 지형 생성 및 높이 계산 단계에 EarthShape의 지도 권한을 주입합니다.

* **지형 생성 어댑터 구축**
* `TFCChunkGenerator`, `ChunkHeightFiller`, `ChunkNoiseFiller`를 대상으로 전용 높이 보정 로직을 작성합니다.
* 지도의 바다 영역은 해수면 아래로, 육지 영역은 해수면 위로 배치되도록 최종 높이를 보정합니다.
* TFC 국지적 구릉, 산, 동굴의 상세 노이즈는 보존하되, 대륙 윤곽은 EarthShape의 데이터에 최종 권한을 부여합니다.


* **해안 및 대륙붕 지형 통합**
* 기존 바닐라 전용 `CoastalShelfFloorMixin`을 비활성화하고, TFC의 `ChunkHeightFiller` 또는 표면 생성 전 단계에 해안 수심과 대륙붕 보정을 직접 통합합니다.
* 토양, 모래, 암석층이 물이나 돌로 부적절하게 덮어씌워지지 않도록 표면 처리 전후의 연산 순서를 제어합니다.


* **TFC 대수층(TFCAquifer) 제어**
* 바닐라 전용 `NoiseBasedAquifer` 믹스인을 우회하고 `TFCAquifer` 대상 맞춤 처리를 작성합니다.
* 지도상의 바다 해수면을 고정하고, 육지 지표면에 불필요한 수원이 생성되는 것을 차단합니다.
* TFC 지하 동굴의 대수층 및 지하수 생성 로직은 보존합니다.



---

## 3단계: 강 수계 시스템 통합 (River Network Integration)

EarthShape의 비트맵 기반 강 지도와 TFC의 생성 로직을 병합합니다.

* **강 우선순위 정립**
* EarthShape의 `rivers.bmp` 데이터를 최우선 기준으로 설정합니다.
* TFC의 자체 지역 강은 지도상의 강에 합류시키거나, 지도 범주 외부 영역에서만 제한적으로 발원하도록 조정합니다.


* **강 식생 및 바닥 깊이 보장**
* 지도 강 영역에 `TFCBiomes.RIVER` 속성 및 TFC 전용 강둑, 식생, 표면 규칙을 적용합니다.
* 물기둥과 강바닥의 수심을 안정적으로 확보하고, 바대로 유입되는 강어귀는 TFC의 해안 및 조수 지형과 자연스럽게 연결합니다.
* TFC 내륙 호수 및 산악 호수가 EarthShape의 육지/바다 판정과 충돌하지 않도록 조정합니다.



---

## 4단계: 기후, 식생 및 바이옴 매핑 (Climate & Biome Mapping)

TFC의 생태계 및 작물 메커니즘이 지도 데이터와 동기화되도록 연동합니다.

* **기후 데이터 통합 (`RegionChunkDataGenerator`)**
* EarthShape의 `earth_temperature.png` 및 나무 지도 레이어를 TFC의 온도, 강수량, 습도, 숲 밀도 데이터로 변환합니다.
* TFC 작물 성장, 동물 산란, 눈/얼음, 계절 및 강수 시스템이 본 기후 데이터에 의존하므로 완전한 데이터 연동을 보장합니다.


* **바이옴 소스 어댑터 연동**
* `RegionBiomeSource` 및 `BiomeSourceExtension`을 통해 EarthShape 레이어 데이터를 TFC `BiomeExtension` 구조체로 변환합니다.
* TFC의 랜덤 무작위 변형은 유지하되, EarthShape가 설정한 대지형, 바다, 강, 육지 범위를 벗어나지 않도록 제한합니다.


* **식생 및 야생 작물 배치 제어**
* TFC 숲 유형, 야생 작물, 관목, 해양 식생이 사막/고산/해안/습지 등 기후 및 지형 분류에 맞는 TFC feature 태그를 따르도록 제어합니다.
* 육상 식생이 바다에 생기거나 해양 식생이 육지에 배치되는 현상을 방지합니다.



### 📍 EarthShape → TFC 기본 바이옴 매핑 가이드

| EarthShape 레이어 | 기본 TFC 매핑 후보 바이옴 |
| --- | --- |
| **바다** | `OCEAN`, `DEEP_OCEAN`, `DEEP_OCEAN_TRENCH`, `OCEAN_REEF` |
| **지도 강** | `RIVER` |
| **해안** | `SHORE`, `TIDAL_FLATS` |
| **습지** | `SALT_MARSH`, `LOWLANDS` |
| **평야 / 도시** | `PLAINS`, `LOWLANDS` |
| **숲** | `LOWLANDS`, `HILLS`, 기후 연동 TFC 숲 |
| **사막** | `BADLANDS`, `INVERTED_BADLANDS`, `CANYONS` |
| **구릉** | `HILLS`, `ROLLING_HILLS`, `HIGHLANDS` |
| **산** | `MOUNTAINS`, `OLD_MOUNTAINS`, `PLATEAU` |
| **화산 지형** | `VOLCANIC_MOUNTAINS`, `VOLCANIC_OCEANIC_MOUNTAINS` |

---

## 5단계: 지질, 암석층 및 광맥 보존 (Geology & Ore Features)

지형 높이와 바이옴이 보정되더라도 TFC 특유의 암석 구조가 파괴되지 않도록 보호합니다.

* **지층 및 광맥 보호 파이프라인 (`RegionChunkDataGenerator`, `RockLayerSettings`)**
* EarthShape 지형 보정 과정에서 단순 `STONE` 블록으로 일괄 덮어쓰는 행위를 엄격히 금지합니다.
* TFC의 기반암, 지하 암석 지층, 지표 돌, 광물 노두, 광맥 배치 로직을 고스란히 유지합니다.
* 새로 형성된 강 및 바다 밑부분에서도 TFC 지층 및 광맥 데이터가 정상 생성되도록 연산 순서를 조율합니다.



---

## 6단계: 표면 생성, 구조물 및 믹스인 제어 (Surface, Structures & Mixins)

표면 블록 덮어쓰기와 구조물 배치 로직, 그리고 기존 믹스인의 부작용을 통제합니다.

* **표면 생성 파이프라인 순서 교정 (`SurfaceManager`)**
* EarthShape 높이 연산 완료 후 TFC surface builder가 토양, 모래, 자갈, 점토, 해안 퇴적물을 덮도록 순서를 설정합니다.
* 파이프라인 후반부에 EarthShape가 공기, 물, 돌을 덮어씌워 TFC 표면 시스템을 파괴하는 현상을 방지합니다.
* 화산, 협곡, 고원, 강둑, 조수평원은 별도의 표면 예외 로직을 구성합니다.


* **구조물 생성 필터링**
* 바닐라용 `SurfaceStructureRateMixin`을 TFC 환경에서는 비활성화하거나 TFC 전용으로 대체합니다.
* 육상 구조물이 바다에, 해양 구조물이 육지에 생성되지 않도록 필터를 적용하고 TFC 구조물 생성 훅과의 충돌 여부를 확인합니다.


* **피처 검증 믹스인 제한 (`AdditionalBiomeFeatureMixin`)**
* `AdditionalBiomeFeatureMixin`이 `ChunkGenerator.validate()` 전체를 취소하는 동작이 TFC 생성기에 영향을 주지 않도록 조치합니다.
* 바닐라 생성기에서 EarthShape 후보가 추가되었을 때만 한정적으로 동작하게 변경하며, TFC의 피처 정렬 및 중복 검사는 유지시킵니다.



---

## 7단계: 플레이어 스폰, 캐싱 최적화 및 회귀 테스트 (Spawn, Caching & QA)

마지막으로 게임플레이 시작점 조정과 성능 최적화, 최종 안정성 검증을 진행합니다.

* **플레이어 스폰 포인트 조정**
* TFC 스폰 탐색 알고리즘과 연동하여 바다, 빙하, 극지, 급경사지에 플레이어가 스폰되지 않도록 방지합니다.
* 안전한 육지 확보 및 초기 자원 접근성 등 TFC 기본 시작 조건 요구사항을 충족시킵니다.


* **청크 캐시 및 캐시 무효화 (Caching System)**
* TFC의 광범위한 지역/기후/암석 캐시 구조에 맞춰 EarthShape 지도 조회 연산을 청크/열 단위 캐시로 통합합니다.
* 바이옴, 높이, 대수층 연산 시 동일 좌표 중복 샘플링을 방지합니다.
* 월드 재시작 또는 데이터팩 리로드(`/reload`) 실행 시 캐시를 명확히 무효화(invalidate) 처리합니다.


* **회귀 테스트 및 검증 항목**
* TFC 미설치 환경 시 기존 바닐라/Forge 월드 생성과의 호환성을 확인합니다.
* 신규 월드 생성에만 패치를 적용하도록 제한합니다.
* **필수 테스트 체크리스트:**
1. 대륙 윤곽 및 지도 바다 윤곽 일치 여부
2. 지도 강 및 강어귀 자연 연결 여부
3. TFC 암석층 및 광맥 정상 생성 여부
4. TFC 계절, 작물 및 식생 정상 작동 여부
5. 산, 협곡, 화산 지형 보존 여부
6. 해안 및 조수평원 형태 검증
7. 스폰 지점 안전성 검증
8. 육지/바다 구조물 위치 필터링 검증
9. 멀티플레이 서버 재시작 및 지속 청크 생성 안정성