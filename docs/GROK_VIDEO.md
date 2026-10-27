# Grok Imagine Video: шпаргалка для previz2shot (на 16.10.2026)

## 1. Что есть сейчас
| | grok-imagine-video-1.5 | 1.5-lite | grok-imagine-video (старая) |
|---|---|---|---|
| Text→video / Image→video | до 1080p нативно | до 1080p (апскейл с 720p) | до 720p |
| Рефы (reference-to-video) | до 14 картинок, 15 с, **720p** | нет | до 7, 10 с, 720p |
| Первый + последний кадр | да | нет | нет |
| Промежуточные keyframes | до 4 | нет | нет |
| Video edit (video→video) | нет | нет | да, исходник до 8,7 с |
| Продление | нет | нет | +2–10 с |
| Длительность | 1–15 с | 1–15 с | 1–15 с |
| Звук | нативный, с липсинком | то же | сгенерированный |
Пропорции: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 21:9, 5:2. В image→video пропорции берутся из картинки.
Источник: https://docs.x.ai/developers/model-capabilities/video/overview

**Цены API** (за секунду): 1.5: 480p $0.08 / 720p $0.14 / 1080p $0.25; lite: $0.02 / $0.03 / $0.14; старая: $0.05 / $0.07, входное видео $0.01/с. Входная картинка $0.01. https://docs.x.ai/developers/pricing
→ 5-секундный шот на 1.5 в 720p стоит около $0.70, в 1080p около $1.25.

## 2. Подписка (grok.com/imagine, приложение)
- 12.10.2026 SuperGrok/Premium+ заменили на The X Subscription. Видео доступно с тарифа Premium ($30). У старых подписчиков SuperGrok тариф и функции сохраняются. В интерфейсе ролик до ~10 с, 720p, 24 fps, 4 варианта на промпт; 15 с только через API. https://felloai.com/grok-imagine-video-generation/ , https://felloai.com/grok-imagine-spicy-mode/
- Режимы: Normal / Fun / Custom / Spicy (Spicy только 18+, нам не нужен). Там же.
- Лимиты официально не публикуются и плавают: по отзывам 15–20 видео 720p в день, у других 50–80. https://www.atlascloud.ai/blog/tips/grok-xai-image-generation-daily-limit , https://www.reddit.com/r/grok/comments/1sh0quo/supergrok_video_generations_limits/
- Подписка ≠ API: кредиты API оплачиваются отдельно в console.x.ai (вывод по докам pricing).

## 3. Comfy (это важно для конкурса)
У Grok есть официальные **partner-ноды Comfy**, так что генерация остаётся «на Comfy API», а оплата идёт кредитами Comfy:
- `GrokVideoNode`: text/image→video, модели video / 1.5 / 1.5-lite, 1–15 с, принимает **одну** стартовую картинку. https://docs.comfy.org/built-in-nodes/GrokVideoNode
- `GrokVideoReferenceNode`: 1–7 рефов, в промпте `@Image1…@Image7`. https://docs.comfy.org/built-in-nodes/GrokVideoReferenceNode
- `GrokVideoEditNode` / `GrokVideoExtendNode` (старая модель). https://docs.comfy.org/tutorials/partner-nodes/grok/grok-video
- В документации нод **нет last_frame и keyframes**: пиннинг кадров есть только в прямом xAI API. Это нужно проверить в Comfy (может, ноды уже обновили).
- Seed не даёт воспроизводимости. https://docs.comfy.org/tutorials/partner-nodes/grok/grok-imagine-video-1-5

## 4. API из Python
`POST https://api.x.ai/v1/videos/generations`, затем поллинг `GET /v1/videos/{request_id}` до `status=done`, потом `video.url`. Картинки передаются как HTTPS URL, data-URI base64 или `file_id`. Есть `xai_sdk` (`client.video.generate(..., image_url=, last_frame_url=, keyframes=[{"image_url":..., "timestamp":2.667}])`).
- keyframes: до 4 штук, строго внутри (0, duration), сетка 1/3 с, между ними минимум 1/3 с.
- Пины лучше всего работают, когда кадры из одной сцены: делай их правкой одного кадра.
- С большим числом рефов: у каждого одна роль, каст маленький, реквизит статичный.
https://docs.x.ai/developers/model-capabilities/video/reference-to-video , https://docs.x.ai/developers/model-capabilities/video/image-to-video
- Отдельного negative prompt в API нет (параметра нет в доках). Что должно остаться неизменным, пиши словами в промпте.

## 5. Как писать промпт
Формула: **одна сцена → субъект → действие → среда → стиль → камера → свет → звук → что не менять**. Один субъект и одно движение камеры. Text→video: опиши кадр, камеру, свет и звук (overview). Image→video: картинка уже задаёт облик, поэтому промпт описывает **что происходит дальше**, а не что на кадре.
Подводные камни: дрейф облика (лечится пинами first/last/keyframes и рефами), надписи (наша «РЮМОЧНАЯ» выйдет кашей, лучше без вывесок), модерация (реальные люди, бренды), рефы ограничены 720p.

Шаблон:
```
[Камера: тип движения, скорость, высота]. [Субъект из первого кадра] [действие + направление + скорость].
[Среда]. Style: [стиль, материалы]. Lighting: [свет]. Audio: [звук].
Keep the car design, colors and track layout exactly as in the frames; no new objects, no text.
```

### Пример 1 (image→video + last_frame, CAM_hero)
```
Low tracking shot following a small red toy race car as it speeds along a miniature
race track from left to right, wheels spinning, slight body roll in the turn.
Rounded toy trees, striped crash barriers and tyre stacks pass by. Style: handmade claymation
miniature, soft plasticine textures, tilt-shift depth of field. Lighting: warm late-afternoon sun,
soft shadows. Audio: buzzing toy engine, tyres on track. Camera stays locked behind the car,
smooth motion. Keep the car identical in every frame; no text, no extra cars.
```
### Пример 2 (reference-to-video, без пина первого кадра)
```
The toy race car from <IMAGE_0> races through the miniature track from <IMAGE_1>,
in the clay style of <IMAGE_2>. Smooth dolly-follow camera at car height, 24fps cinematic motion.
Warm golden light. Engine whine and crowd cheering softly. No text, no people.
```
### Пример 3 (короткий, только движение, если пинов 3)
```
Camera follows the red clay toy car closely as it accelerates down the straight; motion blur on the
track, wheels visibly spinning. Consistent claymation look, warm light, engine sound.
```

## 6. Какие рефы подавать (наши файлы)
- `test_runs/pixar_hero_v4_kf_f0.png` → `image` (первый кадр)
- `test_runs/pixar_hero_v4_kf_f64.png` → `keyframes` t=2.667 с (64/24)
- `test_runs/pixar_hero_v4_kf_f112.png` → `keyframes` t=4.667 с (112/24) при duration=5. Или делаем его `last_frame` с duration≈4.667 → 5 и обрезаем.
- Рефы Prism (`refs_prism/f*.png`) годятся как `reference_images` для стиля, но с пиннингом они могут конфликтовать. Начинать без них.
- Серый `layout_121f_960x544.mp4`: **на 1.5 видео на вход не подаётся**. Подать можно только через старую модель в режиме edit («restyle into claymation, keep geometry/camera»), до 8,7 с, 720p, $0.07/с. Это единственный путь video→video, качество не проверено.
- 960x544 ≈ 16:9 (1.765), так что выход будет 16:9.

## 7. План
1. Ручной тест в grok.com/imagine по подписке Макса: kf_f0 + промпт 1, 6–10 с. Бесплатно в рамках лимита, проверяем стиль и движение.
2. Тест через Comfy partner-ноду GrokVideoNode (кредиты Comfy), чтобы шот засчитался как Comfy API. Проверить, есть ли в ноде last_frame/keyframes.
3. Если пинов в Comfy нет: прямой xAI API (`xai_sdk`) с f0 + keyframes f64/f112. Нужен XAI_API_KEY и пополненный баланс, около $0.7 за шот. Требует одобрения Макса. Для конкурса это не Comfy, поэтому только как сравнение.
4. Эксперимент: GrokVideoEditNode на layout mp4 (первые 8 с) → restyle.
5. Сравнить с LTX v4 по раскадровке и выбрать.
