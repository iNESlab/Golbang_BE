# Generated by Django 5.0.6 on 2024-07-22 17:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_password'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='userId',
            new_name='user_id',
        ),
    ]