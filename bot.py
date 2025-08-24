import logging
logging.basicConfig(level=logging.INFO)

# bot.py — Minecraft Education join-code helper
import os, json
from typing import List, Dict
from dotenv import load_dotenv

import discord
from discord import app_commands
from discord.ext import commands

# ========= Config =========
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "guild_codes.json"   # saved per-server
GUILD_ID = 1408947324524298353   # your server ID

ICONS = [
    # Row 1
    ("book_and_quill", "<:mc_bookandquil:1408972331212079125>"),
    ("balloon",         "<:mc_balloon:1408972329630961673>"),
    ("rail",            "<:mc_rail:1408972955106541721>"),
    ("alex",            "<:mc_alex:1408972326946607147>"),
    ("cookie",          "<:mc_cookie:1408972335540600945>"),
    ("fish",            "<:mc_fish:1408972336652222495>"),

    # Row 2
    ("agent",           "<:mc_agent:1408972325575069789>"),
    ("cake",            "<:mc_cake:1408972332642336961>"),
    ("pickaxe",         "<:mc_picaxe:1408972951906418809>"),
    ("water_bucket",    "<:mc_waterbucket:1408972959426674708>"),
    ("steve",           "<:mc_steve:1408972958239817798>"),
    ("apple",           "<:mc_apple:1408972328036991130>"),

    # Row 3
    ("carrot",          "<:mc_carrot:1408972333716209818>"),
    ("panda",           "<:mc_panda:1408973102909489262>"),
    ("sign",            "<:mc_sign:1408972956436140093>"),
    ("potion",          "<:mc_potion:1408972953529352346>"),
    ("map",             "<:mc_map:1408972340447940638>"),
    ("llama",           "<:mc_llama:1408973101466652722>"),
]
MAX_CODE_LEN = 4


# ========= Data helpers =========
def load_db() -> Dict[str, List[str]]:
    if not os.path.exists(DATA_FILE): 
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_db(data: Dict[str, List[str]]) -> None:
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

db = load_db()

# ========= Bot setup =========
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def slots_render(emojis: List[str]) -> str:
    return " ".join(emojis + ["▢"] * (MAX_CODE_LEN - len(emojis)))

# ---------- UI Buttons ----------
class IconButton(discord.ui.Button):
    def __init__(self, label_name: str, emoji: str):
        super().__init__(style=discord.ButtonStyle.secondary, emoji=emoji)
        self.label_name = label_name
        self.emoji_char = emoji

    async def callback(self, interaction: discord.Interaction):
        view: "CodeBuilderView" = self.view  # type: ignore
        if interaction.user.id != view.owner_id:
            return await interaction.response.send_message(
                "Only the person who started this can select icons.", ephemeral=True
            )
        if len(view.current) >= MAX_CODE_LEN:
            return await interaction.response.send_message(
                f"Code already has {MAX_CODE_LEN} icons. Press Confirm or Clear.",
                ephemeral=True,
            )
        view.current.append(self.emoji_char)
        await view.refresh(interaction)

class ClearButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Clear", row=4)
    async def callback(self, interaction: discord.Interaction):
        view: "CodeBuilderView" = self.view  # type: ignore
        if interaction.user.id != view.owner_id:
            return await interaction.response.send_message(
                "Only the starter can clear.", ephemeral=True
            )
        view.current.clear()
        await view.refresh(interaction)

class ConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Confirm", row=4)
    async def callback(self, interaction: discord.Interaction):
        view: "CodeBuilderView" = self.view  # type: ignore
        if interaction.user.id != view.owner_id:
            return await interaction.response.send_message(
                "Only the starter can confirm.", ephemeral=True
            )
        if len(view.current) != MAX_CODE_LEN:
            return await interaction.response.send_message(
                f"Pick {MAX_CODE_LEN} icons first.", ephemeral=True
            )
        guild_id = str(interaction.guild_id)
        db[guild_id] = list(view.current)
        save_db(db)
        await interaction.response.edit_message(
            content=f"✅ Saved join code for **{interaction.guild.name}**: {slots_render(view.current)}",
            view=None,
        )

class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.secondary, label="Cancel", row=4)
    async def callback(self, interaction: discord.Interaction):
        view: "CodeBuilderView" = self.view  # type: ignore
        if interaction.user.id != view.owner_id:
            return await interaction.response.send_message(
                "Only the starter can cancel.", ephemeral=True
            )
        await interaction.response.edit_message(content="❌ Cancelled.", view=None)

class CodeBuilderView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.current: List[str] = []

        # Lay out icon buttons in rows (keep last row for controls)
        row = 0; col = 0
        for name, emoji in ICONS:
            btn = IconButton(name, emoji)
            btn.row = row
            self.add_item(btn)
            col += 1
            if col == 5:
                col = 0; row += 1
            if row == 4:  # leave row 4 for Clear/Confirm/Cancel
                break

        self.add_item(ClearButton())
        self.add_item(ConfirmButton())
        self.add_item(CancelButton())

    async def refresh(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=f"**Pick {MAX_CODE_LEN} icons (order matters):**\n{slots_render(self.current)}",
            view=self
        )

# ---------- Slash commands ----------
@bot.tree.command(name="setcode", description="Pick and save a 4-icon join code for this server.")
async def setcode(interaction: discord.Interaction):
    view = CodeBuilderView(interaction.user.id)
    await interaction.response.send_message(
        f"**Pick {MAX_CODE_LEN} icons (order matters):**\n{slots_render([])}",
        view=view,
        ephemeral=True
    )

@setcode.error
async def setcode_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You need **Manage Server** to set the code.", ephemeral=True
        )
    else:
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)

@bot.tree.command(name="code", description="Show this server's saved join code.")

async def code(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    code_emojis = db.get(guild_id)
    if not code_emojis or len(code_emojis) != MAX_CODE_LEN:
        return await interaction.response.send_message(
            "No code set yet. Ask server owner to run `/setcode`.", ephemeral=True
        )
    embed = discord.Embed(
        title="Minecraft Education Join Code",
        description=slots_render(code_emojis),
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="resetcode", description="Reset the saved join code for this server.")
@app_commands.checks.has_permissions(manage_guild=True)
async def resetcode(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    if guild_id in db:
        db.pop(guild_id)
        save_db(db)
        await interaction.response.send_message("🗑️ The join code has been reset.", ephemeral=True)
    else:
        await interaction.response.send_message("No code is set yet.", ephemeral=True)

@resetcode.error
async def resetcode_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You need **Manage Server** to reset the code.", ephemeral=True
        )
    else:
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)

@bot.tree.command(name="ping", description="Check if the bot is alive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! The bot is online.")

@bot.tree.command(name="help", description="Show all available commands for this bot.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Minecraft EDU Join Code Bot — Help",
        description="Here are the available commands:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="/setcode",
        value="Pick and save a 4-icon join code for this server.",
        inline=False
    )
    embed.add_field(
        name="/code",
        value="Show the saved join code for this server.",
        inline=False
    )
    embed.add_field(
        name="/resetcode",
        value="Clear the saved join code.",
        inline=False
    )
    embed.add_field(
        name="/ping",
        value="Check if the bot is online.",
        inline=False
    )
    embed.add_field(
        name="/help",
        value="Show this help menu.",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------- Sync (guild + globals) ----------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)

    # keep global commands alive (causes duplicates, but works)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)

    print(f"✅ Synced {len(synced)} commands to guild {GUILD_ID}")
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# ---------- Run ----------
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ No token found in .env")
    bot.run(TOKEN)
