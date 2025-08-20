from django.core.management.base import BaseCommand
from apps.users.models import User
from django.http import HttpRequest
from apps.project_admin.views import generate_test_data
import json

class Command(BaseCommand):
    help = 'Generate test data for the application'

    def handle(self, *args, **options):
        try:
            # Get the first superuser
            superuser = User.objects.filter(is_superuser=True).first()
            
            if not superuser:
                self.stdout.write(
                    self.style.ERROR('No superuser found. Please create a superuser first.')
                )
                return
            
            # Create a mock request object
            request = HttpRequest()
            request.user = superuser
            request.method = 'GET'
            
            # Call the function
            response = generate_test_data(request)
            
            # Parse and display the response
            if hasattr(response, 'content'):
                content = response.content.decode('utf-8')
                try:
                    data = json.loads(content)
                    if data.get('success'):
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ {data.get('message')}")
                        )
                        self.stdout.write(f"📊 {data.get('summary')}")
                        self.stdout.write(f"📈 Created {len(data.get('projects', []))} projects")
                    else:
                        self.stdout.write(
                            self.style.ERROR(f"❌ Error: {data.get('error')}")
                        )
                except json.JSONDecodeError:
                    self.stdout.write(content)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error running test data generation: {str(e)}')
            )
