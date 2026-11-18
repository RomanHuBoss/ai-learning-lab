# Отчёт по доступности вертикального среза

Проверено в демо-режиме.

- Структура использует landmarks `aside`, `header`, `main`, `nav`, `section` и доступные имена экранов.
- Все основные действия представлены кнопками и доступны через клавиатуру.
- У интерактивного графика есть `aria-label` и отдельное текстовое описание.
- Визуальные состояния дублируются текстом и подписями, поэтому смысл не передаётся только цветом.
- Контролы лаборатории имеют видимые labels, значения output и режим запуска, паузы, шага и сброса.
- Реализованы dark/light theme, `prefers-reduced-motion` и ручной переключатель уменьшения движения.
- Макет адаптируется к ширине от 320 пикселей и не требует горизонтальной прокрутки в базовых сценариях.
- Focus-visible оформлен контрастной cyan-обводкой.

## Новая автоматическая проверка

- `scripts/check_accessibility.py` проверяет `lang=ru`, skip-link, landmarks, labels для полей, `alt` у изображений и доступное имя canvas.
- CI запускает этот static check в job `quality`.
- Отдельный CI job `accessibility` поднимает локальный API и запускает Lighthouse для категорий accessibility и performance. Accessibility score ниже 90 завершает job ошибкой, JSON-отчёт и server log сохраняются как artifacts.

## NVDA-oriented manual pass

Проверен accessibility tree в браузере для dashboard, лаборатории, каталога выпускников, панели наставника и админ-панели. Последовательность Tab сохраняет порядок sidebar, topbar и main content, skip-link доступен с первого фокуса, модальные окна имеют `role=dialog` и возвращают фокус на close control. Интерактивные controls лаборатории представлены кнопками и sliders с labels.

В текущем окружении нет исполняемого NVDA, поэтому выполнен NVDA-oriented manual pass по accessibility tree и клавиатурным сценариям. Для release-проверки с реальным NVDA следует пройти сценарии `Tab`, `Shift+Tab`, `Enter`, `Escape`, чтение заголовков и объявление `role=status` после получения CI Lighthouse artifact.

## Измеренный Lighthouse-аудит

Локальный Lighthouse 12.8.2 на Windows для `http://127.0.0.1:8000/` после отключения внешних шрифтов и включения GZipMiddleware дал следующие результаты:

- Accessibility — 95/100
- Performance — 93/100

CI запускает тот же аудит на Ubuntu и завершает job ошибкой, если любой из двух показателей ниже 90. JSON-отчёт и логи сервера публикуются как workflow artifacts.
