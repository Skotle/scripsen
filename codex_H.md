TFC 호환 패치는 “바이옴 추가” 수준이 아니라, TFC 전용 월드 생성 파이프라인 전체를 EarthShape 레이어에 연결하는 작업입니다.

## 반드시 구현

1. TFC 월드 감지 및 분기

- `tfc` 로드 여부와 오버월드 생성기가 `tfc:overworld`인지 확인
- TFC 월드에서는 vanilla/NeoForge용 `MultiNoiseBiomeSource` 경로를 사용하지 않음
- 일반 월드와 TFC 월드의 처리 경로를 분리

2. TFC 바이옴 소스 어댑터

- 대상: `RegionBiomeSource`, `BiomeSourceExtension`
- EarthShape의 대륙/지형/온도/강 마스크를 TFC `BiomeExtension`으로 변환
- TFC의 기본 지역 노이즈·랜덤 변형은 유지하되, 지도 레이어가 지정한 육지/바다/강/대지형 범위를 벗어나지 못하게 제한

3. EarthShape → TFC 바이옴 매핑

| EarthShape 레이어 | 기본 TFC 후보 |
|---|---|
| 바다 | `OCEAN`, `DEEP_OCEAN`, `DEEP_OCEAN_TRENCH`, `OCEAN_REEF` |
| 지도 강 | `RIVER` |
| 해안 | `SHORE`, `TIDAL_FLATS` |
| 습지 | `SALT_MARSH`, `LOWLANDS` |
| 평야/도시 | `PLAINS`, `LOWLANDS` |
| 숲 | `LOWLANDS`, `HILLS`, 기후에 맞는 TFC 숲 생성 |
| 사막 | `BADLANDS`, `INVERTED_BADLANDS`, `CANYONS` |
| 구릉 | `HILLS`, `ROLLING_HILLS`, `HIGHLANDS` |
| 산 | `MOUNTAINS`, `OLD_MOUNTAINS`, `PLATEAU` |
| 화산 지형 | `VOLCANIC_MOUNTAINS`, `VOLCANIC_OCEANIC_MOUNTAINS` |

4. TFC 지형 생성 어댑터

- 대상: `TFCChunkGenerator`, `ChunkHeightFiller`, `ChunkNoiseFiller`
- 기존 EarthShape density function/`NoiseChunk` 보정은 TFC 지형에 적용되지 않으므로 전용 처리 필요
- 지도 바다는 해수면 아래, 지도 육지는 해수면 위가 되도록 TFC 높이 결과를 보정
- TFC의 국지적 구릉·산·동굴은 남기되, 대륙 윤곽은 EarthShape가 최종 권한을 가짐

5. 해안·대륙붕 처리

- 대상: TFC `ChunkHeightFiller` 또는 TFC 표면 생성 전 단계
- 기존 `CoastalShelfFloorMixin`은 vanilla `NoiseChunk` 전용이므로 TFC에서는 무효
- 해안 수심·대륙붕·해저 지지층을 TFC 지형 높이 계산에 통합
- TFC 표면 생성 전후 순서를 정해 토양/모래/암석층을 물·돌로 덮어쓰지 않게 처리

6. TFC 대수층 및 물 처리

- 대상: `TFCAquifer`
- 기존 `NoiseBasedAquifer` 믹스인은 TFC에 적용되지 않음
- 지도 바다의 해수면 유지
- 지도 육지에서 의도하지 않은 표면 수원 제거
- 지도 강에서 물기둥과 강바닥 깊이 보장
- TFC 동굴 대수층·지하수는 가능한 한 보존

7. 강 시스템 통합

- TFC 자체 지역 기반 강과 `rivers.bmp` 중 무엇을 최종 기준으로 할지 결정
- 권장: 지도 강이 우선, TFC 강은 지도 강에 합류하거나 지도 밖에서만 제한적으로 사용
- 지도 강에는 `TFCBiomes.RIVER` 및 TFC 강둑/식생/표면 규칙 적용
- 지도 바다로 들어가는 강어귀는 TFC의 해안·조수 지형과 연결
- TFC의 내륙 호수·산악 호수는 지도 육지/바다 판정에 맞게 제한

8. TFC 기후 데이터 통합

- 대상: `RegionChunkDataGenerator`
- 온도, 강수량, 계절성, 습도, 숲 밀도를 EarthShape의 `earth_temperature.png`·나무 레이어와 연동
- TFC 작물 성장, 식생, 동물 산란, 눈·얼음, 강수는 이 데이터를 사용하므로 바이옴만 바꾸면 안 됨
- 남북 온도대와 지도 기반 건조/습윤 지역이 실제 TFC 기후에도 반영돼야 함

9. TFC 숲·식생·야생 작물

- TFC의 숲 유형, 나무, 야생 작물, 관목, 해양 식생이 EarthShape 기후·지형 분류를 따르게 조정
- 사막/고산/해안/습지는 서로 다른 TFC feature 태그를 사용해야 함
- 바다에 육상 식생, 육지에 해양 식생이 배치되지 않도록 보호

10. 암석층·광맥·지질 보존

- 대상: `RegionChunkDataGenerator`, `RockLayerSettings`, 광맥 feature
- EarthShape의 육지/바다/높이 보정이 TFC 암석층과 광맥 배치를 지우지 않게 처리
- 고정 `STONE` 덮어쓰기 금지
- TFC의 기반암, 암석 지층, 표면 돌, 광물 노두, 광맥은 TFC 로직을 유지
- 새로 생기는 바다/강 아래에서도 암석층·광맥 데이터는 계속 생성

11. TFC 표면 생성 통합

- 대상: `SurfaceManager`, 해안/강/산/화산 surface builder
- EarthShape 높이 보정 후 TFC가 토양, 모래, 자갈, 점토, 암석, 해안 퇴적물을 생성하게 순서 조정
- EarthShape가 마지막에 공기/물/돌을 덮으면 TFC 표면 시스템이 망가지므로 피해야 함
- 화산, 협곡, 고원, 강둑, 조수평원은 전용 예외 처리 필요

12. 구조물 호환

- 기존 `SurfaceStructureRateMixin`의 vanilla 지형 분류를 TFC용으로 교체하거나 TFC 월드에서 비활성화
- TFC 구조물·기후 기반 구조물·강/해안 배치를 보존
- 지도 바다에는 육상 구조물, 지도 육지에는 해양 구조물이 생성되지 않도록 별도 필터
- TFC 구조물 배치 훅과 충돌하지 않도록 TFC 구조물 생성 순서 확인

13. 피처 검증 믹스인 제한

- `AdditionalBiomeFeatureMixin`은 모든 `ChunkGenerator.validate()`를 취소하므로 TFC에도 영향을 줄 수 있음
- TFC 월드에서는 절대 무조건 취소하지 말고, EarthShape가 실제로 후보를 추가한 vanilla 생성기에만 한정
- TFC의 피처 정렬·중복 검사·생성 단계 검증은 유지

14. 추가 바이옴/태그 처리

- 기존 `AdditionalBiomeRegistry`는 vanilla/NeoForge 태그 중심이라 TFC에 맞지 않음
- TFC 태그와 `BiomeExtension` 기반으로 별도 분류 필요:
  - `tfc:is_ocean`
  - `tfc:is_river`
  - `tfc:is_lake`
  - TFC의 해안, 화산, 강수/바람 관련 태그
- `minecraft` 바이옴 후보군을 강제로 반환하는 현재 방식은 TFC 월드에서 사용 금지

15. 스폰 및 시작 지점

- TFC는 자체 스폰 거리/스폰 중심 설정을 사용
- EarthShape 지도에서 바다·빙하·극지·급경사지에 스폰하지 않도록 TFC 스폰 탐색과 연동
- 기본 TFC 시작 조건(안전한 육지, 필요한 자원 접근성)을 보존

16. 세계 프리셋·서버 설정

- TFC 프리셋 `tfc:overworld`를 유지한 상태로 EarthShape 모드를 적용
- EarthShape가 `minecraft:overworld` 프리셋/차원을 덮어써 TFC 프리셋을 무효화하지 않게 방지
- TFC의 `spawn_distance`, 암석층 설정, 온도·강수 스케일, 대륙성 설정과 EarthShape 설정의 우선순위 문서화

17. 성능 및 캐시

- TFC는 지역·강·기후·암석 데이터를 광범위하게 캐시함
- EarthShape 지도 조회도 청크/열 단위 캐시로 통합
- biome/height/aquifer 단계에서 동일 좌표를 반복 샘플링하지 않도록 설계
- 월드 재시작·데이터팩 리로드 시 캐시를 확실히 무효화

18. 안전장치 및 회귀 테스트

- TFC 없는 일반 Forge 월드는 기존 EarthShape 동작 유지
- TFC 활성화 시에만 전용 믹스인/로직 활성화
- 기존 월드에는 소급 적용하지 않고, 새 월드 생성만 지원
- 최소 테스트 항목:
  - 지도 바다/대륙 윤곽
  - 지도 강 및 강어귀
  - TFC 암석층·광맥
  - TFC 계절/작물/식생
  - 산·협곡·화산
  - 해안·조수평원
  - 스폰 지점
  - 구조물
  - 멀티플레이 서버 재시작 및 청크 생성

TFC는 독자 `tfc:overworld` 생성기와 바이옴 소스를 사용하며, 자체 지형·강·기후·암석층 시스템을 갖습니다. 따라서 EarthShape의 기존 vanilla용 믹스인을 그대로 재사용하면 안 됩니다. [TFC 월드 프리셋 문서](https://terrafirmacraft.github.io/Documentation/1.20.x/worldgen/world-preset/), [TFC 월드 생성 문서](https://terrafirmacraft.github.io/Documentation/1.20.x/worldgen/)