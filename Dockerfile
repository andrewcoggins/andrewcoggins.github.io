FROM python:3.7.1

COPY requirements.txt /tmp/

RUN cd /tmp && pip install -r requirements.txt && \
    rm -rf /tmp/requirements.txt /tmp/submodules /root/.cache

WORKDIR /home/app