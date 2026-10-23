FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY src/ /build/src/
RUN npm run build

FROM ubuntu:26.04 AS app
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && useradd --uid 10001 --create-home stream \
    && mkdir -p /var/lib/tactic_stream \
    && chown stream:stream /var/lib/tactic_stream
ENV PATH="/opt/venv/bin:$PATH" TACTIC_DATA_DIR=/var/lib/tactic_stream
WORKDIR /opt/tactic_stream
COPY pyproject.toml README.md LICENSE* ./
COPY src/ ./src/
# Replace checked-in assets with this build; stale hashes must not enter the image.
RUN rm -rf src/tactic_stream/web/assets src/tactic_stream/web/index.html
COPY --from=frontend /build/src/tactic_stream/web/ ./src/tactic_stream/web/
RUN pip install --no-cache-dir '.[postgres]'
USER stream
EXPOSE 8081
CMD ["tactic-stream", "--data-dir", "/var/lib/tactic_stream", "serve", "--host", "0.0.0.0"]

FROM ubuntu:26.04 AS apache
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends apache2 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && a2enmod proxy proxy_http proxy_balancer lbmethod_byrequests headers \
    && a2dissite 000-default
RUN curl --fail --silent --show-error --location https://download.webmin.com/developers-key.asc -o /usr/share/keyrings/webmin.asc \
    && printf 'deb [signed-by=/usr/share/keyrings/webmin.asc] https://download.webmin.com/download/newkey/repository stable contrib\n' > /etc/apt/sources.list.d/webmin.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends webmin openssl \
    && rm -rf /var/lib/apt/lists/*
COPY deploy/docker/apache.conf /etc/apache2/sites-available/tactic-stream.conf
COPY deploy/docker/start-apache.sh /usr/local/bin/start-apache
RUN a2ensite tactic-stream && apache2ctl configtest
EXPOSE 80 10000
CMD ["sh", "/usr/local/bin/start-apache"]
