import sys
import traceback
print("="*60)
print(" ⏳ AQUATRACK PRO ЗАПУСКАЕТСЯ...")
print(" ⏳ Подождите, идет загрузка тяжелых библиотек (Dash, Pandas)...")
print("="*60)

try:
    import dash
    from dash import dcc, html, dash_table, Input, Output, State, ctx, ALL
    import dash_bootstrap_components as dbc
    import pandas as pd
    import pdfplumber
    import base64
    import os
    import re
    import webbrowser
    from threading import Timer
    import plotly.graph_objects as go
    import sqlite3
    print(" ✅ Все библиотеки успешно загружены!")
except Exception as e:
    print(" ❌ ОШИБКА ИМПОРТА БИБЛИОТЕК:")
    traceback.print_exc()
    input("\nНажмите Enter, чтобы закрыть окно...")
    sys.exit(1)


FINA_RECORDS = {
    "50": {
        "М": {
            "50М В/С": 20.88, "100М В/С": 46.40, "200М В/С": 102.00, "400М В/С": 219.96, "800М В/С": 452.12, "1500М В/С": 870.67,
            "50М НА СПИНЕ": 23.55, "100М НА СПИНЕ": 51.60, "200М НА СПИНЕ": 111.92,
            "50М БРАСС": 25.95, "100М БРАСС": 56.88, "200М БРАСС": 125.48,
            "50М БАТТЕРФЛЯЙ": 22.27, "100М БАТТЕРФЛЯЙ": 49.45, "200М БАТТЕРФЛЯЙ": 110.34,
            "200М КОМПЛЕКС": 112.69, "400М КОМПЛЕКС": 242.50
        },
        "Ж": {
            "50М В/С": 23.61, "100М В/С": 51.71, "200М В/С": 112.23, "400М В/С": 235.38, "800М В/С": 484.79, "1500М В/С": 920.48,
            "50М НА СПИНЕ": 26.86, "100М НА СПИНЕ": 57.13, "200М НА СПИНЕ": 123.14,
            "50М БРАСС": 29.16, "100М БРАСС": 64.13, "200М БРАСС": 137.55,
            "50М БАТТЕРФЛЯЙ": 24.43, "100М БАТТЕРФЛЯЙ": 54.33, "200М БАТТЕРФЛЯЙ": 121.81,
            "200М КОМПЛЕКС": 125.70, "400М КОМПЛЕКС": 263.65
        }
    },
    "25": {
        "М": {
            "50М В/С": 19.90, "100М В/С": 44.84, "200М В/С": 98.61, "400М В/С": 212.25, "800М В/С": 440.46, "1500М В/С": 846.88,
            "50М НА СПИНЕ": 22.11, "100М НА СПИНЕ": 48.16, "200М НА СПИНЕ": 105.12,
            "50М БРАСС": 24.95, "100М БРАСС": 55.28, "200М БРАСС": 119.52,
            "50М БАТТЕРФЛЯЙ": 21.32, "100М БАТТЕРФЛЯЙ": 47.68, "200М БАТТЕРФЛЯЙ": 106.85,
            "100М КОМПЛЕКС": 49.28, "200М КОМПЛЕКС": 108.88, "400М КОМПЛЕКС": 234.81
        },
        "Ж": {
            "50М В/С": 22.83, "100М В/С": 49.93, "200М В/С": 109.36, "400М В/С": 230.25, "800М В/С": 474.00, "1500М В/С": 908.24,
            "50М НА СПИНЕ": 25.25, "100М НА СПИНЕ": 54.02, "200М НА СПИНЕ": 117.33,
            "50М БРАСС": 28.37, "100М БРАСС": 62.36, "200М БРАСС": 132.50,
            "50М БАТТЕРФЛЯЙ": 23.72, "100М БАТТЕРФЛЯЙ": 52.71, "200М БАТТЕРФЛЯЙ": 119.32,
            "100М КОМПЛЕКС": 55.11, "200М КОМПЛЕКС": 121.63, "400М КОМПЛЕКС": 255.48
        }
    }
}

def calculate_fina_points(seconds, distance_str, pool_type="50", explicit_gender=None):
    if seconds <= 0: return 0
    
    dist_upper = str(distance_str).strip().upper()
    trans = str.maketrans("ABCEHKMOPTX", "АВСЕНКМОРТХ")
    dist_upper = dist_upper.translate(trans)

    pool_key = str(pool_type).strip()
    if pool_key not in FINA_RECORDS:
        pool_key = "50"

    if explicit_gender in ["М", "Ж"]:
        gender = explicit_gender
    else:
        is_female = any(marker in dist_upper for marker in [" Ж", "ЖЕН", "ДЕВ", "(Ж)", "Ж."])
        gender = "Ж" if is_female else "М"

    records_sub = FINA_RECORDS.get(pool_key, FINA_RECORDS["50"])[gender]

    import re
    def clean_str(s):
        s = s.translate(trans)
        s = re.sub(r'[^А-ЯЁ0-9]', '', s)
        s = re.sub(r'(\d+)М', r'\1', s)
        s = s.replace("ВОЛЬНЫЙ", "ВС").replace("КРОЛЬ", "ВС")
        s = s.replace("НАСПИНЕ", "СПИНА").replace("СПИНЕ", "СПИНА").replace("НС", "СПИНА")
        s = s.replace("БАТТЕРФЛЯЙ", "БАТТ").replace("ДЕЛЬФИН", "БАТТ")
        s = s.replace("КОМПЛЕКСНОЕ", "КОМПЛЕКС").replace("КП", "КОМПЛЕКС")
        return s

    clean_input = clean_str(dist_upper)
    base_time = 0

    for key, time_val in records_sub.items():
        clean_key = clean_str(key)
        if clean_key == clean_input or clean_input in clean_key:
            base_time = time_val
            break

    if base_time > 0:
        return int(1000 * ((base_time / seconds) ** 3))

    return 0

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

print(" ⏳ Настройка путей...")
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

DATA_FOLDER = os.path.join(application_path, 'data')
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

DB_SQLITE_PATH = os.path.join(DATA_FOLDER, 'results.db')
DB_EXCEL_PATH = os.path.join(DATA_FOLDER, 'results.xlsx')
print(f" ✅ Пути настроены. База: {DB_SQLITE_PATH}")

def init_db():
    print(" ⏳ Проверка и инициализация базы данных...")
    conn = sqlite3.connect(DB_SQLITE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            ДАТА TEXT,
            СПОРТСМЕН TEXT,
            ДИСТАНЦИЯ TEXT,
            РЕЗУЛЬТАТ TEXT,
            СЕКУНДЫ REAL,
            БАССЕЙН TEXT,
            ОЧКИ INTEGER
        )
    ''')

    cursor.execute("PRAGMA table_info(results)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'БАССЕЙН' not in columns:
        cursor.execute("ALTER TABLE results ADD COLUMN БАССЕЙН TEXT DEFAULT '50'")
    if 'ОЧКИ' not in columns:
        cursor.execute("ALTER TABLE results ADD COLUMN ОЧКИ INTEGER DEFAULT 0")
        cursor.execute("SELECT rowid, ДИСТАНЦИЯ, СЕКУНДЫ, БАССЕЙН FROM results")
        for row in cursor.fetchall():
            pts = calculate_fina_points(row[2], row[1], row[3])
            cursor.execute("UPDATE results SET ОЧКИ = ? WHERE rowid = ?", (pts, row[0]))

    conn.commit()

    if os.path.exists(DB_EXCEL_PATH):
        try:
            cursor.execute("SELECT COUNT(*) FROM results")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(" 🔄 Обнаружена старая база Excel! Выполняю перенос в SQLite...")
                df = pd.read_excel(DB_EXCEL_PATH)
                if 'СЕКУНДЫ' not in df.columns:
                    df['СЕКУНДЫ'] = df['РЕЗУЛЬТАТ'].apply(time_to_sec)
                if 'БАССЕЙН' not in df.columns:
                    df['БАССЕЙН'] = '50'
                if 'ОЧКИ' not in df.columns:
                    df['ОЧКИ'] = df.apply(lambda r: calculate_fina_points(r['СЕКУНДЫ'], str(r['ДИСТАНЦИЯ']), '50'), axis=1)

                df.to_sql('results', conn, if_exists='append', index=False)
                print(" ✅ Миграция базы данных успешно завершена!")
                
                backup_path = os.path.join(DATA_FOLDER, 'results_backup.xlsx')
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(DB_EXCEL_PATH, backup_path)
                print(f" 📦 Ваш старый Excel сохранен как {backup_path}")
        except Exception as e:
            print(f" ⚠️ Ошибка при миграции базы (Excel может быть поврежден или открыт): {e}")
            
    conn.close()
    print(" ✅ База данных готова к работе!")

try:
    init_db()
except Exception as e:
    print(" ❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ РАБОТЕ С БАЗОЙ ДАННЫХ:")
    traceback.print_exc()
    input("\nНажмите Enter, чтобы закрыть окно...")
    sys.exit(1)

def get_all_results():
    with sqlite3.connect(DB_SQLITE_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM results", conn)

def add_results_to_db(new_rows_list):
    if not new_rows_list: return
    df = pd.DataFrame(new_rows_list)
    with sqlite3.connect(DB_SQLITE_PATH) as conn:
        df.to_sql('results', conn, if_exists='append', index=False)

print(" ⏳ Сборка интерфейса Dash...")
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP], 
    suppress_callback_exceptions=True,
    assets_folder=resource_path('assets')
)
app.title = "Athletics Analytics Pro"

def extract_multiple_results_from_pdf(pdf_path, athletes_str):
    raw_targets = [a.strip().upper() for a in athletes_str.split(',') if a.strip()]
    targets_words = {target: target.split() for target in raw_targets}
    results = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            for line in text.split('\n'):
                line_upper = line.upper()
                
                for target, words in targets_words.items():
                    if all(word in line_upper for word in words):
                        name_pos = line_upper.find(words[0])
                        times_pattern = r'(?<!\d)(?:\d{1,2}:)?\d{2}\.\d{2}(?!\.\d)\b'
                        
                        valid_times = []
                        for match in re.finditer(times_pattern, line):
                            time_str = match.group()
                            time_pos = match.start()
                            if time_pos > name_pos:
                                valid_times.append(time_str)
                        
                        if valid_times:
                            results[target] = valid_times[-1]
                            
    return results, raw_targets

def extract_tournament_ranking(pdf_paths, distance_str, limit_per_file=10, pool_type="50", gender="М"):
    all_results = []
    
    for path in pdf_paths:
        file_results = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                for line in text.split('\n'):
                    name_match = re.search(r'([А-ЯЁ]{3,})\s+([А-ЯЁ][а-яё]+)', line)
                    times_pattern = r'(?<!\d)(?:\d{1,2}:)?\d{2}\.\d{2}(?!\.\d)\b'
                    time_match = re.search(times_pattern, line)

                    if name_match and time_match:
                        last_name = name_match.group(1).capitalize()
                        first_name = name_match.group(2)
                        stop_words = {
                            "РМ", "РЕ", "РР", "РМЮ", "РЕЮ", "РРЮ",
                            "ОТКРЫТЫЕ", "ФИНАЛ", "ПОЛУФИНАЛ", "ЭСТАФЕТА",
                            "ВОЛЬНЫЙ", "СТИЛЬ", "БРАСС", "БАТТЕРФЛЯЙ", "КОМПЛЕКС", 
                            "ЮНОШИ", "ДЕВУШКИ", "МУЖЧИНЫ", "ЖЕНЩИНЫ", "ЮНИОРЫ", "ЮНИОРКИ",
                            "РЕКОРД", "ОЧКИ", "FINA"
                        }
                        
                        if name_match.group(1).upper() in stop_words or name_match.group(2).upper() in stop_words:
                            continue
                        
                        name_pos = line.find(name_match.group(1))
                        
                        valid_times = []
                        for match in re.finditer(times_pattern, line):
                            time_str = match.group()
                            time_pos = match.start()
                            if time_pos > name_pos:
                                valid_times.append(time_str)
                        
                        if valid_times:
                            final_time = valid_times[-1]
                            seconds = time_to_sec(final_time)
                            pts = calculate_fina_points(seconds, distance_str, pool_type, gender)
                            file_results.append({
                                'СПОРТСМЕН': f"{last_name} {first_name}",
                                'РЕЗУЛЬТАТ': final_time,
                                'СЕКУНДЫ': seconds,
                                'ОЧКИ': pts
                            })
                            
                            if len(file_results) >= limit_per_file:
                                break 
                
                if len(file_results) >= limit_per_file:
                    break
        
        all_results.extend(file_results)
        
    return all_results

def time_to_sec(t_str):
    if not isinstance(t_str, str): return 0
    t_str = str(t_str).strip()
    if t_str.count('.') == 2:
        t_str = t_str.replace('.', ':', 1)
        
    parts = t_str.split(':')
    try:
        if len(parts) == 2: return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except: return 0

header = html.Div([
    html.H1("ATHLETICS TRACKER PRO", className="text-center mt-5 mb-2"),
    html.P("Профессиональный учёт и аналитика спортивных достижений", className="text-center text-muted mb-5"),
], className="tracker-header")

tab1_content = html.Div([
    html.Div([
        html.H2("РЕГИСТРАЦИЯ НОВОГО РЕЗУЛЬТАТА", className="section-title"),
        html.P("Заполните поля и загрузите PDF протокол соревнований", className="section-subtitle"),
        dbc.Row([
            dbc.Col(dcc.Input(id="input-date", type="text", placeholder="ДД.ММ.ГГГГ", className="premium-input form-control", maxLength=10), width=2),
            dbc.Col(dcc.Input(id="input-athlete", type="text", placeholder="Фамилии (через запятую)", className="premium-input form-control", list='athlete-suggestions'), width=2),
            dbc.Col(dcc.Input(id="input-distance", type="text", placeholder="Дистанция", className="premium-input form-control"), width=2),
            dbc.Col(dbc.Select(id="input-gender", options=[{"label": "М", "value": "М"}, {"label": "Ж", "value": "Ж"}], value="М", className="premium-input"), width=1),
            dbc.Col(dbc.Select(id="input-pool", options=[{"label": "50м", "value": "50"}, {"label": "25м", "value": "25"}], value="50", className="premium-input"), width=1),
            dbc.Col(dcc.Input(id="input-manual-result", type="text", placeholder="Время (ручн.)", className="premium-input form-control"), width=2),
            dbc.Col(
                dcc.Upload(
                    id='upload-pdf',
                    children=html.Div(['📁 PDF (или ручной)'], id='upload-pdf-text', className="premium-upload"),
                    multiple=False
                ), width=2
            ),
        ], className="mb-4"),
        dbc.Button("ДОБАВИТЬ В БАЗУ ДАННЫХ", id="btn-add", className="premium-btn premium-btn-save w-100 mb-3"),
        dbc.Spinner(html.Div(id="status-msg", className="text-center"), color="primary"),
    ], className="premium-card"),
    
    html.Div([
        html.H6("ПОСЛЕДНИЕ 5 ЗАПИСЕЙ", className="text-muted mb-3 fw-bold"),
        html.Div(id="recent-table-container")
    ], className="premium-card")
], style={'padding': '10px'})

tab2_content = html.Div([
    html.Div([
        html.H2("ФИЛЬТРАЦИЯ И АНАЛИЗ ДАННЫХ", className="section-title"),
        dbc.Row([
            dbc.Col(dcc.Input(id="filter-athlete", type="text", placeholder="Фамилия Имя для отчета...", className="premium-input form-control", list='athlete-suggestions'), width=2),
            dbc.Col(dcc.Input(id="filter-distance", type="text", placeholder="Стиль/Дистанция", className="premium-input form-control"), width=3),
            dbc.Col(dbc.Select(id="filter-pool", options=[{"label": "Все бассейны", "value": "ALL"}, {"label": "50м", "value": "50"}, {"label": "25м", "value": "25"}], value="ALL", className="premium-input"), width=2),
            dbc.Col(dcc.Input(id="filter-start", type="text", placeholder="С даты ДД.ММ.ГГГГ", className="premium-input form-control", maxLength=10), width=2),
            dbc.Col(dcc.Input(id="filter-end", type="text", placeholder="По дату ДД.ММ.ГГГГ", className="premium-input form-control", maxLength=10), width=3),
        ], className="mb-4"),
        html.Div(id="print-command", className="no-print")
    ], className="premium-card no-print"),

    html.Div([
        html.Div(id="print-document-header", className="print-only-header"),
        html.Div(
            dcc.Graph(id='analytics-graph', config={'displayModeBar': False}),
            className="mb-4"
        ),
        
        html.Div([
            dbc.Row([
                dbc.Col(html.Div([
                    html.H2("ДЕТАЛИЗАЦИЯ РЕЗУЛЬТАТОВ", className="section-title no-print"),
                ]), width=6),
                dbc.Col(html.Div([
                    dbc.Button("📊 Скачать базу (Excel)", id="btn-download-excel", className="premium-btn premium-btn-outline float-end ms-2"),
                    dbc.Button("🖨️ Распечатать карточку", id="btn-print-pdf", className="premium-btn premium-btn-outline float-end"),
                ]), width=6, className="no-print d-flex justify-content-end"),
            ], className="mb-3"),
            
            html.Div(id="analytics-table-container")
        ])
    ], className="premium-card raw-data-card")
], style={'padding': '10px'})

tab3_content = html.Div([
    html.Div([
        html.H2("МАССОВЫЙ АНАЛИЗ ПРОТОКОЛОВ", className="section-title"),
        html.P("Добавляйте турниры один за другим для сравнения на одном экране", className="section-subtitle"),
        dbc.Row([
            dbc.Col(dcc.Input(id="bulk-competition", type="text", placeholder="Название турнира", className="premium-input form-control"), width=3),
            dbc.Col(dcc.Input(id="bulk-distance", type="text", placeholder="Дистанция (100м в/с)", className="premium-input form-control"), width=2),
            dbc.Col(dbc.Select(id="bulk-gender", options=[{"label": "М", "value": "М"}, {"label": "Ж", "value": "Ж"}], value="М", className="premium-input"), width=1),
            dbc.Col(dbc.Select(id="bulk-pool", options=[{"label": "50м", "value": "50"}, {"label": "25м", "value": "25"}], value="50", className="premium-input"), width=1),
            dbc.Col(
                dcc.Upload(
                    id='upload-bulk-pdfs',
                    children=html.Div(['📁 Выбрать файлы'], id='upload-bulk-text', className="premium-upload"),
                    multiple=True 
                ), width=2
            ),
            dbc.Col(dbc.Button("➕ ДОБАВИТЬ", id="btn-generate-top", className="premium-btn premium-btn-save w-100"), width=3)
        ], className="mb-4"),
        dbc.Spinner(html.Div(id="bulk-status-msg", className="text-center mb-3 no-print"), color="primary"),
    ], className="premium-card no-print"),

    html.Div([
        html.Div(id="kpi-comparison-window", className="mb-4", style={'display': 'none'}),

        html.Div(id="btn-reopen-modal-container", className="mb-4 text-center", style={'display': 'none'}, children=[
            dbc.Button("📊 Развернуть сравнение 3-х лет", id="btn-reopen-modal", className="premium-btn w-100", style={'backgroundColor': '#007bff'})
        ]),
        
        html.Div([
            dbc.Row([
                dbc.Col(html.H2("СРАВНЕНИЕ РЕЙТИНГОВ", className="section-title no-print"), width=6),
                dbc.Col([
                    dbc.Button("🗑️ Очистить экран", id="btn-clear-top20", className="premium-btn premium-btn-outline me-2"),
                    dbc.Button("💾 Сохранить в PDF", id="btn-print-top20", className="premium-btn premium-btn-outline"),
                ], width=6, className="no-print text-end"),
            ]),
        ], className="mb-4 no-print"),

        html.Div(id="top20-table-container", children=[]) 
        
    ], className="premium-card raw-data-card", id="print-area-top20"),

    # Скрытое модальное окно для 3-х турниров
    dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle("📊 АНАЛИЗ | СРАВНЕНИЕ 3-Х ЭТАПОВ", style={'fontWeight': '800', 'letterSpacing': '1px', 'color': '#ffffff'}),
                style={'backgroundColor': '#0d1117', 'borderBottom': '1px solid #30363d', 'padding': '20px 40px'},
            ),
            dbc.ModalBody(id="modal-compare-3-body", style={'backgroundColor': '#010409', 'padding': '30px 40px'}),
        ],
        id="modal-compare-3",
        fullscreen=True,
        is_open=False,
    ),
], style={'padding': '10px'})

bulk_results_store = dcc.Store(id='bulk-results-store', storage_type='memory', data=[])

app.layout = dbc.Container([
    dcc.Download(id="download-excel"),
    bulk_results_store,
    html.Datalist(id='athlete-suggestions'),
    header,
    dbc.Tabs([
        dbc.Tab(tab1_content, label="Ввод данных", tab_id="tab-1"),
        dbc.Tab(tab2_content, label="Аналитика", tab_id="tab-2"),
        dbc.Tab(tab3_content, label="Рейтинги", tab_id="tab-3"),
    ], id="tabs", active_tab="tab-1", className="nav-pills mb-4")
], className="main-container")

def apply_date_mask(val):
    if not val: return ""
    clean = re.sub(r'\D', '', val)
    result = ""
    for i, char in enumerate(clean):
        if i == 2 or i == 4: result += "."
        result += char
    return result[:10]

@app.callback(Output("input-date", "value"), Input("input-date", "value"))
def mask_date_input(val): return apply_date_mask(val)

@app.callback(Output("filter-start", "value"), Input("filter-start", "value"))
def mask_filter_start(val): return apply_date_mask(val)

@app.callback(Output("filter-end", "value"), Input("filter-end", "value"))
def mask_filter_end(val): return apply_date_mask(val)

@app.callback(Output("upload-pdf-text", "children"), Input("upload-pdf", "filename"))
def update_upload_text(filename):
    if filename: return f"✅ PDF Загружен: {filename}"
    return "📁 PDF (или ручной)"

@app.callback(
    [Output("status-msg", "children"),
     Output("recent-table-container", "children"),
     Output("upload-pdf", "contents"),
     Output("input-manual-result", "value"), 
     Output("btn-add", "n_clicks")],
    [Input("btn-add", "n_clicks"),
     Input("tabs", "active_tab")],
    [State("input-date", "value"),
     State("input-athlete", "value"),
     State("input-distance", "value"),
     State("input-gender", "value"),
     State("input-pool", "value"),
     State("upload-pdf", "contents"),
     State("input-manual-result", "value")]
)
def process_save_and_display_recent(n_clicks, active_tab, date, athlete, distance, gender, pool_type, pdf_contents, manual_result):
    msg = ""
    reset_pdf = dash.no_update
    reset_manual = dash.no_update
    triggered_id = ctx.triggered_id
    
    if triggered_id == "btn-add" and n_clicks:
        if not all([date, athlete, distance]) or len(date) < 10:
            msg = dbc.Alert("Заполните базовые поля (Дата, Спортсмен, Дистанция)!", color="danger")
        elif not pdf_contents and not manual_result:
            msg = dbc.Alert("Загрузите PDF протокол ИЛИ введите результат вручную!", color="warning")
        else:
            try:
                results_dict = {}
                requested_targets = [a.strip().upper() for a in athlete.split(',') if a.strip()]

                if manual_result:
                    clean_time = manual_result.strip().replace(',', '.')
                    for target in requested_targets:
                        results_dict[target] = clean_time
                    reset_manual = "" 
                
                elif pdf_contents:
                    _, content_string = pdf_contents.split(',')
                    temp_pdf = os.path.join(application_path, "temp_protocol.pdf")
                    with open(temp_pdf, "wb") as f:
                        f.write(base64.b64decode(content_string))
                    
                    results_dict, _ = extract_multiple_results_from_pdf(temp_pdf, athlete)
                    
                    if os.path.exists(temp_pdf):
                        os.remove(temp_pdf)
                    reset_pdf = None

                if results_dict:
                    new_rows = []
                    found_msgs = []
                    
                    for name_upper, res_time in results_dict.items():
                        pretty_name = name_upper.title()
                        seconds = time_to_sec(res_time) 
                        pts = calculate_fina_points(seconds, distance.strip(), pool_type, gender)
                        new_rows.append({
                            'ДАТА': date, 
                            'СПОРТСМЕН': pretty_name, 
                            'ДИСТАНЦИЯ': distance.strip(), 
                            'РЕЗУЛЬТАТ': res_time,
                            'СЕКУНДЫ': seconds,
                            'БАССЕЙН': pool_type,
                            'ОЧКИ': pts
                        })
                        found_msgs.append(f"{pretty_name} ({res_time})")
                    add_results_to_db(new_rows)
                    
                    not_found = [t.title() for t in requested_targets if t not in results_dict]
                    
                    success_text = f"✅ Успешно добавлено: {', '.join(found_msgs)}."
                    if not_found:
                        success_text += f" ❌ Не найдены: {', '.join(not_found)}."
                        
                    msg = dbc.Alert(success_text, color="success" if not not_found else "warning")
                else:
                    msg = dbc.Alert("Ни один из спортсменов не найден в PDF.", color="danger")
            
            except Exception as e:
                msg = dbc.Alert(f"Ошибка обработки: {e}", color="danger")

    full_df = get_all_results()
    display_df = full_df.tail(5).iloc[::-1].drop(columns=['СЕКУНДЫ'], errors='ignore')
    table = dash_table.DataTable(
        data=display_df.to_dict('records'),
        style_as_list_view=True,
        style_header={'fontWeight': 'bold'},
        style_cell={'textAlign': 'left', 'padding': '12px'}
    )
    
    return msg, table, reset_pdf, reset_manual, 0

@app.callback(
    [Output("analytics-graph", "figure"),
     Output("analytics-table-container", "children"),
     Output("print-document-header", "children")], 
    [Input("filter-athlete", "value"),
     Input("filter-distance", "value"),
     Input("filter-pool", "value"),
     Input("filter-start", "value"),
     Input("filter-end", "value"),
     Input("tabs", "active_tab")] 
)
def update_analytics(athlete, distance, pool_filter, start_date, end_date, active_tab):
    df = get_all_results()
    athlete_text = athlete.upper() if athlete else "ВСЕ"
    dist_text = f" | Дистанция: {distance.upper()}" if distance else ""
    pool_text = f" | Бассейн: {pool_filter}м" if pool_filter and pool_filter != "ALL" else " | Все бассейны"
    report_title = html.Div([
        html.H1("AQUATRACK PRO | ИНДИВИДУАЛЬНЫЙ ОТЧЕТ"),
        html.H2(f"Спортсмен: {athlete_text}{dist_text}{pool_text}"),
        html.P(f"Дата формирования: {pd.Timestamp.now().strftime('%d.%m.%Y')}")
    ])

    if df.empty:
        return go.Figure().update_layout(title="Нет данных", template="plotly_dark"), html.Div("Нет данных"), report_title

    df['Дата_dt'] = pd.to_datetime(df['ДАТА'], format='%d.%m.%Y', errors='coerce')

    if athlete:
        df = df[df['СПОРТСМЕН'].str.contains(athlete, case=False, na=False)]
    if distance:
        df = df[df['ДИСТАНЦИЯ'].str.contains(distance, case=False, na=False)]
    if pool_filter and pool_filter != "ALL":
        df = df[df['БАССЕЙН'] == pool_filter]
    if start_date and len(start_date) == 10:
        s_dt = pd.to_datetime(start_date, format='%d.%m.%Y')
        df = df[df['Дата_dt'] >= s_dt]
    if end_date and len(end_date) == 10:
        e_dt = pd.to_datetime(end_date, format='%d.%m.%Y')
        df = df[df['Дата_dt'] <= e_dt]

    df = df.sort_values('Дата_dt')

    fig = go.Figure()
    for dist in df['ДИСТАНЦИЯ'].unique():
        dff = df[df['ДИСТАНЦИЯ'] == dist]
        fig.add_trace(go.Scatter(
            x=dff['ДАТА'], y=dff['СЕКУНДЫ'],
            mode='lines+markers+text', name=dist, text=dff['РЕЗУЛЬТАТ'], textposition="top center",
            line=dict(shape='spline', smoothing=0.3, width=3),
            marker=dict(size=10, line=dict(width=2, color='white')),
        ))
    
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor='#141619', paper_bgcolor='#141619',
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#a1a1a1")),
        yaxis_title="Время (секунды)",
        xaxis=dict(showgrid=True, gridcolor='#1f2328'),
        yaxis=dict(showgrid=True, gridcolor='#1f2328'),
        colorway=["#007bff", "#27ae60", "#f39c12", "#c0392b"]
    )

    display_df = df.drop(columns=['Дата_dt', 'СЕКУНДЫ'], errors='ignore')
    table = dash_table.DataTable(
        data=display_df.to_dict('records'),
        style_as_list_view=True,
        style_header={'fontWeight': 'bold'},
        style_cell={'textAlign': 'left', 'padding': '12px'}
    )
    
    return fig, table, report_title

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            setTimeout(function() { window.print(); }, 200);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("btn-print-pdf", "style"),
    Input("btn-print-pdf", "n_clicks"),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            setTimeout(function() { window.print(); }, 200);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("btn-print-top20", "style"),
    Input("btn-print-top20", "n_clicks"),
    prevent_initial_call=True
)

@app.callback(Output("upload-bulk-text", "children"), Input("upload-bulk-pdfs", "filename"))
def update_bulk_upload_text(filenames):
    if filenames: return f"✅ Загружено файлов: {len(filenames)}"
    return "📁 Выбрать файлы"

@app.callback(
    [Output("bulk-status-msg", "children"),
     Output("bulk-results-store", "data"),
     Output("top20-table-container", "children"),
     Output("kpi-comparison-window", "children"),
     Output("kpi-comparison-window", "style"),
     Output("modal-compare-3", "is_open"),
     Output("modal-compare-3-body", "children"),
     Output("btn-reopen-modal-container", "style"),
     Output("upload-bulk-pdfs", "contents"),
     Output("upload-bulk-pdfs", "filename")],
    [Input("btn-generate-top", "n_clicks"),
     Input("btn-clear-top20", "n_clicks"),
     Input("btn-reopen-modal", "n_clicks"),
     Input({'type': 'btn-swap', 'index': ALL}, "n_clicks")],
    [State("bulk-competition", "value"),
     State("bulk-distance", "value"),
     State("bulk-gender", "value"),
     State("bulk-pool", "value"),
     State("upload-bulk-pdfs", "contents"),
     State("upload-bulk-pdfs", "filename"),
     State("bulk-results-store", "data")]
)
def manage_top20(gen_clicks, clear_clicks, reopen_clicks, swap_clicks, comp_title, distance_title, gender, pool_type, list_of_contents, list_of_names, store_data):
    triggered_id = ctx.triggered_id
    msg = dash.no_update
    is_modal_open = dash.no_update

    reset_contents = dash.no_update
    reset_filename = dash.no_update
    
    if triggered_id == "btn-clear-top20":
        return dbc.Alert("Экран очищен.", color="info"), [], [], "", {'display': 'none'}, False, "", {'display': 'none'}, None, None

    data_structure = store_data or []

    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'btn-swap':
        idx_to_remove = triggered_id['index']
        if 0 <= idx_to_remove < len(data_structure):
            data_structure.pop(idx_to_remove)
        is_modal_open = False
        msg = dbc.Alert("Турнир удален. Загрузите новый для замены.", color="info")

    elif triggered_id == "btn-reopen-modal":
        is_modal_open = True
        msg = dash.no_update

    elif triggered_id == "btn-generate-top":
        if not list_of_contents:
            return dbc.Alert("Загрузите PDF файлы!", color="danger"), data_structure, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        comp_label = comp_title.strip() if comp_title else "Неизвестный турнир"
        dist_label = distance_title.strip() if distance_title else "Неизвестная дистанция"
        temp_paths = []

        try:
            for i, content in enumerate(list_of_contents):
                _, content_string = content.split(',')
                temp_pdf = os.path.join(application_path, f"temp_bulk_{i}.pdf")
                with open(temp_pdf, "wb") as f:
                    f.write(base64.b64decode(content_string))
                temp_paths.append(temp_pdf)

            results = extract_tournament_ranking(temp_paths, dist_label, limit_per_file=10, pool_type=pool_type, gender=gender)
            
            if not results:
                return dbc.Alert(f"Спортсмены не найдены ({comp_label}).", color="warning"), data_structure, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

            df = pd.DataFrame(results)
            df = df.sort_values('СЕКУНДЫ') 
            df = df.drop_duplicates(subset=['СПОРТСМЕН'], keep='first') 

            tournament_data = {
                'competition': comp_label,
                'distance': dist_label,
                'gender': gender,
                'pool': pool_type,
                'raw_results': df.to_dict('records')
            }
            
            data_structure.append(tournament_data)
            
            if len(data_structure) > 3:
                data_structure = data_structure[-3:]
                
            if len(data_structure) == 3:
                is_modal_open = True

            msg = dbc.Alert(f"✅ {comp_label} добавлен!", color="success")

            reset_contents = None
            reset_filename = None

        except Exception as e:
            return dbc.Alert(f"Ошибка: {e}", color="danger"), data_structure, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        finally:
            for path in temp_paths:
                if os.path.exists(path):
                    os.remove(path)

    def calc_kpis(df):
        if df.empty: return 0, 0, 0, 0, 0, 0
        return (
            df.iloc[0]['СЕКУНДЫ'], df['СЕКУНДЫ'].median(), df.iloc[-1]['СЕКУНДЫ'],
            df.iloc[0].get('ОЧКИ', 0), df.get('ОЧКИ', pd.Series([0])).median(), df.iloc[-1].get('ОЧКИ', 0)
        )

    def format_diff(new_v, old_v):
        diff = new_v - old_v
        if abs(diff) < 0.001: return html.Div([html.Span("≈ Стабильно", style={'color': '#8b949e'})])
        color, arrow = ("#3fb950", "▼ Улучшение") if diff < 0 else ("#f85149", "▲ Ухудшение")
        return html.Div([html.Span(f"{arrow} ({'+' if diff > 0 else ''}{diff:.2f} сек)", style={'color': color, 'fontWeight': 'bold', 'fontSize': '0.9rem'})])

    def format_points_diff(new_p, old_p):
        diff = int(new_p - old_p)
        if diff == 0: return html.Div([html.Span("≈ 0 очков", style={'color': '#8b949e', 'fontSize': '0.85rem'})])
        color, arrow = ("#3fb950", "▲") if diff > 0 else ("#f85149", "▼")
        return html.Div([html.Span(f"{arrow} {'+' if diff > 0 else ''}{diff} очков", style={'color': color, 'fontWeight': 'bold', 'fontSize': '0.85rem'})])

    box_style = {'textAlign': 'center', 'background': 'rgba(255,255,255,0.03)', 'borderRadius': '10px', 'padding': '15px', 'border': '1px solid #30363d'}
    label_style = {'color': '#8b949e', 'fontSize': '0.8rem', 'fontWeight': '700', 'letterSpacing': '1px', 'marginBottom': '8px'}
    value_style = {'color': '#ffffff', 'fontSize': '1.5rem', 'fontWeight': '800', 'marginBottom': '4px'}
    points_style = {'color': '#e3b341', 'fontSize': '1.1rem', 'fontWeight': '700', 'marginTop': '8px', 'marginBottom': '2px'}

    def create_kpi_block(target_entry, base_entry):
        new_df = pd.DataFrame(target_entry['raw_results']).head(10)
        old_df = pd.DataFrame(base_entry['raw_results']).head(10)
        nf, nm, nl, pf, pm, pl = calc_kpis(new_df)
        of, om, ol, opf, opm, opl = calc_kpis(old_df)
        
        t_name = str(target_entry['competition']).split()[-1]
        b_name = str(base_entry['competition']).split()[-1]
        
        return html.Div([
            html.H5(f"📉 Динамика: {b_name} ➔ {t_name}", style={'color': '#c9d1d9', 'textAlign': 'center', 'fontWeight': 'bold', 'marginBottom': '15px'}),
            dbc.Row([
                dbc.Col(html.Div([html.Div("ЛИДЕР", style=label_style), html.Div(f"{new_df.iloc[0]['РЕЗУЛЬТАТ']}", style=value_style), format_diff(nf, of), html.Div(f"⭐ {int(pf)} FINA", style=points_style), format_points_diff(pf, opf)], style=box_style), width=4),
                dbc.Col(html.Div([html.Div("МЕДИАНА", style=label_style), html.Div(f"{nm:.2f}с", style=value_style), format_diff(nm, om), html.Div(f"⭐ {int(pm)} FINA", style=points_style), format_points_diff(pm, opm)], style=box_style), width=4),
                dbc.Col(html.Div([html.Div("ЗАМЫКАЮЩИЙ", style=label_style), html.Div(f"{new_df.iloc[-1]['РЕЗУЛЬТАТ']}", style=value_style), format_diff(nl, ol), html.Div(f"⭐ {int(pl)} FINA", style=points_style), format_points_diff(pl, opl)], style=box_style), width=4),
            ])
        ], style={'background': '#161b22', 'border': '1px solid #30363d', 'borderRadius': '16px', 'padding': '20px', 'boxShadow': '0 4px 15px rgba(0,0,0,0.3)'})

    table_stack = []
    kpi_content = ""
    kpi_style = {'display': 'none'}
    modal_body = ""
    reopen_btn_style = {'display': 'none'}

    if len(data_structure) == 3:
        reopen_btn_style = {'display': 'block'} 
        modal_cols = []
        
        for i, entry in enumerate(data_structure):
            df_modal = pd.DataFrame(entry['raw_results']).head(10)
            df_modal.insert(0, 'МЕСТО', range(1, len(df_modal) + 1))
            df_modal = df_modal.drop(columns=['СЕКУНДЫ'], errors='ignore')

            df_calc = pd.DataFrame(entry['raw_results']).head(10)
            med_sec = df_calc['СЕКУНДЫ'].median() if not df_calc.empty else 0
            lead_res = df_modal.iloc[0]['РЕЗУЛЬТАТ'] if not df_modal.empty else "-"

            col_content = html.Div([
                dbc.Button("🔄 ЗАМЕНИТЬ ФАЙЛ", id={'type': 'btn-swap', 'index': i}, color="info", outline=True, size="sm", className="w-100 mb-3 fw-bold", style={'borderRadius': '8px', 'letterSpacing': '1px'}),
                html.H3(f"{entry['competition'].upper()}", className="text-center mb-1", style={'color': '#ffffff', 'fontWeight': '800', 'letterSpacing': '0.5px'}),
                
                html.Div([
                    html.Span("Лидер: ", style={'color': '#8b949e', 'fontSize': '0.9rem'}),
                    html.Span(f"{lead_res}", style={'color': '#58a6ff', 'fontWeight': 'bold', 'marginRight': '15px', 'fontSize': '1.1rem'}),
                    html.Span("Медиана: ", style={'color': '#8b949e', 'fontSize': '0.9rem'}),
                    html.Span(f"{med_sec:.2f}с", style={'color': '#3fb950', 'fontWeight': 'bold', 'fontSize': '1.1rem'}),
                ], className="text-center mb-3 mt-2"),
                
                dash_table.DataTable(
                    data=df_modal.to_dict('records'),
                    style_as_list_view=True,
                    style_header={'fontWeight': 'bold', 'backgroundColor': 'transparent', 'color': '#8b949e', 'borderBottom': '1px solid #30363d'},
                    style_cell={'textAlign': 'left', 'padding': '12px', 'backgroundColor': 'transparent', 'color': '#c9d1d9', 'borderBottom': '1px solid #21262d'},
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgba(255,255,255,0.02)'}]
                )
            ], style={
                'background': 'linear-gradient(180deg, #161b22 0%, #0d1117 100%)',
                'border': '1px solid #30363d', 'borderRadius': '20px', 'padding': '25px', 'height': '100%',
                'boxShadow': '0 10px 30px rgba(0,0,0,0.4)'
            })
            modal_cols.append(dbc.Col(col_content, width=4))

        tables_row = dbc.Row(modal_cols, className="align-items-stretch mb-4")

        kpis_row = dbc.Row([
            dbc.Col(create_kpi_block(data_structure[1], data_structure[0]), width=6),
            dbc.Col(create_kpi_block(data_structure[2], data_structure[1]), width=6)
        ])

        modal_body = html.Div([tables_row, html.Hr(style={'borderColor': '#30363d', 'margin': '30px 0'}), kpis_row])
        table_stack = [html.Div("📊 Сравнение 3-х турниров сейчас открыто в полноэкранном режиме. Нажмите кнопку выше, чтобы вернуться к нему.", className="text-center fw-bold mt-5 fs-5")]

    else:
        for entry in data_structure:
            display_df = pd.DataFrame(entry['raw_results']).head(10)
            display_df.insert(0, 'МЕСТО', range(1, len(display_df) + 1))
            display_df = display_df.drop(columns=['СЕКУНДЫ'], errors='ignore')

            gender_badge = entry.get('gender', 'М')
            pool_badge = f" ({gender_badge}, {entry.get('pool', '50')}м)"
            new_table_block = html.Div([
                html.H3(f"{entry['competition'].upper()} | ТОП-10: {entry['distance'].upper()}{pool_badge}", style={'marginTop': '30px', 'marginBottom': '15px'}),
                dash_table.DataTable(
                    data=display_df.to_dict('records'),
                    style_as_list_view=True,
                    style_header={'fontWeight': 'bold'},
                    style_cell={'textAlign': 'left', 'padding': '12px'}
                ),
                html.Hr(style={'borderColor': '#444'})
            ])
            table_stack.append(new_table_block)

        if len(data_structure) == 2:
            kpi_style = {
                'display': 'block',
                'background': 'linear-gradient(135deg, #161b22 0%, #0d1117 100%)',
                'border': '1px solid #30363d',
                'borderRadius': '16px',
                'padding': '0',
                'boxShadow': '0 8px 30px rgba(0,0,0,0.5)'
            }
            kpi_content = create_kpi_block(data_structure[1], data_structure[0])

    return msg, data_structure, table_stack, kpi_content, kpi_style, is_modal_open, modal_body, reopen_btn_style, reset_contents, reset_filename

@app.callback(
    Output("athlete-suggestions", "children"),
    [Input("tabs", "active_tab"),
     Input("status-msg", "children")]
)
def update_athlete_list(active_tab, status_change):
    try:
        df = get_all_results()
        if df.empty:
            return []

        unique_names = sorted(df['СПОРТСМЕН'].unique())
        return [html.Option(value=name) for name in unique_names]
    except:
        return []
    
@app.callback(
    Output("download-excel", "data"),
    Input("btn-download-excel", "n_clicks"),
    prevent_initial_call=True
)
def download_database_excel(n_clicks):
    df = get_all_results()
    df['Дата_dt'] = pd.to_datetime(df['ДАТА'], format='%d.%m.%Y', errors='coerce')
    df = df.sort_values('Дата_dt', ascending=False).drop(columns=['Дата_dt'])
    return dcc.send_data_frame(df.to_excel, "Aquatrack_Full_Database.xlsx", index=False)

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

if __name__ == '__main__':
    print(" 🚀 Запуск веб-сервера (Dash)...")
    try:
        print("="*60)
        print(" 🚀 AQUATRACK PRO УСПЕШНО ЗАПУЩЕН!")
        print("="*60)
        print(" - Интерфейс откроется в вашем браузере автоматически.")
        print(" - Пожалуйста, НЕ ЗАКРЫВАЙТЕ это черное окно, пока работаете.")
        print(" - Чтобы полностью остановить программу, закройте это окно крестиком.")
        print("="*60)
        Timer(1.5, open_browser).start()
        app.run(host='127.0.0.1', port=8050, debug=False)
    except Exception as e:
        print(" ❌ ОШИБКА ПРИ ЗАПУСКЕ СЕРВЕРА:")
        traceback.print_exc()
        input("\nНажмите Enter, чтобы закрыть окно...")
        sys.exit(1)