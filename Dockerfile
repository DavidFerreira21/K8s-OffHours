FROM alpine:3.19

ARG KUBECTL_VERSION=v1.29.2

RUN apk add --no-cache \
    python3 \
    ca-certificates \
    curl

RUN curl -L -o /usr/local/bin/kubectl \
    https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl && \
    chmod +x /usr/local/bin/kubectl

COPY scripts/offhours.py /app/offhours.py

WORKDIR /app

ENTRYPOINT ["python3", "/app/offhours.py"]
