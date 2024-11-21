import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import os
import asyncio
from datetime import datetime, timedelta
import itertools
import time
from dotenv import load_dotenv
import logging
from datetime import timezone

# Configurazione degli intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot.log'
)

# Ottieni il token direttamente dall'ambiente
TOKEN = os.getenv('DISCORD_TOKEN')

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # secondi
        
    async def setup_hook(self):
        await self.user.edit(username="RM Bot")
        # Aggiunta gestione errori
        self.loop.set_exception_handler(self.handle_error)
        
    def handle_error(self, loop, context):
        exception = context.get('exception')
        print(f"Errore catturato nel loop: {exception}")
        # Logica per gestire l'errore

@bot.event
async def on_ready():
    print(f'Bot connesso come {bot.user.name}')

@bot.event
async def on_member_join(member):
    try:
        # Stampa di debug
        print(f"Nuovo membro entrato: {member.name}")
        
        # Lista dei possibili nomi del ruolo (per gestire variazioni maiuscole/minuscole)
        possible_role_names = ["Membro", "membro", "MEMBRO"]
        
        guild = member.guild
        role = None
        
        # Cerca il ruolo tra le possibili varianti
        for role_name in possible_role_names:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                break
        
        if role:
            await member.add_roles(role)
            print(f"Ruolo {role.name} assegnato a {member.name}")
            logging.info(f"Ruolo {role.name} assegnato a {member.name}")
        else:
            print(f"Ruolo Membro non trovato. Ruoli disponibili: {[r.name for r in guild.roles]}")
            logging.error(f"Ruolo Membro non trovato. Ruoli disponibili: {[r.name for r in guild.roles]}")
            # Crea il ruolo se non esiste
            role = await guild.create_role(name="Membro", reason="Ruolo automatico per nuovi membri")
            await member.add_roles(role)
            logging.info(f"Creato e assegnato nuovo ruolo Membro a {member.name}")
            
    except Exception as e:
        print(f"Errore nell'assegnazione del ruolo: {str(e)}")
        logging.error(f"Errore nell'assegnazione del ruolo: {str(e)}")

# Prima definisci la classe Modal
class CloseTicketModal(discord.ui.Modal, title="Chiusura Ticket"):
    motivo = discord.ui.TextInput(
        label="Motivo della Chiusura",
        placeholder="Inserisci il motivo della chiusura del ticket...",
        required=True,
        max_length=1000,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Mappa dei tipi di ticket basata sul nome del canale
        ticket_types = {
            "compra": "Compra Prodotto",
            "supporto": "Supporto / Aiuto",
            "bug": "Segnalazione Bug",
            "partner": "Richiesta Partnership"
        }

        # Determina il tipo di ticket dalla categoria del canale
        category_name = interaction.channel.category.name.lower()
        if "purchase" in category_name:
            ticket_type = "Compra Prodotto"
        elif "support" in category_name:
            ticket_type = "Supporto / Aiuto"
        else:
            ticket_type = "Supporto / Aiuto"  # Default fallback
        
        # Sostituisci la gestione del fuso orario
        # Aggiungi 1 ora per il fuso orario italiano (UTC+1)
        channel_created_at = interaction.channel.created_at + timedelta(hours=1)
        current_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Calcola la durata
        duration = current_time - channel_created_at
        duration_seconds = int(duration.total_seconds())
        
        # Formatta le date in italiano
        mesi_ita = {  
            1: "gennaio", 2: "febbraio", 3: "marzo", 4: "aprile",
            5: "maggio", 6: "giugno", 7: "luglio", 8: "agosto",
            9: "settembre", 10: "ottobre", 11: "novembre", 12: "dicembre"
        }
        
        data_apertura = f"{channel_created_at.day} {mesi_ita[channel_created_at.month]} {channel_created_at.year} {channel_created_at.hour}:{channel_created_at.minute:02d}"
        data_chiusura = f"{current_time.day} {mesi_ita[current_time.month]} {current_time.year} {current_time.hour}:{current_time.minute:02d}"
        
        # Trova il canale transcripts
        transcripts_channel = discord.utils.get(interaction.guild.channels, name="transcripts")
        
        # Crea l'embed per la trascrizione
        embed = discord.Embed(
            title="RM Shop - Sistema di Assistenza",
            description="Il tuo Ticket è stato Finalizzato!",
            color=0xfb8801
        )
        
        # Aggiungi i campi all'embed
        embed.add_field(
            name="🔒 | Chiuso Da",
            value=f"{interaction.user.mention} ({interaction.user.id})",
            inline=False
        )
        embed.add_field(
            name=" | Responsabile dell'Assistenza",
            value="Ticket non Assegnato 😕",
            inline=False
        )
        embed.add_field(
            name="❓ | Motivo della Chiusura",
            value=self.motivo.value,  # Usa il motivo inserito dall'utente
            inline=False
        )
        embed.add_field(
            name="📘 | Categoria del Ticket",
            value=ticket_type,
            inline=False
        )
        embed.add_field(
            name="🆔 | ID del Ticket",
            value=interaction.channel.name,
            inline=False
        )
        
        embed.add_field(
            name="📅 | Data di Apertura",
            value=data_apertura,
            inline=False
        )
        embed.add_field(
            name="📅 | Data di Chiusura",
            value=data_chiusura,
            inline=False
        )
        
        # Formatta la durata in modo leggibile
        if duration_seconds < 60:
            durata_str = f"{duration_seconds} secondo/i"
        elif duration_seconds < 3600:
            minuti = duration_seconds // 60
            durata_str = f"{minuti} minuto/i"
        else:
            ore = duration_seconds // 3600
            minuti = (duration_seconds % 3600) // 60
            durata_str = f"{ore} ora/e e {minuti} minuto/i"
        
        embed.add_field(
            name="⏲️ | Durata dell'Assistenza",
            value=durata_str,
            inline=False
        )
        
        embed.set_footer(text=f"{interaction.user.name} - {interaction.user.id} • {current_time.strftime('%H:%M')}")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1199762230900879380/1199762275163750471/rmshopslogo.png")
        
        # Invia l'embed nel canale transcripts
        await transcripts_channel.send(embed=embed)
        
        # Elimina il canale del ticket
        await interaction.channel.delete()

# Sposta questa classe fuori dai callback, prima della classe TicketView
class TicketManageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(
        label=" Chiudi Ticket", 
        emoji="<:rmchiudi:1308904349635969134>",
        style=discord.ButtonStyle.secondary,
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CloseTicketModal())

    @discord.ui.button(
        label=" Rivendica Ticket", 
        emoji="<:rmrive:1308904323991994428>",
        style=discord.ButtonStyle.secondary,
        custom_id="claim_ticket"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verifica se l'utente ha il ruolo Management
        management_role = discord.utils.get(interaction.guild.roles, name="Management")
        if management_role not in interaction.user.roles:
            await interaction.response.send_message(
                "Solo i membri del Management possono rivendicare i ticket.",
                ephemeral=True,
                delete_after=5.0
            )
            return

        await interaction.response.send_message(
            f"Ticket preso in carico da {interaction.user.mention}",
            ephemeral=False,
            delete_after=5.0 
        )
        
        # Aggiorna l'embed originale per mostrare chi ha preso in carico il ticket
        embed = interaction.message.embeds[0]
        description_lines = embed.description.split('\n')
        
        # Cerca la linea che contiene "Ticket preso in carico da"
        for i, line in enumerate(description_lines):
            if "Ticket preso in carico da:" in line or "preso in carico da:" in line:
                # Modifica direttamente la linea corrente invece di quella successiva
                description_lines[i] = f"<:membrorm:1309200450825883708> | Ticket preso in carico da: {interaction.user.mention}"
                break
        
        # Ricostruisci la descrizione
        embed.description = '\n'.join(description_lines)
        await interaction.message.edit(embed=embed)

# Classe per creare la vista con i pulsanti
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Compra Prodotto", 
        style=discord.ButtonStyle.danger,
        custom_id="buy_product"
    )
    async def compra_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Controllo ticket esistente
            existing_ticket = discord.utils.get(interaction.guild.channels, 
                name=f"ticket-{interaction.user.name.lower()}")
            
            if existing_ticket:
                await interaction.response.send_message(
                    f"Hai già un ticket aperto: {existing_ticket.mention}", 
                    ephemeral=True,
                    delete_after=5.0
                )
                return

            # Cerca la categoria "ticket purchase"
            category = discord.utils.get(interaction.guild.categories, name="ticket purchase")
            if not category:
                # Se non esiste, creala
                category = await interaction.guild.create_category("ticket purchase")
                print(f"Categoria 'ticket purchase' creata")

            # Imposta i permessi del canale
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }

            # Crea il canale nella categoria corretta
            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name.lower()}",
                category=category,
                overwrites=overwrites
            )

            # Crea l'embed per il nuovo ticket
            embed = discord.Embed(
                title="RM Shop - Sistema di Assistenza",
                description=(
                    "## <:logorm:1308916945852170291> | Benvenuto/a nel tuo ticket\n\n"
                    "<:caterm:1309199827212435597> | Categoria del Ticket:\n"
                    "Ticket Compra Prodotto\n"
                    "\n"
                    "<:inform:1309199465328017499> | INFORMAZIONI IMPORTANTI:\n\n"
                    "<:ticketrm:1309203090028761098> | I Ticket sono completamente privati, solo i membri dello STAFF hanno accesso a questo canale.\n\n"
                    "<:tagrm:1309200275659161670> | Evita di TAGGARE, attendi che un membro dello STAFF sia disponibile per aiutarti.\n\n"
                    "<:membrorm:1309200450825883708> | Ticket preso in carico da: "
                    "\n\n"
                ),
                color=0xfb8801
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/825772229152604220/1309170964835340288/rmshooop.png?ex=67409bf9&is=673f4a79&hm=e04de21733922f555eac914f23f6355b5f9b50d48f3bc627c53df03a18b0ae39&")
            embed.set_footer(text="Questo canale è destinato al tuo SUPPORTO, sentiti libero di dire ciò di cui hai bisogno!", icon_url="https://cdn.discordapp.com/attachments/825772229152604220/1308480493406257192/rmshops.png?ex=673ec1ac&is=673d702c&hm=f884451f50feaf65967d30472ce22d4b7e0345c3dcbadac28683fbf51d9a3abf&")

            # Modifica la vista per includere tutti i pulsanti necessari
            manage_view = TicketManageView()
            await channel.send(embed=embed, view=manage_view)
            
            # Invia il messaggio di conferma che si autodistruggerà
            temp_message = await interaction.response.send_message(
                f"Ho creato il tuo ticket: <#{channel.id}>",
                delete_after=5.0  # Si eliminerà dopo 5 secondi
            )

        except Exception as e:
            print(f"Errore nella creazione del ticket: {e}")
            await interaction.response.send_message(
                "Si è verificato un errore nella creazione del ticket.", 
                ephemeral=True
            )

    @discord.ui.button(label="Supporto / Aiuto", style=discord.ButtonStyle.blurple)
    async def supporto_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Controllo ticket esistente
            existing_ticket = discord.utils.get(interaction.guild.channels, 
                name=f"ticket-{interaction.user.name.lower()}")
            
            if existing_ticket:
                await interaction.response.send_message(
                    f"Hai già un ticket aperto: {existing_ticket.mention}", 
                    ephemeral=True,
                    delete_after=5.0
                )
                return

            # Cerca la categoria "ticket support"
            category = discord.utils.get(interaction.guild.categories, name="ticket support")
            if not category:
                # Se non esiste, creala
                category = await interaction.guild.create_category("ticket support")
                print(f"Categoria 'ticket support' creata")

            # Imposta i permessi del canale
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }

            # Crea il canale nella categoria corretta
            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name.lower()}",
                category=category,
                overwrites=overwrites
            )

            # Nuovo embed con lo stesso formato
            embed = discord.Embed(
                title="RM Shop - Sistema di Assistenza",
                description=(
                    "## <:logorm:1308916945852170291> | Benvenuto/a nel tuo ticket\n\n"
                    "<:caterm:1309199827212435597> | Categoria del Ticket:\n"
                    "Ticket Supporto\n"
                    "\n"
                    "<:inform:1309199465328017499> | INFORMAZIONI IMPORTANTI:\n\n"
                    "<:ticketrm:1309203090028761098> | I Ticket sono completamente privati, solo i membri dello STAFF hanno accesso a questo canale.\n\n"
                    "<:tagrm:1309200275659161670> | Evita di TAGGARE, attendi che un membro dello STAFF sia disponibile per aiutarti.\n\n"
                    "<:membrorm:1309200450825883708> | Ticket preso in carico da: "
                    "\n\n"
                ),
                color=0xfb8801
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/825772229152604220/1309170964835340288/rmshooop.png?ex=67409bf9&is=673f4a79&hm=e04de21733922f555eac914f23f6355b5f9b50d48f3bc627c53df03a18b0ae39&")
            embed.set_footer(text="Questo canale è destinato al tuo SUPPORTO, sentiti libero di dire ciò di cui hai bisogno!", icon_url="https://cdn.discordapp.com/attachments/825772229152604220/1308480493406257192/rmshops.png?ex=673ec1ac&is=673d702c&hm=f884451f50feaf65967d30472ce22d4b7e0345c3dcbadac28683fbf51d9a3abf&")

            # Usa la stessa vista con i pulsanti di gestione
            manage_view = TicketManageView()
            await channel.send(embed=embed, view=manage_view)
            
            # Messaggio di conferma temporaneo
            await interaction.response.send_message(
                f"Ho creato il tuo ticket: <#{channel.id}>",
                ephemeral=True,
                delete_after=5.0
            )

        except Exception as e:
            print(f"Errore nella creazione del ticket: {e}")
            await interaction.response.send_message(
                "Si è verificato un errore nella creazione del ticket.", 
                ephemeral=True
            )

# Classe per creare la vista con i pulsanti di chiusura del ticket
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Chiudi Ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.channel.name.startswith("ticket-"):
                await interaction.response.send_message(
                    "Questo comando può essere usato solo nei canali ticket!", 
                    ephemeral=True
                )
                return

            await interaction.response.send_message("Il ticket verrà chiuso tra 5 secondi...")
            await asyncio.sleep(5)
            await interaction.channel.delete()

        except Exception as e:
            print(f"Errore nella chiusura del ticket: {e}")
            await interaction.response.send_message(
                "Si è verificato un errore nella chiusura del ticket.", 
                ephemeral=True
            )

    @discord.ui.button(label="📝 Reclamo Ticket", style=discord.ButtonStyle.gray)
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.channel.name.startswith("ticket-"):
                await interaction.response.send_message(
                    "Questo comando può essere usato solo nei canali ticket!", 
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"Ticket preso in carico da {interaction.user.mention}"
            )

        except Exception as e:
            print(f"Errore nel reclamo del ticket: {e}")
            await interaction.response.send_message(
                "Si è verificato un errore nel reclamo del ticket.", 
                ephemeral=True
            )

# Comando per inviare il messaggio con il pulsante
@bot.command()
async def ticket(ctx):
    embed = discord.Embed(
        title="Servizi",
        description="## `Metodi di Pagamento:`\n"
                   "\n"
                   "## <:pprm:1308896425504931940> • `PayPal`\n"
                   "## <a:cardrm:1308883074309947474> • `Carta di Credito`",
        color=0xfb8801
    )
    
    file = discord.File("images/rmshops.png", filename="rmshops.png")
    embed.set_image(url="attachment://rmshops.png")
    
    view = TicketView()
    await ctx.send(file=file, embed=embed, view=view)

async def start_server(port):
    # Crea un web server asincrono semplice
    from aiohttp import web
    
    async def handle(request):
        return web.Response(text="Bot is running")
    
    app = web.Application()
    app.router.add_get('/', handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Server web in ascolto sulla porta {port}")

def run_bot():
    import asyncio
    
    async def start_bot():
        port = int(os.getenv('PORT', 8080))
        
        # Avvia il web server
        await start_server(port)
        
        try:
            if TOKEN is None:
                print("Token non configurato!")
                return
                
            await bot.start(TOKEN)
            
        except Exception as e:
            print(f"Errore imprevisto: {e}")
            import traceback
            traceback.print_exc()
    
    # Usa asyncio.run per gestire il loop degli eventi
    while True:
        try:
            asyncio.run(start_bot())
        except Exception as e:
            print(f"Errore durante l'esecuzione del bot: {e}")
            time.sleep(5)

@tasks.loop(minutes=5)
async def check_connection():
    logging.info(f"Bot status: {bot.status}")

if __name__ == "__main__":
    run_bot()
