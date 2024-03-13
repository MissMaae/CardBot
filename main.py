from typing import Final
import os
import discord
import mysql.connector
import random
import datetime
from io import BytesIO
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands
from discord.ext import commands
from responses import get_response
from PIL import Image
from discord.utils import format_dt
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
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))



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

#@bot.tree.command(name = "hello")
#async def hello(interaction: discord.Interaction):
#    await interaction.response.send_message(content=f"Hey {interaction.user.mention}! This is a slash command!",
#        file=discord.File(image_buffer, filename="result_image.png"))

@bot.tree.command(name = "say")
@app_commands.describe(thing_to_say = "What should I say?")
async def say(interaction: discord.Interaction, thing_to_say : str):
    await interaction.response.send_message(f"Hey {interaction.user.name}! said: `{thing_to_say}`")

@bot.tree.command(name = "pull")
async def pull(interaction: discord.Interaction):
    user_id = getID(interaction)

    cursor.execute("SELECT NextPull FROM userdata WHERE UserID = %s", (user_id,))
    next_pull_time = cursor.fetchone()
    current_time = datetime.datetime.now()

    if next_pull_time and next_pull_time["NextPull"] and next_pull_time["NextPull"] != "":

        print(next_pull_time["NextPull"])
        next_pull_time = datetime.datetime.strptime(next_pull_time["NextPull"], "%Y-%m-%d %H:%M:%S")

        discord_timestamp = format_dt(next_pull_time, style='R')

        if current_time < next_pull_time:
            await interaction.response.send_message(
                f"Your next card is available {discord_timestamp}."
            )
            return None

    new_next_pull_time = (current_time + datetime.timedelta(minutes=10)).replace(microsecond=0)

    cursor.execute("UPDATE userdata SET NextPull = %s WHERE UserID = %s", (new_next_pull_time, user_id))
    mydb.commit()

    card = get_random_card()
    card_id = card["CardID"]

    if card_id is None:
        return None
    foil_value = 1 if random.random() < 0.2 else 0
    foil_value = 1
    # Construct the SQL query with placeholders
    query = (
        "INSERT INTO `cardinstances` "
        "(`InstanceID`, `UserID`, `CardID`, `Foil`, `InstanceCount`) "
        "VALUES (NULL, %s, %s, %s, '')"
    )

    # Execute the query with the provided values
    cursor.execute(query, (user_id, card_id, foil_value))

    last_insert_id_query = "SELECT * FROM `cardinstances` WHERE `InstanceID` = LAST_INSERT_ID()"
    cursor.execute(last_insert_id_query)
    inserted_record = cursor.fetchone()

    mydb.commit()  # Commit the changes to the database

    cardImage = getCardImage(card, foil_value)

    cardname = card['Name']
    cardNum = inserted_record['InstanceCount']
    flavourText = card['FlavourText']
    cardRarity = card['Rarity'].lower()

    messageText = f"You got a {cardname} card. It is numbered {cardNum}! Its rarity is {cardRarity}"

    if foil_value == 1:
        messageText += " Ooh, its also foil! Nice!"
    messageText += f"\n *{flavourText}*"
    await interaction.response.send_message(messageText,
                                            file=discord.File(cardImage, filename="Congratulations.png"))



@bot.tree.command(name="mycards")
async def mycards(interaction: discord.Interaction):
    page = 0
    userID = getID(interaction)
    rows = listownedcards(userID)
    max_page = (len(rows) - 1) // 10
    if max_page == 0:
        await interaction.response.send_message(getOwnedCardsString(page, listownedcards(userID)))
    else:
        await interaction.response.send_message(getOwnedCardsString(page, listownedcards(userID)), view=PrevNextButton(page, rows))


"""
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

        # Get the index of the current display
        page = 0
        max_page = (len(rows) - 1) // 10
        start_index = page * 10
        end_index = start_index + 10

        for row in rows[start_index:end_index]:
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


        # Send the response message with buttons
        await interaction.followup.send(response_message)
    else:
        response_message = "You don't have any cards yet."

        # Send the response message
        await interaction.response.send_message(response_message)
    """

"""
class PrevNextButton(discord.ui.View):
    def __init__(self, page: int, interaction):
        super().__init__()
        self.page = page
        self.interaction = interaction
        self.add_item(discord.ui.button(label="<-", style=discord.ButtonStyle.primary))
        self.add_item(discord.ui.button(label="->", style=discord.ButtonStyle.primary))

    @discord.ui.button(label = "")
"""
class PrevNextButton(discord.ui.View):
    def __init__(self, page: int, rows):
        super().__init__()
        self.page = page
        self.rows = rows
        self.max_page = (len(rows) - 1) // 10
    @discord.ui.button(label="<-", custom_id="prev_button")
    async def on_prev_button(self,  interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        if self.page < 0:
            self.page = 0
        await interaction.message.edit(content=getOwnedCardsString(self.page, self.rows), view=self)
        await interaction.response.defer()


    @discord.ui.button(label="->", custom_id="next_button")
    async def on_next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page > self.max_page:
            self.page = self.max_page
        await interaction.message.edit(content=getOwnedCardsString(self.page, self.rows), view=self)
        await interaction.response.defer()



    """
    async def on_button_click(self, button: discord.ui.Button, interaction: discord.Interaction):
        if button.custom_id == "prev_button":
            self.page -= 1
        elif button.custom_id == "next_button":
            self.page += 1
        print(self.page)
        await interaction.response.edit_message(content=listownedcards(self.page, self.interaction), view=self)
    """

def listownedcards(user_id : int):
    # Get the UserID from the interaction


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
    return rows

def getOwnedCardsString(page: int, rows):
    max_page = (len(rows) - 1) // 10
    start_index = page * 10
    end_index = start_index + 10


    # Check if any cards were found
    if rows:
        # Prepare the response message
        response_message = f"Page {page + 1} of {max_page + 1}\n```\n"
        response_message += "{:<10} {:<30} {:<10} {:<10} {:<10} {:<10}\n".format(
            "CardID", "Name", "Version", "Number", "Rarity", "Type"
        )

        # Get the index of the current display

        #


        for row in rows[start_index:end_index]:
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
        return response_message
    return None


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

def get_random_card():
    # Define the probabilities for each rarity level
    rarity_probabilities = {
        "Common": 0.5,
        "Uncommon": 0.35,
        "Rare": 0.1,
        "Mythic Rare": 0.5,
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
    query = f"SELECT * FROM cards WHERE Rarity = '{rarity}' ORDER BY RAND() LIMIT 1"

    # Execute the query
    cursor.execute(query)

    # Fetch the result
    result = cursor.fetchone()

    if result:
        return result
    else:
        return None

def getCardImage(theCard, foil : int):
    print(theCard)
    try:
        cardImage = theCard["Picture"]
        background = Image.open(os.path.join(ROOT_DIR, f"Images\\{cardImage}"))
    except Exception as e:
        background = Image.open(os.path.join(ROOT_DIR, f"Images\\MissingArt.png"))
    try:
        rarityLayer = getCardRarityImage(theCard["Rarity"])
        factionLayer = getCardFactionImage(theCard["Faction"])
        background.paste(rarityLayer, (0, 0), rarityLayer)
        background.paste(factionLayer, (0, 0), factionLayer)

        if(foil == 1):
            path = os.path.join(ROOT_DIR, 'Overlays\\')
            foilLayer = Image.open(os.path.join(path, 'Foil.png'))

            background.paste(foilLayer, (0,0), foilLayer)


        image_buffer = BytesIO()
        background.save(image_buffer, format="PNG")
        image_buffer.seek(0)
        return image_buffer
    except Exception as e:
        print(e)
        return None

def getCardRarityImage(cardRarity):
    outimage = None
    path = os.path.join(ROOT_DIR, 'Overlays\\')
    match cardRarity:
        case 'Common':
            outimage = Image.open(os.path.join(path, 'Common.png'))
        case 'Uncommon':
            outimage = Image.open(os.path.join(path, 'Uncommon.png'))
        case 'Rare':
            outimage = Image.open(os.path.join(path, 'Rare.png'))
        case 'Mythic Rare':
            outimage = Image.open(os.path.join(path, 'Mythic.png'))
        case _:
            outimage = None
    return outimage

def getCardFactionImage(cardFaction):
    outimage = None
    path = os.path.join(ROOT_DIR, 'Overlays\\')
    match cardFaction:
        case 'Phoenix Company':
            outimage = Image.open(os.path.join(path, 'Phoenix.png'))
        case 'T.A.L.O.S Company':
            outimage = Image.open(os.path.join(path, 'TALOS.png'))
        case 'Battalion Command':
            outimage = Image.open(os.path.join(path, 'Command.png'))
        case 'Meowmelts':
            outimage = Image.open(os.path.join(path, 'Meowmelt.png'))
        case 'Events':
            outimage = Image.open(os.path.join(path, 'Event.png'))
        case 'Community':
            outimage = Image.open(os.path.join(path, 'Community.png'))
        case _:
            outimage = None
    return outimage


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