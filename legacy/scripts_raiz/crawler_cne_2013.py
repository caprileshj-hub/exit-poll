# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import time
import json
import re
import os

class CNECrawler2013:
    """
    Crawler diseñado para extraer la estructura de centros de votación y sus resultados históricos
    desde la copia de Wayback Machine del sitio del CNE (Elección Presidencial 2013).
    """
    
    def __init__(self):
        # URL base apuntando al snapshot de Mayo 2013
        self.base_url = "https://web.archive.org/web/20130505152937/http://www.cne.gob.ve/resultado_presidencial_2013/r/1/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.centros_data = []
        self.visited_urls = set()

    def _get_soup(self, relative_path):
        """Descarga y parsea una página del CNE desde Wayback Machine."""
        if relative_path in self.visited_urls:
            return None
        
        url = f"{self.base_url}{relative_path}"
        print(f"🌐 GET {url}")
        
        try:
            # Pausa para respetar límites de Wayback Machine y evitar bloqueos
            time.sleep(1.5) 
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                self.visited_urls.add(relative_path)
                return BeautifulSoup(response.content, 'html.parser')
            else:
                print(f"❌ Error {response.status_code} en {relative_path}")
                return None
        except Exception as e:
            print(f"❌ Excepción conectando a {url}: {e}")
            return None

    def extraer_id_centro(self, href):
        """Extrae el ID del centro (generalmente 9 dígitos) desde el enlace HTML."""
        # Ejemplo href: reg_010101001.html 
        match = re.search(r'reg_(\d+)\.html', href)
        if match:
            return match.group(1)
        return "UNKNOWN"

    def procesar_parroquia(self, soup, codigo_parroquia):
        """
        Busca la tabla de centros en la página de la parroquia.
        Extrae: Nombre, ID (del link), Votos Oficialismo, Votos Oposición.
        """
        # Buscamos todas las tablas y filtramos la que parece tener datos de centros
        tablas = soup.find_all('table')
        
        centros_encontrados = 0
        
        for tabla in tablas:
            filas = tabla.find_all('tr')
            for fila in filas:
                celdas = fila.find_all('td')
                if not celdas: continue
                
                # Verificar si la primera celda tiene un link a un centro (patrón reg_...)
                link = celdas[0].find('a', href=True)
                if link and 'reg_' in link['href']:
                    href = link['href']
                    nombre_centro = link.get_text(strip=True)
                    id_centro = self.extraer_id_centro(href)
                    
                    # Extraer datos numéricos de las siguientes celdas
                    votos = []
                    for celda in celdas[1:]:
                        # Limpiar puntos de miles (ej: "1.200" -> "1200")
                        texto = celda.get_text(strip=True).replace('.', '')
                        if texto.isdigit():
                            votos.append(int(texto))
                    
                    # Heurística para 2013:
                    # Tomamos los dos valores más altos como referencia de la polarización del centro.
                    if len(votos) >= 2:
                        votos_ordenados = sorted(votos, reverse=True)
                        voto_mayor = votos_ordenados[0]
                        voto_segundo = votos_ordenados[1]
                        total_validos = sum(votos)
                        
                        self.centros_data.append({
                            'estado_code': codigo_parroquia[:2],
                            'municipio_code': codigo_parroquia[2:4],
                            'parroquia_code': codigo_parroquia[4:6],
                            'id_centro': id_centro,
                            'nombre': nombre_centro,
                            'votos_top1': voto_mayor, 
                            'votos_top2': voto_segundo,
                            'total_historico': total_validos,
                            'source_url': href
                        })
                        centros_encontrados += 1
        
        print(f"   -> Encontrados {centros_encontrados} centros en Parroquia {codigo_parroquia}")

    def crawl_recursive(self, codigo_actual, nivel):
        """
        Recorre recursivamente: Estado -> Municipio -> Parroquia.
        nivel 0: Estado (XX0000)
        nivel 1: Municipio (XXXX00)
        nivel 2: Parroquia (XXXXXX) -> Procesa Centros
        """
        filename = f"reg_{codigo_actual}.html"
        soup = self._get_soup(filename)
        if not soup: return

        if nivel == 2:
            # Estamos en nivel Parroquia, extraemos centros y terminamos esta rama
            self.procesar_parroquia(soup, codigo_actual)
            return

        # Buscar sub-enlaces para bajar de nivel
        links = soup.find_all('a', href=True)
        sub_codigos = set()
        
        for link in links:
            href = link['href']
            # Regex para capturar reg_XXXXXX.html
            match = re.search(r'reg_(\d{6})\.html', href)
            if match:
                codigo_encontrado = match.group(1)
                
                # Validar jerarquía para no saltar a otros estados
                if nivel == 0: # Estado -> Municipio
                    # Debe coincidir el prefijo de estado (XX) y tener municipio != 00
                    if codigo_encontrado.startswith(codigo_actual[:2]) and codigo_encontrado[2:4] != '00' and codigo_encontrado[4:] == '00':
                        sub_codigos.add(codigo_encontrado)
                
                elif nivel == 1: # Municipio -> Parroquia
                    # Debe coincidir prefijo estado+mun (XXXX) y tener parroquia != 00
                    if codigo_encontrado.startswith(codigo_actual[:4]) and codigo_encontrado[4:] != '00':
                        sub_codigos.add(codigo_encontrado)

        # Iterar sobre los hijos encontrados
        for sub_code in sorted(list(sub_codigos)):
            self.crawl_recursive(sub_code, nivel + 1)

    def ejecutar(self, codigo_estado_inicial="010000"):
        print(f"🚀 Iniciando Crawling desde {codigo_estado_inicial}...")
        self.crawl_recursive(codigo_estado_inicial, 0)
        
        # Guardar resultados
        archivo_salida = f"centros_cne_2013_{codigo_estado_inicial}.json"
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(self.centros_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Finalizado. Datos guardados en {archivo_salida}")

if __name__ == "__main__":
    # Ejemplo: Crawling de Distrito Capital (010000)
    # Puedes cambiar esto por el código de otro estado (ej. Zulia 210000, Miranda 130000)
    crawler = CNECrawler2013()
    crawler.ejecutar("010000")
