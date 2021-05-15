FROM stellar/base:latest

MAINTAINER Mat Schaffer <mat@stellar.org>

EXPOSE 11625
EXPOSE 11626

VOLUME /data
VOLUME /heka

ADD stellar-core.deb /
ADD install /
RUN /install

ADD heka /heka
ADD confd /etc/confd
ADD utils /utils
ADD start /

CMD ["/start"]
