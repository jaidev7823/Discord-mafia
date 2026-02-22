import discord   # Installed via pip
import os        # Built-in (No pip install needed)
import requests  # Installed via pip
from dotenv import load_dotenv # Installed via pip
from discord import app_commands
from discord.ext import commands

class CreateAgentModal(discord.ui.Modal, title="Create AI Agent"):

    name = discord.ui.TextInput(
        label="Agent Name",
        max_length=30
    )

    personality = discord.ui.TextInput(
        label="Personality",
        style=discord.TextStyle.paragraph,
        max_length=300
    )

    backstory = discord.ui.TextInput(
        label="Backstory",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    system_prompt = discord.ui.TextInput(
        label="System Prompt",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Here you will save to DB later
        await interaction.response.send_message(
            f"Agent `{self.name}` received successfully.",
            ephemeral=True
        )