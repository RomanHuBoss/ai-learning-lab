"""Replace generated lesson filler with domain-specific teaching blocks."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT_PATH = ROOT / "data" / "lesson_content.json"


def profile(lesson_id: str, title: str) -> dict:
    module = int(lesson_id.split(".", 1)[0])
    if lesson_id == "1.01":
        return {
            "intuition": "Переменная — это имя, связанное со значением в памяти программы. В ML такие имена будут хранить признаки, целевую переменную, параметры модели и результат вычисления. Сначала научимся читать это связывание на маленьком примере.",
            "formal": "Оператор присваивания x = v создаёт или обновляет связывание имени x со значением v. Для выражения net = price * (1 - discount) Python сначала вычисляет правую часть, затем сохраняет результат под именем net. Тип значения определяет допустимые операции, а новое присваивание не меняет старое значение, если на него больше нет ссылки.",
            "manual": "Пусть price = 1200, discount = 0,15 и tax = 0,20. Последовательно вычислите discount_price = price · (1 − discount) = 1020 и total = discount_price · (1 + tax) = 1224. Проверьте результат обратным вычислением цены без налога.",
            "table": {"headers": ["Имя", "Выражение", "Значение", "Тип"], "rows": [["price", "1200", "1200", "int"], ["discount", "0,15", "0,15", "float"], ["total", "1020 · 1,20", "1224", "float"]], "caption": "Пошаговое вычисление цены"},
            "points": [{"x": 0, "y": 0}, {"x": 1, "y": 2}, {"x": 2, "y": 4}, {"x": 3, "y": 6}],
            "graph": {"type": "line", "x_label": "шаг вычисления", "y_label": "значение", "series": [{"name": "x · 2", "values": [0, 2, 4, 6]}]},
            "formulas": ["discount_price = price · (1 − discount)", "total = discount_price · (1 + tax)"],
            "code": "# Переменные и выражения\nprice = 1200\ndiscount = 0.15\ntax = 0.20\ndiscount_price = price * (1 - discount)\ntotal = discount_price * (1 + tax)\nprint(discount_price, total)",
        }
    if module in (6, 7):
        return {
            "intuition": f"В теме «{title}» сначала отделите устойчивый сигнал от случайных колебаний. Сравните две маленькие выборки и проверьте, изменится ли вывод после добавления одного наблюдения.",
            "formal": f"Для темы «{title}» обозначим наблюдения x₁,…,xₙ, оценку θ̂ и ошибку e. Формула метрики должна быть выбрана до просмотра ответа и сопровождаться оценкой неопределённости.",
            "manual": f"Возьмите значения 2, 3, 3, 8 и разберите тему «{title}» вручную. Сначала посчитайте основной показатель, затем сравните его с результатом для 2, 3, 3, 4.",
            "table": {"columns": ["Выборка", "Центр", "Разброс", "Вывод"], "rows": [["A", "4,0", "2,4", "неустойчиво"], ["B", "3,0", "0,8", "стабильнее"]]},
            "graph": {"type": "line", "x_label": "номер наблюдения", "y_label": "оценка", "series": [{"name": "выборка A", "values": [2, 3, 3, 8]}, {"name": "выборка B", "values": [2, 3, 3, 4]}]},
            "code": f"# {title}\nvalues = [2, 3, 3, 8]\nmean = sum(values) / len(values)\nprint(round(mean, 2))",
        }
    if module in (8, 9, 10, 11):
        return {
            "intuition": f"В теме «{title}» разделите задачу на признаки, целевую переменную и правило проверки. Модель должна улучшать результат на новых строках, а не просто запоминать таблицу.",
            "formal": f"Пусть X — матрица признаков, y — цель, а fθ(X) — предсказание для темы «{title}». Параметры θ выбираются по функции потерь на train, а решение оценивается на независимом validation или test.",
            "manual": f"Составьте три строки X для темы «{title}». Выполните один шаг модели вручную, сравните ŷ с y и укажите, какая ошибка попадёт в метрику.",
            "table": {"columns": ["Объект", "Признак x₁", "Признак x₂", "Цель y", "Предсказание"], "rows": [["A", "1", "0", "0", "0,2"], ["B", "0", "1", "1", "0,8"], ["C", "1", "1", "1", "0,6"]]},
            "graph": {"type": "scatter", "x_label": "признак x₁", "y_label": "признак x₂", "series": [{"name": "класс 0", "values": [[1, 0], [0, 0]]}, {"name": "класс 1", "values": [[0, 1], [1, 1]]}]},
            "code": f"# {title}\nX = [[1, 0], [0, 1], [1, 1]]\ny = [0, 1, 1]\nprediction = [0.2, 0.8, 0.6]\nprint(sum((a - b) ** 2 for a, b in zip(y, prediction)) / len(y))",
        }
    if module in (12, 13):
        return {
            "intuition": f"В теме «{title}» проследите сигнал через слои и отдельно проследите ошибку назад. Измените один вес, чтобы увидеть, почему маленький шаг иногда улучшает, а иногда ухудшает обучение.",
            "formal": f"Нейрон вычисляет z = wᵀx + b и h = φ(z). Для темы «{title}» градиент ∂L/∂w задаёт направление изменения веса, а эпоха и пакет определяют, как часто это изменение применяется.",
            "manual": f"Возьмите x=(1,2), w=(0,5;−0,25), b=0,1 для темы «{title}». Выполните прямой проход, найдите L=(ŷ−y)² и сделайте один шаг w := w−η∇L.",
            "table": {"columns": ["Шаг", "Вес w", "Потеря L", "Градиент"], "rows": [["0", "0,50", "0,36", "−1,20"], ["1", "0,62", "0,21", "−0,82"], ["2", "0,70", "0,12", "−0,49"]]},
            "graph": {"type": "line", "x_label": "шаг", "y_label": "потеря", "series": [{"name": "обучение", "values": [0.36, 0.21, 0.12, 0.08]}, {"name": "проверка", "values": [0.4, 0.24, 0.2, 0.22]}]},
            "code": f"# {title}\nw, b = 0.5, 0.1\nx, y, rate = 2.0, 1.0, 0.1\nfor _ in range(3):\n    prediction = w * x + b\n    error = prediction - y\n    w -= rate * 2 * error * x\n    b -= rate * 2 * error\nprint(round(w, 3), round(b, 3))",
        }
    if module in (14, 15, 16, 17):
        return {
            "intuition": f"В теме «{title}» проследите путь текста от токенов до ответа. Отделяйте то, что модель получила из контекста, от того, что она восстановила вероятностно.",
            "formal": f"Пусть последовательность токенов имеет длину T, а размер представления равен d. Для темы «{title}» важно явно указать, где появляются logits, вероятности, контекстное ограничение и функция потерь.",
            "manual": f"Возьмите фразу «модель читает данные» и разберите тему «{title}» на трёх шагах. Запишите токены, промежуточное представление и проверяемый критерий ответа.",
            "table": {"columns": ["Этап", "Вход", "Выход", "Что проверяем"], "rows": [["1", "текст", "токены", "разбиение"], ["2", "токены", "векторы", "размерность"], ["3", "контекст", "логиты", "опора ответа"]]},
            "graph": {"type": "bar", "x_label": "токен", "y_label": "вероятность", "series": [{"name": "следующий токен", "values": [0.52, 0.28, 0.12, 0.08]}]},
            "code": f"# {title}\ntokens = ['модель', 'читает', 'данные']\ncontext = ' '.join(tokens)\nprint(context, len(tokens))",
        }
    if module in (18,):
        return {
            "intuition": f"В теме «{title}» структура связей становится частью входа. Сначала опишите узлы и рёбра, затем покажите, какую информацию узел получает от соседей.",
            "formal": f"Граф G=(V,E) задаёт узлы V и рёбра E. В теме «{title}» слой передачи сообщений агрегирует hᵤ для u∈N(v), применяет W и нелинейность, сохраняя инвариантность к порядку соседей.",
            "manual": f"Постройте граф A—B—C и назначьте признаки 1, 2, 4. Для темы «{title}» усредните признаки соседей B, затем добавьте ребро A—C и сравните обновлённое значение.",
            "table": {"columns": ["Узел", "Соседи", "Признак", "После агрегации"], "rows": [["A", "B", "1", "2"], ["B", "A,C", "2", "2,5"], ["C", "B", "4", "2"]]},
            "graph": {"type": "network", "nodes": ["A", "B", "C"], "edges": [["A", "B"], ["B", "C"]]},
            "code": f"# {title}\nneighbors = {{'A': ['B'], 'B': ['A', 'C'], 'C': ['B']}}\nfeatures = {{'A': 1.0, 'B': 2.0, 'C': 4.0}}\nprint(sum(features[n] for n in neighbors['B']) / 2)",
        }
    if module in (19,):
        return {
            "intuition": f"В теме «{title}» модель читает последовательность и переносит скрытое состояние. Сравните ранний и поздний сигнал, чтобы увидеть проблему длинной зависимости и роль ворот памяти.",
            "formal": f"Рекуррентный переход задаёт hₜ=f(xₜ,hₜ₋₁). В теме «{title}» LSTM использует iₜ, fₜ, oₜ и cₜ, а GRU объединяет управление памятью в два воротных коэффициента.",
            "manual": f"Возьмите x=(0,2,1,3) для темы «{title}» и обновляйте hₜ=0,7hₜ₋₁+0,3xₜ. Повторите расчёт с коэффициентом 0,95 и сравните память о первом значении.",
            "table": {"columns": ["Шаг", "xₜ", "hₜ", "Память о первом сигнале"], "rows": [["1", "0,2", "0,06", "высокая"], ["2", "1,0", "0,34", "средняя"], ["3", "3,0", "1,14", "низкая"]]},
            "graph": {"type": "line", "x_label": "шаг", "y_label": "скрытое состояние", "series": [{"name": "RNN", "values": [0.06, 0.34, 1.14, 1.7]}, {"name": "LSTM", "values": [0.06, 0.4, 1.2, 1.8]}]},
            "code": f"# {title}\nhidden = 0.0\nfor token in [0.2, 1.0, 3.0]:\n    hidden = 0.7 * hidden + 0.3 * token\n    print(round(hidden, 3))",
        }
    if module in (20,):
        return {
            "intuition": f"В теме «{title}» разделите память весов, память активаций и память KV-кэша. Затем сопоставьте их с размером модели, длиной контекста и доступной видеопамятью.",
            "formal": f"Для темы «{title}» оценка памяти весов равна P·b/8 байт, где P — число параметров, b — битность. К этому добавляются активации, KV-кэш и служебный запас, поэтому размер файла модели не равен требуемой VRAM.",
            "manual": f"Оцените тему «{title}» для модели 7 млрд параметров в FP16 и INT4. Сравните 14 ГБ и 3,5 ГБ весов, затем оставьте запас на KV-кэш и пакет запросов.",
            "table": {"columns": ["Режим", "Бит на параметр", "Вес 7B", "Практический вывод"], "rows": [["FP32", "32", "28 ГБ", "нужна большая VRAM"], ["FP16", "16", "14 ГБ", "GPU 16 ГБ на грани"], ["INT4", "4", "3,5 ГБ", "доступен локальный запуск"]]},
            "graph": {"type": "bar", "x_label": "режим", "y_label": "ГБ", "series": [{"name": "память весов", "values": [28, 14, 7, 3.5]}]},
            "code": f"# {title}\nparameters = 7_000_000_000\nfor bits in (32, 16, 8, 4):\n    print(bits, round(parameters * bits / 8 / 1e9, 2), 'GB')",
        }
    if module in (21,):
        return {
            "intuition": f"В теме «{title}» прошлое должно оставаться отделённым от будущего. Сначала сформируйте лаги и окно признаков, затем проверьте прогноз на следующем временном отрезке.",
            "formal": f"Для темы «{title}» признак lag-k равен yₜ₋ₖ, а walk-forward оценка обучает модель только на данных до момента t и проверяет её на будущем интервале. Случайное перемешивание здесь создаёт утечку.",
            "manual": f"Для ряда [10, 12, 11, 15, 18] постройте lag-1 и прогноз на следующий момент в теме «{title}». Отметьте, какие строки нельзя использовать при обучении первого прогноза.",
            "table": {"columns": ["Дата", "yₜ", "lag-1", "Прогноз", "Ошибка"], "rows": [["1", "10", "—", "—", "—"], ["2", "12", "10", "11", "1"], ["3", "11", "12", "12", "1"]]},
            "graph": {"type": "line", "x_label": "время", "y_label": "значение", "series": [{"name": "факт", "values": [10, 12, 11, 15, 18]}, {"name": "прогноз", "values": [10, 11, 12, 13, 16]}]},
            "code": f"# {title}\nseries = [10, 12, 11, 15, 18]\nlag_1 = series[:-1]\nfuture = series[1:]\nprint(list(zip(lag_1, future)))",
        }
    if module in (22,):
        return {
            "intuition": f"В теме «{title}» агент наблюдает состояние, выбирает действие и получает награду. Сравните исследование нового действия с использованием уже найденного хорошего действия.",
            "formal": f"Для темы «{title}» политика π(a|s) выбирает действие a в состоянии s. В epsilon-greedy с вероятностью ε выбирается случайное действие, иначе действие с максимальной оценкой Q(s,a).",
            "manual": f"Для двух действий с оценками Q=[0, 0,5] и ε=0,2 разберите тему «{title}» на десяти шагах. Посчитайте ожидаемую долю исследования и использования.",
            "table": {"columns": ["Действие", "Оценка Q", "Наблюдений", "Средняя награда"], "rows": [["лево", "0,20", "5", "0,20"], ["право", "0,75", "12", "0,75"]]},
            "graph": {"type": "line", "x_label": "шаг", "y_label": "regret", "series": [{"name": "epsilon-greedy", "values": [8, 6, 4, 3, 2]}]},
            "code": f"# {title}\nq = [0.2, 0.75]\nepsilon = 0.2\nbest = max(range(len(q)), key=q.__getitem__)\nprint(best, epsilon)",
        }
    return {
        "intuition": f"В теме «{title}» система проходит путь от входа до измеряемого результата. Сначала зафиксируйте контракт и ограничение, затем проверьте воспроизводимость на повторном запуске.",
        "formal": f"Для темы «{title}» опишите входы, состояние, преобразование и выход. Добавьте проверяемое ограничение по качеству, задержке, стоимости, безопасности или версии данных.",
        "manual": f"Составьте небольшой сценарий для темы «{title}»: вход, один шаг обработки, результат и проверка. Укажите, какая ошибка должна остановить публикацию.",
        "table": {"columns": ["Шаг", "Артефакт", "Проверка", "Статус"], "rows": [["1", "данные", "версия зафиксирована", "готово"], ["2", "модель", "метрика рассчитана", "проверить"], ["3", "сервис", "контракт отвечает", "проверить"]]},
        "graph": {"type": "flow", "nodes": ["вход", "обработка", "проверка", "результат"], "edges": [["вход", "обработка"], ["обработка", "проверка"], ["проверка", "результат"]]},
        "code": f"# {title}\ndef run(input_value):\n    result = {{'value': input_value, 'checked': True}}\n    return result\nprint(run('demo'))",
    }


def lab_for(lesson_id: str, title: str) -> str:
    value = title.lower()
    if any(word in value for word in ("узлы", "рёбра", "граф")):
        return "graph-playground"
    if any(word in value for word in ("rnn", "рекуррент", "lstm", "gru", "скрытое состояние", "длинной зависимости")):
        return "rnn-flow"
    if any(word in value for word in ("перцептрон", "нейрон", "прямой проход", "активац", "xor")):
        return "forward-pass"
    if any(word in value for word in ("обратное распространение", "sgd", "momentum", "adam")):
        return "backprop"
    if any(word in value for word in ("токен",)):
        return "tokenization"
    if any(word in value for word in ("query", "key", "value", "вниман")):
        return "attention-map"
    if "transformer" in value:
        return "transformer-flow"
    if any(word in value for word in ("изображение", "свёртк", "генератив")):
        return "convolution"
    if any(word in value for word in ("веса", "параметры", "квантиз", "оборуд", "gpu", "vram")):
        return "hardware-selector"
    if any(word in value for word in ("инференс", "контекстное окно", "память")):
        return "memory-budget"
    if any(word in value for word in ("rag", "поиск", "агент", "галлюцинац")):
        return "concept-map"
    if any(word in value for word in ("метрик", "mae", "mse", "rmse", "accuracy", "precision", "recall", "f1", "рекомендац")):
        return "metric-choice"
    if any(word in value for word in ("дерев", "лес", "бустинг")):
        return "tree-depth"
    if any(word in value for word in ("регресс", "обучение с учителем", "ближайших")):
        return "classification-boundary"
    if any(word in value for word in ("кластер", "компонент")):
        return "tensor-shapes"
    if any(word in value for word in ("временн", "walk-forward", "лаг", "дрейф")):
        return "rnn-flow"
    if any(word in value for word in ("fastapi", "api", "docker")):
        return "api-design"
    if any(word in value for word in ("sandbox", "секрет", "права")):
        return "sandbox"
    if any(word in value for word in ("лог", "метрик", "ci", "монитор", "откат", "версиониров")):
        return "experiment-tracker"
    if "защит" in value:
        return "project-defense"
    return "concept-map"


content = json.loads(CONTENT_PATH.read_text(encoding="utf8"))
for lesson in content["lessons"]:
    if not str(lesson.get("intuition", "")).startswith("Начните с маленького") and lesson.get("lesson_id") != "1.01":
        continue
    current = profile(lesson["lesson_id"], lesson["title"])
    lesson["intuition"] = current["intuition"]
    lesson["formal_explanation"] = current["formal"]
    lesson["manual_example"] = current["manual"]
    lesson["code_example"] = current["code"]
    lesson["interactive_lab"] = lab_for(lesson["lesson_id"], lesson["title"])
    if current.get("formulas"):
        lesson["formulas"] = current["formulas"]
    if current.get("points"):
        lesson["visualization_points"] = current["points"]
    graph = current.get("graph", {"type": "line", "series": []})
    lesson["visualization"] = {
        "type": graph["type"],
        "fallback": f"Уникальная схема и числовая иллюстрация темы «{lesson['title']}».",
        "alt": f"Графическая иллюстрация темы «{lesson['title']}».",
        "graph": graph,
    }
    lesson["table"] = current["table"]
    lesson["summary"] = [
        f"Объясните тему «{lesson['title']}» через её входы и проверяемый результат.",
        "Проверьте формулу на маленьком числовом примере.",
        "Свяжите наблюдение с лабораторией и ограничением метода.",
    ]

intro = next(lesson for lesson in content["lessons"] if lesson["lesson_id"] == "1.01")
intro.update(
    {
        "what_is_known": [
            "Для старта достаточно уметь читать числа и простые арифметические действия.",
            "Вы будете проверять каждый шаг на маленьком примере.",
        ],
        "learning_objectives": [
            "создать переменную и выбрать понятное имя",
            "вычислить выражение с несколькими признаками",
            "объяснить, как числовой вход превращается в результат модели",
        ],
        "why_it_matters": "Любая ML-система начинается с измеряемых признаков и явного результата. Переменные позволяют назвать эти величины, а выражения — воспроизводимо посчитать первый прогноз.",
        "intuition": "Представьте квартиру как строку таблицы. Площадь, этаж и расстояние до метро становятся отдельными переменными. Когда мы складываем их с выбранными весами, получаем прозрачный первый прогноз, который можно проверить вручную.",
        "formal_explanation": "Переменная связывает имя со значением. Выражение вычисляется по правилам приоритета операций. В простейшей модели ŷ = b + w₁x₁ + w₂x₂, где x₁ и x₂ — признаки, w₁ и w₂ — их веса, b — базовый уровень, а ŷ — предсказание. На этом уроке веса задаются явно, поэтому можно проверить каждый вклад.",
        "manual_example": "Пусть площадь x₁=40 м², этаж x₂=3, базовый уровень b=20, w₁=2 и w₂=1. Тогда ŷ = 20 + 2·40 + 1·3 = 103. Если площадь увеличить до 45 м², вклад площади вырастет на 10, а новый прогноз станет 113.",
        "code_example": "# Прозрачный первый прогноз\narea = 40\nfloor = 3\nbias = 20\nprice = bias + 2 * area + floor\nprint(price)  # 103",
        "visualization": {
            "type": "table-and-line",
            "fallback": "Таблица признаков показывает вклад площади и этажа, а линия прогноза растёт при увеличении площади.",
            "alt": "Таблица признаков и линия линейного прогноза цены.",
            "graph": {
                "type": "line",
                "x_label": "площадь, м²",
                "y_label": "предсказание",
                "series": [{"name": "y = 20 + 2x + 3", "values": [63, 83, 103, 123]},],
            },
        },
        "table": {
            "columns": ["Переменная", "Значение", "Вес", "Вклад"],
            "rows": [["площадь x₁", "40", "2", "80"], ["этаж x₂", "3", "1", "3"], ["база b", "20", "—", "20"], ["итог ŷ", "—", "—", "103"]],
        },
        "misconceptions": [
            "Имя переменной не меняет значение, но плохое имя затрудняет проверку расчёта.",
            "Вес показывает вклад признака в этой формуле, но не доказывает причинность.",
            "Один ручной прогноз не заменяет проверку на наборе новых объектов.",
        ],
        "summary": [
            "Переменная хранит значение, а выражение задаёт воспроизводимый расчёт.",
            "Линейный прогноз складывает базовый уровень и взвешенные признаки.",
            "Перед переходом к модели проверьте расчёт на двух-трёх строках таблицы.",
        ],
        "remediation": {"if_wrong": "Повторите расчёт ŷ = b + w₁x₁ + w₂x₂ на таблице урока и измените только один признак.", "next_link": None},
    }
)

for lesson in content["lessons"]:
    if lesson.get("lesson_id") == "1.01":
        lesson["interactive_lab"] = "variable-playground"
        lesson["formulas"] = ["ŷ = b + w₁x₁ + w₂x₂", "вклад признака = вес × значение"]
        continue
    if lesson.get("formulas"):
        continue
    module = int(lesson["lesson_id"].split(".", 1)[0])
    if module in (6, 7):
        formulas = ["MAE = (1/n) · Σ|yᵢ − ŷᵢ|", "95% ДИ = оценка ± критическое значение · SE"]
    elif module in (8, 9, 10, 11):
        formulas = ["ŷ = fθ(X)", "MSE = (1/n) · Σ(yᵢ − ŷᵢ)²"]
    elif module in (12, 13):
        formulas = ["z = wᵀx + b", "w ← w − η · ∇L(w)"]
    elif module in (14, 15, 16, 17):
        formulas = ["Attention(Q,K,V) = softmax(QKᵀ/√dₖ) · V", "p(token | context) = softmax(logits)"]
    elif module == 18:
        formulas = ["hᵥ′ = σ(W · AGG({hᵤ : u ∈ N(v)}) + b)", "G = (V, E)"]
    elif module == 19:
        formulas = ["hₜ = f(xₜ, hₜ₋₁)", "cₜ = fₜ ⊙ cₜ₋₁ + iₜ ⊙ ĉₜ"]
    elif module == 20:
        formulas = ["память весов ≈ P · b / 8 байт", "KV-кэш ∝ длина контекста × число слоёв"]
    elif module == 21:
        formulas = ["lagₖ(t) = yₜ₋ₖ", "ошибка прогноза = yₜ − ŷₜ"]
    elif module == 22:
        formulas = ["Q(s,a) ← Q(s,a) + α[r + γ maxₐ′Q(s′,a′) − Q(s,a)]", "π(a|s) = ε·случайно + (1−ε)·argmax Q"]
    else:
        formulas = ["результат = f(вход, версия данных, параметры)", "стоимость = ресурсы × время × тариф"]
    lesson["formulas"] = formulas

for lesson in content["lessons"]:
    if not lesson.get("table"):
        lesson["table"] = {
            "columns": ["Шаг", "Вход", "Преобразование", "Результат"],
            "rows": [["1", "пример A", "применили правило", "значение 1"], ["2", "пример B", "проверили ограничение", "значение 2"], ["3", "пример C", "сравнили с целью", "вывод"]],
        }
    visualization = lesson.setdefault("visualization", {})
    if not visualization.get("graph"):
        visualization["graph"] = {
            "type": "line",
            "x_label": "шаг",
            "y_label": "значение",
            "series": [{"name": "пример", "values": [1, 2, 3, 4]}],
        }

CONTENT_PATH.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
