const state = {
  view: localStorage.getItem('ailab:view') || 'dashboard',
  theme: localStorage.getItem('ailab:theme') || 'dark',
  fontSize: Number(localStorage.getItem('ailab:font-size') || 15),
  progress: Number(localStorage.getItem('ailab:progress') || 0),
  lessonId: localStorage.getItem('ailab:lesson') || '1.01',
  lessons: [],
  modules: [],
  selectedModuleId: localStorage.getItem('ailab:module') || '',
  lessonContent: new Map(),
  currentUser: null,
  lab: { step: 0, running: false, timer: null, w: -3 },
  selectedAnswer: null,
  selectedTerm: null,
  taskQuestion: null,
  exam: {attemptId: null, questions: []},
  tooltips: new Map()
};

let terms = [
  {ru:'Признак', en:'feature', symbol:'x', definition:'Измеряемое свойство объекта, которое модель использует для предсказания.', example:'Для цены квартиры признаками могут быть площадь, этаж и район.', related:['набор данных','целевая переменная'], lesson:'1.03'},
  {ru:'Функция потерь', en:'loss function', symbol:'L', definition:'Число, которое показывает, насколько предсказание модели отличается от правильного ответа.', example:'Среднеквадратичная ошибка усиливает влияние больших промахов.', related:['градиент','градиентный спуск'], lesson:'1.04'},
  {ru:'Градиентный спуск', en:'gradient descent', symbol:'∇', definition:'Итеративный способ менять параметры модели в сторону уменьшения функции потерь.', example:'Если градиент положительный, вес уменьшается на шаг, пропорциональный скорости обучения.', related:['скорость обучения','производная'], lesson:'1.04'},
  {ru:'Переобучение', en:'overfitting', symbol:'↗', definition:'Ситуация, когда модель хорошо запомнила обучающие данные, но плохо работает на новых примерах.', example:'Слишком глубокое дерево может идеально разделить тренировочную выборку и ошибаться на тестовой.', related:['регуляризация','разбиение'], lesson:'2.06'},
  {ru:'Признак утечки', en:'data leakage', symbol:'!', definition:'Информация из будущего или из тестовой выборки, которая случайно попала в обучение.', example:'Нельзя вычислять среднее по всем данным до разделения на выборки.', related:['воспроизводимость','тестовая выборка'], lesson:'1.08'},
  {ru:'Тензор', en:'tensor', symbol:'T', definition:'Многомерный массив чисел. В машинном обучении им удобно представлять таблицы, изображения и последовательности.', example:'Изображение RGB 28×28 можно хранить как тензор формы 3×28×28.', related:['форма','пакет'], lesson:'3.02'},
  {ru:'Векторное представление', en:'embedding', symbol:'↯', definition:'Плотный числовой вектор, который кодирует сходство объектов в геометрическом пространстве.', example:'Похожие по смыслу слова получают близкие векторы.', related:['поиск','токенизация'], lesson:'4.04'},
  {ru:'Механизм внимания', en:'attention', symbol:'◎', definition:'Способ взвесить элементы контекста, чтобы модель сосредоточилась на наиболее связанных частях.', example:'В предложении модель может усилить связь местоимения с существительным.', related:['Query, Key, Value','Transformer'], lesson:'4.02'},
  {ru:'Поиск с дополнением контекста', en:'Retrieval-Augmented Generation', acronym:'RAG', symbol:'⌁', definition:'Подход, в котором перед генерацией ответа модель получает найденные фрагменты документов.', example:'Учебный помощник сначала находит нужный урок, затем цитирует его в ответе.', related:['разбиение документов','цитирование'], lesson:'4.08'},
  {ru:'Дообучение', en:'fine-tuning', symbol:'✦', definition:'Дополнительное обучение исходной модели на примерах нужного поведения или предметной области.', example:'Модель можно дообучить отвечать в формате карточки ошибки.', related:['LoRA','качество выборки'], lesson:'4.06'}
];

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[character]));

function persist() {
  localStorage.setItem('ailab:view', state.view);
  localStorage.setItem('ailab:theme', state.theme);
  localStorage.setItem('ailab:font-size', String(state.fontSize));
  localStorage.setItem('ailab:progress', String(state.progress));
  localStorage.setItem('ailab:lesson', state.lessonId);
  localStorage.setItem('ailab:module', state.selectedModuleId);
}

function renderProgress() {
  const progress = Math.max(0, Math.min(100, Math.round(state.progress)));
  const ring = $('#progress-ring');
  const percent = $('#progress-percent');
  const count = $('#progress-count');
  if (ring) {
    ring.style.setProperty('--progress', `${progress}%`);
    ring.setAttribute('aria-label', `${progress} процентов курса`);
  }
  if (percent) percent.textContent = String(progress);
  if (count) count.textContent = `${Math.round(progress * 36 / 100)} из 36`;
  renderPathState();
}

function renderPathState() {
  const completed = Math.round(Math.max(0, Math.min(100, state.progress)) * 36 / 100);
  const pathProgress = $('#path-progress');
  const pathModule = $('#path-module');
  if (pathProgress) pathProgress.textContent = `${completed} / 36`;
  if (pathModule) pathModule.textContent = String(Math.min(9, Math.floor(completed / 4) + 1)).padStart(2, '0');
  renderPathGraph();
  const graphNodes = $$('.graph-node[data-lesson-id]');
  if (!graphNodes.length) return;
  const activeLessonIndex = Math.max(0, state.lessons.findIndex((lesson) => lesson.id === state.lessonId));
  graphNodes.forEach((node) => {
    const lessonIndex = state.lessons.findIndex((lesson) => lesson.id === normalizeLessonId(node.dataset.lessonId));
    const completedNode = Boolean(state.currentUser) && lessonIndex >= 0 && lessonIndex < completed;
    const currentNode = lessonIndex === activeLessonIndex;
    node.classList.toggle('complete', completedNode);
    node.classList.toggle('current', currentNode);
    node.classList.toggle('locked', !completedNode && !currentNode);
    const status = node.querySelector('small');
    if (status) status.textContent = completedNode ? 'освоено' : currentNode ? 'сейчас' : 'доступно после проверки';
  });
}

function renderPathGraph() {
  const tabs = $('#path-module-tabs');
  const canvas = $('#graph-canvas');
  if (!tabs || !canvas || !state.lessons.length) return;
  const modules = state.modules.length ? state.modules : [...new Map(state.lessons.map((lesson) => [lesson.module_id || `m-${lesson.id.split('.')[0]}`, {id: lesson.module_id || `m-${lesson.id.split('.')[0]}`, title: lesson.stage || 'Модуль'}])).values()];
  const activeLesson = currentLesson();
  const selectedId = state.selectedModuleId && modules.some((module) => module.id === state.selectedModuleId) ? state.selectedModuleId : activeLesson?.module_id || modules[0]?.id;
  state.selectedModuleId = selectedId || '';
  tabs.innerHTML = modules.map((module, index) => `<button class="path-module-tab ${module.id === selectedId ? 'active' : ''}" role="tab" aria-selected="${module.id === selectedId}" data-action="select-module" data-module-id="${escapeHtml(module.id)}">${String(index + 1).padStart(2, '0')} · ${escapeHtml(module.title || module.stage || 'Модуль')}</button>`).join('');
  const module = modules.find((item) => item.id === selectedId) || modules[0];
  const moduleLessons = state.lessons.filter((lesson) => (lesson.module_id || `m-${lesson.id.split('.')[0]}`) === module.id);
  $('#path-module-title').textContent = `${module.title || module.stage || 'Модуль'} · ${moduleLessons.length} урока`;
  $('#path-module-description').textContent = module.description || module.focus || 'Уроки модуля связаны prerequisite-переходами.';
  const positions = moduleLessons.map((_, index) => [120 + index * 240, 200]);
  const lines = moduleLessons.slice(1).map((_, index) => `<path d="M${positions[index][0]} 200 L${positions[index + 1][0]} 200"/>`).join('');
  const nodes = moduleLessons.map((lesson, index) => {
    const lessonIndex = state.lessons.findIndex((item) => item.id === lesson.id);
    const completed = Boolean(state.currentUser) && lessonIndex >= 0 && lessonIndex < Math.round(state.progress * 36 / 100);
    const current = lesson.id === state.lessonId;
    const className = completed ? 'complete' : current ? 'current' : 'locked';
    const content = state.lessonContent.get(lesson.id) || {};
    const title = content.title || lesson.title || lesson.id;
    return `<div class="graph-node ${className}" role="button" tabindex="0" data-action="open-lesson" data-lesson-id="${escapeHtml(lesson.id)}" aria-label="Открыть урок ${escapeHtml(lesson.id)}" style="left:${(positions[index][0] / 9.6)}%;top:50%"><span>${String(index + 1).padStart(2, '0')}</span><strong>${escapeHtml(title)}</strong><small>${completed ? 'освоено' : current ? 'сейчас' : 'доступно после проверки'}</small></div>`;
  }).join('');
  canvas.innerHTML = `<svg class="graph-lines" viewBox="0 0 960 400" preserveAspectRatio="none" aria-hidden="true">${lines}</svg>${nodes}`;
  persist();
}

function applyRoleVisibility() {
  const role = state.currentUser?.role || '';
  $$('[data-roles]').forEach((element) => {
    const roles = element.dataset.roles.split(',').map((item) => item.trim());
    element.hidden = !role || !roles.includes(role);
  });
  $$('[data-authenticated-only]').forEach((element) => { element.hidden = !state.currentUser; });
  $$('[data-progress-only]').forEach((element) => { element.hidden = !state.currentUser || state.progress <= 0; });
  $$('[data-zero-progress]').forEach((element) => { element.hidden = state.progress > 0; });
  $$('[data-guest-only]').forEach((element) => { element.hidden = Boolean(state.currentUser); });
}

function renderDashboardDate() {
  const target = $('#dashboard-date');
  if (!target) return;
  target.textContent = new Intl.DateTimeFormat('ru-RU', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'}).format(new Date()).toUpperCase();
}

function applyUserState(user) {
  state.currentUser = user || null;
  if (!user && (state.view === 'mentor' || state.view === 'admin')) setView('dashboard');
  const name = user?.display_name || 'участник';
  const initials = user ? name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase() : 'AI';
  $('#workspace-name').textContent = user?.display_name || 'Демо-профиль';
  $('#workspace-avatar').textContent = initials;
  $('#top-avatar').textContent = initials;
  $('#dashboard-name').textContent = user ? name.split(/\s+/)[0] : 'участник';
  $('#workspace-track').textContent = user ? `Роль · ${user.role}` : 'Локальная траектория';
  applyRoleVisibility();
  renderDashboardLesson();
}

function renderDashboardLesson() {
  const lesson = currentLesson();
  if (!lesson) return;
  const content = state.lessonContent.get(lesson.id) || {};
  const title = content.title || lesson.title || 'Первый урок';
  const number = String(lesson.id || '1.01').split('.')[1] || '01';
  const moduleNumber = String(lesson.id || '1.01').split('.')[0] || '1';
  $('#dashboard-lesson-status').textContent = `УРОК ${lesson.id}`;
  $('#dashboard-lesson-number').textContent = number.padStart(2, '0');
  $('#dashboard-lesson-module').textContent = `МОДУЛЬ ${moduleNumber.padStart(2, '0')} · ${lesson.stage || 'ОСНОВЫ'}`;
  $('#dashboard-lesson-title').textContent = title;
  $('#dashboard-lesson-description').textContent = content.why_it_matters || lesson.description || 'Начните с первого урока курса и двигайтесь по prerequisite-графу.';
  $('#dashboard-lesson-meta').textContent = `◷ ${content.duration_minutes || lesson.duration_minutes || 35} мин · ◌ Лекция и практика`;
}

function showToast(message, type = 'info') {
  const region = $('.toast-region');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  region.append(toast);
  setTimeout(() => toast.remove(), 3600);
}

function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  $$('.segmented button').forEach((button) => button.classList.toggle('selected', button.dataset.themeChoice === state.theme));
  persist();
}

function applyTypography() {
  const size = Math.max(14, Math.min(19, Number(state.fontSize) || 15));
  state.fontSize = size;
  document.documentElement.style.setProperty('--base-font-size', `${size}px`);
  const input = $('#font-size');
  const output = $('#font-size-output');
  if (input) input.value = String(size);
  if (output) output.textContent = `${size} px`;
  persist();
}

function setView(view) {
  if (view === 'mentor' && !['mentor', 'instructor', 'admin'].includes(state.currentUser?.role)) view = 'dashboard';
  if (view === 'admin' && state.currentUser?.role !== 'admin') view = 'dashboard';
  const target = $(`#view-${view}`);
  if (!target) return;
  state.view = view;
  $$('.view').forEach((section) => section.classList.toggle('active', section === target));
  $$('.nav-item').forEach((button) => button.classList.toggle('active', button.dataset.view === view));
  const nav = $(`.nav-item[data-view="${view}"]`);
  $('#breadcrumb-current').textContent = nav ? nav.textContent.trim() : view;
  persist();
  if (view === 'dashboard') renderDashboardLesson();
  if (view === 'lab') requestAnimationFrame(drawLab);
  if (view === 'alumni') loadAlumni($('#alumni-search')?.value || '');
  if (view === 'mentor') loadMentorDashboard();
  if (view === 'admin') loadAdminDashboard();
  if (view === 'exam') loadExams();
  if (view === 'tasks') loadTaskForCurrentLesson();
  window.scrollTo({top: 0, behavior: document.documentElement.classList.contains('reduced-motion') ? 'auto' : 'smooth'});
}

const fallbackLessons = [
  {id:'1.01', title:'Переменные и выражения'},
  {id:'1.02', title:'Типы данных и преобразования'},
  {id:'1.03', title:'Функции и параметры'},
  {id:'1.04', title:'Функция потерь и градиентный спуск'},
  {id:'1.05', title:'Циклы и условия'},
  {id:'1.06', title:'Коллекции и обработка данных'},
  {id:'1.07', title:'Таблицы, признаки и выборки'},
  {id:'1.08', title:'Разбиение данных и качество'},
];

function currentLesson() {
  return state.lessons.find((lesson) => lesson.id === state.lessonId) || state.lessons[0] || fallbackLessons[0];
}

function normalizeLessonId(value) {
  return String(value || '').replace(/^0(?=\d\.)/, '');
}

function renderLesson() {
  const lesson = currentLesson();
  if (!lesson) return;
  state.lessonId = lesson.id;
  const content = state.lessonContent.get(lesson.id) || {};
  const title = content.title || lesson.title;
  const index = Math.max(0, state.lessons.findIndex((item) => item.id === lesson.id));
  const previous = state.lessons[index - 1];
  const next = state.lessons[index + 1];
  $('#lab-title').textContent = title;
  $('#lab-lesson-kicker').textContent = `УРОК ${lesson.id} · ${lesson.lab || 'ПРАКТИКА'}`;
  $('#lab-lesson-lead').textContent = content.why_it_matters || lesson.objectives?.join(' · ') || 'Разберите тему на примере и закрепите её практикой.';
  $('#lesson-navigation-title').textContent = title;
  $('#lesson-navigation-position').textContent = `${index + 1} из ${state.lessons.length}`;
  const previousButton = $('#lesson-prev');
  const nextButton = $('#lesson-next');
  previousButton.disabled = !previous;
  nextButton.disabled = !next;
  previousButton.setAttribute('aria-disabled', String(!previous));
  nextButton.setAttribute('aria-disabled', String(!next));
  const list = (items, fallback) => (items?.length ? items : fallback).map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  const known = content.what_is_known || [];
  const objectives = content.learning_objectives || lesson.objectives || ['Понять основную идею темы', 'Применить её в практике'];
  const misconceptions = content.misconceptions || [];
  const summary = content.summary || ['Разберите пример', 'Проверьте себя', 'Сделайте практическое упражнение'];
  const visualization = content.visualization?.fallback || 'Схема и маленький численный пример помогают связать формулу с наблюдаемым поведением.';
  const remediation = content.remediation?.if_wrong || 'Вернитесь к prerequisite и повторите ручной пример.';
  $('#lesson-content').innerHTML = `<div class="lesson-content-header"><div><span class="panel-kicker">ЛЕКЦИЯ · УРОК ${escapeHtml(lesson.id)}</span><h2>${escapeHtml(title)}</h2></div><span class="lesson-duration">${content.duration_minutes || lesson.duration_minutes || '—'} мин</span></div><div class="lesson-content-actions"><button class="button button-primary" data-action="lesson-lab">Открыть лабораторию ↓</button><button class="button button-ghost" data-action="lesson-tasks">Перейти к проверке →</button></div><div class="lesson-lecture-grid"><div><h3>Что уже известно</h3><ul>${list(known, ['Базовые понятия предыдущих уроков'])}</ul><h3>Цели урока</h3><ul>${list(objectives, ['Понять основную идею темы', 'Применить её в практике'])}</ul><h3>Интуиция</h3><p>${escapeHtml(content.intuition || 'Сначала сформулируйте идею своими словами, затем проверьте её на маленьком примере.')}</p><h3>Визуализация</h3><p>${escapeHtml(visualization)}</p><h3>Формальное объяснение</h3><p>${escapeHtml(content.formal_explanation || 'Свяжите обозначения, входы, выходы и ограничение метода.')}</p></div><div><h3>Почему это важно</h3><p>${escapeHtml(content.why_it_matters || 'Эта тема связывает фундаментальные понятия с рабочими ML/AI-сценариями.')}</p><h3>Ручной пример</h3><p>${escapeHtml(content.manual_example || 'Решите небольшой пример вручную и проверьте численный результат.')}</p><h3>Типичные заблуждения</h3><ul>${list(misconceptions, ['Не подменяйте интуицию формальным условием.', 'Проверяйте результат на новых данных.'])}</ul><h3>Мини-тест</h3><p>Идентификатор проверки <strong>${escapeHtml(content.mini_test || lesson.assessment || 'после лекции')}</strong>. После ответа разберите причину ошибки.</p><h3>Если ответ неверен</h3><p>${escapeHtml(remediation)}</p><h3>Короткое резюме</h3><ul>${list(summary, ['Повторите ключевую идею', 'Сделайте практическое упражнение'])}</ul></div></div>${content.code_example ? `<details class="lesson-code"><summary>Пример кода</summary><pre><code>${escapeHtml(content.code_example)}</code></pre></details>` : ''}<div class="lesson-content-footer"><span>Лаборатория <strong>${escapeHtml(content.interactive_lab || lesson.lab || 'практика')}</strong></span><span>Упражнение <strong>${escapeHtml(content.independent_exercise || lesson.exercise_id || 'практика')}</strong></span><button class="text-button" data-action="lesson-exam">Открыть экзамен →</button></div>`;
  persist();
  renderPathState();
  renderInteractiveLab(content, lesson);
}

function labKind(content, lesson) {
  const value = content.interactive_lab || '';
  if (value) return value;
  const title = `${lesson.title || ''} ${lesson.description || ''}`.toLowerCase();
  if (title.includes('граф') || title.includes('функц')) return 'function-plot';
  if (title.includes('врем')) return 'time-series-split';
  if (title.includes('граф')) return 'graph-playground';
  return 'guided-practice';
}

function renderInteractiveLab(content, lesson) {
  const layout = $('#lab-layout');
  const generic = $('#lab-generic');
  if (!layout || !generic) return;
  const kind = labKind(content, lesson);
  if (kind === 'gradient-descent') {
    layout.hidden = false;
    generic.hidden = true;
    return;
  }
  layout.hidden = true;
  generic.hidden = false;
  generic.dataset.labKind = kind;
  const title = content.title || lesson.title || 'Практическая лаборатория';
  const description = content.why_it_matters || lesson.description || 'Проверьте идею на небольшом интерактивном примере.';
  const visual = {
    'variable-playground': '<table><thead><tr><th>Имя</th><th>Значение</th><th>Тип</th></tr></thead><tbody><tr><td>x</td><td id="generic-x-value">3</td><td>int</td></tr><tr><td>name</td><td>AI Lab</td><td>str</td></tr><tr><td>enabled</td><td>True</td><td>bool</td></tr></tbody></table>',
    'data-cleaning': '<table><thead><tr><th>row</th><th>value</th><th>status</th></tr></thead><tbody><tr><td>1</td><td>12.4</td><td>ok</td></tr><tr><td>2</td><td>—</td><td>missing</td></tr><tr><td>3</td><td>999.0</td><td>outlier</td></tr></tbody></table>',
    'tensor-shapes': '<svg viewBox="0 0 520 220" role="img" aria-label="Схема формы тензора"><rect x="60" y="45" width="150" height="110" rx="12" fill="rgba(125,211,252,.16)" stroke="#7dd3fc"/><rect x="250" y="72" width="150" height="56" rx="12" fill="rgba(167,139,250,.16)" stroke="#a78bfa"/><path d="M210 100h40" stroke="#67e8a5" stroke-width="4"/><text x="88" y="105" fill="currentColor">batch × channels × H × W</text><text x="277" y="105" fill="currentColor">2 × 3 × 28 × 28</text></svg>',
    'graph-playground': '<svg viewBox="0 0 520 220" role="img" aria-label="Граф с узлами и рёбрами"><path d="M110 110 L250 55 L400 115 L250 170 Z M110 110 L400 115" stroke="#7dd3fc" stroke-width="3" fill="none"/><circle cx="110" cy="110" r="24" fill="#17263c" stroke="#7dd3fc" stroke-width="3"/><circle cx="250" cy="55" r="24" fill="#17263c" stroke="#a78bfa" stroke-width="3"/><circle cx="400" cy="115" r="24" fill="#17263c" stroke="#67e8a5" stroke-width="3"/><circle cx="250" cy="170" r="24" fill="#17263c" stroke="#f4bf67" stroke-width="3"/><text x="103" y="116" fill="currentColor">A</text><text x="243" y="61" fill="currentColor">B</text><text x="393" y="121" fill="currentColor">C</text><text x="243" y="176" fill="currentColor">D</text></svg>',
    'rnn-flow': '<svg viewBox="0 0 520 220" role="img" aria-label="Последовательность RNN"><path d="M70 110 H450" stroke="#7dd3fc" stroke-width="4"/><path d="M125 100 l12 10 -12 10 M225 100 l12 10 -12 10 M325 100 l12 10 -12 10" fill="none" stroke="#7dd3fc" stroke-width="3"/><rect x="45" y="72" width="55" height="76" rx="10" fill="#17263c" stroke="#7dd3fc"/><rect x="145" y="72" width="55" height="76" rx="10" fill="#17263c" stroke="#a78bfa"/><rect x="245" y="72" width="55" height="76" rx="10" fill="#17263c" stroke="#67e8a5"/><rect x="345" y="72" width="55" height="76" rx="10" fill="#17263c" stroke="#f4bf67"/><text x="61" y="115" fill="currentColor">x₁</text><text x="161" y="115" fill="currentColor">x₂</text><text x="261" y="115" fill="currentColor">x₃</text><text x="361" y="115" fill="currentColor">x₄</text></svg>',
  }[kind] || '<svg viewBox="0 0 520 220" role="img" aria-label="Схема эксперимента"><path d="M40 170 C110 80 175 155 245 70 S370 140 480 45" fill="none" stroke="#7dd3fc" stroke-width="4"/><circle cx="245" cy="70" r="8" fill="#67e8a5"/><path d="M40 180 H480" stroke="rgba(148,163,184,.4)"/></svg>';
  const controls = {
    'variable-playground': '<label class="generic-control">Измените x<input type="range" min="0" max="10" value="3" data-lab-input="x"><output data-lab-output="x">3</output></label><div class="generic-result" data-lab-result>Вычисление: x + 1 = 4</div>',
    'data-cleaning': '<label class="generic-control">Стратегия пропусков<select data-lab-input="missing"><option value="median">Заполнить медианой</option><option value="drop">Удалить строку</option></select></label><label class="generic-control">Обработать выброс<input type="checkbox" checked data-lab-input="outlier"></label><div class="generic-result" data-lab-result>После очистки: 3 строки, 0 пропусков, 0 выбросов</div>',
    'tensor-shapes': '<label class="generic-control">Размер batch<input type="number" min="1" max="128" value="2" data-lab-input="batch"></label><label class="generic-control">Каналы<input type="number" min="1" max="8" value="3" data-lab-input="channels"></label><div class="generic-result" data-lab-result>Форма [2, 3, 28, 28] · 4704 чисел</div>',
    'metric-choice': '<label class="generic-control">Порог классификации<input type="range" min="0" max="100" value="50" data-lab-input="threshold"><output data-lab-output="threshold">0.50</output></label><div class="generic-result" data-lab-result>Precision 0.78 · Recall 0.71 · F1 0.74</div>',
    'hardware-selector': '<label class="generic-control">Размер модели, млрд параметров<input type="range" min="1" max="70" value="7" data-lab-input="params"><output data-lab-output="params">7B</output></label><label class="generic-control">Квантизация<select data-lab-input="quant"><option value="16">FP16</option><option value="8">INT8</option><option value="4">INT4</option></select></label><div class="generic-result" data-lab-result>Оценка VRAM: 14 GB · подходит GPU 16 GB</div>',
    'memory-budget': '<label class="generic-control">Контекст, токенов<input type="range" min="1024" max="32768" step="1024" value="8192" data-lab-input="context"><output data-lab-output="context">8192</output></label><div class="generic-result" data-lab-result>Память KV-cache: 1.2 GB · запас: 4.8 GB</div>',
  }[kind] || '<label class="generic-control">Интенсивность опыта<input type="range" min="0" max="100" value="50" data-lab-input="intensity"><output data-lab-output="intensity">50</output></label><button class="button button-primary" data-action="generic-lab-run">Запустить опыт</button><div class="generic-result" data-lab-result>Готово к запуску. Измените параметр и проверьте гипотезу.</div>';
  generic.innerHTML = `<div class="generic-lab-header"><div><span class="generic-lab-kind">ИНТЕРАКТИВНАЯ ЛАБОРАТОРИЯ · ${escapeHtml(kind)}</span><h2>${escapeHtml(title)}</h2><p>${escapeHtml(description)}</p></div><button class="button button-primary" data-action="generic-lab-run">Запустить опыт</button></div><div class="generic-lab-body"><div class="generic-visual">${visual}</div><div class="generic-controls">${controls}</div></div><div class="generic-lab-footer"><span>Связанные понятия: ${(content.learning_objectives || lesson.objectives || []).slice(0, 3).map(escapeHtml).join(' · ')}</span><span>Проверка после опыта — кнопка «Перейти к проверке» выше</span></div>`;
  updateGenericLab();
}

function updateGenericLab() {
  const generic = $('#lab-generic');
  if (!generic || generic.hidden) return;
  const kind = generic.dataset.labKind;
  const value = (name, fallback) => generic.querySelector(`[data-lab-input="${name}"]`)?.value ?? fallback;
  const result = generic.querySelector('[data-lab-result]');
  if (kind === 'variable-playground') {
    const x = Number(value('x', 3));
    generic.querySelector('[data-lab-output="x"]').textContent = String(x);
    result.textContent = `Вычисление: x + 1 = ${x + 1}`;
  } else if (kind === 'tensor-shapes') {
    const batch = Number(value('batch', 2));
    const channels = Number(value('channels', 3));
    result.textContent = `Форма [${batch}, ${channels}, 28, 28] · ${batch * channels * 28 * 28} чисел`;
  } else if (kind === 'metric-choice') {
    const threshold = Number(value('threshold', 50));
    generic.querySelector('[data-lab-output="threshold"]').textContent = (threshold / 100).toFixed(2);
    const precision = (0.58 + threshold / 250).toFixed(2);
    const recall = (0.95 - threshold / 250).toFixed(2);
    const f1 = (2 * precision * recall / (Number(precision) + Number(recall))).toFixed(2);
    result.textContent = `Precision ${precision} · Recall ${recall} · F1 ${f1}`;
  } else if (kind === 'hardware-selector') {
    const params = Number(value('params', 7));
    const quant = Number(value('quant', 16));
    const vram = (params * quant / 8).toFixed(1);
    generic.querySelector('[data-lab-output="params"]').textContent = `${params}B`;
    result.textContent = `Оценка VRAM: ${vram} GB · ${vram <= 16 ? 'подходит GPU 16 GB' : 'нужен GPU с большей памятью'}`;
  } else if (kind === 'memory-budget') {
    const context = Number(value('context', 8192));
    generic.querySelector('[data-lab-output="context"]').textContent = String(context);
    result.textContent = `Память KV-cache: ${(context / 6800).toFixed(1)} GB · запас ${(8 - context / 6800).toFixed(1)} GB`;
  } else if (kind === 'data-cleaning') {
    const missing = value('missing', 'median');
    const outlier = generic.querySelector('[data-lab-input="outlier"]')?.checked;
    result.textContent = `После очистки: ${missing === 'drop' ? 2 : 3} строки, 0 пропусков, ${outlier ? 0 : 1} выбросов`;
  }
}

function openLesson(lessonId) {
  const normalizedId = normalizeLessonId(lessonId);
  const target = state.lessons.find((lesson) => lesson.id === normalizedId);
  if (target) {
    state.lessonId = normalizedId;
    state.selectedModuleId = target.module_id || `m-${normalizedId.split('.')[0]}`;
  }
  setView('lab');
  renderLesson();
}

function moveLesson(direction) {
  const index = state.lessons.findIndex((lesson) => lesson.id === state.lessonId);
  const target = state.lessons[index + direction];
  if (!target) return;
  openLesson(target.id);
}

async function loadLessons() {
  state.lessonId = normalizeLessonId(state.lessonId);
  state.lessons = fallbackLessons;
  renderLesson();
  try {
    const [program, content] = await Promise.all([fetchJson('/api/full-program'), fetchJson('/api/lesson-content')]);
    state.modules = program.modules || [];
    state.lessons = (program.lessons || []).map((lesson) => ({...lesson, id: normalizeLessonId(lesson.id), lab: lesson.lab || lesson.lab_id}));
    (content.lessons || []).forEach((lesson) => state.lessonContent.set(normalizeLessonId(lesson.lesson_id), lesson));
    state.lessonId = normalizeLessonId(state.lessonId);
    if (!state.lessons.some((lesson) => lesson.id === state.lessonId)) state.lessonId = state.lessons[0].id;
    renderLesson();
  } catch (error) {
    try {
      const [program, content] = await Promise.all([fetchJson('/data/full_program.json'), fetchJson('/data/lesson_content.json')]);
      state.modules = program.modules || [];
      state.lessons = (program.lessons || []).map((lesson) => ({...lesson, id: normalizeLessonId(lesson.id), lab: lesson.lab || lesson.lab_id}));
      (content.lessons || []).forEach((lesson) => state.lessonContent.set(normalizeLessonId(lesson.lesson_id), lesson));
      if (!state.lessons.some((lesson) => lesson.id === state.lessonId)) state.lessonId = state.lessons[0].id;
      renderLesson();
    } catch (fallbackError) {
      console.info('Локальный каталог уроков использует встроенную копию', fallbackError);
    }
  }
}

async function loadCurrentUser() {
  const token = localStorage.getItem('ailab:token');
  if (!token) { applyUserState(null); return; }
  try {
    const user = await fetchJson('/api/auth/me');
    applyUserState(user);
    const profile = await fetchJson('/api/profile/me').catch(() => null);
    if (profile) {
      state.progress = Number(profile.completion_percent || 0);
      renderProgress();
      applyRoleVisibility();
      if (profile.completed_lessons?.length) state.lessonId = normalizeLessonId(profile.completed_lessons.at(-1));
    }
    renderDashboardLesson();
  } catch (error) {
    localStorage.removeItem('ailab:token');
    applyUserState(null);
  }
}

function openModal(title, body, actions = '') {
  $('#modal-content').innerHTML = `<p class="panel-kicker">AI LEARNING LAB</p><h2 id="modal-title">${title}</h2>${body}${actions ? `<div class="modal-actions">${actions}</div>` : ''}`;
  $('#modal-backdrop').hidden = false;
  $('.modal-close').focus();
}

function closeModal() { $('#modal-backdrop').hidden = true; }

function drawLab() {
  const canvas = $('#gradient-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 900;
  const height = Math.max(260, width * .41);
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  const dark = state.theme !== 'light';
  ctx.fillStyle = dark ? '#0a1424' : '#f0f5fb';
  ctx.fillRect(0, 0, width, height);
  const pad = {left: 48, right: 20, top: 22, bottom: 36};
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  ctx.strokeStyle = dark ? 'rgba(148,163,184,.12)' : 'rgba(71,85,105,.12)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = pad.top + (plotH / 4) * i;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width - pad.right, y); ctx.stroke();
  }
  ctx.fillStyle = dark ? '#71819a' : '#748399';
  ctx.font = '10px DM Sans';
  ctx.fillText('потеря L(w)', 8, 14);
  ctx.fillText('вес w', width - 43, height - 10);
  const xFor = (w) => pad.left + ((w + 4) / 8) * plotW;
  const yFor = (loss) => pad.top + (1 - Math.min(loss, 16) / 16) * plotH;
  ctx.strokeStyle = '#a78bfa'; ctx.lineWidth = 2.4; ctx.beginPath();
  for (let x = -4; x <= 4.01; x += .08) { const y = yFor(x * x); x === -4 ? ctx.moveTo(xFor(x), y) : ctx.lineTo(xFor(x), y); }
  ctx.stroke();
  const path = [];
  let w = -3;
  for (let i = 0; i <= state.lab.step; i += 1) { path.push({w, loss: w * w}); const gradient = 2 * w + Number($('#regularization')?.value || .04) * 2 * w; w -= Number($('#learning-rate')?.value || .12) * gradient; }
  if (path.length) {
    ctx.strokeStyle = '#7dd3fc'; ctx.lineWidth = 2; ctx.beginPath();
    path.forEach((point, index) => index ? ctx.lineTo(xFor(point.w), yFor(point.loss)) : ctx.moveTo(xFor(point.w), yFor(point.loss))); ctx.stroke();
    path.forEach((point, index) => { ctx.beginPath(); ctx.fillStyle = index === path.length - 1 ? '#67e8a5' : '#7dd3fc'; ctx.arc(xFor(point.w), yFor(point.loss), index === path.length - 1 ? 5 : 3, 0, Math.PI * 2); ctx.fill(); });
  }
  updateLabReadout(w, path[path.length - 1]?.loss ?? 9);
}

function updateLabReadout(w, loss) {
  const currentW = state.lab.step === 0 ? -3 : w;
  const gradient = 2 * currentW + Number($('#regularization')?.value || .04) * 2 * currentW;
  $('#lab-step-count').textContent = String(state.lab.step);
  $('#readout-step').textContent = String(state.lab.step);
  $('#readout-w').textContent = currentW.toFixed(2);
  $('#readout-loss').textContent = (currentW * currentW).toFixed(2);
  $('#readout-gradient').textContent = gradient.toFixed(2);
}

function stepLab() {
  if (state.lab.step >= 24) { stopLab(); $('#lab-status').textContent = 'Минимум найден · попробуйте другой темп'; return; }
  state.lab.step += 1;
  $('#lab-status').textContent = `Выполняется шаг ${state.lab.step} из 24`;
  drawLab();
  if (state.lab.step >= 24) { stopLab(); $('#lab-status').textContent = 'Минимум найден · попробуйте другой темп'; }
}

function startLab() {
  if (state.lab.running) return;
  state.lab.running = true;
  $('#lab-status').textContent = 'Лаборатория запущена';
  state.lab.timer = setInterval(stepLab, 360);
}

function stopLab() {
  state.lab.running = false;
  if (state.lab.timer) clearInterval(state.lab.timer);
  state.lab.timer = null;
}

function resetLab() { stopLab(); state.lab.step = 0; $('#lab-status').textContent = 'Готово к запуску'; drawLab(); }

const demoAlumni = [
  {id:'demo-1',display_name:'Мария Воронова',headline:'ML-аналитик · табличные данные',level:'младший практик',skills:['Python','классическое ML','метрики'],projects:['Предсказатель стоимости жилья'],city:'Казань'},
  {id:'demo-2',display_name:'Илья Соколов',headline:'Инженер LLM-приложений',level:'младший практик',skills:['RAG','Transformer','оценка'],projects:['Помощник по учебным материалам'],city:'Москва'},
  {id:'demo-3',display_name:'Надежда Белова',headline:'Исследователь компьютерного зрения',level:'младший практик',skills:['PyTorch','CNN','анализ ошибок'],projects:['Классификатор изображений'],city:'Новосибирск'},
  {id:'demo-4',display_name:'Роман Ким',headline:'ML-инженер в обучении',level:'младший практик',skills:['GNN','временные ряды','Docker'],projects:['Безопасный ML-сервис'],city:'Санкт-Петербург'}
];

async function fetchJson(url, options = {}) {
  const token = localStorage.getItem('ailab:token');
  const headers = {'Content-Type':'application/json', ...(options.headers || {})};
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(url, {...options, headers});
  if (response.status === 401) {
    localStorage.removeItem('ailab:token');
    applyUserState(null);
  }
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || `HTTP ${response.status}`);
  return response.json();
}

function renderAlumni(items = demoAlumni) {
  const grid = $('#alumni-grid');
  if (!grid) return;
  $('#alumni-count').textContent = items.length;
  grid.innerHTML = items.map((item) => `<article class="alumni-card" data-alumni-id="${escapeHtml(item.id)}"><span class="alumni-avatar">${escapeHtml(item.display_name.split(' ').map((part) => part[0]).slice(0,2).join(''))}</span><div><h3>${escapeHtml(item.display_name)}</h3><p>${escapeHtml(item.headline || item.level || 'Выпускник AI Learning Lab')}${item.city ? ` · ${escapeHtml(item.city)}` : ''}</p><div class="term-related">${(item.skills || []).slice(0,3).map((skill) => `<span>${escapeHtml(skill)}</span>`).join('')}</div></div></article>`).join('');
  $$('.alumni-card', grid).forEach((card) => card.addEventListener('click', () => {
    const item = items.find((candidate) => candidate.id === card.dataset.alumniId);
    if (!item) return;
    $('#alumni-detail').innerHTML = `<span class="panel-kicker">ПУБЛИЧНЫЙ ПРОФИЛЬ</span><h2>${escapeHtml(item.display_name)}</h2><p>${escapeHtml(item.headline || item.level || '')}</p><div class="term-example"><strong>Компетенции</strong><br>${escapeHtml((item.skills || []).join(' · '))}</div><div class="term-example"><strong>Проекты</strong><br>${escapeHtml((item.projects || []).join(' · ') || 'Не опубликованы')}</div>`;
  }));
}

async function loadAlumni(filter = '') {
  const normalized = filter.trim().toLowerCase();
  try {
    const payload = await fetchJson(`/api/alumni${normalized ? `?q=${encodeURIComponent(normalized)}` : ''}`);
    const rows = payload.items || payload;
    renderAlumni(rows.map((item) => ({...item, id: item.id || item.user_id, headline: item.bio || item.level, skills: item.skills || item.interests || [], projects: (item.projects || []).map((project) => typeof project === 'string' ? project : project.title)})));
  } catch (error) {
    renderAlumni(demoAlumni.filter((item) => `${item.display_name} ${item.headline} ${item.skills.join(' ')} ${item.projects.join(' ')}`.toLowerCase().includes(normalized)));
  }
}

async function loadMentorDashboard() {
  try {
    const cohorts = await fetchJson('/api/cohorts');
    const dashboards = await Promise.all(cohorts.slice(0, 5).map((cohort) => fetchJson(`/api/mentor/cohorts/${cohort.id}/dashboard`)));
    const members = dashboards.flatMap((dashboard) => dashboard.members || []);
    $('#mentor-learners').textContent = members.length;
    $('#mentor-mastery').textContent = '—';
    $('#mentor-gaps').textContent = members.reduce((total, member) => total + (member.gaps || []).length, 0);
    $('#mentor-projects').textContent = members.reduce((total, member) => total + (member.projects_on_review || 0), 0);
    $('#mentor-cohorts').innerHTML = dashboards.map((dashboard) => `<div class="role-row"><span class="mastery-icon cyan">◌</span><div><strong>${escapeHtml(dashboard.cohort_name)}</strong><span>${dashboard.member_count || 0} участников · gap map доступна</span></div></div>`).join('') || '<div class="empty-state">Группы пока не назначены.</div>';
  } catch (error) {
    $('#mentor-learners').textContent = '—'; $('#mentor-mastery').textContent = '—'; $('#mentor-gaps').textContent = '—'; $('#mentor-projects').textContent = '—';
    $('#mentor-cohorts').innerHTML = '<div class="empty-state">Нужна сессия с ролью mentor, instructor или admin для просмотра закрытых данных группы.</div>';
  }
}

async function loadAdminDashboard() {
  try {
    const payload = await fetchJson('/api/admin/dashboard');
    $('#admin-users').textContent = payload.users ?? 0; $('#admin-alumni').textContent = payload.published_alumni ?? payload.alumni ?? 0; $('#admin-cohorts').textContent = payload.cohorts ?? 0;
    const users = payload.recent_users || await fetchJson('/api/admin/users').catch(() => []);
    $('#admin-user-list').innerHTML = users.map((item) => `<div class="role-row"><span class="mastery-icon violet">${escapeHtml((item.role || 'l')[0].toUpperCase())}</span><div><strong>${escapeHtml(item.display_name)}</strong><span>${escapeHtml(item.email)} · ${escapeHtml(item.role)}</span></div></div>`).join('') || '<div class="empty-state">Нет данных пользователей.</div>';
  } catch (error) {
    $('#admin-users').textContent = '—'; $('#admin-alumni').textContent = '—'; $('#admin-cohorts').textContent = '—';
    $('#admin-user-list').innerHTML = '<div class="empty-state">Войдите как администратор, чтобы загрузить закрытую статистику.</div>';
  }
}

async function loadExams() {
  const list = $('#exam-list');
  try {
    const exams = await fetchJson('/api/exams');
    const examAction = localStorage.getItem('ailab:token') ? 'Начать →' : 'Войти для начала →';
    list.innerHTML = exams.map((exam) => `<div class="role-row"><span class="mastery-icon cyan">◉</span><div><strong>${escapeHtml(exam.title)}</strong><span>версия ${escapeHtml(exam.version)} · ${exam.question_count} вопросов · проходной порог ${exam.pass_percent}%</span></div><button class="text-button" data-exam-start="${exam.id}">${examAction}</button></div>`).join('') || '<div class="empty-state">Опубликованных экзаменов пока нет.</div>';
    if (localStorage.getItem('ailab:token')) {
      const attempts = await fetchJson('/api/attempts/me');
      $('#attempt-list').innerHTML = attempts.map((attempt) => `<div class="role-row"><span class="mastery-icon ${attempt.passed ? 'cyan' : 'amber'}">${attempt.passed ? '✓' : '·'}</span><div><strong>Попытка #${attempt.id}</strong><span>${attempt.score_percent}% · ${attempt.status}</span></div></div>`).join('') || '<div class="empty-state">Попыток пока нет.</div>';
    }
  } catch (error) {
    list.innerHTML = '<div class="empty-state">Войдите в аккаунт, чтобы начать экзамен.</div>';
  }
}

async function loadTaskForCurrentLesson() {
  const list = $('#task-answer-list');
  if (!list) return;
  try {
    const bank = await fetchJson('/api/questions');
    const normalized = normalizeLessonId(state.lessonId);
    const question = bank.find((item) => normalizeLessonId(item.lesson_id) === normalized) || bank[0];
    state.taskQuestion = question;
    state.selectedAnswer = null;
    const options = question.options || [];
    $('#task-badge').textContent = question.lesson_id ? `УРОК ${question.lesson_id}` : 'ПРОВЕРКА';
    $('#task-position').textContent = `Вопрос по уроку ${question.lesson_id || normalized}`;
    $('#task-difficulty').textContent = question.difficulty || '● ● ○';
    $('#task-question-title').textContent = question.prompt || 'Проверьте понимание темы.';
    $('#task-question-context').textContent = question.solution || 'Выберите ответ, затем разберите причину результата.';
    if (options.length) {
      list.innerHTML = options.map((option, index) => `<button class="answer" data-answer="${escapeHtml(option)}"><span class="answer-key">${String.fromCharCode(65 + index)}</span><span>${escapeHtml(option)}</span></button>`).join('');
    } else {
      list.innerHTML = `<label class="generic-control" for="task-free-answer">Ответ</label><input id="task-free-answer" data-answer-input type="text" placeholder="Введите ответ" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)">`;
    }
    $('#question-feedback').textContent = '';
    $('#task-score').textContent = '0 / 0';
  } catch (error) {
    $('#question-feedback').textContent = 'Не удалось загрузить вопрос. Откройте лекцию и повторите попытку.';
  }
}

async function startExam(examId) {
  try {
    const started = await fetchJson(`/api/exams/${examId}/start`, {method: 'POST'});
    state.exam.attemptId = started.attempt_id; state.exam.questions = [];
    const bank = await fetchJson('/api/questions');
    state.exam.questions = started.question_ids.map((id) => bank.find((question) => question.id === id)).filter(Boolean);
    $('#exam-workspace').hidden = false; $('#exam-workspace-title').textContent = started.exam.title;
    $('#exam-questions').innerHTML = state.exam.questions.map((question, index) => { const selectId = `exam-answer-${escapeHtml(question.id)}`; return `<div class="exam-question" style="padding:14px 0;border-bottom:1px solid var(--line)"><p><strong>${index + 1}. ${escapeHtml(question.prompt)}</strong></p><label for="${selectId}">Ответ к вопросу ${index + 1}</label><select id="${selectId}" data-exam-answer="${escapeHtml(question.id)}" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)"><option value="">Выберите ответ</option>${(question.options || []).map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`).join('')}</select></div>`; }).join('');
    $('#exam-output').textContent = 'Попытка сохранена. Ответьте на вопросы и отправьте её.';
  } catch (error) {
    const message = /Bearer|токен|401/i.test(error.message || '') ? 'Сначала войдите или зарегистрируйтесь. Токен создаётся автоматически после входа.' : (error.message || 'Не удалось начать экзамен');
    showToast(message, 'info');
  }
}

async function submitExam() {
  if (!state.exam.attemptId) return;
  const answers = {};
  $$('[data-exam-answer]').forEach((select) => { if (select.value) answers[select.dataset.examAnswer] = select.value; });
  try {
    const result = await fetchJson(`/api/attempts/${state.exam.attemptId}/submit`, {method: 'POST', body: JSON.stringify({answers})});
    $('#exam-output').className = result.passed ? 'question-feedback good' : 'question-feedback bad';
    $('#exam-output').textContent = `Результат: ${result.score_percent}% · ${result.passed ? 'экзамен пройден' : 'нужно повторение'}`;
    loadExams();
  } catch (error) { $('#exam-output').className = 'question-feedback bad'; $('#exam-output').textContent = error.message; }
}

async function downloadCsv(url, filename) {
  const token = localStorage.getItem('ailab:token');
  if (!token) { showToast('Сначала войдите в аккаунт нужной роли', 'info'); return; }
  const response = await fetch(url, {headers: {Authorization: `Bearer ${token}`} });
  if (!response.ok) { showToast('Экспорт недоступен для текущей роли', 'info'); return; }
  const blob = await response.blob();
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = filename; link.click(); URL.revokeObjectURL(link.href);
}

function renderTerms(filter = '') {
  const list = $('#term-list');
  const normalized = filter.trim().toLowerCase();
  const filtered = terms.filter((term) => `${term.ru} ${term.en} ${term.acronym || ''} ${term.definition} ${(term.related || []).join(' ')}`.toLowerCase().includes(normalized));
  list.innerHTML = filtered.map((term, index) => `<button class="term-item ${state.selectedTerm === term.ru ? 'selected' : ''}" data-term-index="${terms.indexOf(term)}"><span class="term-symbol">${term.symbol}</span><span><strong>${term.ru}</strong><span>${term.en}${term.acronym ? ` · ${term.acronym}` : ''}</span></span></button>`).join('') || '<div class="panel"><p>Термин не найден. Попробуйте «градиент» или «внимание».</p></div>';
  $$('.term-item', list).forEach((button) => button.addEventListener('click', () => selectTerm(Number(button.dataset.termIndex))));
}

function selectTerm(index) {
  const term = terms[index]; if (!term) return;
  state.selectedTerm = term.ru;
  renderTerms($('#term-search')?.value || '');
  $('#term-detail').innerHTML = `<span class="panel-kicker">СЛОВАРЬ · УРОК ${term.lesson}</span><h2>${term.ru}</h2><div class="term-english">${term.en}${term.acronym ? ` · ${term.acronym}` : ''}</div><p>${term.definition}</p><div class="term-example"><strong>Пример</strong><br>${term.example}</div><div class="term-related">${term.related.map((item) => `<span>${item}</span>`).join('')}</div><button class="text-button" data-action="open-lesson" data-lesson-id="${escapeHtml(term.lesson)}" style="margin-top:16px">Открыть урок <span>→</span></button>`;
}

async function loadTerms() {
  try {
    const response = await fetch('/api/terms');
    if (!response.ok) return;
    const content = await response.json();
    terms = content.map((term) => ({
      ru: term.approved_ru_term,
      en: term.english_term,
      acronym: term.acronym,
      symbol: term.acronym || term.approved_ru_term.slice(0, 1),
      definition: term.extended_definition || term.short_definition,
      example: term.example,
      related: term.related_concepts || [],
      lesson: term.first_lesson_id
    }));
    renderTerms($('#term-search')?.value || '');
  } catch (error) {
    console.info('Демо-словарь использует встроенную копию', error);
  }
}

function chooseAnswer(button) {
  state.selectedAnswer = button.dataset.answer;
  $$('.answer').forEach((answer) => answer.classList.toggle('selected', answer === button));
}

function checkAnswer() {
  const feedback = $('#question-feedback');
  const input = $('#task-free-answer');
  const selected = state.selectedAnswer || input?.value.trim();
  const expected = state.taskQuestion?.answer;
  if (!selected) { feedback.className = 'question-feedback bad'; feedback.textContent = 'Введите или выберите ответ, затем нажмите «Проверить ответ».'; return; }
  $$('.answer').forEach((answer) => { answer.classList.remove('correct', 'wrong'); if (answer.dataset.answer === String(expected)) answer.classList.add('correct'); if (answer.dataset.answer === selected && String(expected) !== selected) answer.classList.add('wrong'); });
  if (String(expected).trim().toLowerCase() === String(selected).trim().toLowerCase()) { feedback.className = 'question-feedback good'; feedback.textContent = state.taskQuestion?.solution || 'Верно. Разберите, почему этот ответ следует из лекции.'; $('#task-score').textContent = '1 / 1'; showToast('Ответ принят · +10 XP', 'success'); }
  else { feedback.className = 'question-feedback bad'; feedback.textContent = state.taskQuestion?.solution ? `Пока нет. Подсказка: ${state.taskQuestion.solution}` : 'Пока нет. Вернитесь к лекции и повторите пример.'; $('#task-score').textContent = '0 / 1'; }
}

async function submitTutor() {
  const question = $('#tutor-question')?.value.trim();
  const attempt = $('#tutor-attempt')?.value.trim();
  const output = $('#tutor-output');
  if (!question) { output.className = 'question-feedback bad'; output.textContent = 'Сформулируйте вопрос по теме курса.'; return; }
  output.className = 'question-feedback'; output.textContent = 'Тьютор ищет опору в материалах курса…';
  try {
    const response = await fetch('/api/tutor/ask', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question, attempt, lesson_id: '1.04', hint_level: attempt ? 2 : 1, provider: 'demo'})});
    const result = await response.json();
    output.className = result.mode === 'blocked' ? 'question-feedback bad' : 'question-feedback good';
    output.innerHTML = `<strong>${result.answer}</strong>${result.citations?.length ? `<br><small>Источники: ${result.citations.map((citation) => citation.citation || citation.title).join(', ')}</small>` : ''}`;
  } catch (error) {
    output.className = 'question-feedback bad'; output.textContent = 'Тьютор временно недоступен. Повторите запрос в demo-режиме.';
  }
}

async function authRequest(mode) {
  const email = $('#auth-email')?.value.trim();
  const password = $('#auth-password')?.value;
  const displayName = $('#auth-name')?.value.trim() || 'Ученик AI Learning Lab';
  const output = $('#auth-output');
  if (!email || !password || (mode === 'register' && displayName.length < 2)) { output.className = 'question-feedback bad'; output.textContent = 'Заполните имя, электронную почту и пароль.'; return; }
  if (mode === 'register' && password.length < 10) { output.className = 'question-feedback bad'; output.textContent = 'Пароль должен содержать минимум 10 символов.'; return; }
  try {
    const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
    const body = mode === 'register' ? {email, password, display_name: displayName} : {email, password};
    const response = await fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
    const result = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(result.detail) ? result.detail.map((item) => item.msg || 'Проверьте данные').join('. ') : result.detail;
      throw new Error(detail || 'Не удалось выполнить вход');
    }
    localStorage.setItem('ailab:token', result.access_token);
    applyUserState(result.user);
    await loadCurrentUser();
    output.className = 'question-feedback good'; output.textContent = `Вход выполнен. Роль: ${result.user.role}. Прогресс можно сохранять в PostgreSQL.`;
    showToast('Сессия сохранена', 'success');
  } catch (error) {
    output.className = 'question-feedback bad'; output.textContent = error.message;
  }
}

function logout() {
  localStorage.removeItem('ailab:token');
  state.progress = 0;
  state.lessonId = '1.01';
  applyUserState(null);
  renderProgress();
  renderLesson();
  closeModal();
  setView('dashboard');
  showToast('Вы вышли из аккаунта', 'success');
}

async function loadMyProfile() {
  const token = localStorage.getItem('ailab:token');
  const output = $('#profile-output');
  if (!token) { output.textContent = 'Сначала войдите в аккаунт.'; return; }
  try {
    const profile = await fetchJson('/api/profile/me');
    $('#profile-bio').value = profile.bio || '';
    $('#profile-status').value = profile.status || 'learning';
    $('#profile-completion').value = profile.completion_percent ?? 0;
    $('#profile-publish').checked = Boolean(profile.publish_in_catalog);
    output.className = 'question-feedback good'; output.textContent = 'Профиль загружен из PostgreSQL.';
  } catch (error) { output.className = 'question-feedback bad'; output.textContent = error.message; }
}

async function saveMyProfile() {
  const output = $('#profile-output');
  try {
    await fetchJson('/api/profile/me', {method: 'PUT', body: JSON.stringify({bio: $('#profile-bio').value, status: $('#profile-status').value, completion_percent: Number($('#profile-completion').value || 0), publish_in_catalog: $('#profile-publish').checked})});
    output.className = 'question-feedback good'; output.textContent = 'Профиль сохранён. Публикация появится после выполнения условий выпуска.';
    showToast('Профиль сохранён', 'success');
  } catch (error) { output.className = 'question-feedback bad'; output.textContent = error.message; }
}

async function joinCohort() {
  const code = $('#cohort-code')?.value.trim();
  const output = $('#cohort-output');
  const token = localStorage.getItem('ailab:token');
  if (!token) { output.textContent = 'Сначала войдите в аккаунт.'; return; }
  if (!code) { output.textContent = 'Введите код группы.'; return; }
  const response = await fetch(`/api/cohorts/join?invite_code=${encodeURIComponent(code)}`, {method: 'POST', headers: {Authorization: `Bearer ${token}`} });
  const result = await response.json();
  output.className = response.ok ? 'question-feedback good' : 'question-feedback bad'; output.textContent = response.ok ? `Вы вступили в группу «${result.name}».` : (result.detail || 'Не удалось вступить в группу.');
}

async function runCode() {
  const code = $('#code-editor')?.value || '';
  const output = $('#code-output');
  output.textContent = 'Запуск в изолированном worker…';
  try {
    const response = await fetch('/api/code/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({code, timeout_seconds: 3})});
    const result = await response.json();
    output.textContent = `${result.status}\n${result.stdout || ''}${result.stderr || ''}${result.blocked_reason ? `\n${result.blocked_reason}` : ''}`;
    output.style.color = result.status === 'ok' ? 'var(--green)' : 'var(--amber)';
  } catch (error) {
    output.textContent = 'Worker недоступен. Проверьте /api/sandbox/policy и состояние Docker.';
    output.style.color = 'var(--red)';
  }
}

function exportProgress() {
  const payload = {version: 1, exportedAt: new Date().toISOString(), view: state.view, theme: state.theme, progress: state.progress, completed: ['1.01','1.02','1.03'], nextReview: ['Функция потерь','Градиент']};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type:'application/json'});
  const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'ai-learning-lab-progress.json'; a.click(); URL.revokeObjectURL(url); showToast('Прогресс экспортирован', 'success');
}

function openProjectWorkspace() {
  const workspace = $('#project-workspace');
  if (!workspace) return;
  closeModal();
  setView('projects');
  workspace.hidden = false;
  workspace.innerHTML = `<span class="panel-kicker">ПРОЕКТ · МОДУЛЬ 02</span><h2>Предсказатель стоимости жилья</h2><p>Соберите воспроизводимый ML-конвейер от постановки задачи до модельной карточки. Каждый шаг связан с уроком, лабораторией и acceptance-проверкой.</p><div class="project-workspace-grid"><div><h3>План работы</h3><ul class="project-step-list"><li><input type="checkbox" data-project-step="problem"><span><strong>1. Сформулировать задачу</strong><br>Целевая переменная, единица наблюдения и риск утечки.</span></li><li><input type="checkbox" data-project-step="data"><span><strong>2. Подготовить данные</strong><br>Разбиение train/validation/test до вычисления статистик.</span></li><li><input type="checkbox" data-project-step="models"><span><strong>3. Сравнить модели</strong><br>Baseline, дерево и ансамбль с одинаковым протоколом оценки.</span></li><li><input type="checkbox" data-project-step="errors"><span><strong>4. Разобрать ошибки</strong><br>Пять примеров, где модель ошиблась, и гипотеза улучшения.</span></li><li><input type="checkbox" data-project-step="card"><span><strong>5. Оформить модельную карточку</strong><br>Данные, метрики, ограничения, мониторинг и план отката.</span></li></ul></div><div class="project-acceptance"><h3>Acceptance criteria</h3><ul><li>Нет data leakage</li><li>MAE и RMSE на отложенной выборке</li><li>Сравнены минимум три модели</li><li>Описаны пять ошибок</li><li>README запускается одной командой</li></ul><div id="project-check-output" class="generic-result" style="margin-top:14px">Проверки ещё не запускались.</div></div></div><div class="project-workspace-actions"><button class="button button-primary" data-action="project-run-check">Запустить acceptance-проверки</button><button class="button button-ghost" data-action="project-open-sandbox">Открыть sandbox</button><button class="button button-ghost" data-action="project-save">Сохранить шаги</button></div>`;
  workspace.scrollIntoView({behavior: 'smooth', block: 'start'});
}

async function runProjectCheck() {
  const output = $('#project-check-output');
  if (!output) return;
  output.textContent = 'Запускаю минимальный smoke-проверочный набор…';
  try {
    const response = await fetch('/api/code/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({code: 'print("project smoke: OK")', timeout_seconds: 3})});
    const result = await response.json();
    output.textContent = result.status === 'ok' ? 'Smoke-проверка sandbox пройдена. Заполните пять шагов проекта и приложите результаты.' : 'Проверка sandbox завершилась с ошибкой.';
    output.className = result.status === 'ok' ? 'generic-result' : 'generic-result bad';
  } catch (error) {
    output.className = 'generic-result bad';
    output.textContent = 'Sandbox недоступен. Проверьте Docker worker.';
  }
}

function saveProjectSteps() {
  const completed = $$('[data-project-step]:checked').map((item) => item.dataset.projectStep);
  localStorage.setItem('ailab:project-steps', JSON.stringify(completed));
  showToast(`Сохранено шагов: ${completed.length}`, 'success');
}

function action(name, element = null) {
  const actions = {
    'toggle-theme': () => { state.theme = state.theme === 'dark' ? 'light' : 'dark'; applyTheme(); drawLab(); showToast(state.theme === 'dark' ? 'Тёмная тема включена' : 'Светлая тема включена'); },
    'continue-learning': () => openLesson(state.lessonId),
    'lesson-lab': () => { setView('lab'); requestAnimationFrame(() => { const target = $('#lab-generic')?.hidden ? $('#gradient-canvas') : $('#lab-generic'); target?.scrollIntoView({behavior: 'smooth', block: 'center'}); }); },
    'generic-lab-run': () => { updateGenericLab(); showToast('Опыт пересчитан', 'success'); },
    'lesson-tasks': () => setView('tasks'),
    'lesson-exam': () => setView('exam'),
    'lesson-prev': () => moveLesson(-1),
    'lesson-next': () => moveLesson(1),
    'select-module': () => { state.selectedModuleId = element?.dataset.moduleId || state.selectedModuleId; renderPathGraph(); },
    'open-diagnostic': () => openModal('Входная диагностика', '<p>Демо-диагностика состоит из 36 адаптивных вопросов. Ответы помогут выбрать темп и открыть первый prerequisite-узел.</p><div class="modal-code">01 · арифметика и функции<br>02 · Python и алгоритмы<br>03 · вероятность и статистика<br>04 · интуиция машинного обучения</div>', '<button class="button button-ghost" data-action="close-modal">Позже</button><button class="button button-primary" data-action="start-diagnostic">Начать диагностику →</button>'),
    'start-diagnostic': () => { closeModal(); showToast('Диагностика запланирована · первый блок готов'); setView('tasks'); },
    'open-review': () => openModal('Повторение · функция потерь', '<p>Сравните две точки на параболе и объясните, почему знак градиента меняет направление шага.</p><div class="modal-code">L(w) = w²<br>∂L/∂w = 2w<br><br>Если w &lt; 0, градиент отрицательный, поэтому шаг увеличивает w.</div>', '<button class="button button-primary" data-action="go-lab">Открыть лабораторию →</button>'),
    'go-lab': () => { closeModal(); setView('lab'); },
    'hint': () => { $('#question-feedback').className = 'question-feedback'; $('#question-feedback').textContent = 'Подсказка: нулевой градиент говорит о локальном наклоне функции, но ничего не говорит о значении самой функции.'; },
    'lab-run': startLab,
    'lab-pause': () => { if (state.lab.running) { stopLab(); $('#lab-status').textContent = 'Пауза · продолжите запуск'; } else startLab(); },
    'lab-step': stepLab,
    'lab-reset': resetLab,
    'open-lab-text': () => openModal('Текстовое описание графика', '<p>Фиолетовая линия показывает параболу L(w) = w². Голубые точки — последовательность весов модели. При каждом шаге вес смещается по направлению, противоположному градиенту. Зелёная точка — последний рассчитанный вес.</p><p>Измените скорость обучения и сравните, приближается ли траектория к нулю или перелетает через минимум.</p>'),
    'open-code-runner': () => openModal('Безопасный Python-runner', '<p>Код отправляется в отдельный worker с ограничением времени, вывода, памяти и запрещёнными операциями. Сеть и доступ к секретам отключены на production-границе контейнера.</p><textarea id="code-editor" rows="8" class="modal-code" style="width:100%;resize:vertical">print(2 + 3)</textarea><pre id="code-output" class="modal-code" aria-live="polite">Готово к запуску</pre>', '<button class="button button-primary" data-action="run-code">Запустить в sandbox →</button>'),
    'run-code': runCode,
    'check-answer': checkAnswer,
    'open-project': openProjectWorkspace,
    'start-project': openProjectWorkspace,
    'project-run-check': runProjectCheck,
    'project-open-sandbox': () => action('open-code-runner'),
    'project-save': saveProjectSteps,
    'new-project': () => openModal('Новый проект', '<p>Выберите основу для портфолио. Сейчас доступны 6 сквозных сценариев, которые открываются по prerequisite-графу.</p><div class="modal-actions"><button class="button button-primary" data-action="start-project">Предсказатель стоимости →</button></div>'),
    'tutor': () => openModal('AI-тьютор · режим наводящих вопросов', '<p>Тьютор сначала просит вашу попытку, затем даёт подсказку и цитирует материалы курса. Готовое решение не раскрывается до попытки.</p><label class="range-label" for="tutor-question">Вопрос</label><textarea id="tutor-question" rows="3" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)" placeholder="Например, почему градиент меняет знак?"></textarea><label class="range-label" for="tutor-attempt">Ваша попытка</label><textarea id="tutor-attempt" rows="3" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)" placeholder="Что вы уже проверили?"></textarea><div id="tutor-output" class="question-feedback" role="status"></div>', '<button class="button button-ghost" data-action="go-lab">Открыть лабораторию</button><button class="button button-primary" data-action="tutor-submit">Спросить тьютора →</button>'),
    'tutor-submit': submitTutor,
    'show-all-activity': () => openModal('История активности', '<p>Сегодня · 18:42 · урок «Среднее и медиана» · +24 XP</p><p>Сегодня · 17:15 · лаборатория «Линейная регрессия» · 86%</p><p>Вчера · 21:03 · достижение «Первый график» · +50 XP</p>'),
    'open-profile': () => { openModal('Профиль и сессия', '<p><strong>Ваш профиль</strong><br>Локальная траектория обучения</p><p>Для сохранения прогресса и доступа к ролевым панелям войдите или зарегистрируйтесь.</p><label class="range-label" for="auth-name">Имя</label><input id="auth-name" type="text" value="Участник AI Learning Lab" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)"><label class="range-label" for="auth-email">Электронная почта</label><input id="auth-email" type="email" placeholder="you@example.com" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)"><label class="range-label" for="auth-password">Пароль</label><input id="auth-password" type="password" placeholder="не менее 10 символов" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)"><div id="auth-output" class="question-feedback" role="status"></div><div class="modal-code">Пароль должен содержать минимум 10 символов.</div><label class="range-label" for="profile-bio">О себе</label><textarea id="profile-bio" rows="2" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)"></textarea><label class="range-label" for="profile-status">Статус</label><select id="profile-status" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)"><option value="learning">обучается</option><option value="completed">курс завершён</option><option value="graduate">выпускник</option></select><label class="range-label" for="profile-completion">Завершение курса, %</label><input id="profile-completion" type="number" min="0" max="100" value="0" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)"><label class="switch-row"><span><strong>Согласие на каталог выпускников</strong><small>Публикация доступна после экзамена и обязательных проектов</small></span><input id="profile-publish" type="checkbox"><i class="switch"></i></label><div id="profile-output" class="question-feedback" role="status"></div><label class="range-label" for="cohort-code">Код группы</label><input id="cohort-code" type="text" placeholder="AI-DEMO" style="width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;color:var(--text);background:var(--surface-2)"><div id="cohort-output" class="question-feedback" role="status"></div>', '<button class="button button-ghost" data-action="auth-login">Войти</button><button class="button button-primary" data-action="auth-register">Зарегистрироваться</button><button class="button button-ghost" data-action="profile-load">Загрузить профиль</button><button class="button button-primary" data-action="profile-save">Сохранить профиль</button><button class="button button-ghost" data-action="join-cohort">Вступить в группу</button><button class="button button-danger" data-action="auth-logout">Выйти</button>'); $('#modal-content [data-action="auth-logout"]').hidden = !state.currentUser; },
    'auth-login': () => authRequest('login'),
    'auth-register': () => authRequest('register'),
    'auth-logout': logout,
    'profile-load': loadMyProfile,
    'profile-save': saveMyProfile,
    'join-cohort': joinCohort,
    'mentor-refresh': loadMentorDashboard,
    'admin-refresh': loadAdminDashboard,
    'load-exams': loadExams,
    'submit-exam': submitExam,
    'mentor-export': async () => { try { const cohorts = await fetchJson('/api/cohorts'); if (cohorts[0]) await downloadCsv(`/api/mentor/cohorts/${cohorts[0].id}/export.csv`, `cohort-${cohorts[0].id}.csv`); else showToast('Нет доступной группы для экспорта', 'info'); } catch (error) { showToast('Экспорт наставника недоступен', 'info'); } },
    'admin-export': () => downloadCsv('/api/admin/export/alumni.csv', 'alumni.csv'),
    'notifications': () => openModal('Уведомления', '<p>Сегодня в 21:00 — повторение темы «Функции потерь».</p><p>До контрольной модуля 01 осталось 5 дней.</p>'),
    'search': () => openModal('Поиск по кампусу', '<p>Ищите уроки, термины, проекты и лаборатории. Введите запрос в словаре или откройте карту курса.</p>', '<button class="button button-primary" data-action="go-dictionary">Открыть словарь →</button>'),
    'go-dictionary': () => { closeModal(); setView('dictionary'); $('#term-search').focus(); },
    'open-lesson': () => { closeModal(); openLesson(element?.dataset.lessonId || state.lessonId); },
    'reset-progress': () => { localStorage.removeItem('ailab:progress'); localStorage.removeItem('ailab:view'); localStorage.removeItem('ailab:lesson'); state.progress = 0; state.lessonId = '1.01'; state.lab.step = 0; renderProgress(); renderLesson(); resetLab(); showToast('Демо-прогресс сброшен до 0%', 'success'); setView('dashboard'); },
    'export-progress': exportProgress,
    'close-modal': closeModal
  };
  if (actions[name]) actions[name](element);
}

document.addEventListener('click', (event) => {
  const viewButton = event.target.closest('[data-view]'); if (viewButton) { setView(viewButton.dataset.view); return; }
  const examButton = event.target.closest('[data-exam-start]'); if (examButton) { startExam(Number(examButton.dataset.examStart)); return; }
  const actionButton = event.target.closest('[data-action]'); if (actionButton) { action(actionButton.dataset.action, actionButton); return; }
  const answer = event.target.closest('.answer'); if (answer) { chooseAnswer(answer); return; }
  const choice = event.target.closest('.choice'); if (choice) { $$('.choice').forEach((item) => item.classList.remove('selected')); choice.classList.add('selected'); const feedback = $('#choice-feedback'); if (choice.dataset.choice === 'overshoot') { feedback.className = 'choice-feedback good'; feedback.textContent = 'Верно. При 0.24 шаги становятся крупнее и могут перелетать через минимум.'; } else { feedback.className = 'choice-feedback bad'; feedback.textContent = 'Сравните величину шага с наклоном параболы. Попробуйте вариант про перелёт через минимум.'; } return; }
  if (event.target.id === 'modal-backdrop') closeModal();
});

document.addEventListener('mouseover', (event) => {
  const element = event.target.closest('[data-tooltip]'); if (!element) return;
  const tooltip = document.createElement('div'); tooltip.className = 'tooltip'; tooltip.textContent = element.dataset.tooltip; document.body.append(tooltip); state.tooltips.set(element, tooltip);
  const rect = element.getBoundingClientRect(); tooltip.style.left = `${Math.min(window.innerWidth - tooltip.offsetWidth - 12, Math.max(12, rect.left - tooltip.offsetWidth + rect.width))}px`; tooltip.style.top = `${rect.bottom + 8}px`;
});
document.addEventListener('mouseout', (event) => { const element = event.target.closest('[data-tooltip]'); const tooltip = state.tooltips.get(element); if (tooltip) { tooltip.remove(); state.tooltips.delete(element); } });

$('#learning-rate').addEventListener('input', (event) => { $('#lr-value').textContent = Number(event.target.value).toFixed(2); $('#parameter-tip-text').textContent = Number(event.target.value) > .2 ? 'Высокая скорость ускоряет шаги, но повышает риск перелёта через минимум.' : 'Эта скорость даёт устойчивые шаги для выбранной функции.'; resetLab(); });
$('#batch-size').addEventListener('input', (event) => { $('#batch-value').textContent = event.target.value; resetLab(); });
$('#regularization').addEventListener('input', (event) => { $('#reg-value').textContent = Number(event.target.value).toFixed(2); resetLab(); });
$('#term-search').addEventListener('input', (event) => renderTerms(event.target.value));
$('#alumni-search')?.addEventListener('input', (event) => loadAlumni(event.target.value));
$$('[data-theme-choice]').forEach((button) => button.addEventListener('click', () => { state.theme = button.dataset.themeChoice; applyTheme(); drawLab(); }));
$('#reduce-motion').addEventListener('change', (event) => document.documentElement.classList.toggle('reduced-motion', event.target.checked));
$('#font-size')?.addEventListener('input', (event) => { state.fontSize = Number(event.target.value); applyTypography(); });
window.addEventListener('resize', () => { if (state.view === 'lab') drawLab(); });
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeModal(); });
document.addEventListener('keydown', (event) => {
  if (!['Enter', ' '].includes(event.key)) return;
  const actionButton = event.target.closest('[data-action]');
  if (!actionButton || event.target.matches('button, input, select, textarea')) return;
  event.preventDefault();
  action(actionButton.dataset.action, actionButton);
});
document.addEventListener('input', (event) => {
  if (event.target.matches('[data-lab-input]')) updateGenericLab();
});

$$('[data-tooltip]').forEach((element) => {
  if (!element.getAttribute('aria-label')) element.setAttribute('aria-label', `Подсказка. ${element.dataset.tooltip}`);
  element.title = element.dataset.tooltip;
});
applyTheme(); applyTypography(); renderDashboardDate(); renderProgress(); setView(state.view); renderTerms(); loadTerms(); loadLessons(); loadCurrentUser(); drawLab();
