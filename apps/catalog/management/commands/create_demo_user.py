from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Creates a default warehouse admin operator user (admin / admin123)."

    def handle(self, *args, **options):
        username = "admin"
        password = "admin123password"
        email = "admin@warehouse.local"

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully with password: {password}"))
        else:
            self.stdout.write(f"User '{username}' already exists.")

