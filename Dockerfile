FROM alpine:3.21

ARG KUBECTL_VERSION=stable

RUN apk add --no-cache \
    python3 \
    ca-certificates \
    curl && \
    update-ca-certificates

RUN set -eux; \
    if [ "${KUBECTL_VERSION}" = "stable" ]; then \
      KVER="$(curl -fsSL https://dl.k8s.io/release/stable.txt)"; \
    else \
      KVER="${KUBECTL_VERSION}"; \
    fi; \
    curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KVER}/bin/linux/amd64/kubectl"; \
    curl -fsSL -o /tmp/kubectl.sha256 "https://dl.k8s.io/release/${KVER}/bin/linux/amd64/kubectl.sha256"; \
    echo "$(cat /tmp/kubectl.sha256)  /usr/local/bin/kubectl" | sha256sum -c -; \
    chmod +x /usr/local/bin/kubectl; \
    rm -f /tmp/kubectl.sha256

COPY scripts/offhours.py /app/offhours.py

WORKDIR /app

ENTRYPOINT ["python3", "/app/offhours.py"]
