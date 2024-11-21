import discord
from discord.ext import commands
from discord.ui import View, Button
import os
import asyncio
import datetime
import pytz
from discord.ext import tasks
import itertools
import time
from dotenv import load_dotenv
import logging

# Aggiungi all'inizio del file
load_dotenv()

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
    role_name = "Membro"
    guild = member.guild  # Prendi il server (guild) dove l'utente si è unito
    role = discord.utils.get(guild.roles, name=role_name)
    
    if role:
        await member.add_roles(role)  # Assegna il ruolo al nuovo membro
        print(f"Ruolo Membro assegnato a {member.name}")

    else:
        print(f"Ruolo Membro non trovato!")

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
            "compra": "Acquisto Prodotto",
            "supporto": "Supporto Generale",
            "bug": "Segnalazione Bug",
            "partner": "Richiesta Partnership"
            # Aggiungi altri tipi secondo necessità
        }

        # Determina il tipo di ticket dal nome del canale
        channel_name = interaction.channel.name.lower()
        ticket_type = next(
            (tipo for chiave, tipo in ticket_types.items() if chiave in channel_name),
            "Supporto Generale"  # Valore predefinito se nessuna corrispondenza trovata
        )
        
        # Imposta il fuso orario italiano
        timezone_IT = pytz.timezone('Europe/Rome')
        
        # Converti i tempi nel fuso orario italiano
        channel_created_at = interaction.channel.created_at.astimezone(timezone_IT)
        current_time = datetime.datetime.now(timezone_IT)
        
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
            value=ticket_type,  # Usa il tipo di ticket corretto
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
        button.style = discord.ButtonStyle.primary
        button.color = discord.Color.from_rgb(251, 136, 1)  # RGB per #fb8801
        try:
            # Controlla se l'utente ha già un ticket aperto
            existing_ticket = discord.utils.get(interaction.guild.channels, 
                name=f"ticket-{interaction.user.name.lower()}")
            
            if existing_ticket:
                await interaction.response.send_message(
                    f"Hai già un ticket aperto: {existing_ticket.mention}", 
                    ephemeral=True
                )
                return

            # Cerca la categoria "ticket aperti"
            category = discord.utils.get(interaction.guild.categories, name="ticket aperti")
            if not category:
                # Se non esiste, creala
                category = await interaction.guild.create_category("ticket aperti")
                print(f"Categoria 'ticket aperti' creata")

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
                    "<a:rmalert:1308900242409918618> | Benvenuto/a nel tuo ticket\n\n"
                    "<:rmfolder:1308900703602999377> | Categoria del Ticket:\n"
                    "\n"
                    "<a:rmalert:1308900242409918618> | INFORMAZIONI IMPORTANTI:\n\n"
                    " | TICKET sono completamente privati, solo i membri dello STAFF hanno accesso a questo canale.\n\n"
                    "<a:rmalert:1308900242409918618> | Evita di fare TAG, attendi che un membro dello STAFF sia disponibile per aiutarti.\n\n"
                    "👥 | Ticket preso in carico da: "
                    "\n\n"
                    "✅ | Questo canale è destinato al tuo SUPPORTO, sentiti libero di dire ciò di cui hai bisogno!\n\n"
                ),
                color=0xfb8801
            )
            embed.set_footer(text="Grazie per aver scelto i nostri servizi", icon_url="https://cdn.discordapp.com/attachments/825772229152604220/1308480493406257192/rmshops.png?ex=673ec1ac&is=673d702c&hm=f884451f50feaf65967d30472ce22d4b7e0345c3dcbadac28683fbf51d9a3abf&")

            # Modifica la vista per includere tutti i pulsanti necessari
            class TicketManageView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)
                    
                # Aggiungi i pulsanti
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
                    await interaction.response.send_message(
                        f"Ticket preso in carico da {interaction.user.mention}",
                        ephemeral=False,
                        delete_after=5.0 
                    )
                    
                    # Aggiorna l'embed originale per mostrare chi ha preso in carico il ticket
                    embed = interaction.message.embeds[0]
                    description_lines = embed.description.split('\n')
                    for i, line in enumerate(description_lines):
                        if "Ticket preso in carico da:" in line:
                            description_lines[i+1] = f"{interaction.user.mention}"
                    
                    embed.description = '\n'.join(description_lines)
                    await interaction.message.edit(embed=embed)

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
            # Simile al codice sopra ma per ticket di supporto
            existing_ticket = discord.utils.get(interaction.guild.channels, 
                name=f"ticket-{interaction.user.name.lower()}")
            
            if existing_ticket:
                await interaction.response.send_message(
                    f"Hai già un ticket aperto: {existing_ticket.mention}", 
                    ephemeral=True
                )
                return

            category = discord.utils.get(interaction.guild.categories, name="Ticket")
            if not category:
                category = await interaction.guild.create_category("Ticket")

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }

            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name.lower()}",
                category=category,
                overwrites=overwrites
            )

            embed = discord.Embed(
                title="Nuovo Ticket Supporto",
                description=f"Ticket creato da {interaction.user.mention}\n"
                           f"Un membro del nostro staff ti risponderà il prima possibile.",
                color=discord.Color.green()
            )

            close_view = TicketCloseView()
            await channel.send(embed=embed, view=close_view)
            
            await interaction.response.send_message(
                f"Ho creato il tuo ticket: {channel.mention}", 
                ephemeral=True
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

# Modifica la parte finale del file
def run_bot():
    while True:
        try:
            token = os.getenv('DISCORD_TOKEN')
            if token is None:
                print("Token non trovato nel file .env!")
                break
            bot.run(token, reconnect=True)
        except discord.ConnectionClosed:
            print("Connessione persa. Tentativo di riconnessione...")
            time.sleep(5)
        except discord.LoginFailure:
            print("Token non valido. Verifica il token del bot.")
            break
        except Exception as e:
            print(f"Errore imprevisto: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)

@tasks.loop(minutes=5)
async def check_connection():
    logging.info(f"Bot status: {bot.status}")

if __name__ == "__main__":
    run_bot()