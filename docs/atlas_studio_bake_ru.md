# Atlas AI Studio (mlxar GmbH, atlas.design): пайплайн и бейк, по шагам

Метки: **[C]** подтверждено их сайтом или доками · **[I]** вывод из доков · **[S]** предположение.
Проверено 27.10.2026. Источники перечислены в конце.

## Главное
Хорошие ассеты у них получаются не из-за ручного бейка в Blender. Это **детерминированный нодовый граф**:
чистый концепт → dense hi-poly (Tripo/Meshy/Hunyuan с fallback) → Optimize Mesh (ретопо до бюджета + UV) →
BBox Fit → **Bake High→Low** (normal/albedo/rough/metal/AO) → опционально retexture → GLB/FBX + LOD.
Blender у них в основном работает как **хостовый Blender с агентом** (Blender Agent node: настоящие вызовы bpy, рендер в Cycles)
и нужен для сборки сцены, света и рендера. [C] Сам бейк сделан отдельной нодой. В доках не сказано, на чём она работает: на Blender (Cycles bake)
или на своём коде. [S] По параметрам (AO samples, margin, explicit resolution) это очень похоже на Cycles bake.

## Пайплайн по шагам
1. **Арт-библия / контекст** [C]: стиль, палитра, негативные правила и референсы подтягиваются в каждый прогон (Memory Core / Context).
2. **Концепт → чистый input** [C]: одиночный объект на нейтральном или прозрачном фоне, ≥1024², **перспективная камера + тени**
   (depth cues). Для персонажей лист стандартизируют в T-pose. Мусор вычищают нодами Multimodal / Precise Text Edit.
   Для закрытых зон используют multi-view (front/back/side).
3. **Image→3D, сразу в hi-detail** [C]: Tripo3D v3.x (Geometry Ultra), Meshy v6, Hunyuan3D 3.1, Trellis 2, свой Titan v1, с fallback-цепочкой.
   PBR включают **на первом прогоне**: потом уже не включить. Пример с драконом: реконструкция на 100k faces.
4. **Auto Transform Mesh** [C]: pivot, масштаб, оси, центрирование.
5. **Optimize Mesh** [C]: ретопо до бюджета (Atlas Remesh / Simple Decimate) и **unwrap UV в том же прогоне**.
   Бюджеты: mobile ~5k tris/1K, console ~20k/2K, PC ~50k/2K. Пример: дракон 100k→15k.
   Треугольники подходят для статики, квады нужны для рига и сабдива.
6. **Mesh BBox Fit** [C]: перед бейком выравнивают масштаб и позицию low и high. Из-за этого бейк не «плывёт».
7. **Bake High-Poly → Low-Poly** [C]: каналы normal, albedo, roughness, metallic, AO (+height там, где он нужен).
   Правила: UV low-poly **без overlap в 0–1**; разрешение задаётся явно; margin растёт вместе с разрешением (Auto);
   у AO регулируется число сэмплов.
8. **(Re)texture Mesh** [C], опционально: рестайл по тексту или референсу без перегенерации геометрии.
9. **LOD + риг** [C]: LOD-тиры (например, 5k/3k/1k или 20k/7.5k/2.5k), гуманоидный скелет + skin weights + клипы.
10. **Blender Agent → Render** [C]: хостовый Blender, выбранная LLM гоняет bpy, сверяется по скриншотам, собирает и светит сцену.
    На выходе .blend + GLB, а нода Render даёт PNG из Cycles. Предупреждение из доков: **GLB не запекает процедурные материалы**,
    поэтому всё процедурное нужно запечь в текстуры до экспорта.
11. **Экспорт** [C]: GLB с встроенным PBR или FBX. Удачный граф публикуют как версионированный API.

Чего нет в публичных источниках: туториалов про ручной бейк (cage, extrusion, curvature/thickness) и названий аддонов.
Про Blender MCP и видео-туториалы в X я сегодня отдельно не перепроверял. [S] Скорее всего, внутри используются стандартные bpy-бейки.

## Что повторить в твоём пайплайне (IEA-5 / персонажи)
1. Генерируй hi-poly **максимального качества** (Tripo Ultra + PBR on). Этот меш — источник деталей, а не финал.
2. Low-poly делай отдельно: для мото это твой блокаут или ретопо (Quad Remesher / Instant Meshes / Decimate),
   для персонажа это ретопо под AccuRIG. Бюджет зависит от платформы.
3. UV: Smart UV Project (angle ~66°, island margin 0.003–0.005) или UVPackmaster; 0–1, без overlap; texel density одинаковая.
4. Выравнивание: Apply All Transforms на обоих мешах и одинаковый origin; high и low лежат точно друг на друге.
5. Cycles bake: Selected to Active, **Cage** (дубль low + Displace/Push ~0.01–0.03) или Extrusion ~0.02, Max Ray Distance небольшой.
   - Normal: Tangent, OpenGL для Blender/Unity, DirectX (инверсия G) для Unreal; Non-Color; лучше 16-bit.
   - Diffuse: только Color (без Direct/Indirect), это альбедо из PBR Tripo.
   - Roughness / Metallic: через Emission-трюк (вывести канал в Emission и бейкать Emit).
   - AO: 128–256 сэмплов; Curvature/Cavity при необходимости через Pointiness/Geometry → Emit, для грязи и сколов.
   - Разрешение 2K (4K для героя, потом даунскейл), margin 16px на 2K / 32px на 4K, режим Extend.
6. Проверка: собери low с картами, смотри в matcap + HDRI, ищи швы и «волны»; при артефактах правь cage, а не бейк.
7. Процедурку (шум, грязь) запекай до экспорта в GLB.
8. Автоматизация в духе Atlas: оформи шаги 4–6 как bpy-скрипт или через Blender MCP. Тогда «один граф с фиксированными
   настройками» каждый раз даёт одинаковый результат, а для каждого шага модель проверяет себя по скриншоту.

## Источники
- https://docs.atlas.design/atlas-ai-studio-overview/node-index/mesh-nodes : нода Bake High→Low, каналы, UV 0–1, BBox Fit, AO samples, margin.
- https://docs.atlas.design/atlas-ai-studio-overview/node-index/mesh-nodes/3d-generation-best-practices : подготовка input, бэкенды, ошибки, порядок hi→retopo→bake.
- https://atlas.design/features/ai-retopology : граф дракона 100k→15k→bake, бюджеты по платформам, LOD, форматы, честное «hero asset всё равно доводит художник».
- https://atlas.design/blender-agent и https://docs.atlas.design/atlas-ai-studio-overview/node-index/mesh-nodes/scene-nodes : хостовый Blender, агент на bpy, .blend/GLB, Cycles render, GLB не запекает процедурку.
- https://atlas.design : модели (Tripo3D v3.1, Meshy v6, Hunyuan 3.1, Trellis 2, Titan v1), fallback-цепочка, концепт→T-pose→меш.
