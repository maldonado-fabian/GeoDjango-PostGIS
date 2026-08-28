"""Carga las evaluaciones por inmueble de una amenaza desde un CSV.

El CSV lo produce `scripts/excel_a_csv.py` a partir del .xlsx de la amenaza:

    rol_sii,1,2,...,N

donde el número de columna es el ORDEN del sub-indicador dentro de la amenaza.
El comando lo resuelve al `sub_indicadores.id` real consultando la base, así que
sirve para cualquier amenaza — no sólo para la primera, que era la limitación del
notebook `poblar_fuerza_bruta.ipynb` (asumía `id_subindicador = n° de columna`).

El match es por POSICIÓN, no por nombre: los nombres del Excel y de la base
difieren en varios casos ("Muro cortafuegos" vs "Muro cortafuego", "N° de calles
de acceso" vs "Número de calles de acceso").
"""

import csv
from collections import Counter, defaultdict
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.models import Amenazas, Clases, Evaluacion, Inmuebles, SubIndicadores

VACIOS = {'', '-', '--', 'n/a', 'N/A', 'nan', 'None'}


class Command(BaseCommand):
    help = 'Carga las evaluaciones de una amenaza desde un CSV generado con scripts/excel_a_csv.py'

    def add_arguments(self, parser):
        parser.add_argument('csv', help='CSV con cabecera rol_sii,1,2,...,N')
        parser.add_argument('--amenaza', required=True,
                            help='nombre de la amenaza, tal como está en la tabla amenazas')
        parser.add_argument('--fecha', default=None,
                            help='fecha de evaluación en formato AAAA-MM-DD (por defecto, hoy)')
        parser.add_argument('--dry-run', action='store_true',
                            help='valida y reporta sin escribir en la base')

    def handle(self, *args, **options):
        amenaza = self._amenaza(options['amenaza'])
        fecha = self._fecha(options['fecha'])
        subindicadores = self._subindicadores(amenaza)
        clases = self._clases_validas(subindicadores)
        inmuebles = dict(Inmuebles.objects.values_list('rol_sii', 'id'))

        self.stdout.write(
            f'Amenaza "{amenaza.nombre}" (id {amenaza.pk}): '
            f'{len(subindicadores)} sub-indicadores · {len(inmuebles)} inmuebles en la base'
        )

        filas, columnas = self._leer_csv(options['csv'])
        if columnas != len(subindicadores):
            raise CommandError(
                f'El CSV trae {columnas} columnas de valores pero la amenaza '
                f'"{amenaza.nombre}" tiene {len(subindicadores)} sub-indicadores. '
                f'¿El CSV corresponde a otra amenaza?'
            )

        evaluaciones, informe = self._construir(
            filas, subindicadores, clases, inmuebles, fecha
        )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                f'\n[dry-run] {len(evaluaciones)} evaluaciones listas para escribir. '
                f'No se modificó la base.'
            ))
        else:
            creadas, actualizadas = self._guardar(evaluaciones, amenaza)
            self.stdout.write(self.style.SUCCESS(
                f'\n{creadas} evaluaciones creadas · {actualizadas} actualizadas'
            ))

        self._informar(informe)

    # ── Resolución de catálogo ───────────────────────────────────────────────

    def _amenaza(self, nombre):
        try:
            return Amenazas.objects.get(nombre__iexact=nombre)
        except Amenazas.DoesNotExist:
            existentes = ', '.join(Amenazas.objects.values_list('nombre', flat=True)) or '(ninguna)'
            raise CommandError(f'No existe la amenaza "{nombre}". Disponibles: {existentes}')

    def _fecha(self, valor):
        if not valor:
            return date.today()
        try:
            return datetime.strptime(valor, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f'Fecha inválida: "{valor}". Se espera AAAA-MM-DD.')

    def _subindicadores(self, amenaza):
        """Sub-indicadores de la amenaza en el mismo orden en que el Excel los lista.

        `scripts/excel_a_csv.py` los emite de izquierda a derecha, que es el orden
        en que se insertaron; de ahí que ordenar por (indicador_id, id) coincida.
        """
        subs = list(
            SubIndicadores.objects
            .filter(indicador__amenaza=amenaza)
            .order_by('indicador_id', 'id')
        )
        if not subs:
            raise CommandError(f'La amenaza "{amenaza.nombre}" no tiene sub-indicadores cargados.')
        return subs

    def _clases_validas(self, subindicadores):
        """{sub_indicador_id: {valores admitidos}}"""
        validas = defaultdict(set)
        for sub_id, valor in Clases.objects.filter(
            sub_indicador__in=subindicadores
        ).values_list('sub_indicador_id', 'valor'):
            validas[sub_id].add(valor)
        return validas

    # ── Lectura y armado ─────────────────────────────────────────────────────

    def _leer_csv(self, ruta):
        try:
            with open(ruta, newline='', encoding='utf-8') as fh:
                filas = list(csv.reader(fh))
        except OSError as e:
            raise CommandError(f'No se pudo leer el CSV: {e}')

        if len(filas) < 2:
            raise CommandError('El CSV no tiene filas de datos.')

        cabecera = filas[0]
        if not cabecera or cabecera[0].strip().lower() != 'rol_sii':
            raise CommandError('La primera columna del CSV debe llamarse "rol_sii".')

        return filas[1:], len(cabecera) - 1

    def _construir(self, filas, subindicadores, clases, inmuebles, fecha):
        ahora = timezone.now()
        evaluaciones = []
        informe = {
            'roles_no_encontrados': set(),
            'valores_invalidos': Counter(),
            'celdas_vacias': 0,
            'filas': len(filas),
        }

        for fila in filas:
            rol = fila[0].strip()
            id_inmueble = inmuebles.get(rol)
            if id_inmueble is None:
                informe['roles_no_encontrados'].add(rol)
                continue

            for pos, sub in enumerate(subindicadores):
                bruto = fila[pos + 1].strip() if pos + 1 < len(fila) else ''

                if bruto in VACIOS:
                    informe['celdas_vacias'] += 1
                    continue

                try:
                    valor = int(float(bruto))
                except ValueError:
                    informe['valores_invalidos'][(sub.nombre, bruto)] += 1
                    continue

                if valor not in clases[sub.pk]:
                    informe['valores_invalidos'][(sub.nombre, bruto)] += 1
                    continue

                evaluaciones.append(Evaluacion(
                    id_inmueble_id=id_inmueble,
                    id_subindicador_id=sub.pk,
                    valor=valor,
                    fecha_evaluacion=fecha,
                    fecha_creacion=ahora,
                    fecha_actualizacion=ahora,
                ))

        return evaluaciones, informe

    # ── Escritura ────────────────────────────────────────────────────────────

    def _guardar(self, evaluaciones, amenaza):
        """Upsert idempotente: re-ejecutar el comando actualiza, no duplica."""
        if not evaluaciones:
            return 0, 0

        existentes = set(
            Evaluacion.objects
            .filter(id_subindicador__indicador__amenaza=amenaza)
            .values_list('id_inmueble_id', 'id_subindicador_id')
        )
        actualizadas = sum(
            1 for e in evaluaciones
            if (e.id_inmueble_id, e.id_subindicador_id) in existentes
        )

        with transaction.atomic():
            Evaluacion.objects.bulk_create(
                evaluaciones,
                update_conflicts=True,
                unique_fields=['id_inmueble', 'id_subindicador'],
                update_fields=['valor', 'fecha_evaluacion', 'fecha_actualizacion'],
                batch_size=1000,
            )

        return len(evaluaciones) - actualizadas, actualizadas

    # ── Informe ──────────────────────────────────────────────────────────────

    def _informar(self, informe):
        self.stdout.write(f'\nFilas leídas: {informe["filas"]}')

        if informe['celdas_vacias']:
            self.stdout.write(f'Celdas sin evaluar omitidas: {informe["celdas_vacias"]}')

        faltantes = informe['roles_no_encontrados']
        if faltantes:
            muestra = ', '.join(sorted(faltantes)[:5])
            self.stdout.write(self.style.WARNING(
                f'Roles SII sin inmueble en la base: {len(faltantes)} (ej.: {muestra}…)'
            ))

        invalidos = informe['valores_invalidos']
        if invalidos:
            total = sum(invalidos.values())
            self.stdout.write(self.style.WARNING(
                f'Valores rechazados por no corresponder a ninguna clase: {total}'
            ))
            for (sub, valor), n in invalidos.most_common():
                self.stdout.write(f'    {sub}: "{valor}" ×{n}')
