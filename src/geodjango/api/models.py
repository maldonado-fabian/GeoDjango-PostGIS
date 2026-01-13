# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.contrib.gis.db import models


class Amenazas(models.Model):
    nombre = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'amenazas'


class Clases(models.Model):
    sub_indicador = models.ForeignKey('SubIndicadores', models.DO_NOTHING)
    nombre = models.CharField(max_length=100)
    valor = models.IntegerField()
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'clases'
        unique_together = (('sub_indicador', 'nombre'),)


class Evaluacion(models.Model):
    id_inmueble = models.ForeignKey('Inmuebles', models.DO_NOTHING, db_column='id_inmueble')
    id_clase = models.ForeignKey(Clases, models.DO_NOTHING, db_column='id_clase')
    fecha_evaluacion = models.DateField()
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'evaluacion'
        unique_together = (('id_inmueble', 'id_clase', 'fecha_evaluacion'),)


class Indicadores(models.Model):
    amenaza = models.ForeignKey(Amenazas, models.DO_NOTHING)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    peso = models.DecimalField(max_digits=2, decimal_places=2)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'indicadores'
        unique_together = (('amenaza', 'nombre'),)


class Inmuebles(models.Model):
    manzana = models.IntegerField(blank=True, null=True)
    predio = models.IntegerField(blank=True, null=True)
    rol_sii = models.IntegerField(unique=True)
    direccion = models.CharField(max_length=255)
    geom = models.PointField(blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'inmuebles'


class SubIndicadores(models.Model):
    indicador = models.ForeignKey(Indicadores, models.DO_NOTHING)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    peso = models.DecimalField(max_digits=5, decimal_places=4)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sub_indicadores'
        unique_together = (('indicador', 'nombre'),)
