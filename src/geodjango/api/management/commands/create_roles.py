from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Creates viewer and editor groups for role-based access control'

    def handle(self, *args, **options):
        for name in ('viewer', 'editor'):
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group: {name}'))
            else:
                self.stdout.write(f'Group already exists: {name}')
