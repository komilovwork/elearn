import asyncio
import os
import django
from django.core.management.base import BaseCommand


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.telegram.bot import start_bot


class Command(BaseCommand):
    help = 'Run Telegram bot'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Telegram bot...')
        )
        try:
            asyncio.run(start_bot())
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Bot stopped by user')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running bot: {e}')
            )
