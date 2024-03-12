from typing import Final
import os
import discord
import mysql.connector
import random

from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands
from discord.ext import commands
from responses import get_response
from PIL import Image
# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
print(TOKEN)


intents: Intents = discord.Intents.all()
#intents: Intents = Intents.default()
#intents.message_content = True # NOQA
#client: Client = Client(intents=intents)
bot: commands.Bot = commands.Bot(command_prefix="!", intents=intents)
#background = Image.open("test1.png")
#foreground = Image.open("test2.png")

#background.paste(foreground, (0, 0), foreground)
#background.show()

mydb = mysql.connector.connect(
    host = 'localhost',
    user = 'root',
    password ='',
    database = 'cardsdb'
)



cursor = mydb.cursor(dictionary = True)
"""
async def send_message(message: Message, user_message: str) -> None:
    if not user_message:
        print('(Message was empty because intents were not enabled probably')
        return

    if is_private := user_message[0] == '?':
        user_message = user_message[1:]
    try:
        response: str = get_response(user_message)
        await message.author.send(response) if is_private else await message.channel.send(response)
    except Exception as e:
        print(e)
"""

@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')
    try:
        #synced = await bot.slash_command.sync_all_commands()
        synced = await bot.tree.sync()

        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name = "hello")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hey {interaction.user.mention}! This is a slash command!")

@bot.tree.command(name = "say")
@app_commands.describe(thing_to_say = "What should I say?")
async def say(interaction: discord.Interaction, thing_to_say : str):
    await interaction.response.send_message(f"Hey {interaction.user.name}! said: `{thing_to_say}`")

@bot.tree.command(name = "pull")
async def pull(interaction: discord.Interaction):
    user_id = getID(interaction)
    card_id = get_random_card_id()

    if card_id is None:
        return None
    foil_value = 1 if random.random() < 0.2 else 0

    # Construct the SQL query with placeholders
    query = (
        "INSERT INTO `cardinstances` "
        "(`InstanceID`, `UserID`, `CardID`, `Foil`, `InstanceCount`) "
        "VALUES (NULL, %s, %s, %s, '')"
    )

    # Execute the query with the provided values
    cursor.execute(query, (user_id, card_id, foil_value))
    mydb.commit()  # Commit the changes to the database

    await interaction.response.send_message(f"UserID: {user_id} RandomCardID: {card_id} Foil: {foil_value}")

@bot.tree.command(name = "mycards")
async def mycards(interaction: discord.Interaction):
    # Get the UserID from the interaction
    user_id = getID(interaction)

    # Construct the SQL query to retrieve user's cards with additional information
    query = (
        "SELECT ci.CardID, c.Name, ci.Foil, ci.InstanceCount AS Number, c.Rarity, c.Faction AS Type "
        "FROM cardinstances ci "
        "JOIN cards c ON ci.CardID = c.CardID "
        "WHERE ci.UserID = %s"
    )

    # Execute the query with the provided UserID
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()

    # Check if any cards were found
    if rows:
        # Prepare the response message
        response_message = "Your cards:\n```\n"
        response_message += "{:<10} {:<30} {:<10} {:<10} {:<10} {:<10}\n".format(
            "CardID", "Name", "Version", "Number", "Rarity", "Type"
        )
        for row in rows:
            card_id = row["CardID"]
            card_name = row["Name"]
            version = "Foil" if row["Foil"] else "Regular"
            instance_count = row["Number"]
            rarity = row["Rarity"]
            card_type = row["Type"]

            response_message += "{:<10} {:<30} {:<10} {:<10} {:<10} {:<10}\n".format(
                card_id, card_name, version, instance_count, rarity, card_type
            )
        response_message += "```"
    else:
        response_message = "You don't have any cards yet."

    # Send the response message
    await interaction.response.send_message(response_message)

"""
@client.event
async def on_message(message: Message) -> None:
    if message.author == client.user:
        return
    username: str = str(message.author)
    user_message : str = message.content
    channel: str = str(message.channel)

    print(f'[{channel}] {username}: "{user_message}"')
    await send_message(message, user_message)

@bot.command()
async def set(ctx):
    sql = "INSERT INTO users (ID, BALANCE) VALUES(%s, %s)"
    val = (ctx.author.id, "50")
    cursor.execute(sql, val)
"""

def get_random_card_id():
    # Define the probabilities for each rarity level
    rarity_probabilities = {
        "Common": 0.5,
        "Rare": 0.35,
        "Epic": 0.1,
        "Legendary": 0.5,
    }

    # Get a random value to determine the rarity
    rarity_roll = random.random()

    # Determine the rarity based on the roll
    rarity = ""
    for rarity_level, probability in rarity_probabilities.items():
        if rarity_roll < probability:
            rarity = rarity_level
            break
        rarity_roll -= probability

    # Query for a random card of the determined rarity
    query = f"SELECT CardID FROM cards WHERE Rarity = '{rarity}' ORDER BY RAND() LIMIT 1"

    # Execute the query
    cursor.execute(query)

    # Fetch the result
    result = cursor.fetchone()

    if result:
        return result['CardID']
    else:
        return None

def getID(interaction: discord.Interaction) -> int:
    discord_id = interaction.user.id
    cursor.execute(f"SELECT UserID FROM userdata WHERE DiscordID = {discord_id}")
    rows = cursor.fetchall()

    if rows:
        # If a record exists, return the existing UserID
        return rows[0]["UserID"]
    else:
        # If no record exists, create a new record and return the new UserID
        cursor.execute(f"INSERT INTO userdata (DiscordID) VALUES ({discord_id})")
        mydb.commit()  # Commit the changes to the database
        return cursor.lastrowid

def main() -> None:
    bot.run(token=TOKEN)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
# https://discord.com/oauth2/authorize?client_id=1216739702166786060&permissions=534723950656&scope=bot
#2147560448