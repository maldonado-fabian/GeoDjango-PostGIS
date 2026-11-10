from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea (o resetea) el superusuario de desarrollo admin/admin para el login del front."

    def handle(self, *args, **options):
        User = get_user_model()
        user, _ = User.objects.get_or_create(username='admin')
        user.is_staff = True
        user.is_superuser = True
        user.set_password('admin')
        user.save()
        self.stdout.write(self.style.SUCCESS("Usuario 'admin' listo (contraseña: admin)"))
