# Generated by Django 3.2.16 on 2023-09-29 20:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_user_username'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'ordering': [-1], 'verbose_name': 'пользователь', 'verbose_name_plural': 'пользователи'},
        ),
        migrations.AlterModelManagers(
            name='user',
            managers=[
            ],
        ),
    ]
