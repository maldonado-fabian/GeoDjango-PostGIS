
### Para correr el server en Apple Silicon ARM64

requisitos: geos, gdal

```brew install geos gdal```

librerias necesarias en requirements.txt

En terminal:

```GDAL_LIBRARY_PATH=/opt/homebrew/lib/libgdal.dylib GEOS_LIBRARY_PATH=/opt/homebrew/lib/libgeos_c.dylib ./manage.py runserver```

