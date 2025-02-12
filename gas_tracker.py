import os
import requests
import discord
from discord.ext import tasks
from dotenv import load_dotenv

# 🔹 Carregar variáveis de ambiente (.env)
load_dotenv()
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")  # Chave da API Etherscan

# 🔹 Função para buscar a taxa de Gwei via API da Etherscan
async def fetch_gas_price():
    url = f"https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={ETHERSCAN_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data["status"] == "1" and "result" in data:
            safe_gwei = float(data["result"]["SafeGasPrice"])      # Baixo
            propose_gwei = float(data["result"]["ProposeGasPrice"]) # Médio
            fast_gwei = float(data["result"]["FastGasPrice"])      # Alto
            
            return propose_gwei, safe_gwei, fast_gwei
        else:
            print(f"❌ Erro na resposta da Etherscan: {data}")
            return None, None, None
    except requests.RequestException as e:
        print(f"❌ Erro ao buscar preço do Gwei: {e}")
        return None, None, None

# 🔹 Determinar o nível do Gwei com base na API da Etherscan
def get_gwei_indicator(gwei_price, safe_gwei, propose_gwei, fast_gwei):
    if gwei_price >= fast_gwei:
        return "🔴 ↗️"
    elif gwei_price >= safe_gwei:
        return "🟢 ↘️"
    #else:
        return "🟢 ↘️"

# 🔹 Função para buscar preço de token na API da Binance
async def fetch_token_price(symbol):
    symbol = symbol.lower()

    if symbol == "gweieth":
        print("✅ Buscando Gwei na Etherscan (não na Binance)")
        propose_gwei, _, _ = await fetch_gas_price()
        return propose_gwei

    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
    try:
        print(f"📡 Fazendo requisição para Binance: {url}")  # Debug
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data.get("price", 0))
    except requests.RequestException as e:
        print(f"❌ Erro ao buscar preço do {symbol}: {e}")
        return None

# 🔹 Comando para adicionar um canal de gás (Gwei)
async def add_gas_channel(interaction: discord.Interaction, bot):
    guild = interaction.guild

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False),
        guild.me: discord.PermissionOverwrite(manage_channels=True, view_channel=True, connect=True, speak=True)
    }

    # Criar canal temporário com nome inicial
    new_channel = await guild.create_voice_channel(name="⛽ Gwei: Carregando...", overwrites=overwrites)
    
    # Buscar preço do gás usando a Etherscan
    propose_gwei, safe_gwei, fast_gwei = await fetch_gas_price()
    if propose_gwei is not None:
        indicator = get_gwei_indicator(propose_gwei, safe_gwei, propose_gwei, fast_gwei)
        new_channel_name = f"{indicator} GAS: {propose_gwei:.2f} Gwei"
        try:
            await new_channel.edit(name=new_channel_name)
            print(f"✅ Canal de gás criado: {new_channel_name}")
        except discord.Forbidden:
            print("❌ Permissão negada para editar o nome do canal.")
        except discord.HTTPException as e:
            print(f"❌ Erro ao editar o nome do canal: {e}")
    
    # Salvar ID do canal para atualizações futuras
    bot.tracked_tokens[("gwei", "eth")] = new_channel.id
    return new_channel.id

# 🔹 Atualização automática do canal de gás (a cada 10 minutos)
@tasks.loop(seconds=350)
async def update_gas_channel(bot):
    await bot.wait_until_ready()
    
    # Verificar se o canal de Gwei foi criado
    if ("gwei", "eth") in bot.tracked_tokens:
        channel_id = bot.tracked_tokens[("gwei", "eth")]
        channel = bot.get_channel(channel_id)
        
        if channel is None:
            print(f"❌ Canal de gás não encontrado (ID: {channel_id}). Removendo da lista.")
            bot.tracked_tokens.pop(("gwei", "eth"), None)
            return
        
        # Buscar nova taxa de Gwei usando a Etherscan
        propose_gwei, safe_gwei, fast_gwei = await fetch_gas_price()
        if propose_gwei is not None:
            indicator = get_gwei_indicator(propose_gwei, safe_gwei, propose_gwei, fast_gwei)
            new_channel_name = f"{indicator} GAS: {propose_gwei:.2f} Gwei"
            try:
                await channel.edit(name=new_channel_name)
                print(f"✅ Atualizado para: {new_channel_name}")
            except discord.Forbidden:
                print("❌ Sem permissão para editar canal.")
            except discord.HTTPException as e:
                print(f"❌ Erro ao editar canal: {e}")