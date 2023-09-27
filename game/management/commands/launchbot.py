from django.core.management.base import BaseCommand
from underkingbot.settings import DISCORD_TOKEN
import interactions


class Command(BaseCommand):
    help = 'Launch the Discord bot'

    def handle(self, *args, **options):
        client = interactions.Client(
            token=DISCORD_TOKEN,
            intents=interactions.Intents.DEFAULT,
            debug_scope=462152304167223316)
        client.load_extension('bot')
        client.start()
