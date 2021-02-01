FROM ubuntu:xenial

MAINTAINER Mat Schaffer <mat@stellar.org>

ENV STELLAR_CORE_VERSION 15.2.0-441.620af1f.xenial~clawbackPR~buildtests

EXPOSE 11625
EXPOSE 11626

VOLUME /data
VOLUME /postgresql-unix-sockets
VOLUME /heka

ADD install /
RUN /install

RUN wget -qO - https://apt.stellar.org/SDF.asc | apt-key add -
RUN echo "deb https://apt.stellar.org xenial unstable" | tee -a /etc/apt/sources.list.d/SDF-unstable.list
RUN apt-get update
RUN apt-get install -y stellar-core=${STELLAR_CORE_VERSION}

ADD heka /heka
ADD confd /etc/confd
ADD utils /utils
ADD start /

CMD ["/start"]
