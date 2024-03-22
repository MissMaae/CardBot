from typing import Final
import os
import discord
import mysql.connector
import random
import datetime
import typing
import io
import base64
from io import BytesIO
from dotenv import load_dotenv
from discord import Intents, Client, Message, app_commands, Embed
from discord.ext import commands
from responses import get_response
from PIL import Image, ImageOps, ImageFont, ImageDraw, ImageFilter
from discord.utils import format_dt
#from matplotlib import font_manager
# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
print(TOKEN)

currencyName = "screamcoin"

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

hiddenchannelname = 'hiddenchannel'

@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')
    try:
        #synced = await bot.slash_command.sync_all_commands()
        synced = await bot.tree.sync()

        print(f"Synced {len(synced)} command(s)")
        global hiddenchannel
        hiddenchannel = getHiddenchannel()
    except Exception as e:
        print(e)

def getHiddenchannel():
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name == hiddenchannelname:
                return channel
                print("found hidden channel.")
                break
    print("channel not found")
    return None

@bot.tree.command(name = "open_pack")
async def openpack(interaction: discord.Interaction):
    user_id = getID(interaction)

    cursor.execute("SELECT NextPull FROM userdata WHERE UserID = %s", (user_id,))
    next_pull_time = cursor.fetchone()
    current_time = datetime.datetime.now()
    """
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
    
    # cursor.execute("UPDATE userdata SET NextPull = %s WHERE UserID = %s", (new_next_pull_time, user_id))
    cursor.execute("UPDATE userdata SET NextPull = %s, Currency = Currency + 10 WHERE UserID = %s",
                   (new_next_pull_time, user_id))
    mydb.commit()
    """
    pack_structure = ["Common","Common","Common","Uncommon","Uncommon","Rare"]
    pack_structure[5] = "Mythic Rare" if random.random() < 0.2 else "Rare"

    packLength = len(pack_structure)
    cards = [None] * packLength
    print("cardlength " + str(len(cards)))
    print("packlength " + str(len(pack_structure)))
    foilValues = [None] * packLength
    cardImages = [None] * packLength
    index = 0
    for rarity in pack_structure:

        card = get_random_card(rarity)
        card_id = card["CardID"]
        cards[index] = card
        #if card_id is None:
        #    return None
        foil_value = 1 if random.random() < 0.1 else 0
        foilValues[index] = foil_value
        # foil_value = 1
        # Construct the SQL query with placeholders
        query = (
            "INSERT INTO `cardinstances` "
            "(`InstanceID`, `UserID`, `CardID`, `Foil`, `InstanceCount`) "
            "VALUES (NULL, %s, %s, %s, '')"
        )

        cursor.execute(query, (user_id, card_id, foil_value))

        last_insert_id_query = "SELECT InstanceCount FROM `cardinstances` WHERE `InstanceID` = LAST_INSERT_ID()"
        cursor.execute(last_insert_id_query)
        newInstanceCount = cursor.fetchone()['InstanceCount']
        cardImages[index] = getCardImage(card, foilValues[index], newInstanceCount)

        index += 1
    max_images_per_line = 3
    widths, heights = zip(*(i.size for i in cardImages))

    max_height = max(heights)
    max_width = max(widths)*max_images_per_line

    # Calculate number of lines needed
    num_lines = -(-len(cardImages) // max_images_per_line)

    packImage = Image.new('RGBA', (max_width, max_height * num_lines))

    x_offset, y_offset = 0, 0
    image_count = 0

    for im in cardImages:
        packImage.paste(im, (x_offset, y_offset))
        x_offset += im.size[0]

        image_count += 1

        # Check if we need to start a new line
        if image_count >= max_images_per_line:
            y_offset += max_height
            x_offset = 0
            image_count = 0



    packImage.save('test.png')
    mydb.commit()

    myEmbed = await imageToEmbed(packImage, "AAAAAND OPEN!", "you got some cards!", rarityToColour(pack_structure[5]))

    await interaction.response.send_message("Here ya go!", view=OpenPackButton(myEmbed))


class OpenPackButton(discord.ui.View):
    def __init__(self, myEmbed):
        super().__init__()
        self.myEnb = myEmbed

    @discord.ui.button(label="OPEN PACK!", custom_id="open_button")
    async def open_button(self,  interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.message.edit(embed=self.myEnb, view=None)
        await interaction.response.defer()

async def imageToEmbed(image, title, description, colour = 0xa84342):
    imgmessage = await hiddenchannel.send(file=discord.File(cardToBuffer(image), filename="AWMCards.png"))
    image_url = imgmessage.attachments[0].url
    new_embed = Embed(title=title, description=description, color=colour)
    new_embed.set_image(url=image_url)
    return new_embed

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

    #cursor.execute("UPDATE userdata SET NextPull = %s WHERE UserID = %s", (new_next_pull_time, user_id))
    cursor.execute("UPDATE userdata SET NextPull = %s, Currency = Currency + 1 WHERE UserID = %s",
                   (new_next_pull_time, user_id))
    mydb.commit()

    card = get_random_card()
    card_id = card["CardID"]

    if card_id is None:
        return None
    foil_value = 1 if random.random() < 0.2 else 0
    #foil_value = 1
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

    messageText = f"You got a {cardname} card. It is numbered {cardNum}! Its rarity is {cardRarity}."

    if foil_value == 1:
        messageText += " Ooh, its also foil! Nice!"
    messageText += f"\n *{flavourText}*"
    myEmbed = await imageToEmbed(cardImage, "You got a card!", messageText, rarityToColour(card['Rarity']))

    await interaction.response.send_message(embed=myEmbed)

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

def cardToBuffer(cardImage):
    image_buffer = BytesIO()
    cardImage.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    return image_buffer



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


def listownedcards(user_id : int):
    # Get the UserID from the interaction


    # Construct the SQL query to retrieve user's cards with additional information

    query = (
        "SELECT ci.CardID, ci.InstanceID, c.Name, ci.Foil, ci.InstanceCount AS Number, ci.SalePrice AS Market_price , c.Rarity, c.Faction AS Type "
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
        response_message += "{:<10} {:<10} {:<30} {:<10} {:<10} {:<10} {:<10} {:<10}\n".format(
            "CardID", "InstanceID", "Name", "Version", "Number", "Rarity", "Type", "Market price"
        )

        # Get the index of the current display

        #


        for row in rows[start_index:end_index]:
            card_id = row["CardID"]
            instance_id = row["InstanceID"]
            card_name = row["Name"]
            version = "Foil" if row["Foil"] else "Regular"
            instance_count = row["Number"]
            rarity = row["Rarity"]
            card_type = row["Type"]
            sale_price = row["Market_price"] if row["Market_price"] else "Not for sale"

            response_message += "{:<10} {:<10} {:<30} {:<10} {:<10} {:<10} {:<10} {:<10}\n".format(
                card_id, instance_id, card_name, version, instance_count, rarity, card_type, sale_price
            )

        response_message += "```"
        return response_message
    return None


def getCardList():
    # Query for a random card of the determined rarity
    query = f"SELECT Name FROM cards"
    cursor.execute(query)

    # Fetch the result
    return cursor.fetchall()

allcards = getCardList()

@bot.tree.command()
async def viewcard(interaction: discord.Interaction, cardname: str):
    query = f"SELECT * FROM cards WHERE Name = '{cardname}' LIMIT 1"
    cursor.execute(query)
    foundCard = cursor.fetchone()
    messageText = f"{foundCard['Name']} \n *{foundCard['FlavourText']}*"

    myEmbed = await imageToEmbed(getCardImage(foundCard, 0), "Card found", messageText, rarityToColour(foundCard['Rarity']))

    await interaction.response.send_message(embed=myEmbed)



@viewcard.autocomplete("cardname")
async def viewcard_autocompletion(
    interaction: discord.Interaction,
    current: str
) -> typing.List[app_commands.Choice[str]]:
    data = []
    #print(allcards)
    for card_choice in allcards:
        card_name = card_choice['Name']
        data.append(app_commands.Choice(name=card_name, value=card_name))
    return data

def get_random_card(rarity = None):
    if rarity == None:
    # Define the probabilities for each rarity level
        rarity_probabilities = {
            "Common": 0.5,
            "Uncommon": 0.35,
            "Rare": 0.1,
            "Mythic Rare": 0.05,
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
    query = f"SELECT * FROM cards WHERE Rarity = '{rarity}' AND Active = 1 ORDER BY RAND() LIMIT 1"

    # Execute the query
    cursor.execute(query)

    # Fetch the result
    result = cursor.fetchone()

    if result:
        return result
    else:
        return None

def getCardImage(theCard, foil : int, instanceNum = None):
    print(theCard)
    try:
        cardImage = theCard["Picture"]
        background = Image.open(os.path.join(ROOT_DIR, f"Images\\{cardImage}"))#.convert("RGBA")
    except Exception as e:
        background = Image.open(os.path.join(ROOT_DIR, f"Images\\MissingArt.png"))#.convert("RGBA")
    try:
        #underlay = Image.open(os.path.join(ROOT_DIR, f"Overlays\\underLayer.png"))
        #overlay = Image.open(os.path.join(ROOT_DIR, f"Overlays\\overLayer.png"))
        mask = Image.open(os.path.join(ROOT_DIR, f"Overlays\\Mask.png"))

        background = Image.composite(background, Image.new("RGBA", background.size, (0, 0, 0, 0)), mask)
        rarityLayer = getCardRarityImage(theCard["Rarity"])
        factionLayer = getCardFactionImage(theCard["Faction"])
        #background.paste(underlay, (0, 0), underlay)
        background.paste(rarityLayer, (0, 0), rarityLayer)
        background.paste(factionLayer, (0, 0), factionLayer)

        #print(font_manager.get_font_names())

        width, height = background.size

        draw = ImageDraw.Draw(background)
        fontpath = os.path.join(ROOT_DIR, 'spectrashell.otf')
        myFont = ImageFont.truetype(fontpath, 38)
        myFont2 = ImageFont.truetype(fontpath, 20)

        if instanceNum != None:
            instanceFont = ImageFont.truetype(fontpath, 15)
            instancenumText = f"#{instanceNum}"
            #instancenumText = f"#10000000000"
            instextwidth, instextheight = get_text_dimensions(instancenumText, instanceFont)
            draw.text((width - instextwidth - 25, height - 50), instancenumText, (0, 0, 0), font=instanceFont)

        cardname = theCard["Name"]
        textwidth, textheight = get_text_dimensions(cardname, myFont)
        textwidth2, textheight2 = get_text_dimensions(theCard["Faction"], myFont2)

        draw.text(((width/2) - (textwidth/2), height-82), cardname, (0, 0, 0), font=myFont)
        draw.text( ((width/2) - (textwidth2/2), height-105), theCard["Faction"], (0, 0, 0), font=myFont2)
        #background.paste(overlay, (0, 0), overlay)

        if theCard["Illustrator"] is not None and theCard["Illustrator"] != "":
            illusFont = ImageFont.truetype(fontpath, 12)
            text = f"Illus. {theCard["Illustrator"]}"
            illusW, illusH = get_text_dimensions(text, illusFont)
            txt = Image.new('L', (illusW, illusH))
            d = ImageDraw.Draw(txt)
            d.text((0, 0), text, font=illusFont, fill=255)
            w = txt.rotate(90, expand=1)
            background.paste(ImageOps.colorize(w, (0,0,0), (255,255,255)), (437+illusH,height-60 - illusW),  w)


        if (foil == 1):
            path = os.path.join(ROOT_DIR, 'Overlays\\')
            foilLayer = Image.open(os.path.join(path, 'Foil.png'))
            #background.paste(foilLayer, (0, 0), foilLayer)
            background = Image.alpha_composite(background, foilLayer)

        return background
    except Exception as e:
        print(e)
        return None

def get_text_dimensions(text_string, font):
    # https://stackoverflow.com/a/46220683/9263761
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return (text_width, text_height)

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
        case 'Location':
            outimage = Image.open(os.path.join(path, 'Location.png'))
        case _:
            outimage = None
    return outimage


def rarityToColour(rarity):
    outcolour = None
    match rarity:
        case 'Common':
            outcolour = 0x000000
        case 'Uncommon':
            outcolour = 0xa2c5d6
        case 'Rare':
            outcolour = 0xceb370
        case 'Mythic Rare':
            outcolour = 0xb02911
        case _:
            outcolour = None
    return outcolour

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

async def getIDMember(user: discord.Member) -> int:
    discord_id = user.id
    if discord_id is None:
        return None

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

@bot.tree.command()
async def viewmycard(interaction: discord.Interaction, instanceid: int):
    query = (
        "SELECT ci.CardID, ci.InstanceID, c.Name,c.FlavourText, ci.Foil, ci.InstanceCount, c.Rarity, c.Picture , c.Faction, c.Illustrator "
        "FROM cardinstances ci "
        "JOIN cards c ON ci.CardID = c.CardID "
        "WHERE ci.InstanceID = %s"

    )
    cursor.execute(query, (instanceid,))

    foundCard = cursor.fetchone()
    if foundCard == None:
        await interaction.response.send_message("Card not found")
        return

    print(foundCard)
    messageText = f"{foundCard['Name']} \n *{foundCard['FlavourText']}*"
    myEmbed = await imageToEmbed(getCardImage(foundCard, foundCard['Foil'], foundCard['InstanceCount']), "Card found", messageText, rarityToColour(foundCard['Rarity']))
    await interaction.response.send_message(embed=myEmbed)

@bot.tree.command()
async def givecard(interaction: discord.Interaction, instanceid: int, recipient: discord.Member):
    try:
        myID = getID(interaction)
        recipientID = await getIDMember(recipient)

        if(recipientID == None):
            await interaction.response.send_message("User not found.")
            return

        if recipientID == myID:
            await interaction.response.send_message("You cannot give yourself cards.")
            return
        query = f"SELECT * FROM cardinstances WHERE InstanceID = '{instanceid}' AND UserID = '{myID}'"
        cursor.execute(query)
        foundCard = cursor.fetchall()
        print(foundCard)
        if(len(foundCard) == 0):
            await interaction.response.send_message("Either the instance could not be found or you do not own it.")
            return

        query = f"UPDATE cardinstances SET SalePrice = NULL, UserID = '{recipientID}' WHERE InstanceID = '{instanceid}' AND UserID = '{myID}' LIMIT 1"
        cursor.execute(query)
        mydb.commit()

        await interaction.response.send_message(f"Success! {recipient} now owns the card with instanceID {instanceid}.")
    except Exception as e:
        await interaction.response.send_message("Error.")

@bot.tree.command()
async def market_buy(interaction: discord.Interaction, instanceid: int):
    try:

        query = f"SELECT * FROM cardinstances WHERE InstanceID = '{instanceid}' AND SalePrice IS NOT NULL"
        cursor.execute(query)
        foundCard = cursor.fetchall()[0]

        if not foundCard:
            await interaction.response.send_message("A card was not found or the card is not for sale.")
            return None

        discord_id = interaction.user.id
        query = cursor.execute(f"SELECT * FROM userdata WHERE DiscordID = '{discord_id}' LIMIT 1")
        cursor.execute(query)
        myuser = cursor.fetchall()[0]

        print("Found card:", foundCard)
        print("Buyer:", myuser)
        sellerID = foundCard['UserID']
        myID = myuser['UserID']

        if sellerID == myID:
            await interaction.response.send_message(f"You cannot buy this card because you are the seller.")
            return

        if myuser['Currency'] < foundCard['SalePrice']:
            await interaction.response.send_message(f"You don't have enough {currencyName}.")
            return

        query = "UPDATE userdata SET Currency = Currency + %s WHERE UserID = '%s'"
        cursor.execute(query, (foundCard['SalePrice'], sellerID))

        query = "UPDATE userdata SET Currency = Currency - %s WHERE UserID = '%s'"
        cursor.execute(query, (foundCard['SalePrice'], myID))

        query = f"UPDATE cardinstances SET SalePrice = NULL, UserID = '{myID}' WHERE InstanceID = '{instanceid}' LIMIT 1"
        cursor.execute(query)

        mydb.commit()
        await interaction.response.send_message("You just bought a card!")
    except Exception as e:
        await interaction.response.send_message("Error encountered")

@bot.tree.command()
async def collection(interaction: discord.Interaction):
    discord_id = interaction.user.id
    cursor.execute(f"SELECT Currency, UserID FROM userdata WHERE DiscordID = {discord_id}")
    rows = cursor.fetchall()

    if rows:
        # If a record exists, return the existing UserID
        amount = rows[0]["Currency"]


    else:
        # If no record exists, create a new record and return the new UserID
        cursor.execute(f"INSERT INTO userdata (DiscordID) VALUES ({discord_id})")
        mydb.commit()  # Commit the changes to the database
        cursor.execute(f"SELECT Currency, UserID FROM userdata WHERE DiscordID = {discord_id}")
        rows = cursor.fetchall()
        amount = rows[0]["Currency"]

    user_id = rows[0]["UserID"]
    total_unique_cards_query = f"SELECT COUNT(DISTINCT CardID) AS cardcount FROM cardinstances WHERE UserID = '{user_id}'"
    cursor.execute(total_unique_cards_query)

    total_unique_cards = cursor.fetchone()['cardcount']

        # Query to count unique cards by faction
    faction_unique_cards_query = (
        f"SELECT Faction, COUNT(DISTINCT cardinstances.CardID) AS FactionCount "
        f"FROM cardinstances "
        f"JOIN cards ON cardinstances.CardID = cards.CardID "
        f"WHERE UserID = '{user_id}' "
        f"GROUP BY Faction"
    )
    cursor.execute(faction_unique_cards_query)
    faction_unique_cards = cursor.fetchall()
    print(faction_unique_cards)
    outstring = f"You have {amount} {currencyName}. \n"
    outstring += f"Your collection progress is {total_unique_cards} out of {len(allcards)} \n"
    outstring += f"Your card count by faction is: \n"

    for entry in faction_unique_cards:
        outstring += f"{entry['Faction']} : {entry['FactionCount']} \n"

    await interaction.response.send_message(outstring)

@bot.tree.command()
async def market_sell(interaction: discord.Interaction, instanceid: int, price: int):
    try:
        myID = getID(interaction)
        query = f"UPDATE cardinstances SET SalePrice = {price} WHERE InstanceID = {instanceid} AND UserID = {myID}"
        cursor.execute(query)
        mydb.commit()
        await interaction.response.send_message(f"Card listed for sale for {price} {currencyName}.")
    except Exception as e:
        await interaction.response.send_message("Either the card was not found or you do not own it.")
@bot.tree.command()
async def market_delist(interaction: discord.Interaction, instanceid: int):
    try:
        myID = getID(interaction)
        query =  f"UPDATE cardinstances SET SalePrice = NULL WHERE InstanceID = '{instanceid}' AND UserID = '{myID}'"
        cursor.execute(query)
        mydb.commit()
        await interaction.response.send_message(f"Card delisted.")

    except Exception as e:
        await interaction.response.send_message("Either the card was not found or you do not own it.")

@bot.tree.command()
async def market_show(interaction: discord.Interaction, cardname : str):
    # Get the user ID of the person who called the command
    myID = getID(interaction)

    # Query the database to find card instances
    query = (
        f"SELECT * "
        f"FROM cardinstances "
        f"JOIN cards ON cardinstances.CardID = cards.CardID "
        f"JOIN userdata ON cardinstances.UserID = userdata.UserID "
        f"WHERE cards.Name = '{cardname}' "
        #f"AND cardinstances.UserID != {myID} "
        f"AND cardinstances.SalePrice IS NOT NULL "
        f"ORDER BY cardinstances.SalePrice"
    )
    page = 0
    cursor.execute(query)
    card_instances = cursor.fetchall()
    print(card_instances)
    mystring = await getMarketString(page, card_instances)


    # Display the results
    if card_instances:
        if((len(card_instances) - 1) // 10) == 0:
            await interaction.response.send_message(mystring)
        else:
            await interaction.response.send_message(mystring, view=PrevNextButtonMarket(page, card_instances))
    else:
        await interaction.response.send_message(f"No card instances found for {cardname}")

@market_show.autocomplete("cardname")
async def market_show_autocompletion(
    interaction: discord.Interaction,
    cardname: str
) -> typing.List[app_commands.Choice[str]]:
    data = []
    #print(allcards)
    for card_choice in allcards:
        card_name = card_choice['Name']
        data.append(app_commands.Choice(name=card_name, value=card_name))
    return data



class PrevNextButtonMarket(discord.ui.View):
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
        await interaction.message.edit(content=getMarketString(self.page, self.rows), view=self)
        await interaction.response.defer()


    @discord.ui.button(label="->", custom_id="next_button")
    async def on_next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page > self.max_page:
            self.page = self.max_page
        await interaction.message.edit(content=getMarketString(self.page, self.rows), view=self)
        await interaction.response.defer()


async def getMarketString(page: int, rows):
    max_page = (len(rows) - 1) // 10
    start_index = page * 10
    end_index = start_index + 10

    # Check if any cards were found
    if rows:
        # Prepare the response message
        response_message = f"Page {page + 1} of {max_page + 1}\n```\n"
        response_message += "{:<10} {:<10} {:<30} {:<10} {:<20} {:<10} {:<10}\n".format(
            "InstanceID", "CardID", "Name", "Price", "Seller", "Version", "Card number"
        )

        for row in rows[start_index:end_index]:
            instance_id = row["InstanceID"]
            card_id = row["CardID"]
            card_name = row["Name"]
            sale_price = row["SalePrice"] if row["SalePrice"] else "Not for sale"
            version = "Foil" if row["Foil"] else "Regular"
            card_number = row["InstanceCount"]
            # Fetch the username based on DiscordID
            discord_id = row["DiscordID"]
            try:
                seller = await bot.fetch_user(int(discord_id))
                seller_name = seller.name
            except discord.NotFound:
                seller_name = "Unknown"

            response_message += "{:<10} {:<10} {:<30} {:<10} {:<20} {:<10} {:<10}\n".format(
                instance_id, card_id, card_name, sale_price, seller_name, version, card_number
            )

        response_message += "```"
        return response_message
    return None



def main() -> None:
    #getCardList()
    bot.run(token=TOKEN)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
# https://discord.com/oauth2/authorize?client_id=1216739702166786060&permissions=534723950656&scope=bot
#2147560448