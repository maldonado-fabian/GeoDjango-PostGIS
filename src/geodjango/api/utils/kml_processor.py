# utils/kml_processor.py
import re
import zipfile
import tempfile
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom

class KMLProcessor:
    @staticmethod
    def parse_description_html(html_content):
        """Extrae datos de la tabla HTML en description"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        datos = {
            'rol_sii': '',
            'direccion': '',
            'mzs_sii': '',
            'prd_sii': ''
        }
        
        # Buscar todas las filas de la tabla
        rows = soup.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) == 2:
                key = tds[0].get_text(strip=True)
                value = tds[1].get_text(strip=True)
                
                if key == 'ROL_SII':
                    datos['rol_sii'] = value
                elif key == 'Direccion':
                    datos['direccion'] = value
                elif key == 'Mzs_SII':
                    datos['mzs_sii'] = value
                elif key == 'Prd_SII':
                    datos['prd_sii'] = value
        
        return datos
    
    @staticmethod
    def parse_geometry(geom_str):
        """Convierte cadena MULTIPOLYGON Z a Geometry de Django"""
        try:
            # Limpiar y convertir a formato WKT estándar
            if geom_str.startswith('MULTIPOLYGON Z'):
                # Remover la Z si no es necesaria
                geom_str = geom_str.replace('MULTIPOLYGON Z', 'MULTIPOLYGON')
            
            # Crear geometría
            geometry = GEOSGeometry(geom_str, srid=4326)
            
            # Asegurar que sea MultiPolygon
            if isinstance(geometry, Polygon):
                geometry = MultiPolygon(geometry)
            
            return geometry
        except Exception as e:
            raise ValueError(f"Error al parsear geometría: {e}")
    
    @staticmethod
    def extract_from_kml(kml_content):
        """Extrae datos de un archivo KML"""
        root = ET.fromstring(kml_content)
        
        # Namespaces de KML
        namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'gx': 'http://www.google.com/kml/ext/2.2'
        }
        
        inmuebles = []
        
        # Buscar todos los Placemarks
        placemarks = root.findall('.//kml:Placemark', namespaces)
        
        for placemark in placemarks:
            # Extraer description
            description_elem = placemark.find('kml:description', namespaces)
            if description_elem is None:
                description_elem = placemark.find('description', namespaces)
            
            # Extraer geometry
            geometry_elem = None
            for geom_tag in ['MultiGeometry', 'Polygon', 'MultiPolygon']:
                geometry_elem = placemark.find(f'.//kml:{geom_tag}', namespaces)
                if geometry_elem is not None:
                    break
            
            if description_elem is not None and geometry_elem is not None:
                # Parsear datos
                datos = KMLProcessor.parse_description_html(
                    description_elem.text or ''
                )
                
                # Convertir geometría a WKT
                # Nota: Para una implementación más robusta, podrías usar
                # lxml o parsear directamente las coordenadas
                coordinates = []
                coord_elements = geometry_elem.findall('.//kml:coordinates', namespaces)
                
                for coords in coord_elements:
                    coord_text = coords.text.strip() if coords.text else ''
                    if coord_text:
                        # Parsear coordenadas
                        coord_list = []
                        for point in coord_text.split():
                            xyz = point.split(',')
                            if len(xyz) >= 2:
                                # Tomar solo longitud y latitud (ignorar Z si existe)
                                coord_list.append(f"{xyz[0]} {xyz[1]}")
                        
                        if coord_list:
                            coordinates.append(f"(({', '.join(coord_list)}))")
                
                if coordinates:
                    wkt_geom = f"MULTIPOLYGON({', '.join(coordinates)})"
                    datos['geom'] = KMLProcessor.parse_geometry(wkt_geom)
                    
                    inmuebles.append(datos)
        
        return inmuebles
    
    @staticmethod
    def extract_from_kmz(file_path):
        """Extrae datos de un archivo KMZ"""
        with zipfile.ZipFile(file_path, 'r') as kmz:
            # Buscar el archivo KML principal
            kml_files = [f for f in kmz.namelist() if f.endswith('.kml')]
            
            if not kml_files:
                raise ValueError("No se encontró archivo KML en el KMZ")
            
            # Leer el primer KML
            with kmz.open(kml_files[0]) as kml_file:
                kml_content = kml_file.read().decode('utf-8')
            
            return KMLProcessor.extract_from_kml(kml_content)