from playwright.sync_api import sync_playwright, TimeoutError
from dotenv import load_dotenv
import os
import sys
import paramiko
import datetime

def log(msg):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg)
    
    # Guardar en archivo de log local
    try:
        with open("reporte_actividad.log", "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except:
        pass


# Intentar cargar .env desde el directorio local del bot
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

USUARIO_ID = os.getenv("USUARIO_ID")
LOGIN = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")
RUTA_DESCARGA = os.getenv("RUTA_DESCARGA", r"C:\Botmedicar")

# Configuración SFTP
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")
SFTP_PORT = int(os.getenv("SFTP_PORT", 22))
SFTP_REMOTE_PATH = os.getenv("SFTP_REMOTE_PATH", "/medicar/ciclicoinventario")

URL_LOGIN = "https://medicar.sis-colombia.com/pharmaser/mutualser/"
URL_INVENTARIO = "https://medicar.sis-colombia.com/pharmaser/mutualser/el_admin/inventario/seguimiento/inventario.php"

# =========================
# VALIDACIONES
# =========================
def validar_config():
    if not os.path.exists(RUTA_DESCARGA):
        os.makedirs(RUTA_DESCARGA)
        log(f"Carpeta de descarga creada: {RUTA_DESCARGA}")

# =========================
# LOGIN
# =========================
def login(page):
    log("Iniciando sesion silenciosa...")
    page.goto(URL_LOGIN)
    page.wait_for_selector("input[placeholder='Identificación']")
    
    page.locator("input[placeholder='Identificación']").first.fill(USUARIO_ID)
    page.locator("input[placeholder='Login']").first.fill(LOGIN)
    page.locator("input[type='password']").first.fill(PASSWORD)

    with page.expect_navigation():
        page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")

# =========================
# ACEPTAR TERMINOS
# =========================
def aceptar_terminos(page):
    try:
        page.locator("text=Aceptar").click(timeout=5000)
        log("Acceso concedido")
    except TimeoutError:
        pass

# =========================
# IR A INVENTARIO
# =========================
def ir_inventario(page):
    log("Accediendo al modulo de inventario...")
    page.goto(URL_INVENTARIO)

# =========================
# EXPORTAR (MODO AUTOMÁTICO)
# =========================
def exportar_inventario(page):
    boton = page.locator('input[name="boton_exportar"][value="Exportar"]')
    if boton.count() == 0:
        log("Error: No se encontro el boton de exportar.")
        return

    # Manejar posibles alertas
    page.on("dialog", lambda dialog: dialog.accept())

    try:
        # Abrir pestaña de procesamiento
        with page.context.expect_page(timeout=60000) as new_page_info:
            boton.click(force=True)
        
        new_page = new_page_info.value
        log("Generando archivo en el servidor (esto puede tardar unos minutos)...")

        # Esperar la descarga real al llegar al 100%
        with new_page.expect_download(timeout=300000) as download_info:
            pass
        
        download = download_info.value
        
        # Rutas: temporal y final
        ruta_final = os.path.join(RUTA_DESCARGA, "inventario.xls")
        ruta_temp = os.path.join(RUTA_DESCARGA, "inventario.xls.tmp")
        
        # Guardar primero en archivo temporal para asegurar descarga completa
        download.save_as(ruta_temp)
        log(f"Archivo descargado exitosamente.")
        
        # Reemplazar el archivo definitivo localmente
        if os.path.exists(ruta_final):
            os.remove(ruta_final)
        os.rename(ruta_temp, ruta_final)
        log(f"Archivo local actualizado: {ruta_final}")
        
        # Subir a SFTP el archivo ya renombrado
        subir_a_sftp(ruta_final)
        
        log(f"EXITO: Inventario actualizado y subido correctamente.")
        new_page.close()

    except Exception as e:
        # Limpiar archivo temporal si quedó a medio descargar
        ruta_temp = os.path.join(RUTA_DESCARGA, "inventario.xls.tmp")
        if os.path.exists(ruta_temp):
            try:
                os.remove(ruta_temp)
                log("Archivo temporal incompleto eliminado.")
            except:
                pass
        
        log(f"Error durante la exportacion: {e}")
        raise

# =========================
# SUBIR A SFTP
# =========================
def subir_a_sftp(ruta_local):
    if not SFTP_HOST:
        log("Aviso: SFTP_HOST no configurado, omitiendo subida.")
        return

    log(f"Iniciando subida por SFTP a {SFTP_HOST}...")
    transport = None
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Asegurar que el directorio remoto existe (no es recursivo, asume que la ruta base existe)
        nombre_archivo = os.path.basename(ruta_local)
        ruta_remota = os.path.join(SFTP_REMOTE_PATH, nombre_archivo).replace("\\", "/")
        
        log(f"Subiendo {nombre_archivo} -> {ruta_remota}")
        sftp.put(ruta_local, ruta_remota)
        
        sftp.close()
        log("Subida SFTP completada exitosamente.")

    except Exception as e:
        log(f"Error en SFTP: {e}")
        raise  # Re-lanzar para que el llamador sepa que fallo
    finally:
        if transport:
            transport.close()

# =========================
# MAIN
# =========================
def run():
    log("=== INICIO DE EJECUCION ===")
    validar_config()

    try:
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(120000)
        page.set_default_navigation_timeout(120000)

        try:
            login(page)
            aceptar_terminos(page)
            ir_inventario(page)

            page.wait_for_selector('input[name="boton_exportar"]', timeout=120000)
            exportar_inventario(page)

        except Exception as e:
            log(f"Error en el proceso automatico: {e}")
            browser.close()
            raise

        browser.close()
        log("=== PROCESO FINALIZADO ===")

# =========================
# EJECUCIÓN
# =========================
if __name__ == "__main__":
    run()
