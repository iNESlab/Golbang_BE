# Generated by Django 4.2.14 on 2024-08-28 06:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0003_clubmember_total_handicap_rank_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="clubmember",
            name="total_handicap_rank",
        ),
        migrations.RemoveField(
            model_name="clubmember",
            name="total_points",
        ),
        migrations.RemoveField(
            model_name="clubmember",
            name="total_rank",
        ),
    ]
