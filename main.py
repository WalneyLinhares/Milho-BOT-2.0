import os
import asyncio
import json
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
UPDATE_INTERVAL = 20
API_KEY = os.getenv("API_KEY")

MESSAGE_ID_FILE = "message_id.json"
MESSAGE_ID = None
LAST_UPDATE = 0
PENDING_DATA = None  # Guarda o último dado recebido

# ------------------ FUNÇÕES DE PERSISTÊNCIA ------------------
def save_message_id(msg_id):
    with open(MESSAGE_ID_FILE, "w") as f:
        json.dump({"id": msg_id}, f)

def load_message_id():
    global MESSAGE_ID
    try:
        with open(MESSAGE_ID_FILE, "r") as f:
            data = json.load(f)
            MESSAGE_ID = data.get("id")
    except FileNotFoundError:
        MESSAGE_ID = None

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

    # Guarda os dados para atualizar periodicamente
    PENDING_DATA = {"room_name": room_name, "user_count": user_count}
    print(PENDING_DATA)
    return {"status": "ok"}

# ------------------ FUNÇÃO DE ATUALIZAÇÃO DO EMBED ------------------
async def update_embed_periodically():
    global MESSAGE_ID, LAST_UPDATE, PENDING_DATA
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Canal não encontrado!")
        return

    load_message_id()
    print(f"Iniciando loop de atualização no canal: {channel.name} ({CHANNEL_ID})")

    while not bot.is_closed():
        now = datetime.now().timestamp()
        if PENDING_DATA and now - LAST_UPDATE >= UPDATE_INTERVAL:
            try:
                room_name = PENDING_DATA["room_name"]
                user_count = PENDING_DATA["user_count"]

                embed = discord.Embed(
                    title=f"{room_name.upper()}",
                    description="Chame seus amigos e vem jogar!"
                )
                embed.set_thumbnail(url=GIF_URL)
                embed.add_field(
                    name="",
                    value=f"```fix\n🎮 {user_count} Usuários no quarto\n```",
                    inline=False
                )
                embed.add_field(
                    name="",
                    value=f"```fix\n{ROOM_LINK}```",
                    inline=True
                )

                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                label="QUARTO",
                url=ROOM_LINK,
                style=discord.ButtonStyle.link
                ))

                view.add_item(discord.ui.Button(
                label="💎 VIP",
                url="https://discord.com/channels/1186736897544945828/1211844747241586748",
                style=discord.ButtonStyle.link
                ))

                embed.set_footer(text=f"🕔{datetime.now().strftime('%d/%m/%Y - %H:%M')}")

                if MESSAGE_ID is None:
                    msg = await channel.send(embed=embed, view=view)
                    MESSAGE_ID = msg.id
                    save_message_id(MESSAGE_ID)
                    print(f"Mensagem enviada: {MESSAGE_ID}")
                else:
                    try:
                        msg = await channel.fetch_message(MESSAGE_ID)
                        await msg.edit(embed=embed, view=view)
                        print("Mensagem atualizada")
                    except discord.errors.NotFound:
                        # Se a mensagem foi deletada, enviar nova
                        msg = await channel.send(embed=embed, view=view)
                        MESSAGE_ID = msg.id
                        save_message_id(MESSAGE_ID)
                        print("Mensagem anterior não encontrada. Nova mensagem enviada.")

                LAST_UPDATE = now
            except Exception as e:
                print("Erro ao atualizar embed:", e)

        await asyncio.sleep(5)  # verifica a cada 5 segundos se há atualização

# ------------------ FUNÇÃO PRINCIPAL ------------------
async def main():
    # Cria task do FastAPI
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())

    # Cria task de atualização do embed
    update_task = asyncio.create_task(update_embed_periodically())

    # Inicia o bot
    await bot.start(TOKEN)

# ------------------ EXECUTAR ------------------
if __name__ == "__main__":
    asyncio.run(main())