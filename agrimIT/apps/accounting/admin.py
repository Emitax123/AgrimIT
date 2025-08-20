from django.contrib import admin

# Register your models here.
from .models import * # Import all models from the current app

# Register each model

admin.site.register(Account)
admin.site.register(MonthlyFinancialSummary)
