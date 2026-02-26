FROM ubuntu:24.04

RUN apt-get update && apt-get install -y wget unzip

RUN wget https://github.com/jthomperoo/simple-proxy/releases/download/v1.4.0/simple-proxy_linux_amd64.zip \
    && unzip -d simple-proxy simple-proxy_linux_amd64.zip \
    && cp simple-proxy/simple-proxy /usr/bin/simple-proxy \
    && rm -r simple-proxy/ simple-proxy_linux_amd64.zip

COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["./start.sh"]
