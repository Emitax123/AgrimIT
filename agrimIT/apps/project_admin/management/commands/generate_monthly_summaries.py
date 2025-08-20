from django.core.management.base import BaseCommand
from apps.users.models import User
from django.http import HttpRequest
from apps.project_admin.views import generate_monthly_summaries
import json

class Command(BaseCommand):
    help = 'Generate monthly financial summaries from existing accounting data'

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
            response = generate_monthly_summaries(request)
            
            # Parse and display the response
            if hasattr(response, 'content'):
                content = response.content.decode('utf-8')
                try:
                    data = json.loads(content)
                    if data.get('success'):
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ {data.get('message')}")
                        )
                        self.stdout.write(f"📊 Processed {data.get('total_projects_processed')} projects")
                        
                        # Show summary details
                        summaries = data.get('summaries', [])
                        for summary in summaries:
                            status = "Created" if summary['created'] else "Updated"
                            self.stdout.write(
                                f"📈 {status} summary for {summary['month']:02d}/{summary['year']}: "
                                f"${summary['total_advance']:,.2f} advance - "
                                f"${summary['total_expenses']:,.2f} expenses = "
                                f"${summary['net_worth']:,.2f} net worth"
                            )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f"❌ Error: {data.get('error')}")
                        )
                except json.JSONDecodeError:
                    self.stdout.write(content)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error running monthly summaries generation: {str(e)}')
            )
