import os
import json
import discord
from discord.ext import commands, tasks
import requests
import requests_cache
import asyncio
from discord import app_commands
from dotenv import load_dotenv
from gas_tracker import add_gas_channel, update_gas_channel

# 🔹 Carregar variáveis de ambiente (.env) para manter o token seguro
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN") # O token deve ser armazenado no arquivo .env

# 🔹 Configuração dos intents (permitindo acesso a mensagens e eventos básicos)
intents = discord.Intents.default()
intents.message_content = True # Necessário para ler e enviar mensagens

# 🔹 Criar o bot com prefixo '!' (pode ser alterado)
bot = commands.Bot(command_prefix="!", intents=intents)
tracked_tokens = {}
previous_prices = {}
# No bot (não dentro de um comando, mas antes dele)
bot.tracked_tokens = tracked_tokens

# 🔹 Listas de tokens e moedas fiat disponíveis
AVAILABLE_TOKENS = ["BTC", "ETH", "XRP", "ADA", "SOL", "DOGE", "AAVE"]
AVAILABLE_FIAT = ["USDT", "EUR", "BRL"]

# 🔹 Criar sessão de cache para evitar chamadas repetidas à API
session = requests_cache.CachedSession('crypto_cache', expire_after=340)  # Cache de 340s

BASE_URL = "https://api.binance.com/api/v3/ticker/price"

async def fetch_token_price(symbol):
    url = f"{BASE_URL}?symbol={symbol}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get("price", 0))
    except requests.RequestException as e:
        print(f"❌ Erro ao buscar preço do {symbol}: {e}")
        return None

@tasks.loop(seconds=320) #atualiza o preço a cada 5 minutos
async def update_channel_names():
    await bot.wait_until_ready()
    
    for (token, currency), channel_id in list(tracked_tokens.items()):
        symbol = f"{token}{currency}"
        channel = bot.get_channel(channel_id)
        if channel is None:
            print(f"❌ Erro: Canal com ID {channel_id} não encontrado para {symbol}! Removendo da lista.")
            tracked_tokens.pop((token, currency), None)
            continue

        new_price = await fetch_token_price(symbol)
        if new_price is not None:
            previous_price = previous_prices.get((token, currency), new_price)
            trend_symbol = "↗️" if new_price > previous_price else "↘️" # Determinar o emoji e a seta com base na variação do preço   
            color_indicator = "🟢" if new_price > previous_price else "🔴"
            new_channel_name = f"{color_indicator} {trend_symbol} {token}: ${new_price:,.2f}"
            previous_prices[(token, currency)] = new_price

            try:
                await channel.edit(name=new_channel_name)
                print(f"✅ Canal atualizado para: {new_channel_name}")
            except discord.Forbidden:
                print("❌ Permissão negada para editar o nome do canal.")
            except discord.HTTPException as e:
                print(f"❌ Erro ao editar o nome do canal: {e}")

@bot.tree.command(name="add_token", description="Adiciona um novo token")
@app_commands.describe(token="Escolha o token", currency="Escolha a moeda fiat")
@app_commands.choices(
    token=[app_commands.Choice(name=token, value=token) for token in AVAILABLE_TOKENS],
    currency=[app_commands.Choice(name=fiat, value=fiat) for fiat in AVAILABLE_FIAT]
)
async def add_token(interaction: discord.Interaction, token: str, currency: str):
    guild = interaction.guild

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(manage_channels=True, view_channel=True, connect=True, speak=True)
    }

    # Cria um novo canal com os dados do token selecionado como nome do canal e desativa conexão para membros
    new_channel = await guild.create_voice_channel(name=f"{token}-{currency}-loading", overwrites=overwrites)
    tracked_tokens[(token, currency)] = new_channel.id

    symbol = f"{token}{currency}"
    new_price = await fetch_token_price(symbol)
    if new_price is not None:
        previous_prices[(token, currency)] = new_price
        new_channel_name = f"🟢 ↗️ {token}: ${new_price:,.2f}"
        try:
            await new_channel.edit(name=new_channel_name)
            print(f"✅ Canal criado para: {new_channel_name}")
        except discord.Forbidden:
            print("❌ Permissão negada para editar o nome do canal.")
        except discord.HTTPException as e:
            print(f"❌ Erro ao editar o nome do canal: {e}")
    else:
        print(f"❌ Não foi possível obter o preço de {symbol}.")

    await interaction.response.send_message(f"✅ Token {token}/{currency} adicionado com sucesso", ephemeral=True)

# Comando /add_gas
@bot.tree.command(name="add_gas", description="Adiciona um canal com a taxa de Gwei da rede Ethereum")
async def add_gas(interaction: discord.Interaction):
    channel_id = await add_gas_channel(interaction, bot)
    await interaction.response.send_message("✅ Canal de Gwei adicionado com sucesso!", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        await bot.tree.sync()
        print("✅ Comandos sincronizados com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")
    if not update_channel_names.is_running():
        update_channel_names.start()

    if not update_gas_channel.is_running():
        update_gas_channel.start(bot)    

# 🔹 Rodar o bot
bot.run(TOKEN)
