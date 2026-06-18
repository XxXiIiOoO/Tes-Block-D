FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /opt/blocktest-presets

COPY requirements.txt /tmp/preset-requirements.txt
RUN pip install --no-cache-dir -r /tmp/preset-requirements.txt

COPY run_preset.py /opt/blocktest-presets/run_preset.py
