# Hand-written migration: add `user` to MonthlyFinancialSummary uniqueness
# and swap the (year, month) index for (user, year, month).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0004_accountmovement_accounting__user_id_afcb86_idx_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='monthlyfinancialsummary',
            unique_together={('user', 'year', 'month')},
        ),
        migrations.RemoveIndex(
            model_name='monthlyfinancialsummary',
            name='accounting__year_50c5ea_idx',
        ),
        migrations.AddIndex(
            model_name='monthlyfinancialsummary',
            index=models.Index(fields=['user', 'year', 'month'], name='acc_summary_user_ym_idx'),
        ),
    ]
