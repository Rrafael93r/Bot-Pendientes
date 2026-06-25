"""
API FastAPI para el Bot Medicar.
Expone endpoints de estado, control del archivo y ejecución manual.
El scheduling se maneja con APScheduler (reemplaza a cron).
"""

import os
import threading
from datetime import datetime

from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from bot_medicar import run

app = FastAPI(title="Bot Medicar API", version="1.0.0")

# ---------- Configuración ----------
RUTA_DESCARGA = os.getenv("RUTA_DESCARGA", "/app/downloads")
ARCHIVO = os.path.join(RUTA_DESCARGA, "inventario.xls")

CRON_HOUR_1 = int(os.getenv("CRON_HOUR_1", "6"))
CRON_MINUTE_1 = int(os.getenv("CRON_MINUTE_1", "0"))
CRON_HOUR_2 = int(os.getenv("CRON_HOUR_2", "18"))
CRON_MINUTE_2 = int(os.getenv("CRON_MINUTE_2", "0"))

# ---------- Estado global ----------
lock = threading.Lock()
job_state = {
    "status": "idle",           # idle | running | success | error
    "last_run_start": None,
    "last_run_end": None,
    "last_result": None,
    "last_error": None,
}


def _update_state(status: str, result: str = None, error: str = None):
    with lock:
        now = datetime.utcnow().isoformat()
        job_state["status"] = status
        if status == "running":
            job_state["last_run_start"] = now
            job_state["last_result"] = None
            job_state["last_error"] = None
        else:
            job_state["last_run_end"] = now
            job_state["last_result"] = result
            job_state["last_error"] = error


def _run_bot():
    """Wrapper seguro para ejecutar el bot sin matar el proceso."""
    _update_state("running")
    try:
        run()
        _update_state("success", result="Ejecucion completada correctamente")
    except Exception as exc:
        _update_state("error", result="Ejecucion fallida", error=str(exc))


def _job_listener(event):
    """Listener de APScheduler para sincronizar estado."""
    if event.exception:
        _update_state("error", result="Ejecucion programada fallida", error=str(event.exception))
    else:
        _update_state("success", result="Ejecucion programada completada")


# ---------- Scheduler ----------
scheduler = BackgroundScheduler()
scheduler.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

scheduler.add_job(
    _run_bot,
    trigger=CronTrigger(hour=CRON_HOUR_1, minute=CRON_MINUTE_1),
    id="run_morning",
    replace_existing=True,
)
scheduler.add_job(
    _run_bot,
    trigger=CronTrigger(hour=CRON_HOUR_2, minute=CRON_MINUTE_2),
    id="run_evening",
    replace_existing=True,
)


@app.on_event("startup")
def startup():
    scheduler.start()
    print(f"[Bot Medicar] Scheduler iniciado. Proximas ejecuciones:")
    for job in scheduler.get_jobs():
        print(f"  - {job.id}: {job.next_run_time}")


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown(wait=False)


# ---------- Endpoints ----------
@app.get("/")
def root():
    return {"service": "Bot Medicar API", "status": "ok"}


@app.get("/status")
def get_status():
    """Estado del scheduler y de la última ejecución."""
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            "id": job.id,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })

    return {
        "scheduler_running": scheduler.running,
        "execution": {
            "status": job_state["status"],
            "last_run_start": job_state["last_run_start"],
            "last_run_end": job_state["last_run_end"],
            "last_result": job_state["last_result"],
            "last_error": job_state["last_error"],
        },
        "scheduled_jobs": jobs_info,
    }


@app.get("/file-status")
def get_file_status():
    """Metadatos del archivo descargado."""
    if not os.path.exists(ARCHIVO):
        return {
            "exists": False,
            "message": "El archivo aun no ha sido descargado.",
        }

    stat = os.stat(ARCHIVO)
    return {
        "exists": True,
        "path": ARCHIVO,
        "size_bytes": stat.st_size,
        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "age_seconds": int((datetime.now() - datetime.fromtimestamp(stat.st_mtime)).total_seconds()),
    }


@app.post("/run")
def trigger_run():
    """Ejecuta el bot manualmente de forma asíncrona."""
    if job_state["status"] == "running":
        raise HTTPException(status_code=409, detail="El bot ya se encuentra en ejecucion")

    thread = threading.Thread(target=_run_bot, daemon=True)
    thread.start()

    return {
        "message": "Ejecucion manual iniciada",
        "started_at": datetime.utcnow().isoformat(),
    }
