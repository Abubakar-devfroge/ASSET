from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates test users for development'

    def handle(self, *args, **kwargs):
        # Create admin user
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                'admin', 'admin@example.com', 'admin',
                first_name='Admin', last_name='User'
            )
            self.stdout.write(self.style.SUCCESS('Created admin user'))

        # Create regular users
        test_users = [
            ('user1', 'John', 'Doe'),
            ('user2', 'Jane', 'Smith'),
            ('user3', 'Bob', 'Johnson'),
        ]

        for username, first_name, last_name in test_users:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    password=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=f'{username}@example.com'
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {first_name} {last_name}')
                ) 