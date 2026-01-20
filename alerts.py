import requests
from bs4 import BeautifulSoup
import re
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACIÓN ---
URL_BORA = "https://www.boletinoficial.gob.ar/seccion/primera"
ARCHIVO_ESTADO = "data/estado.json"

# Datos desde Secrets de GitHub
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = 587
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

def obtener_publicaciones():
    """Obtiene Leyes y Decretos de la web del BORA."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(URL_BORA, headers=headers, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        items = []
        # Buscamos enlaces que coincidan con el patrón de avisos
        enlaces = soup.find_all('a', href=re.compile(r"/detalleAviso/primera/\d+/\d+"))
        print(f"DEBUG: Se encontraron {len(enlaces)} enlaces de avisos en total.")
        
        for a in enlaces:
            href = a.get('href')
            match_id = re.search(r"/(\d+)/", href)
            if not match_id: continue
            aviso_id = match_id.group(1)
            
            # Buscamos la categoría (buscando hacia arriba en el HTML)
            categoria = "OTROS"
            parent = a.find_previous(['h5', 'h4', 'div'], class_=re.compile(r'seccion-rubro|titulo-seccion|bg-blue'))
            if parent:
                texto_cat = parent.get_text(strip=True).upper()
                if "LEYES" in texto_cat: categoria = "LEYES"
                elif "DECRETOS" in texto_cat: categoria = "DECRETOS"
                elif "RESOLUCIONES GENERALES" in texto_cat: categoria = "RESOLUCIONES GENERALES"
                elif "RESOLUCIONES" in texto_cat: categoria = "RESOLUCIONES"
                elif "DISPOSICIONES" in texto_cat: categoria = "DISPOSICIONES"
                elif "DECISIONES ADMINISTRATIVAS" in texto_cat: categoria = "DECISIONES ADMINISTRATIVAS"
                elif "CONCURSOS" in texto_cat: categoria = "CONCURSOS"
                elif "AVISOS" in texto_cat: categoria = "AVISOS"
            
            print(f"DEBUG: Encontrado aviso {aviso_id} - Categoría: {categoria}")
            
            # Ahora capturamos casi todo, excepto si es realmente desconocido
            if categoria == "OTROS":
                continue

            # Extraer número y resumen
            nro = "S/N"
            resumen = ""
            detalle = a.find('div', class_='item-detalle')
            if detalle:
                smalls = detalle.find_all('small')
                if len(smalls) >= 1: nro = smalls[0].get_text(strip=True)
                if len(smalls) >= 2: resumen = smalls[1].get_text(strip=True)

            items.append({
                "id": aviso_id,
                "categoria": categoria,
                "numero": nro,
                "resumen": resumen,
                "url": f"https://www.boletinoficial.gob.ar{href}"
            })
        return items
    except Exception as e:
        print(f"Error al scrapear BORA: {e}")
        return []

def enviar_email(nuevos_items):
    """Compone y envía el email con las novedades."""
    if not nuevos_items:
        return

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"🔔 Alerta BORA: Nuevas Leyes y Decretos detectados"

    cuerpo = "<h2>Nuevas publicaciones en el Boletín Oficial</h2>"
    cuerpo += "<p>Se han detectado las siguientes normas de interes, agrupadas por categoría:</p>"

    # Agrupamos por categoría
    agrupados = {}
    for item in nuevos_items:
        cat = item['categoria']
        if cat not in agrupados: agrupados[cat] = []
        agrupados[cat].append(item)

    for cat, items in agrupados.items():
        cuerpo += f"<h3 style='background-color: #f8f9fa; padding: 10px; border-left: 5px solid #007bff;'>{cat} ({len(items)})</h3>"
        for item in items:
            cuerpo += f"""
            <div style="margin-bottom: 15px; padding-left: 10px;">
                <p style="margin-bottom: 5px;"><b>{item['numero']}</b></p>
                <p style="color: #444; margin-top: 0; font-size: 0.9em;">{item['resumen']}</p>
                <a href="{item['url']}" style="color: #007bff; text-decoration: none; font-weight: bold;">🔗 Ver en BORA</a>
            </div>
            """
        cuerpo += "<hr style='border: 0; border-top: 1px solid #eee;'>"

    cuerpo += "<p><small>Este es un aviso automático generado por tu Alerta BORA personalizada.</small></p>"
    msg.attach(MIMEText(cuerpo, 'html'))

    try:
        print(f"DEBUG: Intentando conectar a {SMTP_SERVER} para enviar mail a {EMAIL_RECEIVER}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email enviado con éxito.")
    except Exception as e:
        print(f"❌ Error al enviar email: {e}")
        raise e # Forzamos que el workflow falle si no puede enviar el mail

def main():
    if not all([SMTP_USER, SMTP_PASSWORD, EMAIL_RECEIVER]):
        print("Error: Credenciales de email no configuradas.")
        return

    # Cargar estado anterior
    os.makedirs("data", exist_ok=True)
    if os.path.exists(ARCHIVO_ESTADO):
        with open(ARCHIVO_ESTADO, 'r') as f:
            vistos = json.load(f)
    else:
        vistos = []

    publicaciones = obtener_publicaciones()
    nuevas = [p for p in publicaciones if p['id'] not in vistos]

    if nuevas:
        print(f"Detectadas {len(nuevas)} publicaciones nuevas.")
        enviar_email(nuevas)
        # Actualizar estado (guardamos IDs para no repetir)
        vistos.extend([n['id'] for n in nuevas])
        # Solo guardamos los últimos 200 IDs para no inflar el archivo
        vistos = vistos[-200:]
        with open(ARCHIVO_ESTADO, 'w') as f:
            json.dump(vistos, f)
    else:
        print("No hay novedades.")

if __name__ == "__main__":
    main()
