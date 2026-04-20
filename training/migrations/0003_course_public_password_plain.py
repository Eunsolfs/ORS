from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0002_course_visibility_and_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="public_access_password_plain",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="公开访问密码明文"),
        ),
    ]
