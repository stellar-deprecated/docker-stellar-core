FROM stellar/base:latest

MAINTAINER Mat Schaffer <mat@stellar.org>

ENV STELLAR_CORE_VERSION 12.4.0-1179-d2a53959

EXPOSE 11625
EXPOSE 11626

VOLUME /data
VOLUME /postgresql-unix-sockets
VOLUME /heka

ADD install /
RUN /install

ADD heka /heka
ADD confd /etc/confd
ADD utils /utils
ADD start /

CMD ["/start"]
