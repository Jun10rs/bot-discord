import json
import discord
from discord import app_commands

# Função para carregar perfis do JSON
def load_profiles():
    try:
        with open("profiles.json", "r") as f:
            data = json.load(f)
            return data.get("profiles", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Função para salvar perfis no JSON
def save_profiles(profiles):
    with open("profiles.json", "w") as f:
        json.dump({"profiles": profiles}, f, indent=4)

# Classe com os comandos Slash
class TwitterCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="twitter", description="Comandos para monitorar Twitter")

    @app_commands.command(name="add", description="Adiciona um perfil do Twitter para monitoramento")
    @app_commands.describe(username="Nome de usuário do Twitter (sem @)")
    async def add_twitter(self, interaction: discord.Interaction, username: str):
        profiles = load_profiles()

        if username in profiles:
            await interaction.response.send_message(f"O perfil @{username} já está sendo monitorado!", ephemeral=True)
            return

        profiles.append(username)
        save_profiles(profiles)
        await interaction.response.send_message(f"✅ Perfil @{username} adicionado com sucesso!", ephemeral=True)

    @app_commands.command(name="list", description="Lista os perfis do Twitter monitorados")
    async def list_twitter(self, interaction: discord.Interaction):
        profiles = load_profiles()

        if not profiles:
            await interaction.response.send_message("Nenhum perfil está sendo monitorado.", ephemeral=True)
        else:
            await interaction.response.send_message("👀 Perfis monitorados:\n" + "\n".join(f"- @{p}" for p in profiles), ephemeral=True)

    @app_commands.command(name="remove", description="Remove um perfil do Twitter do monitoramento")
    @app_commands.describe(username="Nome de usuário do Twitter (sem @)")
    async def remove_twitter(self, interaction: discord.Interaction, username: str):
        profiles = load_profiles()

        if username not in profiles:
            await interaction.response.send_message(f"O perfil @{username} não está sendo monitorado.", ephemeral=True)
            return

        profiles.remove(username)
        save_profiles(profiles)
        await interaction.response.send_message(f"✅ Perfil @{username} removido com sucesso!", ephemeral=True)
