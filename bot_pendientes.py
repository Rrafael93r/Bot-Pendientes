"""
Bot Pendientes - Cierre Pendientes Evento y Capita
==================================================
1. Inicia sesion en el portal Medicar (mismas credenciales que bot_medicar).
2. Abre el informe 'cierrePendientes.php'.
3. Ajusta el filtro de fechas: fecha_final = hoy, fecha_inicial = hoy - N dias (60).
4. Pulsa 'Exportar Pendientes Punto' y descarga el CSV generado.
5. Carga el CSV en la tabla MySQL `reporte_pendientes` (TRUNCATE + INSERT).

Pensado para ejecutarse una vez al dia (4:00 a.m.) via Programador de tareas.
"""

import os
import sys
import csv
import re
import datetime

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import pymysql

# =========================
# LOG
# =========================
LOG_FILE = "pendientes_actividad.log"


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# =========================
# CONFIG
# =========================
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

USUARIO_ID = os.getenv("USUARIO_ID")
LOGIN = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")
RUTA_DESCARGA = os.getenv("RUTA_DESCARGA", "./downloads")

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DB")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_TABLE = os.getenv("MYSQL_TABLE", "reporte_pendientes")

DIAS_ATRAS = int(os.getenv("PENDIENTES_DIAS_ATRAS", "60"))

BASE = "https://medicar.sis-colombia.com/pharmaser/mutualser"
URL_LOGIN = BASE + "/"
URL_INFORME = BASE + "/el_admin/informes/cierrePendientes.php"
URL_EXPORT = BASE + "/el_admin/informes/exportarPendientesCierrePunto.php"
URL_DOWNLOAD = BASE + "/el_admin/informes/download.php"

# Tiempo maximo (ms) para que el servidor genere el archivo (rangos amplios
# son lentos: ~14 s por dia; 60 dias ~14 min). 35 min de margen.
EXPORT_TIMEOUT_MS = 35 * 60 * 1000

# El portal devuelve 403 si el User-Agent parece un navegador automatizado.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# Columnas destino, EN EL MISMO ORDEN que las 28 primeras columnas del CSV.
COLUMNAS = [
    "localidad", "nombre_punto", "convenio", "plan", "subplan",
    "tipo_documento", "numero_documento", "nombre_beneficiario", "categoria",
    "no_autorizacion", "autorizacion", "tipo_formula", "fecha_pendiente",
    "numero_dias", "molecula", "plu_punto", "articulo_punto", "plu_opcion",
    "articulo_opcion", "cantidad_formulada", "cantidad_pendiente",
    "vlr_unitario", "vlr_total", "fecha_generacion", "lugar_entrega",
    "direccion_entrega", "telefono_entrega", "disponible",
]
# Indices (0-based) de las columnas que requieren conversion de tipo.
COL_ENTEROS = {13, 19, 20}          # numero_dias, cantidad_formulada, cantidad_pendiente
COL_DECIMALES = {21}                # vlr_unitario  (decimal normal, ej 1047080.000000)
COL_PESOS = {22}                    # vlr_total     (formato miles colombiano, ej 14.271.600)
COL_FECHA = {12}                    # fecha_pendiente  (YYYY-MM-DD)
COL_FECHAHORA = {23}                # fecha_generacion (YYYY-MM-DD HH:MM[:SS])


def validar_config():
    faltan = [k for k, v in {
        "USUARIO_ID": USUARIO_ID, "LOGIN": LOGIN, "PASSWORD": PASSWORD,
        "MYSQL_HOST": MYSQL_HOST, "MYSQL_DB": MYSQL_DB,
        "MYSQL_USER": MYSQL_USER, "MYSQL_PASSWORD": MYSQL_PASSWORD,
    }.items() if not v]
    if faltan:
        raise RuntimeError("Faltan variables en .env: " + ", ".join(faltan))
    if not os.path.exists(RUTA_DESCARGA):
        os.makedirs(RUTA_DESCARGA)
        log(f"Carpeta de descarga creada: {RUTA_DESCARGA}")


# =========================
# NAVEGACION / DESCARGA
# =========================
def login(page):
    log("Iniciando sesion...")
    page.goto(URL_LOGIN, wait_until="domcontentloaded")
    page.wait_for_selector("input[placeholder='Identificación']", timeout=30000)
    page.locator("input[placeholder='Identificación']").first.fill(USUARIO_ID)
    page.locator("input[placeholder='Login']").first.fill(LOGIN)
    page.locator("input[type='password']").first.fill(PASSWORD)
    with page.expect_navigation():
        page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")


def aceptar_terminos(page):
    try:
        page.locator("text=Aceptar").click(timeout=5000)
        log("Terminos aceptados.")
    except PWTimeout:
        pass


def calcular_fechas():
    hoy = datetime.date.today()
    inicio = hoy - datetime.timedelta(days=DIAS_ATRAS)
    return inicio, hoy


def descargar_csv(context, page):
    """Genera la exportacion y descarga el CSV directamente via HTTP autenticado.

    El boton 'Exportar Pendientes Punto' llama a exportarPendientesCierrePunto.php,
    que transmite una barra de progreso y al 100% redirige a
    download.php?file=PendientesPunto<ini>-<fin>.csv. En vez de depender del
    evento de descarga del navegador (fragil en rangos grandes), pedimos esas
    URLs con el APIRequestContext, que comparte las cookies de sesion.
    """
    inicio, fin = calcular_fechas()
    log(f"Rango de fechas: {inicio.isoformat()} -> {fin.isoformat()}")

    # Visitar el informe para asentar la sesion/cookies.
    page.goto(URL_INFORME, wait_until="networkidle")

    exp_url = (f"{URL_EXPORT}?orden_columna=despacho.fcdespa&tipo_orden="
               f"&f_fecha={inicio.isoformat()}&f_fecha_final={fin.isoformat()}"
               f"&f_ssc=todos&f_sucursal=todos&f_splan=todos")

    log("Generando archivo en el servidor (puede tardar varios minutos)...")
    r = context.request.get(exp_url, timeout=EXPORT_TIMEOUT_MS)
    if r.status != 200:
        raise RuntimeError(f"La exportacion respondio HTTP {r.status}.")
    html = r.text()

    # Nombre real del archivo desde el redirect final; si no, lo construimos.
    m = re.search(r'download\.php\?file=([^"\']+)', html)
    if m:
        filename = m.group(1).strip()
    else:
        filename = f"PendientesPunto{inicio.isoformat()}-{fin.isoformat()}.csv"
        log(f"ADVERTENCIA: no se hallo el redirect; usando nombre por defecto {filename}")
    log(f"Generacion completa. Archivo en servidor: {filename}")

    # Descargar el CSV.
    cr = context.request.get(f"{URL_DOWNLOAD}?file={filename}", timeout=180000)
    if cr.status != 200:
        raise RuntimeError(f"download.php respondio HTTP {cr.status}.")
    body = cr.body()
    if not body or not body.lstrip()[:9].lower().startswith(b"localidad"):
        raise RuntimeError("El archivo descargado no parece el CSV esperado "
                           f"(primeros bytes: {body[:60]!r}).")

    destino = os.path.join(RUTA_DESCARGA, "pendientes_punto.csv")
    tmp = destino + ".tmp"
    with open(tmp, "wb") as f:
        f.write(body)
    if os.path.exists(destino):
        os.remove(destino)
    os.rename(tmp, destino)
    log(f"CSV descargado: {destino} ({os.path.getsize(destino)} bytes)")
    return destino


# =========================
# PARSEO + CARGA A MYSQL
# =========================
def _to_int(v):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def _to_dec(v):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _to_pesos(v):
    """vlr_total viene con puntos como separador de miles (ej. '14.271.600').
    Se quitan los puntos para obtener el valor entero en pesos."""
    v = (v or "").strip()
    if v == "":
        return None
    s = v.replace(".", "")
    try:
        return int(s)
    except ValueError:
        return None


def _to_fecha(v):
    v = (v or "").strip()
    if v == "":
        return None
    return v[:10]  # YYYY-MM-DD


def _to_fechahora(v):
    v = (v or "").strip()
    if v == "":
        return None
    # Acepta 'YYYY-MM-DD HH:MM' o 'YYYY-MM-DD HH:MM:SS'
    if len(v) == 16:
        v = v + ":00"
    return v[:19]


def parsear_csv(ruta):
    """Lee el CSV (latin-1, separador ';') y devuelve filas listas para INSERT."""
    filas = []
    with open(ruta, "r", encoding="latin-1", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        encabezado = next(reader, None)
        if not encabezado:
            raise RuntimeError("El CSV esta vacio (sin encabezado).")
        for raw in reader:
            if not raw or all((c or "").strip() == "" for c in raw):
                continue
            campos = (raw + [""] * 28)[:28]  # asegurar 28 columnas
            fila = []
            for i in range(28):
                val = (campos[i] or "").strip()
                if i in COL_ENTEROS:
                    fila.append(_to_int(val))
                elif i in COL_DECIMALES:
                    fila.append(_to_dec(val))
                elif i in COL_PESOS:
                    fila.append(_to_pesos(val))
                elif i in COL_FECHA:
                    fila.append(_to_fecha(val))
                elif i in COL_FECHAHORA:
                    fila.append(_to_fechahora(val))
                else:
                    fila.append(val if val != "" else None)
            filas.append(tuple(fila))
    return filas


def cargar_mysql(filas):
    if not filas:
        log("ADVERTENCIA: 0 filas en el CSV. NO se trunca la tabla para no perder datos.")
        return 0

    placeholders = ", ".join(["%s"] * len(COLUMNAS))
    cols = ", ".join(f"`{c}`" for c in COLUMNAS)
    sql_insert = f"INSERT INTO `{MYSQL_TABLE}` ({cols}) VALUES ({placeholders})"

    log(f"Conectando a MySQL {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB} ...")
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, database=MYSQL_DB,
        charset="utf8mb4", connect_timeout=30, local_infile=False,
    )
    try:
        with conn.cursor() as cur:
            log(f"TRUNCATE `{MYSQL_TABLE}` ...")
            cur.execute(f"TRUNCATE TABLE `{MYSQL_TABLE}`")
            log(f"Insertando {len(filas)} filas ...")
            cur.executemany(sql_insert, filas)
        conn.commit()
        log(f"EXITO: {len(filas)} filas cargadas en `{MYSQL_TABLE}`.")
        return len(filas)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =========================
# MAIN
# =========================
def run():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    log("=== INICIO BOT PENDIENTES ===")
    validar_config()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            ignore_https_errors=True,
            accept_downloads=True,
            user_agent=USER_AGENT,
            locale="es-CO",
            extra_http_headers={"Accept-Language": "es-CO,es;q=0.9"},
        )
        page = context.new_page()
        page.set_default_timeout(120000)
        page.set_default_navigation_timeout(120000)
        page.on("dialog", lambda d: d.accept())

        try:
            login(page)
            aceptar_terminos(page)
            ruta_csv = descargar_csv(context, page)
        finally:
            browser.close()

    filas = parsear_csv(ruta_csv)
    log(f"Filas parseadas del CSV: {len(filas)}")
    cargar_mysql(filas)
    log("=== PROCESO FINALIZADO ===")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log(f"ERROR FATAL: {e}")
        sys.exit(1)
