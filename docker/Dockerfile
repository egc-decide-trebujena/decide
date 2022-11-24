from python:3.8.13-alpine3.16

ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

RUN apk add --no-cache git postgresql-dev gcc libc-dev
RUN apk add --no-cache gcc g++ make libffi-dev python3-dev build-base
RUN apk add py3-pip py3-pillow py3-cffi py3-brotli gcc musl-dev python3-dev pango

RUN pip install gunicorn
RUN pip install ipdb
RUN pip install ipython

WORKDIR /app

RUN git clone https://github.com/egc-decide-trebujena/decide.git .
RUN git pull origin milestone/M2
RUN echo "$(<requirements.txt)"s
RUN pip install -U pip
RUN pip install -r requirements.txt

WORKDIR /app/decide

# local settings.py
ADD docker-settings.py /app/decide/local_settings.py

RUN ./manage.py collectstatic

#CMD ["gunicorn", "-w 5", "decide.wsgi", "--timeout=500", "-b 0.0.0.0:5000"]
