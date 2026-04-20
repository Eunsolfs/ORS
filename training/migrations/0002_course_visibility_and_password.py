from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("training", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="public_access_password_hash",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="公开访问密码哈希"),
        ),
        migrations.AddField(
            model_name="course",
            name="visibility",
            field=models.CharField(
                choices=[("department", "同科室可见（需登录）"), ("public", "所有人可见（可选访问密码）")],
                default="department",
                max_length=20,
                verbose_name="访问权限",
            ),
        ),
        migrations.AlterField(
            model_name="course",
            name="status",
            field=models.CharField(
                choices=[("draft", "草稿"), ("published", "发布"), ("inactive", "失效")],
                default="published",
                max_length=20,
                verbose_name="状态",
            ),
        ),
    ]
