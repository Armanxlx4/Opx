import discord
from discord.ext import commands
import requests
import datetime
from datetime import timedelta

# === API-Football Configuration ===
API_KEY = "b945f050c82bd445083a021aa3d39b8e"  # Your API-Football API key
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_KEY
}

def get_fixtures_by_date(date_str: str):
    """
    Retrieve fixtures for a given date from API-Football.
    """
    url = f"{BASE_URL}/fixtures"
    params = {"date": date_str}
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("response", [])
    except Exception as e:
        print(f"Error fetching fixtures for {date_str}: {e}")
        return []

def get_prediction_for_fixture(fixture_id):
    """
    Retrieve prediction data for a fixture using its fixture ID.
    """
    url = f"{BASE_URL}/predictions"
    params = {"fixture": fixture_id}
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("response", [])
    except Exception as e:
        print(f"Error fetching predictions for fixture {fixture_id}: {e}")
        return []

def create_prediction_embed(fixture, prediction_data):
    """
    Create an attractive Discord embed displaying the fixture details along with
    cleanly formatted prediction fields using underlined and bold text for labels.
    The embed displays:
      • Winner (with comment)
      • Win/Draw flag
      • Under/Over prediction
      • Goals info (home and away)
      • Advice based on prediction
      • Percentages for home, draw, and away
    Emojis, dynamic colors, and markdown formatting are applied.
    """
    fixture_info = fixture.get("fixture", {})
    teams = fixture.get("teams", {})

    fixture_id = fixture_info.get("id", "N/A")
    fixture_date = fixture_info.get("date", "N/A")
    home_team_data = teams.get("home", {})
    away_team_data = teams.get("away", {})
    home_team = home_team_data.get("name", "N/A")
    away_team = away_team_data.get("name", "N/A")
    home_logo = home_team_data.get("logo")
    away_logo = away_team_data.get("logo")

    # Default values for prediction fields.
    winner_str = "Data not available"
    win_or_draw_str = "Data not available"
    under_over_str = "Data not available"
    goals_str = "Data not available"
    advice_str = "No advice available"
    percent_str = "Data not available"

    if prediction_data:
        # Use the first prediction object.
        pred = prediction_data[0]
        predictions = pred.get("predictions", {})

        # Format Winner field.
        winner_obj = predictions.get("winner", {})
        winner_name = winner_obj.get("name")
        winner_comment = winner_obj.get("comment")
        if winner_name and winner_comment:
            winner_str = f"{winner_name} ({winner_comment})"
        elif winner_name:
            winner_str = f"{winner_name}"

        # Format Win_or_draw flag.
        win_or_draw = predictions.get("win_or_draw")
        if win_or_draw is not None:
            win_or_draw_str = f"{win_or_draw}"

        # Format Under_over value.
        under_over = predictions.get("under_over")
        if under_over is not None:
            under_over_str = f"{under_over}"

        # Format Goals data.
        goals_obj = predictions.get("goals", {})
        home_goals = goals_obj.get("home")
        away_goals = goals_obj.get("away")
        if home_goals is not None and away_goals is not None:
            goals_str = f"Home: {home_goals}, Away: {away_goals}"

        # Format Advice.
        advice = predictions.get("advice")
        if advice:
            advice_str = advice

        # Format Percentages data.
        percent_obj = predictions.get("percent", {})
        home_percent = percent_obj.get("home")
        draw_percent = percent_obj.get("draw")
        away_percent = percent_obj.get("away")
        if home_percent and draw_percent and away_percent:
            percent_str = f"Home: {home_percent}, Draw: {draw_percent}, Away: {away_percent}"

    # Set embed color based on predicted winner.
    color = discord.Color.blue()  # Default color
    if winner_str != "Data not available":
        if home_team.lower() in winner_str.lower():
            color = discord.Color.green()
        elif away_team.lower() in winner_str.lower():
            color = discord.Color.red()
        elif "draw" in winner_str.lower():
            color = discord.Color.gold()

    # Build a neat prediction output string with underlined and bold labels.
    prediction_output = (
        f"__**🏆 Winner:**__ {winner_str}\n"
        f"__**🤝 Win/Draw:**__ {win_or_draw_str}\n"
        f"__**📏 Under/Over:**__ {under_over_str}\n"
        f"__**⚽ Goals:**__ {goals_str}\n"
        f"__**💡 Advice:**__ {advice_str}\n"
        f"__**📊 Percent:**__ {percent_str}"
    )

    embed = discord.Embed(
        title=f"⚽ {home_team} vs {away_team}",
        description=f"**Fixture ID:** {fixture_id}\n**Date:** {fixture_date}",
        color=color
    )
    embed.add_field(name="🔮 Predictions", value=prediction_output, inline=False)
    embed.set_footer(text="Created by #armanxd_007 | Data provided by API-Football")

    # Add team logo as thumbnail (prefers home team's logo if available).
    if home_logo:
        embed.set_thumbnail(url=home_logo)
    elif away_logo:
        embed.set_thumbnail(url=away_logo)

    return embed

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
# Disable the default help command.
bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)

@bot.event
async def on_ready():
    print("Bot is ready!")
    await bot.change_presence(activity=discord.Game(name="Predictions | !help"))

# --- Prediction Command ---
@bot.command(name="prediction")
async def prediction(ctx, additional: int = 0):
    """
    Get predictions for upcoming fixtures.
    
    Usage:
      • `!prediction`             -> Displays the first match prediction.
      • `!prediction 2`           -> Displays that match plus 2 additional predictions.
      (If there aren’t enough fixtures for today, the bot searches up to 7 days ahead.)
    """
    required_count = 1 + additional
    aggregated_fixtures = []
    
    current_date = datetime.datetime.today()
    days_checked = 0

    # Search for fixtures for today and subsequent days (up to 7 days ahead).
    while len(aggregated_fixtures) < required_count and days_checked < 7:
        date_str = current_date.strftime('%Y-%m-%d')
        fixtures = get_fixtures_by_date(date_str)
        if fixtures:
            aggregated_fixtures.extend(fixtures)
        current_date += timedelta(days=1)
        days_checked += 1

    if not aggregated_fixtures:
        await ctx.send("🚫 No fixtures found for the next 7 days.")
        return

    for fixture in aggregated_fixtures[:required_count]:
        fixture_id = fixture.get("fixture", {}).get("id")
        prediction_data = get_prediction_for_fixture(fixture_id)
        embed = create_prediction_embed(fixture, prediction_data)
        await ctx.send(embed=embed)

# --- Ping Command ---
@bot.command(name="ping")
async def ping(ctx):
    """
    Responds with the bot's latency.
    """
    latency_ms = round(bot.latency * 1000, 2)
    await ctx.send(f"🏓 Pong! Latency: {latency_ms}ms")

# --- Custom Help Command ---
@bot.command(name="help")
async def help_command(ctx):
    """
    Display a help message with information on available commands.
    """
    embed = discord.Embed(
        title="🤖 Bot Help",
        description="Here are the available commands:",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="!prediction [number]",
        value="⚽ **Prediction:** Gets match predictions.\n"
              "• `!prediction` - shows one prediction.\n"
              "• `!prediction 2` - shows that match plus 2 additional predictions (searched up to 7 days ahead if needed).",
        inline=False
    )
    embed.add_field(
        name="!ping",
        value="🏓 **Ping:** Displays the bot's latency.",
        inline=False
    )
    embed.add_field(
        name="!help",
        value="ℹ️ **Help:** Displays this help message.",
        inline=False
    )
    embed.set_footer(text="Created by #armanxd_007 | Data provided by API-Football")
    await ctx.send(embed=embed)

# --- Global Error Handler ---
@bot.event
async def on_command_error(ctx, error):
    """
    Global error handler for bot commands.
    """
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❗ Error: Missing required argument. Use `!help` for usage instructions.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❗ Error: Command not found. Use `!help` to see available commands.")
    else:
        await ctx.send(f"❗ An unexpected error occurred: {error}")

# Replace "YOUR_DISCORD_BOT_TOKEN" with your actual bot token.
bot.run("MTM1Njk2Mzk0MTE0MTcwODgxMA.GY8Bh6.MokPGrwi4vyhSYZSJfJpKIPO0T1rp73kCZO05c")
