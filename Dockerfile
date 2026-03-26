FROM cdrx/pyinstaller-windows:python3

USER root

# Ставим xvfb для виртуального экрана
RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем весь код и папку assets в контейнер
COPY . .

# Обновляем pip и ставим упаковщик
RUN python -m pip install --upgrade pip

# Ставим нужные версии упаковщика
RUN python -m pip install "pyinstaller==5.13.2" "setuptools<65.0.0" "wheel" "pefile"

# Ставим библиотеки нашего проекта
RUN pip install -r requirements.txt

# Собираем .exe файл (добавлены --windowed и --add-data)
RUN xvfb-run -a pyinstaller --onefile --clean \
    --name "AquaTrack_Pro" \
    --hidden-import "pandas" \
    --hidden-import "openpyxl" \
    --hidden-import "pdfplumber" \
    --collect-all "dash" \
    --collect-all "dash_bootstrap_components" \
    --collect-all "plotly" \
    --add-data "assets;assets" \
    app.py