import discord
import asyncio
import aiohttp
import os
import json
from dotenv import load_dotenv

# Discord to HTTP POST Forwarding Bot

# Signs in to a Discord account and sends all messages it sees in a
# specified channel to a designated HTTP POST endpoint.

load_dotenv('.env')
TOKEN = os.getenv('DISCORD_TOKEN')
POST_URL = os.getenv('MESSAGE_URL')
CHANNEL_ID = os.getenv('CHANNEL_ID')
ADMIN_ROLES = (os.getenv('ADMIN_ROLES') or "").split(',')

print("Admin roles: " + str(ADMIN_ROLES))

client = discord.Client()

session = aiohttp.ClientSession()

chat_enabled = True

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

async def handle_admin_command(message):
    global chat_enabled 

    if message.clean_content == "!chat clear":
        data = {
            "event": "clear_messages"
        }
        await session.post(POST_URL, data=json.dumps(data))
        await message.channel.send("Instructing all viewers to clear their chat history.")
        return
    
    if message.clean_content == "!chat stop":
        await message.channel.send("Stopping all live chat. Use `!chat resume` when you're ready for live chat to restart. Use `!chat clear` if you need to clear the live chat.")
        chat_enabled = False            
        return

    if message.clean_content == "!chat resume":
        await message.channel.send("Resuming live chat.")
        chat_enabled = True
        return
    
    if message.clean_content == "!chat help":
        await message.channel.send("I'm the bot that updates the live chat next to the video player. I support the following commands:\n\n- `!chat clear`: Clears the live chat history for all viewers.\n- `!chat stop`: Clears chat history and stops updating live chat. Use in case of emergency.\n- `!chat resume`: Resumes updating live chat. Use after `!chat stop`.\n\nBot commands will not show up in live chat. Only the following roles can send commands: " + ", ".join([f"`{r.name}`" for r in message.guild.roles if str(r.id) in ADMIN_ROLES]))
        return

@client.event
async def on_message(message):

    global chat_enabled

    if message.author == client.user:
        return
    
    if message.is_system():
        return

    if message.clean_content.startswith("!chat"):
        # Was it sent by someone with a role we'll respond to?
        if any(r for r in message.author.roles if str(r.id) in ADMIN_ROLES):
            # Then handle the command and return
            await handle_admin_command(message)
        return

    if chat_enabled == False:
        return

    if str(message.channel.id) != CHANNEL_ID:
        return

    if len(message.clean_content) == 0:
        return

    # This is a message! Post it to the URL.
    data = {
        "event": "message_create",
        "author": message.author.display_name,
        "message": message.clean_content,
        "id": message.id,
        "avatar": str(message.author.avatar_url_as(format='png', size=64))
    }

    await session.post(POST_URL, data=json.dumps(data))

    print(json.dumps(data, indent=2))    

@client.event
async def on_raw_message_delete(payload):
    data = {
        "event": "message_delete",
        "id": payload.message_id,
    }

    await session.post(POST_URL, data=json.dumps(data))

    print(json.dumps(data, indent=2))
    
@client.event
async def on_message_edit(before, after):

    if before.clean_content == after.clean_content:
        # message text wasn't updated, so do nothing (this happens when discord adds a URL preview to a message)
        return

    data = {
        "event": "message_update",
        "id": after.id,
        "message": after.clean_content,
    }

    await session.post(POST_URL, data=json.dumps(data))

    print(json.dumps(data, indent=2))

# Start running!
print(f'Starting up...')
client.run(TOKEN)