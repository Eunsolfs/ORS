from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("handover", "0002_alter_handoveritem_blood_transfusion_checks_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="handoversession",
            name="handover_by",
            field=models.CharField(blank=True, default="", max_length=50, verbose_name="交班人"),
        ),
        migrations.AddField(
            model_name="handoversession",
            name="takeover_by",
            field=models.CharField(blank=True, default="", max_length=50, verbose_name="接班人"),
        ),
    ]
