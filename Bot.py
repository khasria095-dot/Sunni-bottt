import os
import asyncio
import logging
from datetime import datetime
import pytz
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import httpx
from bs4 import BeautifulSoup

TOKEN   = os.environ["BOT_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])
BCN_TZ  = pytz.timezone("Europe/Madrid")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

async def get_trenes_sants():
    url = "https://horarios.renfe.com/cer/hjcer310.jsp?NUCLEO=50&I=s&CP=NO&TIPOCONSULTA=A&Idioma=CA&Estacion=79600"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tr")[1:8]
        lines = []
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.select("td")]
            if len(cols) >= 3:
                lines.append(f"🚂 {cols[0]}  {cols[1]}  ➜  {cols[2]}")
        return "\n".join(lines) if lines else "No hay datos ahora mismo."
    except Exception as e:
        return "❌ No se pudo obtener info de trenes."

async def get_vuelos(terminal):
    t = "T1" if "1" in terminal else "T2"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://www.aena.es/es/aeropuerto-barcelona/llegadas.html", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr.flight-row")[:8]
        lines = []
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.select("td")]
            if len(cols) >= 4:
                lines.append(f"✈️ {cols[0]}  {cols[1]}  {cols[2]}  {cols[3]}")
        return f"*Llegadas {t} — El Prat*\n\n" + "\n".join(lines) if lines else f"No hay datos de {t} ahora."
    except:
        return f"❌ No se pudo obtener vuelos {t}."

async def get_eventos_campnou():
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://www.fcbarcelona.es/es/calendario", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        hoy = datetime.now(BCN_TZ).strftime("%Y-%m-%d")
        eventos = []
        for item in soup.select("article"):
            texto = item.get_text(separator=" ", strip=True)
            if hoy in texto:
                eventos.append(texto[:120])
        return eventos[:3]
    except:
        return []

async def get_eventos_palau():
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://www.palausantjordi.cat/es/agenda", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        hoy = datetime.now(BCN_TZ).strftime("%d/%m/%Y")
        eventos = []
        for item in soup.select("article"):
            texto = item.get_text(separator=" ", strip=True)
            if hoy in texto:
                eventos.append(texto[:120])
        return eventos[:3]
    except:
        return []

async def alerta_diaria(context):
    bot = context.bot
    msgs = []
    cn = await get_eventos_campnou()
    if cn:
        msgs.append("⚽ *Camp Nou hoy:*\n" + "\n".join(cn))
    ps = await get_eventos_palau()
    if ps:
        msgs.append("🎵 *Palau Sant Jordi hoy:*\n" + "\n".join(ps))
    if msgs:
        await bot.send_message(chat_id=CHAT_ID, text="🗓 *Eventos hoy en Barcelona*\n\n" + "\n\n".join(msgs), parse_mode="Markdown")

async def cmd_start(update, ctx):
    await update.message.reply_text("👋 Hola Sunni!\n\n📌 *Comandos:*\n• `trenes` — Llegadas a Sants\n• `vuelos t1` — Terminal 1\n• `vuelos t2` — Terminal 2\n• `eventos` — Hoy en Barcelona", parse_mode="Markdown")

async def handle_message(update, ctx):
    texto = update.message.text.lower().strip()
    if "tren" in texto or "sants" in texto:
        await update.message.reply_text("🔍 Buscando...")
        await update.message.reply_text(await get_trenes_sants())
    elif "vuelo" in texto or "prat" in texto:
        terminal = "T1" if "1" in texto else "T2"
        await update.message.reply_text("🔍 Buscando...")
        await update.message.reply_text(await get_vuelos(terminal), parse_mode="Markdown")
    elif "evento" in texto or "partido" in texto or "concierto" in texto:
        cn = await get_eventos_campnou()
        ps = await get_eventos_palau()
        if cn or ps:
            msg = ""
            if cn: msg += "⚽ *Camp Nou:*\n" + "\n".join(cn) + "\n\n"
            if ps: msg += "🎵 *Palau Sant Jordi:*\n" + "\n".join(ps)
            await update.message.reply_text(msg.strip(), parse_mode="Markdown")
        else:
            await update.message.reply_text("Hoy no hay eventos.")
    else:
        await update.message.reply_text("Prueba con: *trenes*, *vuelos t1*, *vuelos t2*, *eventos*", parse_mode="Markdown")

def main():
    from datetime import timedelta
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    now = datetime
