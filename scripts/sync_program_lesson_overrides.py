"""Align the first five curriculum modules with the expanded program catalog."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize(value):
    match = re.match(r"0?(\d+)\.(\d+)$", str(value or ""))
    return f"{int(match.group(1))}.{match.group(2)}" if match else str(value or "")


program = json.loads((ROOT / "data/full_program.json").read_text(encoding="utf8"))
content = json.loads((ROOT / "data/lesson_content.json").read_text(encoding="utf8"))
questions = json.loads((ROOT / "data/questions.json").read_text(encoding="utf8"))
program_by_id = {normalize(item["id"]): item for item in program["lessons"]}
content_by_id = {normalize(item["lesson_id"]): item for item in content["lessons"]}
question_by_id = {}
question_exact = {}
for question in questions:
    question_exact.setdefault(str(question.get("lesson_id")), question["id"])
    question_by_id.setdefault(normalize(question.get("lesson_id")), question["id"])


def lab_for(title):
    value = title.lower()
    if "производн" in value or "градиент" in value or "оптимиз" in value or "потер" in value:
        return "gradient-descent"
    if "коллекц" in value or "типы данных" in value:
        return "type-inspector"
    if "перемен" in value or "тип" in value:
        return "variable-playground"
    if "вероят" in value or "случайн" in value:
        return "metric-choice"
    if "услов" in value or "цик" in value or "функц" in value:
        return "function-plot"
    if "numpy" in value or "вектор" in value or "матриц" in value:
        return "tensor-shapes"
    if "данн" in value or "pandas" in value or "пропуск" in value or "категор" in value or "разбиен" in value:
        return "data-cleaning"
    return "concept-map"


def profile(lesson):
    title = lesson["title"]
    value = title.lower()
    if "математическ" in value or ("модел" in value and "функц" in value):
        intuition = "Функция задаёт правило, которое каждому допустимому входу сопоставляет результат. График делает это правило видимым: по его наклону можно понять, как изменится результат при небольшом изменении признака."
        formal = "Функция f: X → Y отображает вход x в результат y=f(x). Для линейной зависимости y = a·x + b параметр a задаёт наклон, b — значение при x=0. Область определения и единицы измерения входят в модель и должны быть указаны явно."
        manual = "Рассмотрите y = 2x + 3. Для x=0, 1 и 4 получаются y=3, 5 и 11. Сравните приращения: увеличение x на 1 добавляет к результату 2, поэтому наклон равен 2."
        formulas = ["y = f(x)", "y = a · x + b", "наклон = Δy / Δx"]
        table = {"columns": ["x", "f(x)=2x+3", "Изменение x", "Изменение y"], "rows": [["0", "3", "—", "—"], ["1", "5", "+1", "+2"], ["4", "11", "+3", "+6"]]}
        graph = {"type": "line", "x_label": "вход x", "y_label": "результат f(x)", "series": [{"name": "y = 2x + 3", "values": [3, 5, 7, 9, 11]}]}
        code = "# Функция как математическая модель\ndef model(x):\n    return 2 * x + 3\n\nfor x in (0, 1, 4):\n    print(x, model(x))"
    elif "исследователь" in value or "гипотез" in value:
        intuition = "Исследовательский отчёт связывает вопрос, данные, измерение и вывод. Читатель должен видеть, откуда взялись числа, какое сравнение проведено и где заканчивается уверенность результата."
        formal = "Отчёт фиксирует постановку H₀/H₁, источник и разбиение данных, выбранную метрику и неопределённость оценки. Вывод должен быть воспроизводимым: другой человек получает тот же результат из тех же версий данных и кода."
        manual = "Сравните две группы значений A=[10, 12, 11] и B=[8, 9, 10]. Посчитайте средние, разницу 2,0 и перечислите ограничения вывода по трём наблюдениям."
        formulas = ["разница = среднее(A) − среднее(B)", "вывод = результат + допущения + ограничения"]
        table = {"columns": ["Шаг отчёта", "Что фиксируем", "Проверка"], "rows": [["1", "вопрос и гипотеза", "гипотеза измерима"], ["2", "данные и разбиение", "нет утечки"], ["3", "метрика и вывод", "указаны ограничения"]]}
        graph = {"type": "bar", "x_label": "группа", "y_label": "среднее значение", "series": [{"name": "среднее", "values": [11, 9]}]}
        code = "# Минимальный исследовательский отчёт\ngroup_a = [10, 12, 11]\ngroup_b = [8, 9, 10]\nmean = lambda values: sum(values) / len(values)\nprint(round(mean(group_a) - mean(group_b), 2))"
    elif "случайн" in value:
        intuition = "Случайная величина переводит исход эксперимента в число, поэтому можно обсуждать не один результат, а распределение и его типичные отклонения."
        formal = "Случайная величина X имеет распределение вероятностей. Математическое ожидание E[X] задаёт центр, а дисперсия Var(X)=E[(X−E[X])²] измеряет разброс вокруг него."
        manual = "Для честной кости X∈{1,…,6} все исходы имеют вероятность 1/6. Среднее E[X]=3,5. Сравните его с наблюдаемой серией 1, 6, 2 и объясните, почему трёх бросков мало для вывода."
        formulas = ["E[X] = Σ x · P(X=x)", "Var(X) = E[(X − E[X])²]"]
        table = {"columns": ["Исход x", "P(X=x)", "x·P(X=x)"], "rows": [["1", "1/6", "0,167"], ["3", "1/6", "0,500"], ["6", "1/6", "1,000"]]}
        graph = {"type": "bar", "x_label": "исход x", "y_label": "вероятность", "series": [{"name": "честная кость", "values": [0.167, 0.167, 0.167, 0.167, 0.167, 0.167]}]}
        code = "# Распределение честной кости\noutcomes = range(1, 7)\nmean = sum(outcomes) / len(tuple(outcomes))\nprint(mean)"
    elif "производн" in value or "градиент" in value or "оптимиз" in value or "потер" in value:
        intuition = "Производная показывает локальный наклон, а градиент говорит, в какую сторону изменить параметр, чтобы уменьшить ошибку. Один числовой шаг связывает формулу с поведением модели."
        formal = "Для L(w)=w² производная dL/dw=2w. Обновление w ← w − η·dL/dw уменьшает L при подходящей скорости η и может перескочить минимум при слишком большом шаге."
        manual = "Возьмите w=3 и η=0,1. Градиент равен 6, новый вес 2,4, а потеря меняется с 9 до 5,76. Повторите шаг и сравните скорость уменьшения."
        formulas = ["L(w) = w²", "w ← w − η · ∂L/∂w"]
        table = {"columns": ["Шаг", "w", "L(w)", "градиент"], "rows": [["0", "3,00", "9,00", "6,00"], ["1", "2,40", "5,76", "4,80"], ["2", "1,92", "3,69", "3,84"]]}
        graph = {"type": "line", "x_label": "шаг", "y_label": "потеря", "series": [{"name": "L(w)", "values": [9, 5.76, 3.69, 2.36]}]}
        code = "w = 3.0\nfor _ in range(3):\n    gradient = 2 * w\n    w -= 0.1 * gradient\n    print(round(w, 2), round(w * w, 2))"
    elif "коллекц" in value or "типы данных" in value:
        intuition = "Тип данных определяет, какие операции безопасны и как значение проходит через программу. Коллекция объединяет несколько значений, но порядок, индексы и ключи нужно проверять явно."
        formal = "Число, вещественное значение, строка, список и словарь имеют разные операции и правила доступа. Для списка a[i] индекс выбирает элемент, а для словаря d[key] ключ выбирает значение."
        manual = "Разберите values = [10, 20, 30] и record = {'city': 'Москва', 'rooms': 2}. Получите values[1] = 20 и record['rooms'] = 2, затем объясните, почему values['rooms'] недопустимо."
        formulas = ["list[i] → элемент по индексу", "dict[key] → значение по ключу"]
        table = {"columns": ["Значение", "Тип", "Доступ", "Результат"], "rows": [["3", "int", "3 + 2", "5"], ["[10,20,30]", "list", "[1]", "20"], ["rooms:2", "dict", "['rooms']", "2"]]}
        graph = {"type": "flow", "nodes": ["значение", "тип", "операция", "результат"], "edges": [["значение", "тип"], ["тип", "операция"], ["операция", "результат"]]}
        code = "values = [10, 20, 30]\nrecord = {'city': 'Москва', 'rooms': 2}\nprint(values[1], record['rooms'])"
    elif "перемен" in value or "тип" in value:
        intuition = "Переменная связывает имя со значением, а тип задаёт допустимые операции. Это первый слой воспроизводимости для признаков и результатов модели."
        formal = "Присваивание x = v создаёт связывание имени x со значением v. Тип значения определяет операции, а выражение вычисляется до присваивания результата."
        manual = "Создайте price = 1200, discount = 0,15 и вычислите net = price · (1 − discount) = 1020. Измените скидку и объясните, какое связывание обновилось."
        formulas = ["net = price · (1 − discount)", "type(value) определяет допустимые операции"]
        table = {"columns": ["Имя", "Значение", "Тип", "Операция"], "rows": [["price", "1200", "int", "умножение"], ["discount", "0,15", "float", "вычитание"], ["net", "1020", "float", "результат"]]}
        graph = {"type": "line", "x_label": "скидка", "y_label": "цена", "series": [{"name": "net", "values": [1200, 1140, 1080, 1020]}]}
        code = "price = 1200\ndiscount = 0.15\nnet = price * (1 - discount)\nprint(net)"
    elif "вероят" in value:
        intuition = "Вероятность описывает неопределённость числом от 0 до 1. Условная вероятность уточняет оценку после того, как стало известно событие B, поэтому порядок вопроса и доступная информация имеют значение."
        formal = "Для событий A и B при P(B)>0 условная вероятность равна P(A|B)=P(A∩B)/P(B). Независимость означает P(A|B)=P(A), а не просто отсутствие связи в одном наблюдении."
        manual = "Из 100 заявок 20 относятся к сегменту B, а 5 одновременно имеют событие A. Тогда P(A|B)=5/20=0,25. Сравните с P(A)=5/100=0,05 и объясните разницу знаменателей."
        formulas = ["P(A|B) = P(A∩B) / P(B)", "P(A) = число исходов A / число всех исходов"]
        table = {"columns": ["Событие", "Количество", "Вероятность"], "rows": [["B", "20", "0,20"], ["A∩B", "5", "0,05"], ["A|B", "5 из 20", "0,25"]]}
        graph = {"type": "bar", "x_label": "событие", "y_label": "вероятность", "series": [{"name": "оценка", "values": [0.05, 0.2, 0.25]}]}
        code = "# Условная вероятность\na_and_b = 5\nb = 20\nprint(a_and_b / b)"
    elif "услов" in value or "цик" in value or "функц" in value:
        intuition = "Условие выбирает ветку, цикл повторяет шаг, а функция собирает повторяемое правило с входами и выходом. Вместе они превращают расчёт в проверяемый алгоритм."
        formal = "Функция f принимает аргументы и возвращает результат. Ветвление выбирает путь по булеву условию, а цикл применяет тело к последовательности до выполнения условия остановки."
        manual = "Для списка [2, 5, 8] оставьте только значения больше 4, затем примените функцию square(x)=x². Получите [25, 64] и проверьте длину результата."
        formulas = ["f(x) = x²", "если условие, то ветка A, иначе ветка B"]
        table = {"columns": ["Вход", "Условие", "Действие", "Выход"], "rows": [["2", "2 > 4 — нет", "пропустить", "—"], ["5", "5 > 4 — да", "возвести в квадрат", "25"], ["8", "8 > 4 — да", "возвести в квадрат", "64"]]}
        graph = {"type": "flow", "nodes": ["вход", "условие", "функция", "выход"], "edges": [["вход", "условие"], ["условие", "функция"], ["функция", "выход"]]}
        code = "values = [2, 5, 8]\nresult = [x * x for x in values if x > 4]\nprint(result)"
    elif "numpy" in value or "вектор" in value or "матриц" in value:
        intuition = "Массив хранит много чисел с одной формой. Вектор и матрица позволяют выполнить одну операцию сразу над признаками, если размерности согласованы."
        formal = "Вектор x имеет форму (n,), матрица A — форму (m,n). Произведение Ax определено, когда внутренняя размерность совпадает, а результат имеет форму (m,)."
        manual = "Умножьте A=[[1,2],[3,4]] на x=[10,20]. Получите [50,110], затем измените форму x и объясните, почему операция перестала быть допустимой."
        formulas = ["A ∈ Rᵐˣⁿ, x ∈ Rⁿ, Ax ∈ Rᵐ", "shape(Ax) = (m,)"]
        table = {"columns": ["Объект", "Форма", "Пример", "Результат"], "rows": [["x", "(2,)", "[10,20]", "вектор"], ["A", "(2,2)", "[[1,2],[3,4]]", "матрица"], ["Ax", "(2,)", "[50,110]", "произведение"]]}
        graph = {"type": "flow", "nodes": ["вектор x", "матрица A", "произведение Ax"], "edges": [["вектор x", "произведение Ax"], ["матрица A", "произведение Ax"]]}
        code = "import numpy as np\nA = np.array([[1, 2], [3, 4]])\nx = np.array([10, 20])\nprint(A @ x)"
    elif "данн" in value or "pandas" in value or "пропуск" in value or "категор" in value or "разбиен" in value:
        intuition = "Качество модели начинается с таблицы. Пропуски, категории и границы выборок нужно увидеть до обучения, иначе модель получит скрытую подсказку или неверный тип признака."
        formal = "Разделите преобразование данных и обучение модели в конвейере. Статистики imputer и encoder оцениваются только на train, затем применяются к validation и test без повторного подглядывания."
        manual = "В таблице из трёх строк найдите пропуск, категорию и значение, вычисленное после момента теста. Исправьте пропуск медианой, закодируйте категорию и удалите утечку."
        formulas = ["X_train, X_valid, X_test = split(X)", "fit(transformer, X_train) → transform(X_valid)"]
        table = {"columns": ["Строка", "До обработки", "Операция", "После проверки"], "rows": [["1", "12,4", "без изменений", "12,4"], ["2", "—", "медиана train", "12,4"], ["3", "город=Москва", "кодирование", "1,0"]]}
        graph = {"type": "flow", "nodes": ["таблица", "очистка", "разбиение", "модель"], "edges": [["таблица", "очистка"], ["очистка", "разбиение"], ["разбиение", "модель"]]}
        code = "rows = [{'city': 'Москва', 'value': 12.4}, {'city': 'СПб', 'value': None}]\nmedian = 12.4\nprint(median)"
    else:
        intuition = f"Тема «{title}» связывает численный пример, формальное правило и проверяемый результат. Начните с малого входа, измените один параметр и объясните разницу."
        formal = f"Для темы «{title}» явно задайте вход, преобразование и результат. Проверьте размерности, допущения и ограничение метода до перехода к лаборатории."
        manual = f"Разберите тему «{title}» на трёх небольших значениях и запишите каждый промежуточный шаг. Сравните результат с независимой проверкой."
        formulas = ["результат = f(вход)", "ошибка = цель − предсказание"]
        table = {"columns": ["Шаг", "Вход", "Операция", "Результат"], "rows": [["1", "A", "применить правило", "1"], ["2", "B", "проверить ограничение", "2"], ["3", "C", "сравнить с целью", "вывод"]]}
        graph = {"type": "line", "x_label": "шаг", "y_label": "значение", "series": [{"name": "пример", "values": [1, 2, 3]}]}
        code = f"# {title}\nvalues = [1, 2, 3]\nprint(values)"
    return {"intuition": intuition, "formal": formal, "manual": manual, "formulas": formulas, "table": table, "graph": graph, "code": code}


for lesson_id, lesson in program_by_id.items():
    if lesson_id not in content_by_id or lesson_id == "1.01" or int(lesson_id.split(".", 1)[0]) > 5:
        continue
    item = content_by_id[lesson_id]
    current = profile(lesson)
    item.update({
        "title": lesson["title"],
        "why_it_matters": f"Тема «{lesson['title']}» нужна, чтобы связать понятие с проверяемым расчётом и применить его в задаче ML/AI.",
        "prerequisites": [normalize(value) for value in lesson.get("prerequisite_ids", [])],
        "learning_objectives": lesson.get("objectives", []),
        "what_is_known": [f"Перед этим уроком нужно понимать тему «{content_by_id.get(normalize(lesson.get('prerequisite_ids', [''])[0]), {}).get('title', 'предыдущий урок')}»." if lesson.get("prerequisite_ids") else "Умеете читать числа и проверять небольшой пример."],
        "intuition": current["intuition"],
        "formal_explanation": current["formal"],
        "manual_example": current["manual"],
        "formulas": current["formulas"],
        "table": current["table"],
        "visualization": {"type": current["graph"]["type"], "fallback": f"Схема темы «{lesson['title']}».", "alt": f"Визуализация темы «{lesson['title']}».", "graph": current["graph"]},
        "code_example": current["code"],
        "interactive_lab": lab_for(lesson["title"]),
        "independent_exercise": lesson.get("exercise_id"),
        "mini_test": question_exact.get(str(lesson["id"]), question_by_id.get(lesson_id, item.get("mini_test"))),
        "misconceptions": ["Один пример не доказывает устойчивость метода.", "Проверка результата должна следовать из формулы и данных."],
        "summary": [f"Объясните тему «{lesson['title']}» через входы и результат.", "Проверьте формулу вручную.", "Свяжите наблюдение с лабораторией и ограничением метода."],
        "remediation": {"if_wrong": "Вернитесь к предыдущему уроку и повторите числовой пример.", "next_link": normalize(lesson.get("prerequisite_ids", [""])[-1]) if lesson.get("prerequisite_ids") else None},
    })

legacy_first_module_questions = {"1.01": "q-001", "1.02": "q-002", "1.03": "q-003", "1.04": "q-004"}
for lesson_id, question_id in legacy_first_module_questions.items():
    if lesson_id in content_by_id:
        content_by_id[lesson_id]["mini_test"] = question_id

(ROOT / "data/lesson_content.json").write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf8")

# Replace generated goal-recitation questions with checks that use each lesson's
# own formulas.  The old prompts tested whether a learner could repeat a
# template objective, so they could pass without understanding the material.
for question in questions:
    prompt = str(question.get("prompt", ""))
    if "Какая цель относится" not in prompt and "Какой признак покажет" not in prompt:
        continue
    lesson_id = normalize(question.get("lesson_id"))
    lesson = content_by_id.get(lesson_id)
    if not lesson:
        continue
    formulas = [str(value) for value in lesson.get("formulas", []) if str(value).strip()]
    if not formulas:
        continue
    title = lesson["title"]
    if "Какая цель относится" in prompt:
        answer = formulas[0]
        question["prompt"] = f"Какое правило используется в теме «{title}»?"
        question["options"] = [answer, "Изменять входы после проверки результата", "Игнорировать размерность и единицы измерения"]
        question["answer"] = answer
        question["solution"] = f"В уроке «{title}» разбирается правило «{answer}». Его нужно применить к числовому примеру и проверить результат."
        question["misconception_tags"] = ["формула-путают-с-выводом", f"lesson-{question.get('lesson_id')}"]
    else:
        answer = formulas[1] if len(formulas) > 1 else formulas[0]
        question["prompt"] = f"Какой расчёт нужно уметь повторить в теме «{title}»?"
        question["options"] = [answer, "Сделать вывод без данных и описания ограничений", "Выбрать самый сложный метод без проверки"]
        question["answer"] = answer
        question["solution"] = f"Проверка понимания темы «{title}» включает самостоятельное воспроизведение расчёта «{answer}» и сверку с исходными данными."
        question["misconception_tags"] = ["проверка-без-расчёта", f"lesson-{question.get('lesson_id')}"]

(ROOT / "data/questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
