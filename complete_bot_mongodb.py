import discord
from discord.ext import commands
from discord.ui import Button, View
import os
from datetime import datetime
import asyncio
from flask import Flask
from threading import Thread
import pymongo
from pymongo import MongoClient

# Flask app for keeping bot alive on Render
app = Flask('')

@app.route('/')
def home():
    return "<h1 style='text-align:center; margin-top:50px; font-family:Arial;'>Bot is Active</h1>"

def run():
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot Configuration
PREFIX = '.'
TICKET_CATEGORY = 'Tickets'
LOG_CHANNEL = 'ticket-logs'

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# MongoDB Connection
MONGO_URL = os.getenv('MONGO_URL')
if MONGO_URL:
    try:
        client = MongoClient(MONGO_URL)
        db = client['discord_bot']
        ticket_roles_db = db['ticket_roles']
        print('✅ Connected to MongoDB')
    except Exception as e:
        print(f'❌ MongoDB connection failed: {e}')
        ticket_roles_db = None
else:
    print('⚠️ No MongoDB URL found, data will not persist!')
    ticket_roles_db = None

# Storage
active_tickets = {}
claimed_tickets = {}
ticket_roles = {}

# Color Scheme
COLORS = {
    'partnership': 0x5865F2,
    'middleman': 0xFEE75C,
    'support': 0x57F287,
    'error': 0xED4245,
    'success': 0x57F287,
    'info': 0x5865F2
}

# Ticket Types
TICKET_TYPES = {
    'partnership': {
        'name': 'Partnership',
        'emoji': '🤝',
        'color': COLORS['partnership'],
        'description': 'Discuss partnership opportunities'
    },
    'middleman': {
        'name': 'Middleman',
        'emoji': '⚖️',
        'color': COLORS['middleman'],
        'description': 'Request middleman services'
    },
    'support': {
        'name': 'Support',
        'emoji': '🎫',
        'color': COLORS['support'],
        'description': 'Get help and support'
    }
}

# Button Views
class TicketButtons(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Partnership', emoji='🤝', style=discord.ButtonStyle.primary, custom_id='ticket_partnership')
    async def partnership_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await create_ticket(interaction.guild, interaction.user, 'partnership')
            await interaction.followup.send('✅ Ticket created! Check the ticket channel.', ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send('❌ I don\'t have permission to create channels!', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'❌ Error: {str(e)}', ephemeral=True)

    @discord.ui.button(label='Middleman', emoji='⚖️', style=discord.ButtonStyle.secondary, custom_id='ticket_middleman')
    async def middleman_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await create_ticket(interaction.guild, interaction.user, 'middleman')
            await interaction.followup.send('✅ Ticket created! Check the ticket channel.', ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send('❌ I don\'t have permission to create channels!', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'❌ Error: {str(e)}', ephemeral=True)

    @discord.ui.button(label='Support', emoji='🎫', style=discord.ButtonStyle.success, custom_id='ticket_support')
    async def support_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        try:
            await create_ticket(interaction.guild, interaction.user, 'support')
            await interaction.followup.send('✅ Ticket created! Check the ticket channel.', ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send('❌ I don\'t have permission to create channels!', ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f'❌ Error: {str(e)}', ephemeral=True)

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Close Ticket', emoji='🔒', style=discord.ButtonStyle.danger, custom_id='confirm_close')
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await close_ticket(interaction.channel, interaction.user)

# Events
@bot.event
async def on_ready():
    print(f'✅ Bot is online as {bot.user}')
    print(f'📊 Serving {len(bot.guilds)} servers')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='.help | Ticket System'))

    # Add persistent views
    bot.add_view(TicketButtons())
    bot.add_view(CloseTicketView())
    
    # Load data from MongoDB
    if ticket_roles_db:
        try:
            for doc in ticket_roles_db.find():
                guild_id = doc['guild_id']
                ticket_type = doc['type']
                role_id = doc['role_id']
                
                if guild_id not in ticket_roles:
                    ticket_roles[guild_id] = {}
                ticket_roles[guild_id][ticket_type] = role_id
            print('✅ Loaded ticket roles from database')
        except Exception as e:
            print(f'❌ Error loading data: {e}')

# Help Command
@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(
        title='🎫 Ticket System - Help',
        description='Professional ticket management system for your server',
        color=COLORS['info']
    )
    embed.add_field(
        name='📋 Ticket Commands',
        value='```\n.new <type> - Create a new ticket\n.close - Close current ticket\n.claim - Claim a ticket\n.unclaim - Unclaim a ticket\n.add <user> - Add user to ticket\n.remove <user> - Remove user from ticket\n.rename <name> - Rename ticket channel```',
        inline=False
    )
    embed.add_field(
        name='🏷️ Ticket Types',
        value='```\npartnership - Partnership inquiries\nmiddleman - Middleman services\nsupport - General support```',
        inline=False
    )
    embed.add_field(
        name='⚙️ Setup Commands',
        value='```\n.setup - Create ticket panel\n.stats - View ticket statistics\n.ticketrole <type> <role> - Set role pings\n.ticketroles - View role settings```',
        inline=False
    )
    embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
    embed.timestamp = datetime.utcnow()

    await ctx.reply(embed=embed)

# Setup Command
@bot.command(name='setup')
@commands.has_permissions(administrator=True)
async def setup(ctx):
    embed = discord.Embed(
        title='🎫 Create a Ticket',
        description='Click the button below to create a ticket based on your needs.\n\n**Available Ticket Types:**',
        color=COLORS['info']
    )
    embed.add_field(name='🤝 Partnership', value='For partnership opportunities and collaborations', inline=True)
    embed.add_field(name='⚖️ Middleman', value='For secure middleman services', inline=True)
    embed.add_field(name='🎫 Support', value='For general help and support', inline=True)
    embed.set_footer(text='Select a ticket type to get started')
    embed.timestamp = datetime.utcnow()

    await ctx.send(embed=embed, view=TicketButtons())
    await ctx.reply('✅ Ticket panel created successfully!')

# New Ticket Command
@bot.command(name='new')
async def new_ticket(ctx, ticket_type: str = None):
    if not ticket_type or ticket_type.lower() not in TICKET_TYPES:
        await ctx.reply('❌ Invalid ticket type! Use: `partnership`, `middleman`, or `support`')
        return

    try:
        await create_ticket(ctx.guild, ctx.author, ticket_type.lower())
        await ctx.reply('✅ Ticket created! Check the ticket channel.')
    except discord.Forbidden:
        await ctx.reply('❌ I don\'t have permission to create channels! Give me **Manage Channels** permission.')
    except Exception as e:
        await ctx.reply(f'❌ Error creating ticket: {str(e)}')
        print(f'Ticket creation error: {e}')

# Close Command
@bot.command(name='close')
async def close_command(ctx):
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.reply('❌ This command can only be used in ticket channels!')
        return

    embed = discord.Embed(
        title='⚠️ Close Ticket',
        description='Are you sure you want to close this ticket?',
        color=COLORS['error']
    )
    embed.set_footer(text='This action cannot be undone')

    view = CloseTicketView()
    cancel_button = Button(label='Cancel', style=discord.ButtonStyle.secondary)

    async def cancel_callback(interaction):
        await interaction.response.edit_message(content='❌ Ticket closure cancelled.', embed=None, view=None)

    cancel_button.callback = cancel_callback
    view.add_item(cancel_button)

    await ctx.reply(embed=embed, view=view)

# Claim Command
@bot.command(name='claim')
async def claim(ctx):
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.reply('❌ This command can only be used in ticket channels!')
        return

    if ctx.channel.id in claimed_tickets:
        await ctx.reply('❌ This ticket is already claimed!')
        return

    claimed_tickets[ctx.channel.id] = ctx.author.id

    embed = discord.Embed(
        description=f'✅ Ticket claimed by {ctx.author.mention}',
        color=COLORS['success']
    )
    embed.timestamp = datetime.utcnow()

    await ctx.send(embed=embed)
    await ctx.channel.edit(name=f"{ctx.channel.name}-claimed")

# Unclaim Command
@bot.command(name='unclaim')
async def unclaim(ctx):
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.reply('❌ This command can only be used in ticket channels!')
        return

    if ctx.channel.id not in claimed_tickets:
        await ctx.reply('❌ This ticket is not claimed!')
        return

    claimer = claimed_tickets[ctx.channel.id]
    if claimer != ctx.author.id and not ctx.author.guild_permissions.administrator:
        await ctx.reply('❌ Only the claimer or an administrator can unclaim this ticket!')
        return

    del claimed_tickets[ctx.channel.id]

    embed = discord.Embed(
        description=f'✅ Ticket unclaimed by {ctx.author.mention}',
        color=COLORS['info']
    )
    embed.timestamp = datetime.utcnow()

    await ctx.send(embed=embed)
    new_name = ctx.channel.name.replace('-claimed', '')
    await ctx.channel.edit(name=new_name)

# Add User Command
@bot.command(name='add')
async def add_user(ctx, member: discord.Member = None):
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.reply('❌ This command can only be used in ticket channels!')
        return

    if not member:
        await ctx.reply('❌ Please mention a valid user!')
        return

    await ctx.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)

    embed = discord.Embed(
        description=f'✅ {member.mention} has been added to the ticket',
        color=COLORS['success']
    )
    embed.timestamp = datetime.utcnow()

    await ctx.reply(embed=embed)

# Remove User Command
@bot.command(name='remove')
async def remove_user(ctx, member: discord.Member = None):
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.reply('❌ This command can only be used in ticket channels!')
        return

    if not member:
        await ctx.reply('❌ Please mention a valid user!')
        return

    await ctx.channel.set_permissions(member, overwrite=None)

    embed = discord.Embed(
        description=f'✅ {member.mention} has been removed from the ticket',
        color=COLORS['success']
    )
    embed.timestamp = datetime.utcnow()

    await ctx.reply(embed=embed)

# Rename Command
@bot.command(name='rename')
async def rename(ctx, *, new_name: str = None):
    if not ctx.channel.name.startswith('ticket-'):
        await ctx.reply('❌ This command can only be used in ticket channels!')
        return

    if not new_name:
        await ctx.reply('❌ Please provide a new name for the ticket!')
        return

    new_name = new_name.lower().replace(' ', '-')
    await ctx.channel.edit(name=f'ticket-{new_name}')

    embed = discord.Embed(
        description=f'✅ Ticket renamed to **ticket-{new_name}**',
        color=COLORS['success']
    )
    embed.timestamp = datetime.utcnow()

    await ctx.reply(embed=embed)

# Stats Command
@bot.command(name='stats')
async def stats(ctx):
    tickets = [c for c in ctx.guild.channels if c.name.startswith('ticket-')]
    claimed = [c for c in tickets if c.id in claimed_tickets]

    embed = discord.Embed(
        title='📊 Ticket Statistics',
        color=COLORS['info']
    )
    embed.add_field(name='🎫 Active Tickets', value=f'`{len(tickets)}`', inline=True)
    embed.add_field(name='✅ Claimed Tickets', value=f'`{len(claimed)}`', inline=True)
    embed.add_field(name='⏳ Unclaimed Tickets', value=f'`{len(tickets) - len(claimed)}`', inline=True)
    embed.set_footer(text=f'Requested by {ctx.author}', icon_url=ctx.author.display_avatar.url)
    embed.timestamp = datetime.utcnow()

    await ctx.reply(embed=embed)

# Ticket role setup command
@bot.command(name='ticketrole')
@commands.has_permissions(administrator=True)
async def ticket_role(ctx, ticket_type: str, role: discord.Role):
    """Set which role gets pinged for each ticket type"""
    ticket_type = ticket_type.lower()
    
    if ticket_type not in ['partnership', 'middleman', 'support']:
        embed = discord.Embed(
            title='❌ Invalid Ticket Type',
            description='Valid types: `partnership`, `middleman`, `support`',
            color=COLORS['error']
        )
        return await ctx.send(embed=embed)
    
    guild_id = str(ctx.guild.id)
    
    # Save to MongoDB
    if ticket_roles_db:
        try:
            ticket_roles_db.update_one(
                {'guild_id': guild_id, 'type': ticket_type},
                {'$set': {'guild_id': guild_id, 'type': ticket_type, 'role_id': role.id}},
                upsert=True
            )
            print(f'✅ Saved {ticket_type} role to MongoDB')
        except Exception as e:
            print(f'❌ Error saving to MongoDB: {e}')
    
    # Save to memory
    if guild_id not in ticket_roles:
        ticket_roles[guild_id] = {}
    ticket_roles[guild_id][ticket_type] = role.id
    
    embed = discord.Embed(
        title='✅ Ticket Role Set',
        description=f'**{ticket_type.title()}** tickets will now ping {role.mention}',
        color=COLORS['success']
    )
    await ctx.send(embed=embed)

# View ticket role settings
@bot.command(name='ticketroles')
@commands.has_permissions(administrator=True)
async def ticket_roles_list(ctx):
    """View current ticket role settings"""
    guild_id = str(ctx.guild.id)
    
    embed = discord.Embed(
        title='🎫 Ticket Role Settings',
        color=COLORS['info']
    )
    
    if guild_id not in ticket_roles or not ticket_roles[guild_id]:
        embed.description = 'No ticket roles configured yet.\n\nUse `.ticketrole <type> <role>` to set them.'
    else:
        for ticket_type, role_id in ticket_roles[guild_id].items():
            role = ctx.guild.get_role(role_id)
            if role:
                embed.add_field(
                    name=f'{ticket_type.title()} Tickets',
                    value=f'Pings: {role.mention}',
                    inline=False
                )
    
    await ctx.send(embed=embed)

# Helper function to create tickets
async def create_ticket(guild, user, ticket_type):
    try:
        print(f'[DEBUG] Starting ticket creation for {user.name}')
        ticket_info = TICKET_TYPES[ticket_type]
        
        # Find or create category
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if not category:
            print(f'[DEBUG] Creating category: {TICKET_CATEGORY}')
            category = await guild.create_category(TICKET_CATEGORY)
            print(f'[DEBUG] Category created: {category.id}')
        else:
            print(f'[DEBUG] Found existing category: {category.id}')
        
        # Create ticket channel with permissions that allow pinging everyone/roles
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, 
                send_messages=True, 
                read_message_history=True,
                mention_everyone=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            )
        }
        
        print(f'[DEBUG] Creating ticket channel...')
        ticket_channel = await guild.create_text_channel(
            name=f'ticket-{user.name}-{ticket_type}',
            category=category,
            overwrites=overwrites
        )
        print(f'[DEBUG] Ticket channel created: {ticket_channel.id}')
        
        active_tickets[ticket_channel.id] = {
            'user_id': user.id,
            'type': ticket_type,
            'created_at': datetime.utcnow()
        }
        
        # Get the role to ping based on ticket type
        guild_id = str(guild.id)
        role_to_ping = None
        
        if guild_id in ticket_roles and ticket_type in ticket_roles[guild_id]:
            role_id = ticket_roles[guild_id][ticket_type]
            role_to_ping = guild.get_role(role_id)
        
        # Send initial message with role ping
        if role_to_ping:
            ping_message = f"{role_to_ping.mention} - New {ticket_info['name']} ticket opened!"
            await ticket_channel.send(ping_message, allowed_mentions=discord.AllowedMentions(roles=True))
        
        embed = discord.Embed(
            title=f"{ticket_info['emoji']} {ticket_info['name']} Ticket",
            description=f"Welcome {user.mention}!\n\n**Ticket Type:** {ticket_info['description']}\n\nOur team will be with you shortly. Please describe your inquiry in detail.",
            color=ticket_info['color']
        )
        embed.add_field(
            name='📌 Commands',
            value='`.close` - Close this ticket\n`.claim` - Claim this ticket\n`.add <user>` - Add a user\n`.remove <user>` - Remove a user',
            inline=False
        )
        embed.set_footer(text=f'Ticket created by {user}', icon_url=user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await ticket_channel.send(content=user.mention, embed=embed, view=CloseTicketView())
        print(f'[DEBUG] Ticket creation completed successfully!')
        
    except discord.Forbidden as e:
        print(f'[ERROR] Permission denied: {e}')
        raise
    except Exception as e:
        print(f'[ERROR] Ticket creation failed: {e}')
        raise

async def close_ticket(channel, user):
    ticket_data = active_tickets.get(channel.id)

    embed = discord.Embed(
        title='🔒 Ticket Closed',
        description=f'Ticket closed by {user.mention}',
        color=COLORS['error']
    )
    embed.timestamp = datetime.utcnow()

    await channel.send(embed=embed)

    # Log to ticket-logs if exists
    log_channel = discord.utils.get(channel.guild.channels, name=LOG_CHANNEL)
    if log_channel:
        log_embed = discord.Embed(
            title='🎫 Ticket Closed',
            color=COLORS['error']
        )
        log_embed.add_field(name='Channel', value=channel.name, inline=True)
        log_embed.add_field(name='Closed By', value=user.name, inline=True)
        log_embed.add_field(name='Type', value=ticket_data.get('type', 'Unknown') if ticket_data else 'Unknown', inline=True)
        log_embed.timestamp = datetime.utcnow()

        await log_channel.send(embed=log_embed)

    if channel.id in active_tickets:
        del active_tickets[channel.id]
    if channel.id in claimed_tickets:
        del claimed_tickets[channel.id]

    await asyncio.sleep(5)
    await channel.delete()

# Error Handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.reply('❌ You do not have permission to use this command!')
        except:
            pass
    elif isinstance(error, commands.MemberNotFound):
        try:
            await ctx.reply('❌ User not found!')
        except:
            pass
    elif isinstance(error, commands.CommandInvokeError):
        if 'Forbidden' in str(error):
            print(f'Permission Error: Bot lacks permissions in {ctx.guild.name} - {ctx.channel.name}')
            try:
                await ctx.author.send(f'❌ I don\'t have permission to send messages in #{ctx.channel.name}. Please give me "Send Messages" and "Embed Links" permissions!')
            except:
                pass
        else:
            print(f'Error: {error}')
    else:
        print(f'Error: {error}')

# Run Bot
if __name__ == '__main__':
    keep_alive()
    TOKEN = os.getenv('TOKEN')
    if not TOKEN:
        print('❌ ERROR: No TOKEN found in environment variables!')
        print('Please set your Discord bot token as TOKEN environment variable')
    else:
        print('🚀 Starting Discord Ticket Bot...')
        bot.run(TOKEN)