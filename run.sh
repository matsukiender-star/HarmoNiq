#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ ! -d "venv" ]; then
    echo "Entorno virtual no encontrado. Creando..."
    python3 -m venv --without-pip venv
    ./venv/bin/python -m ensurepip || curl -sSL https://bootstrap.pypa.io/get-pip.py | ./venv/bin/python
    ./venv/bin/pip install yt-dlp shazamio mutagen fastapi uvicorn static-ffmpeg aiofiles
fi

./venv/bin/python run.py
