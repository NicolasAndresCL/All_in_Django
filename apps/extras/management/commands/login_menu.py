"""
Management command: login_menu

Logins automáticos (Selenium) a Cisco Netacad y Sence (Clave Única). Port del menú
de all_in_one, pero leyendo las credenciales desde core.conf (pydantic-settings),
no de os.getenv. Se ejecuta localmente (abre Chrome):

    python manage.py login_menu
"""

import time

from django.core.management.base import BaseCommand

from core.conf import settings as env
from core.logging import get_logger

logger = get_logger(__name__)


def _driver():
    from selenium import webdriver
    return webdriver.Chrome()


def iniciar_cisco():
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    print("\n[PROCESO] Iniciando sesión en Cisco Netacad...")
    driver = _driver()
    wait = WebDriverWait(driver, 20)
    try:
        driver.get("https://www.netacad.com/")
        wait.until(EC.element_to_be_clickable((By.ID, "netacad-login-button"))).click()
        email = wait.until(EC.presence_of_element_located((By.ID, "username")))
        email.send_keys(env.CISCO_USER)
        email.send_keys(Keys.RETURN)
        pwd = wait.until(EC.element_to_be_clickable((By.ID, "password")))
        pwd.send_keys(env.CISCO_PASS)
        pwd.send_keys(Keys.RETURN)
        print("[OK] Sesión de Cisco iniciada.")
        input("Presiona Enter para cerrar el navegador...")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falló Cisco")
        print(f"[ERROR] Cisco: {exc}")
    finally:
        driver.quit()


def iniciar_sence():
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    print("\n[PROCESO] Iniciando sesión en Sence...")
    driver = _driver()
    wait = WebDriverWait(driver, 25)
    try:
        driver.get("https://auladigital.sence.cl/login/index.php")
        wait.until(EC.presence_of_element_located((By.ID, "rut"))).send_keys(env.SENCE_RUT)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span.input-group-addon.aqua-text"))).click()
        time.sleep(1.5)
        wait.until(EC.element_to_be_clickable((By.ID, "btnLogin"))).click()
        wait.until(EC.presence_of_element_located((By.ID, "uname"))).send_keys(env.SENCE_RUT)
        driver.find_element(By.ID, "pword").send_keys(env.CLAVE_UNICA)
        driver.find_element(By.ID, "pword").send_keys(Keys.RETURN)
        print("[OK] Sesión de Sence iniciada.")
        input("Presiona Enter para cerrar el navegador...")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falló Sence")
        print(f"[ERROR] Sence: {exc}")
    finally:
        driver.quit()


# Tabla de despacho (callbacks) en vez de if/elif.
OPCIONES = {"1": iniciar_cisco, "2": iniciar_sence}


class Command(BaseCommand):
    """Menú interactivo de logins con Selenium; despacha por `OPCIONES`."""

    help = "Menú de logins automáticos (Cisco / Sence) con Selenium."

    def handle(self, *args, **opts):
        if not (env.CISCO_USER or env.SENCE_RUT):
            self.stdout.write(self.style.WARNING(
                "No hay credenciales en .env (CISCO_USER / SENCE_RUT). Complétalas primero."
            ))
        while True:
            print("\n=== MENÚ LOGINS ===\n1. Cisco Netacad\n2. Sence (Clave Única)\n3. Salir")
            opcion = input("Selecciona (1-3): ").strip()
            if opcion == "3":
                break
            accion = OPCIONES.get(opcion)
            if accion:
                accion()
            else:
                print("Opción no válida.")
