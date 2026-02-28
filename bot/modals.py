 # bot/modals.py
import discord
import requests

class CreateAgentModal(discord.ui.Modal, title="Create AI Agent"):
    name = discord.ui.TextInput(label="Agent Name", max_length=30)
    personality = discord.ui.TextInput(
        label="Personality", 
        style=discord.TextStyle.paragraph,
        placeholder="e.g., Calm, manipulative, philosophical..."
    )
    backstory = discord.ui.TextInput(
        label="Backstory",
        style=discord.TextStyle.paragraph,
        placeholder="Brief history or background of the agent...",
        required=False  # Make it optional
    )
    system_prompt = discord.ui.TextInput(
        label="System Prompt", 
        style=discord.TextStyle.paragraph,
        placeholder="Instructions for how the agent should behave..."
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Prepare the payload
            payload = {
                "discord_id": str(interaction.user.id),
                "username": interaction.user.name,
                "name": self.name.value,
                "personality": self.personality.value,
                "system_prompt": self.system_prompt.value,
                "pfp_url": None,
            }
            
            # Only add backstory if provided (your backend might require it)
            if hasattr(self, 'backstory') and self.backstory.value:
                payload["backstory"] = self.backstory.value
            else:
                # If backstory is required by backend, provide a default
                payload["backstory"] = f"Agent {self.name.value} created by {interaction.user.name}"
            
            res = requests.post(
                "http://127.0.0.1:8000/agents",
                json=payload,
                timeout=10
            )

            if res.status_code == 200:
                await interaction.response.send_message(
                    f"✅ Agent `{self.name.value}` created successfully!",
                    ephemeral=True,
                )
            else:
                # Try to get error message from response
                error_msg = "Unknown error"
                try:
                    error_data = res.json()
                    if isinstance(error_data, dict):
                        error_msg = error_data.get('detail', str(error_data))
                    else:
                        error_msg = str(error_data)
                except:
                    error_msg = res.text or f"Status code: {res.status_code}"
                
                await interaction.response.send_message(
                    f"❌ Error: {error_msg}",
                    ephemeral=True,
                )

        except requests.exceptions.ConnectionError:
            await interaction.response.send_message(
                "❌ Cannot connect to backend. Is the server running?",
                ephemeral=True,
            )
        except requests.exceptions.Timeout:
            await interaction.response.send_message(
                "❌ Backend request timed out. Please try again.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Unexpected error: {type(e).__name__}: {e}",
                ephemeral=True,
            )          
        
