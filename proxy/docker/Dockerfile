FROM ubuntu:24.04

RUN apt-get update && apt-get install -y wget unzip netcat-traditional --no-install-recommends

RUN wget https://github.com/jthomperoo/simple-proxy/releases/download/v1.4.0/simple-proxy_linux_amd64.zip \
    && unzip -d simple-proxy simple-proxy_linux_amd64.zip \
    && cp simple-proxy/simple-proxy /usr/bin/simple-proxy \
    && rm -r simple-proxy/ simple-proxy_linux_amd64.zip

RUN groupadd -r proxy && useradd --no-log-init -r -g proxy proxy
USER proxy

COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["./start.sh"]
