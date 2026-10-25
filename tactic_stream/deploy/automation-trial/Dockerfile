ARG BASE=tactic-stream-linux-app:latest
FROM ${BASE}
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libegl1 libopengl0 libglib2.0-0t64 libfontconfig1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && /opt/venv/bin/pip install --no-cache-dir PySide6==6.11.1
RUN apt-get update && apt-get install -y --no-install-recommends libxkbcommon0 libdbus-1-3 libgssapi-krb5-2 && rm -rf /var/lib/apt/lists/*
COPY stream/ /opt/trial/src/
COPY pyproject.toml README.md /opt/trial/
RUN /opt/venv/bin/pip install --no-cache-dir /opt/trial
COPY handler/ /opt/trial/handler/
COPY runtime/ /opt/trial/runtime/
ENV HOME=/work/profile PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QSG_RENDER_LOOP=basic QT_QUICK_CONTROLS_STYLE=Basic
LABEL tactic.automation-trial="1"
USER 10001:10001
WORKDIR /work
ENTRYPOINT ["/opt/venv/bin/python", "/opt/trial/runtime/supervisor.py"]
