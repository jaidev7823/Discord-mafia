# bot/views.py

import discord
from bot.modals import CreateAgentModal


LLM_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-opus",
    "claude-3-sonnet"
]


class ModelSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=m) for m in LLM_MODELS]
        super().__init__(
            placeholder="Select LLM Model",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_model = self.values[0]
        await interaction.response.edit_message(view=self.view)


class CreateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Create Agent", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        if not self.view.selected_model:
            await interaction.response.send_message(
                "Select a model first.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            CreateAgentModal(model=self.view.selected_model)
        )


class AgentSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.selected_model = None

        self.add_item(ModelSelect())
        self.add_item(CreateButton())