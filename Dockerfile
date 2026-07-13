# --- Stage 1: Build & Package Resolution ---
FROM python:3.11-slim AS builder

#Installs the compilation tools for our Debian PM
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl\
    build-essential \
    && rm -rf /var/lib/apt/lists/*       
    #Deletes the cached packages

# Force pip to install user-level packages to a predictable, shared path
ENV PYTHONUSERBASE=/usr/local/user_base

#Creates a directory for our application and sets it as the working directory
WORKDIR /app
# Copies the pyproject.toml file to the working directory and installs the dependencies specified in it first,then  caches it(its a time consuming process)
COPY pyproject.toml .
RUN pip install --no-cache-dir --user .

COPY src/ ./src/
COPY configs/ ./configs/
RUN pip install --no-cache-dir --user .

# --- Stage 2: Runtime Environment ---
FROM python:3.11-slim

#Creates a non-root user and group for the application to run as, enhancing security by limiting permissions.
RUN groupadd -r app && useradd -r -g app -d /app -s /bin/false app

WORKDIR /app


ENV PYTHONUSERBASE=/usr/local/user_base
ENV PATH=$PYTHONUSERBASE/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production


COPY --from=builder $PYTHONUSERBASE $PYTHONUSERBASE
COPY --from=builder /app/src ./src
COPY --from=builder /app/configs ./configs


RUN chown -R app:app /app

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]