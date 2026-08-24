#support until 2029
FROM python:3.14.2-slim-bookworm

WORKDIR /app

COPY /src/geodjango/requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y binutils libproj-dev gdal-bin qgis


COPY . .
# recordar
# instalar gdal y geos en el dockerfile

CMD [ "python3", "src/geodjango/manage.py", "runserver", "0.0.0.0:8000"]
