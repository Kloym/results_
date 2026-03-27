import dash
from dash import dcc, html, dash_table, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import pdfplumber
import base64
import os
import re
import sys
import webbrowser
from threading import Timer
import plotly.graph_objects as go

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- НАСТРОЙКА ПУТЕЙ ---
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

DATA_FOLDER = os.path.join(application_path, 'data')
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

DB_PATH = os.path.join(DATA_FOLDER, 'results.xlsx')

def init_db():
    if not os.path.exists(DB_PATH):
        df = pd.DataFrame(columns=['ДАТА', 'СПОРТСМЕН', 'ДИСТАНЦИЯ', 'РЕЗУЛЬТАТ', 'СЕКУНДЫ'])
        df.to_excel(DB_PATH, index=False)
    else:
        try:
            df = pd.read_excel(DB_PATH)
            if 'СЕКУНДЫ' not in df.columns:
                print("🔄 Обнаружена старая версия базы данных. Выполняю обновление...")
                df['СЕКУНДЫ'] = df['РЕЗУЛЬТАТ'].apply(time_to_sec)
                df.to_excel(DB_PATH, index=False)
                print("✅ База данных успешно обновлена до новой версии!")
        except Exception as e:
            print(f"⚠️ Ошибка при проверке старой базы: {e}")

init_db()

app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP], 
    suppress_callback_exceptions=True,
    assets_folder=resource_path('assets')
)
app.title = "Athletics Analytics Pro"

def extract_multiple_results_from_pdf(pdf_path, athletes_str):
    """Ищет результаты конкретных спортсменов."""
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

def extract_tournament_ranking(pdf_paths, limit_per_file=20):
    """Сбор результатов (Топ-20)."""
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
                        
                        name_pos = line.find(name_match.group(1))
                        
                        valid_times = []
                        for match in re.finditer(times_pattern, line):
                            time_str = match.group()
                            time_pos = match.start()
                            
                            if time_pos > name_pos:
                                valid_times.append(time_str)
                        
                        if valid_times:
                            final_time = valid_times[-1]
                            file_results.append({
                                'СПОРТСМЕН': f"{last_name} {first_name}",
                                'РЕЗУЛЬТАТ': final_time,
                                'СЕКУНДЫ': time_to_sec(final_time)
                            })
                            
                            if len(file_results) >= limit_per_file:
                                break 
                
                if len(file_results) >= limit_per_file:
                    break
        
        all_results.extend(file_results)
        
    return all_results

def time_to_sec(t_str):
    if not isinstance(t_str, str): return 0
    parts = t_str.split(':')
    try:
        if len(parts) == 2: return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except: return 0

header = html.Div([
    html.H1("ATHLETICS TRACKER PRO", className="text-center mt-5 mb-2"),
    html.P("Профессиональный учёт и аналитика спортивных достижений", className="text-center text-muted mb-5"),
], className="tracker-header")

# Содержимое вкладки 1: "Ввод данных"
tab1_content = html.Div([
    html.Div([
        html.H2("РЕГИСТРАЦИЯ НОВОГО РЕЗУЛЬТАТА", className="section-title"),
        html.P("Заполните поля и загрузите PDF протокол соревнований", className="section-subtitle"),
        dbc.Row([
            dbc.Col(dcc.Input(id="input-date", type="text", placeholder="ДД.ММ.ГГГГ", className="premium-input form-control", maxLength=10), width=2),
            dbc.Col(dcc.Input(id="input-athlete", type="text", placeholder="Фамилии (через запятую)", className="premium-input form-control"), width=3),
            dbc.Col(dcc.Input(id="input-distance", type="text", placeholder="Дистанция", className="premium-input form-control"), width=2),
            dbc.Col(dcc.Input(id="input-manual-result", type="text", placeholder="Время (ручн.)", className="premium-input form-control"), width=2),
            dbc.Col(
                dcc.Upload(
                    id='upload-pdf',
                    children=html.Div(['📁 PDF (или ручной)'], id='upload-pdf-text', className="premium-upload"),
                    multiple=False
                ), width=3
            ),
        ], className="mb-4"),
        dbc.Button("ДОБАВИТЬ В БАЗУ ДАННЫХ", id="btn-add", className="premium-btn premium-btn-save w-100 mb-3"),
        html.Div(id="status-msg", className="text-center"),
    ], className="premium-card"),
    
    html.Div([
        html.H6("ПОСЛЕДНИЕ 5 ЗАПИСЕЙ", className="text-muted mb-3 fw-bold"),
        html.Div(id="recent-table-container")
    ], className="premium-card")
], style={'padding': '10px'})

# Содержимое вкладки 2: "Аналитика"
tab2_content = html.Div([
    html.Div([
        html.H2("ФИЛЬТРАЦИЯ И АНАЛИЗ ДАННЫХ", className="section-title"),
        dbc.Row([
            dbc.Col(dcc.Input(id="filter-athlete", type="text", placeholder="Фамилия Имя для отчета...", className="premium-input form-control"), width=3),
            dbc.Col(dcc.Input(id="filter-distance", type="text", placeholder="Стиль/Дистанция (100м в/с)", className="premium-input form-control"), width=3),
            dbc.Col(dcc.Input(id="filter-start", type="text", placeholder="С даты ДД.ММ.ГГГГ", className="premium-input form-control", maxLength=10), width=3),
            dbc.Col(dcc.Input(id="filter-end", type="text", placeholder="По дату ДД.ММ.ГГГГ", className="premium-input form-control", maxLength=10), width=3),
        ], className="mb-4"),
        html.Div(id="print-command", className="no-print")
    ], className="premium-card no-print"),

    html.Div([
        html.Div(id="print-document-header", className="print-only-header"),
        html.Div(
            dcc.Graph(id='analytics-graph', config={'displayModeBar': False}),
            className="no-print"
        ),
        
        html.Div([
            dbc.Row([
                dbc.Col(html.Div([
                    html.H2("ДЕТАЛИЗАЦИЯ РЕЗУЛЬТАТОВ", className="section-title no-print"),
                ]), width=6),
                dbc.Col(html.Div([
                    dbc.Button("🖨️ Распечатать карточку", id="btn-print-pdf", className="premium-btn premium-btn-outline float-end"),
                ]), width=6, className="no-print"),
            ], className="mb-3"),
            
            html.Div(id="analytics-table-container")
        ])
    ], className="premium-card raw-data-card")
], style={'padding': '10px'})

# Содержимое вкладки 3: "Рейтинги (Топ-20)"
tab3_content = html.Div([
    html.Div([
        html.H2("МАССОВЫЙ АНАЛИЗ ПРОТОКОЛОВ", className="section-title"),
        html.P("Добавляйте турниры один за другим для сравнения на одном экране", className="section-subtitle"),
        dbc.Row([
            dbc.Col(dcc.Input(id="bulk-competition", type="text", placeholder="Название турнира (напр. Зона 2026)", className="premium-input form-control"), width=3),
            dbc.Col(dcc.Input(id="bulk-distance", type="text", placeholder="Дистанция (100м в/с)", className="premium-input form-control"), width=3),
            dbc.Col(
                dcc.Upload(
                    id='upload-bulk-pdfs',
                    children=html.Div(['📁 Выбрать файлы'], id='upload-bulk-text', className="premium-upload"),
                    multiple=True 
                ), width=3
            ),
            dbc.Col(dbc.Button("➕ ДОБАВИТЬ НА ЭКРАН", id="btn-generate-top", className="premium-btn premium-btn-save w-100"), width=3)
        ], className="mb-4"),
        html.Div(id="bulk-status-msg", className="text-center mb-3 no-print")
    ], className="premium-card no-print"),

    html.Div([
        html.Div(id="kpi-comparison-window", className="mb-4 no-print", style={'display': 'none'}),
        
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
        
    ], className="premium-card raw-data-card", id="print-area-top20")
], style={'padding': '10px'})

bulk_results_store = dcc.Store(id='bulk-results-store', storage_type='memory', data=[])

app.layout = dbc.Container([
    bulk_results_store,
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

# Коллбэки Вкладки 1
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
     State("upload-pdf", "contents"),
     State("input-manual-result", "value")]
)
def process_save_and_display_recent(n_clicks, active_tab, date, athlete, distance, pdf_contents, manual_result):
    df = pd.read_excel(DB_PATH)
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
                        new_rows.append({
                            'ДАТА': date, 
                            'СПОРТСМЕН': pretty_name, 
                            'ДИСТАНЦИЯ': distance.strip(), 
                            'РЕЗУЛЬТАТ': res_time,
                            'СЕКУНДЫ': seconds
                        })
                        found_msgs.append(f"{pretty_name} ({res_time})")
                    
                    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                    df.to_excel(DB_PATH, index=False)
                    
                    not_found = [t.title() for t in requested_targets if t not in results_dict]
                    
                    success_text = f"✅ Успешно добавлено: {', '.join(found_msgs)}."
                    if not_found:
                        success_text += f" ❌ Не найдены: {', '.join(not_found)}."
                        
                    msg = dbc.Alert(success_text, color="success" if not not_found else "warning")
                else:
                    msg = dbc.Alert("Ни один из спортсменов не найден в PDF.", color="danger")
            
            except Exception as e:
                msg = dbc.Alert(f"Ошибка обработки: {e}", color="danger")

    display_df = df.tail(5).iloc[::-1].drop(columns=['СЕКУНДЫ'], errors='ignore')
    table = dash_table.DataTable(
        data=display_df.to_dict('records'),
        style_as_list_view=True,
        style_header={'fontWeight': 'bold'},
        style_cell={'textAlign': 'left', 'padding': '12px'}
    )
    
    return msg, table, reset_pdf, reset_manual, 0

# Коллбэки Вкладки 2
@app.callback(
    [Output("analytics-graph", "figure"),
     Output("analytics-table-container", "children"),
     Output("print-document-header", "children")], 
    [Input("filter-athlete", "value"),
     Input("filter-distance", "value"),
     Input("filter-start", "value"),
     Input("filter-end", "value"),
     Input("tabs", "active_tab")] 
)
def update_analytics(athlete, distance, start_date, end_date, active_tab):
    df = pd.read_excel(DB_PATH)

    athlete_text = athlete.upper() if athlete else "ВСЕ"
    dist_text = f" | Дистанция: {distance.upper()}" if distance else ""
    report_title = html.Div([
        html.H1("AQUATRACK PRO | ИНДИВИДУАЛЬНЫЙ ОТЧЕТ"),
        html.H2(f"Спортсмен: {athlete_text}{dist_text}"),
        html.P(f"Дата формирования: {pd.Timestamp.now().strftime('%d.%m.%Y')}")
    ])

    if df.empty:
        return go.Figure().update_layout(title="Нет данных", template="plotly_dark"), html.Div("Нет данных"), report_title

    df['Дата_dt'] = pd.to_datetime(df['ДАТА'], format='%d.%m.%Y', errors='coerce')

    if athlete:
        df = df[df['СПОРТСМЕН'].str.contains(athlete, case=False, na=False)]
    if distance:
        df = df[df['ДИСТАНЦИЯ'].str.contains(distance, case=False, na=False)]
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
    Output("btn-print-pdf", "id"),
    Input("btn-print-pdf", "n_clicks"),
    prevent_initial_call=True
)

# Коллбэки Вкладки 3
@app.callback(Output("upload-bulk-text", "children"), Input("upload-bulk-pdfs", "filename"))
def update_bulk_upload_text(filenames):
    if filenames: return f"✅ Загружено файлов: {len(filenames)}"
    return "📁 Выбрать файлы"

@app.callback(
    [Output("bulk-status-msg", "children"),
     Output("bulk-results-store", "data"),
     Output("top20-table-container", "children"),
     Output("kpi-comparison-window", "children"),
     Output("kpi-comparison-window", "style")],
    [Input("btn-generate-top", "n_clicks"),
     Input("btn-clear-top20", "n_clicks")],
    [State("bulk-competition", "value"),
     State("bulk-distance", "value"),
     State("upload-bulk-pdfs", "contents"),
     State("upload-bulk-pdfs", "filename"),
     State("bulk-results-store", "data")]
)
def manage_top20(gen_clicks, clear_clicks, comp_title, distance_title, list_of_contents, list_of_names, store_data):
    triggered_id = ctx.triggered_id

    if triggered_id == "btn-clear-top20":
        return dbc.Alert("Экран очищен.", color="info"), [], [], "", {'display': 'none'}

    data_structure = store_data or []
    table_stack = []
    kpi_content = ""
    kpi_style = {'display': 'none'}

    if triggered_id == "btn-generate-top":
        if not list_of_contents:
            return dbc.Alert("Загрузите PDF файлы!", color="danger"), data_structure, dash.no_update, dash.no_update, dash.no_update

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

            results = extract_tournament_ranking(temp_paths, limit_per_file=20)
            
            if not results:
                return dbc.Alert(f"Спортсмены не найдены ({comp_label}).", color="warning"), data_structure, dash.no_update, dash.no_update, dash.no_update

            df = pd.DataFrame(results)
            df = df.sort_values('СЕКУНДЫ') 
            df = df.drop_duplicates(subset=['СПОРТСМЕН'], keep='first') 

            tournament_data = {
                'competition': comp_label,
                'distance': dist_label,
                'raw_results': df.to_dict('records')
            }
            data_structure.append(tournament_data)
            
            msg = dbc.Alert(f"✅ {comp_label} добавлен! Обработано файлов: {len(list_of_names)}.", color="success")

        except Exception as e:
            return dbc.Alert(f"Ошибка: {e}", color="danger"), data_structure, dash.no_update, dash.no_update, dash.no_update
            
        finally:
            for path in temp_paths:
                if os.path.exists(path):
                    os.remove(path)

    for entry in data_structure:
        display_df = pd.DataFrame(entry['raw_results']).head(20)
        display_df.insert(0, 'МЕСТО', range(1, len(display_df) + 1))
        display_df = display_df.drop(columns=['СЕКУНДЫ'], errors='ignore')

        new_table_block = html.Div([
            html.H3(f"{entry['competition'].upper()} | ТОП-20: {entry['distance'].upper()}", style={'marginTop': '30px', 'marginBottom': '15px'}),
            dash_table.DataTable(
                data=display_df.to_dict('records'),
                style_as_list_view=True,
                style_header={'fontWeight': 'bold'},
                style_cell={'textAlign': 'left', 'padding': '12px'}
            ),
            html.Hr(style={'borderColor': '#444'})
        ])
        table_stack.append(new_table_block)

    if len(data_structure) >= 2:
        kpi_style = {
            'display': 'block',
            'background': 'linear-gradient(135deg, #2d333b 0%, #1f2328 100%)',
            'border': '2px solid #007bff',
            'borderRadius': '12px',
            'padding': '25px',
            'boxShadow': '0 8px 30px rgba(0,0,0,0.5)'
        }
        
        entry_last = data_structure[-1]
        entry_prev = data_structure[-2]

        def get_year(title):
            match = re.search(r'(20\d{2})', title)
            return int(match.group(1)) if match else 0

        year_last = get_year(entry_last['competition'])
        year_prev = get_year(entry_prev['competition'])

        if year_last > 0 and year_prev > 0 and year_prev > year_last:
            target_entry = entry_prev
            base_entry = entry_last
        else:
            target_entry = entry_last
            base_entry = entry_prev

        new_df = pd.DataFrame(target_entry['raw_results']).head(20)
        old_df = pd.DataFrame(base_entry['raw_results']).head(20)

        def calc_kpis(df):
            if df.empty: return 0, 0, 0
            return df.iloc[0]['СЕКУНДЫ'], df['СЕКУНДЫ'].mean(), df.iloc[-1]['СЕКУНДЫ']

        nf, nm, nl = calc_kpis(new_df)
        of, om, ol = calc_kpis(old_df)

        def format_diff(new_v, old_v):
            diff = new_v - old_v
            if abs(diff) < 0.001: 
                return html.Div([html.Span("≈ Стабильно", style={'color': '#a1a1a1'})])
            
            color = "#2ecc71" if diff < 0 else "#e74c3c"
            arrow = "▼ Улучшение" if diff < 0 else "▲ Ухудшение"
            plus = "+" if diff > 0 else ""
            
            return html.Div([
                html.Span(f"{arrow} ({plus}{diff:.2f} сек)", style={'color': color, 'fontWeight': 'bold'})
            ])

        box_style = {'textAlign': 'center', 'background': 'rgba(0,0,0,0.2)', 'borderRadius': '8px', 'padding': '15px'}
        label_style = {'color': '#a1a1a1', 'fontSize': '0.9rem', 'fontWeight': '600', 'marginBottom': '8px'}
        value_style = {'color': '#ffffff', 'fontSize': '1.6rem', 'fontWeight': '700', 'marginBottom': '5px'}

        kpi_title_text = f"ДИНАМИКА: {target_entry['competition'].upper()} ОТНОСИТЕЛЬНО {base_entry['competition'].upper()}"

        kpi_content = html.Div([
            html.H4(kpi_title_text, style={'textAlign': 'center', 'fontWeight': 'bold', 'marginBottom': '20px', 'color': '#fff'}),
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("ВРЕМЯ ЛИДЕРА (#1)", style=label_style),
                    html.Div(f"{new_df.iloc[0]['РЕЗУЛЬТАТ']}", style=value_style),
                    format_diff(nf, of)
                ], style=box_style), width=4),
                
                dbc.Col(html.Div([
                    html.Div("СРЕДНЕЕ ВРЕМЯ (Топ-20)", style=label_style),
                    html.Div(f"{nm:.2f} сек", style=value_style),
                    format_diff(nm, om)
                ], style=box_style), width=4),

                dbc.Col(html.Div([
                    html.Div("ВРЕМЯ ПРОХОДА (#20)", style=label_style),
                    html.Div(f"{new_df.iloc[-1]['РЕЗУЛЬТАТ']}", style=value_style),
                    format_diff(nl, ol)
                ], style=box_style), width=4),
            ], className="justify-content-center")
        ])

    return msg if triggered_id == "btn-generate-top" else dash.no_update, data_structure, table_stack, kpi_content, kpi_style

app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0) {
            setTimeout(function() { window.print(); }, 200);
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("btn-print-top20", "id"),
    Input("btn-print-top20", "n_clicks"),
    prevent_initial_call=True
)

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

if __name__ == '__main__':
    print("="*60)
    print(" 🚀 AQUATRACK PRO УСПЕШНО ЗАПУЩЕН!")
    print("="*60)
    print(" - Интерфейс откроется в вашем браузере автоматически.")
    print(" - Пожалуйста, НЕ ЗАКРЫВАЙТЕ это черное окно, пока работаете.")
    print(" - Чтобы полностью остановить программу, закройте это окно крестиком.")
    print("="*60)
    
    Timer(1.5, open_browser).start()
    app.run(host='127.0.0.1', port=8050, debug=False)