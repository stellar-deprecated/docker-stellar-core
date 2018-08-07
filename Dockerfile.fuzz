FROM stellar/base:latest

MAINTAINER Mat Schaffer <mat@stellar.org>

ENV AFL_VERSION 2.52b

ADD fuzz/install /
RUN /install

ADD utils /utils
ADD fuzz/trace /
ADD fuzz/start /

CMD ["/start"]
