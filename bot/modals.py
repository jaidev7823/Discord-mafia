# bot/modals.py
import discord
import requests

class CreateAgentModal(discord.ui.Modal, title="Create AI Agent"):
    name = discord.ui.TextInput(label="Agent Name", max_length=30)
    personality = discord.ui.TextInput(
        label="Personality", style=discord.TextStyle.paragraph
    )

    system_prompt = discord.ui.TextInput(
        label="System Prompt", style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            res = requests.post(
                "http://127.0.0.1:8000/agents",
                json={
                    "discord_id": str(interaction.user.id),
                    "username": interaction.user.name,
                    "name": self.name.value,
                    "personality": self.personality.value,
                    "system_prompt": self.system_prompt.value,
                    "pfp_url": None,
                },
            )

            if res.status_code == 200:
                await interaction.response.send_message(
                    f"Agent `{self.name.value}` created.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"Error: {res.json()}",
                    ephemeral=True,
                )

        except Exception as e:
            await interaction.response.send_message(
                f"Backend error: {e}",
                ephemeral=True,
            )