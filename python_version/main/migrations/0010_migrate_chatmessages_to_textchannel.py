# Generated migration to handle ChatMessage channel FK change
from django.db import migrations


def set_chatmessages_channel_to_null(apps, schema_editor):
    """Set all existing ChatMessage channel fields to NULL before changing FK"""
    ChatMessage = apps.get_model('main', 'ChatMessage')
    # Set all channels to NULL since they reference VoiceChannel which won't exist in TextChannel
    ChatMessage.objects.all().update(channel=None)


def reverse_migration(apps, schema_editor):
    """Reverse migration - nothing to do"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0009_alter_textchannel_unique_together_and_more'),
        # Make sure this runs BEFORE 0008 if possible, but since 0008 is already applied locally,
        # we'll need to handle it differently on VPS
    ]

    operations = [
        migrations.RunPython(set_chatmessages_channel_to_null, reverse_migration),
    ]
