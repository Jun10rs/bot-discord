import json
import asyncio
import os
import tweepy
from discord.ext import tasks
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# Configuração da API do Twitter
client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)

# Dicionário para armazenar os últimos tweets monitorados
last_tweets = {}

# Função para carregar perfis monitorados
def load_profiles():
    try:
        with open("profiles.json", "r") as f:
            data = json.load(f)
            return data.get("profiles", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Função para verificar novos tweets
async def check_tweets(bot):
    profiles = load_profiles()
    channel = bot.get_channel(CHANNEL_ID)  # Substitua pelo ID do canal

    if not channel:
        print("Canal do Discord não encontrado!")
        return

    for username in profiles:
        try:
            # Obtenha o ID do usuário baseado no username
            user = client.get_user(username=username)

            # Agora obtemos os tweets mais recentes
            tweets = client.get_users_tweets(id=user.data.id, max_results=5)

            if tweets.data:
                latest_tweet = tweets.data[0]
                tweet_id = latest_tweet.id
                tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"

                # Verificar se o tweet já foi enviado
                if username in last_tweets and last_tweets[username] == tweet_id:
                    continue  # Nenhum novo tweet

                # Armazenar o id do tweet e enviar a mensagem para o canal do Discord
                last_tweets[username] = tweet_id
                await channel.send(f"📢Fala Formadores, @{username} postou um novo Tweet!:\n{tweet_url}")

                 # Espera 5 segundos entre as requisições para não exceder o limite de taxa
            await asyncio.sleep(5)

        except tweepy.TooManyRequests as e:
            print(f"Erro 429: Excedido o limite de requisições para @{username}. Esperando antes de tentar novamente.")
            # Espera o tempo necessário para a janela de limite de taxa reiniciar (geralmente 15 minutos)
            await asyncio.sleep(900)  # Aguardar 15 minutos

        except Exception as e:
            print(f"Erro ao buscar tweets de @{username}: {e}")

# Criar uma tarefa que roda a cada 3 minutos
@tasks.loop(minutes=3)
async def start_twitter_monitor(bot):
    await check_tweets(bot)
