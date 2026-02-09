# Bruk en lettvekts Python-image
FROM python:3.13-slim

# Installer uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Sett arbeidskatalog
WORKDIR /app

# Kopier prosjektfiler
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY bergen_2026_01_09.csv ./

# Installer avhengigheter (inkludert prosjektet i editable mode)
RUN uv sync --frozen

# Sett PYTHONPATH så Python finner 'frcm' modulen i 'src'
ENV PYTHONPATH=/app/src

# Kommando for å kjøre modellen
ENTRYPOINT ["uv", "run", "python", "-m", "frcm"]
CMD ["./bergen_2026_01_09.csv"]