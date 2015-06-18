FROM stellar/base:latest

MAINTAINER Mat Schaffer <mat@stellar.org>

ENV STELLAR_CORE_VERSION 0.0.1-14-7331642a

EXPOSE 39133
EXPOSE 39132

VOLUME /data
VOLUME /heka

ADD install /
RUN /install

ADD heka /heka
ADD confd /etc/confd
ADD start /

CMD ["/start"]
