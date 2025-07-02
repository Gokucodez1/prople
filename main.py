import discord
from discord.ext import commands
import json
import random
import asyncio
import requests

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

# Initialize bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Global data
category_id = config["CATEGORY_ID"]
admin_ids = config["ADMIN_IDS"]
EMBED_COLOR_GREEN = 0x00ff00
EMBED_COLOR_RED = 0xff0000
EMBED_COLOR_CYAN = 0x00ffff

channel_data = {}  # Stores channel-specific info like roles, amount, txid


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="Auto MM"))
    bot.loop.create_task(auto_check_transactions())
    print("Bot is ready.")


@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.category_id == category_id:
        code = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=24))
        await channel.send(f"```{code}```")
        await channel.send("Please send the **Developer ID** of the user you are dealing with.")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.TextChannel) and message.channel.category_id == category_id:
        await handle_channel_messages(message)

    elif message.content.startswith("$release") and message.channel.category_id == category_id:
        await handle_release_command(message)


async def handle_channel_messages(message):
    channel = message.channel
    author = message.author

    if channel.id not in channel_data:
        channel_data[channel.id] = {
            "users": [],
            "roles": {},
            "amount": None,
            "txid": None,
            "ltc_address": None,
            "start_time": discord.utils.utcnow(),
            "sender_confirmed": False,
            "receiver_confirmed": False
        }

    # Developer ID check (any valid Discord user ID)
    try:
        dev_id = int(message.content.strip())
        added_user = bot.get_user(dev_id)
        if not added_user:
            await channel.send("User not found.")
            return

        overwrites = channel.overwrites_for(added_user)
        overwrites.read_messages = True
        overwrites.send_messages = True
        await channel.set_permissions(added_user, overwrite=overwrites)

        await channel.send(f"{added_user.mention} has been added to the ticket!")
        channel_data[channel.id]["users"].append(added_user.id)

        # Send Crypto MM embed
        embed = discord.Embed(
            title="Crypto MM",
            description="Welcome to our automated cryptocurrency Middleman system!",
            color=EMBED_COLOR_GREEN
        )
        embed.set_footer(text="Created by: Exploit")
        await channel.send(embed=embed)

        # Warning embed
        embed = discord.Embed(
            title="Please Read!",
            description="Ensure all deal conversations happen here.",
            color=EMBED_COLOR_RED
        )
        await channel.send(embed=embed)

        await send_role_selection(channel)

    except ValueError:
        pass  # Skip if message isn't a valid dev ID

    if message.content.lower() in ["sending", "receiving"]:
        role = "Sender" if message.content.lower() == "sending" else "Receiver"
        channel_data[channel.id]["roles"][message.author.id] = role
        await update_role_selection(channel)

        if len(channel_data[channel.id]["roles"]) == 2:
            await send_confirmation(channel)

    elif message.content.isdigit() or '.' in message.content:
        try:
            amount = float(message.content)
            channel_data[channel.id]["amount"] = amount

            await send_deal_amount_confirmation(channel, amount)

        except ValueError:
            await channel.send("Invalid amount.")

    elif message.content.lower() == "correct":
        await channel.send(f"{message.author.mention} responded with 'Correct'")
        is_sender = message.author.id in [u for u, r in channel_data[channel.id]["roles"].items() if r == "Sender"]
        if is_sender:
            channel_data[channel.id]["sender_confirmed"] = True
        else:
            channel_data[channel.id]["receiver_confirmed"] = True

        if channel_data[channel.id]["sender_confirmed"] and channel_data[channel.id]["receiver_confirmed"]:
            await send_payment_invoice(channel)

    elif message.content.lower() == "incorrect":
        channel_data[channel.id]["sender_confirmed"] = False
        channel_data[channel.id]["receiver_confirmed"] = False
        await channel.send(f"{message.author.mention} responded with 'Incorrect'. Please re-enter the deal amount.")


async def handle_release_command(message):
    if message.author.id not in admin_ids:
        await message.channel.send("❌ You don’t have permission to use this command.")
        return

    ch_id = message.channel.id
    if ch_id not in channel_
        await message.channel.send("No active deal in this channel.")
        return

    data = channel_data[ch_id]
    if "amount" not in 
        await message.channel.send("Deal has not reached payment stage yet.")
        return

    receiver = next((u for u, r in data["roles"].items() if r == "Receiver"), None)
    if not receiver:
        await message.channel.send("No Receiver found in this deal.")
        return

    await message.channel.send(f"<@{receiver}> Please provide your Litecoin address.")

    def check(m):
        return m.author.id == receiver and m.channel == message.channel

    try:
        reply = await bot.wait_for("message", check=check, timeout=120)
        ltc_address = reply.content.strip()

        # Simulate sending funds
        txid = "simulated_txid_1234567890abcdef"

        embed = discord.Embed(title="Release Successful", color=EMBED_COLOR_GREEN)
        embed.add_field(name="Address", value=f"`{ltc_address}`", inline=False)
        embed.add_field(name="TXID", value=f"`{txid}`", inline=False)
        embed.add_field(name="You Received", value=f"${data['amount']:.2f}", inline=False)
        await message.channel.send(embed=embed)

        embed = discord.Embed(
            title="Deal Completed",
            description="Thank you for using the auto middleman service.",
            color=EMBED_COLOR_GREEN
        )
        await message.channel.send(embed=embed)

        del channel_data[ch_id]

    except asyncio.TimeoutError:
        await message.channel.send("⏰ Receiver did not respond. Deal canceled.")
        del channel_data[ch_id]


async def auto_check_transactions():
    """Background task that periodically checks for transactions"""
    await bot.wait_until_ready()

    while not bot.is_closed():
        for ch_id, data in list(channel_data.items()):
            channel = bot.get_channel(ch_id)

            if data.get("amount") and not data.get("txid"):
                ltc_address = data.get("ltc_address", random.choice(open("ltcaddy.txt").readlines()).strip())
                channel_data[ch_id]["ltc_address"] = ltc_address

                try:
                    from sochain import check_ltc_transaction
                    tx_data = await check_ltc_transaction(ltc_address)

                    if tx_data["success"]:
                        channel_data[ch_id]["txid"] = tx_data["txid"]
                        await process_auto_release(channel, ch_id)

                except Exception as e:
                    await channel.send(f"⚠️ Error checking transaction: {str(e)}")

            # Check for expired deals
            start_time = data.get("start_time")
            if start_time and (discord.utils.utcnow() - start_time).total_seconds() > 3600:  # 1 hour
                await channel.send("⏰ This deal has expired due to inactivity.")
                del channel_data[ch_id]

        await asyncio.sleep(30)


async def process_auto_release(channel, ch_id):
    data = channel_data[ch_id]
    receiver = next((u for u, r in data["roles"].items() if r == "Receiver"), None)

    if not receiver:
        return

    await channel.send(f"<@{receiver}> Please provide your Litecoin address.")

    def check(m):
        return m.author.id == receiver and m.channel == channel

    try:
        reply = await bot.wait_for("message", check=check, timeout=120)
        ltc_address = reply.content.strip()

        # Simulate sending LTC (until real wallet integration is ready)
        txid = "simulated_txid_" + "".join(random.choices("abcdef0123456789", k=12)

        embed = discord.Embed(title="Release Successful", color=EMBED_COLOR_GREEN)
        embed.add_field(name="Address", value=f"`{ltc_address}`", inline=False)
        embed.add_field(name="TXID", value=f"`{txid}`", inline=False)
        embed.add_field(name="You Received", value=f"${data['amount']:.2f}", inline=False)
        await channel.send(embed=embed)

        embed = discord.Embed(
            title="Deal Completed",
            description="Thank you for using the auto middleman service.",
            color=EMBED_COLOR_GREEN
        )
        await channel.send(embed=embed)

        del channel_data[ch_id]

    except asyncio.TimeoutError:
        await channel.send("⏰ Receiver did not respond. Deal canceled.")
        del channel_data[ch_id]


async def get_ltc_price_usd():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
    try:
        response = requests.get(url)
        data = response.json()
        return data["litecoin"]["usd"]
    except:
        return 856.30  # Fallback rate


async def send_role_selection(channel):
    embed = discord.Embed(title="Role Selection", description="Select your role:", color=EMBED_COLOR_CYAN)
    embed.add_field(name="Sending Litecoin (Buyer)", value="None", inline=False)
    embed.add_field(name="Receiving Litecoin (Seller)", value="None", inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Sending", custom_id="sending"))
    view.add_item(discord.ui.Button(label="Receiving", custom_id="receiving"))
    view.add_item(discord.ui.Button(label="Reset", style=discord.ButtonStyle.danger, custom_id="reset"))

    await channel.send(embed=embed, view=view)


async def update_role_selection(channel):
    embed = discord.Embed(title="Role Selection", description="Select your role:", color=EMBED_COLOR_CYAN)
    roles = channel_data[channel.id]["roles"]
    sender = next((u for u, r in roles.items() if r == "Sender"), None)
    receiver = next((u for u, r in roles.items() if r == "Receiver"), None)

    embed.add_field(name="Sending Litecoin (Buyer)", value=f"<@{sender}>" if sender else "None", inline=False)
    embed.add_field(name="Receiving Litecoin (Seller)", value=f"<@{receiver}>" if receiver else "None", inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Sending", custom_id="sending"))
    view.add_item(discord.ui.Button(label="Receiving", custom_id="receiving"))
    view.add_item(discord.ui.Button(label="Reset", style=discord.ButtonStyle.danger, custom_id="reset"))

    await channel.send(embed=embed, view=view)


async def send_confirmation(channel):
    embed = discord.Embed(title="Confirmation", description="Both users have confirmed their identities.", color=EMBED_COLOR_GREEN)
    roles = channel_data[channel.id]["roles"]
    sender = next((u for u, r in roles.items() if r == "Sender"), None)
    receiver = next((u for u, r in roles.items() if r == "Receiver"), None)

    embed.add_field(name="Sending Litecoin", value=f"<@{sender}>" if sender else "None", inline=False)
    embed.add_field(name="Receiving Litecoin", value=f"<@{receiver}>" if receiver else "None", inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Correct", style=discord.ButtonStyle.green, custom_id="correct"))
    view.add_item(discord.ui.Button(label="Incorrect", style=discord.ButtonStyle.red, custom_id="incorrect"))

    await channel.send(embed=embed, view=view)


async def send_deal_amount_confirmation(channel, amount):
    embed = discord.Embed(title="Deal Amount", color=EMBED_COLOR_GREEN)
    embed.add_field(name="Sender", value=f"<@{channel_data[channel.id]['users'][0]}>", inline=False)
    embed.add_field(name="Amount", value=f"${amount + 0.03:.2f} (Includes $0.03 Fee)", inline=False)
    embed.add_field(name="Net to Receiver", value=f"${amount:.2f}", inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Correct", style=discord.ButtonStyle.green, custom_id="correct"))
    view.add_item(discord.ui.Button(label="Incorrect", style=discord.ButtonStyle.red, custom_id="incorrect"))

    await channel.send(embed=embed, view=view)


async def send_payment_invoice(channel):
    amount = channel_data[channel.id]["amount"] + 0.03
    ltc_address = random.choice(open("ltcaddy.txt").readlines()).strip()
    channel_data[channel.id]["ltc_address"] = ltc_address

    current_rate = await get_ltc_price_usd()
    ltc_amount = amount / current_rate

    embed = discord.Embed(
        title="Payment Invoice",
        description="Please send the funds as part of the deal to the Middleman address specified below. To ensure the validation of your payment, please copy and paste the amount provided.",
        color=EMBED_COLOR_GREEN
    )
    embed.add_field(name="Litecoin Address", value=f"`{ltc_address}`", inline=False)
    embed.add_field(name="USD Amount", value=f"${amount:.2f}", inline=True)
    embed.add_field(name="LTC Amount", value=f"{ltc_amount:.8f}", inline=True)
    embed.add_field(name="Exchange Rate", value=f"1 LTC ≈ ${current_rate:.2f} USD", inline=False)

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Paste", custom_id="paste"))
    view.add_item(discord.ui.Button(label="Scan QR", custom_id="qr"))

    await channel.send(embed=embed, view=view)


# Run the bot
bot.run(config["BOT_TOKEN"])
