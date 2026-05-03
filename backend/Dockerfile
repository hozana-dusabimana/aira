FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libgl1 + libglib2.0-0 are kept so the optional ML backend (ultralytics/opencv)
# can run when AI_ENABLED=true without rebuilding the image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ml.txt ./
RUN pip install -r requirements.txt
# Build with --build-arg INSTALL_ML=1 to bake in the ML stack.
ARG INSTALL_ML=0
RUN if [ "$INSTALL_ML" = "1" ]; then pip install -r requirements-ml.txt; fi

COPY . .

RUN mkdir -p /app/uploads

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health',timeout=3).status==200 else 1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
