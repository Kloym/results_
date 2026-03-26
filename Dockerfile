FROM cdrx/pyinstaller-windows:python3

USER root

RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip

RUN python -m pip install "pyinstaller==5.13.2" "setuptools<65.0.0" "wheel" "pefile"

RUN pip install -r requirements.txt

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