import os
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import discord
from discord.ext import commands
import uvicorn
from dotenv import load_dotenv

# ------------------ CARREGAR VARIÁVEIS DE AMBIENTE ------------------
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
PORT = int(os.getenv("PORT", 8000))
ROOM_LINK = "https://www.habblet.city/room/6065930"
GIF_URL = "https://cdn.discordapp.com/attachments/1303772458762895480/1424811285542863000/load-32.gif"
UPDATE_INTERVAL = 60  # tempo mínimo entre atualizações em segundos

MESSAGE_ID = None
LAST_UPDATE = 0
PENDING_DATA = None  # guarda o último dado recebido

# ------------------ CONFIGURAÇÃO DO BOT ------------------
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ CONFIGURAÇÃO FASTAPI ------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

API_KEY = os.getenv("API_KEY")

# ------------------ FUNÇÃO DE ATUALIZAÇÃO DO EMBED ------------------
async def update_embed_if_needed():
    global MESSAGE_ID, LAST_UPDATE, PENDING_DATA
    if not PENDING_DATA:
        return

    now = datetime.now().timestamp()
    if now - LAST_UPDATE < UPDATE_INTERVAL:
        # ainda não passou o tempo mínimo
        return

    try:
        channel = await bot.fetch_channel(CHANNEL_ID)
        room_name = PENDING_DATA["room_name"]
        user_count = PENDING_DATA["user_count"]

        embed = discord.Embed(
            title=f"{room_name.upper()}",
            description="Chame seus amigos e vem jogar!",
            color=discord.Colour.default()
        )
        embed.set_thumbnail(url=GIF_URL)
        embed.add_field(
            name="Usuários atuais",
            value=f"```fix\n🎮 {user_count} Usuários no quarto\n```",
            inline=False
        )
        embed.add_field(
            name="Link do quarto",
            value=f"```fix\nAcesse o quarto abaixo\n```\n➡️ [Clique aqui para entrar]({ROOM_LINK})",
            inline=False
        )
        embed.set_footer(text=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        if MESSAGE_ID is None:
            msg = await channel.send(embed=embed)
            MESSAGE_ID = msg.id
            print(f"[DEBUG] Mensagem enviada: {MESSAGE_ID}")
        else:
            msg = await channel.fetch_message(MESSAGE_ID)
            await msg.edit(embed=embed)
            print("[DEBUG] Mensagem atualizada")

        LAST_UPDATE = now
        PENDING_DATA = None
    except Exception as e:
        print(f"[ERROR] Falha ao enviar/atualizar embed: {e}")

# ------------------ ENDPOINT FASTAPI ------------------
@app.post("/update-room")
async def update_room(request: Request):
    global PENDING_DATA
    # Verificar a API Key
    key = request.headers.get("x-api-key")
    if key != API_KEY:
        return {"error": "Unauthorized"}, 401

    data = await request.json()
    room_name = data.get("roomName")
    user_count = data.get("userCount")
    if not room_name or user_count is None:
        return {"error": "Dados inválidos"}, 400

    # Salvar dados pendentes
    PENDING_DATA = {"room_name": room_name, "user_count": user_count}
    print(f"[DEBUG] Dados recebidos: {PENDING_DATA}")

    # Chamar atualização imediatamente
    asyncio.create_task(update_embed_if_needed())

    return {"status": "ok"}

# ------------------ FUNÇÃO PRINCIPAL ------------------
async def main():
    # Iniciar FastAPI em task separada
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())

    # Iniciar bot
    await bot.start(TOKEN)

# ------------------ EVENTO ON READY ------------------
@bot.event
async def on_ready():
    print(f"[INFO] Bot conectado como {bot.user}")
    print(f"[INFO] Iniciando loop de atualização no canal: {CHANNEL_ID}")

# ------------------ EXECUTAR ------------------
if __name__ == "__main__":
    asyncio.run(main())