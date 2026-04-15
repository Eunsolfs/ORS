from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from orgs.models import Department, DepartmentMember


class Command(BaseCommand):
    help = "Bootstrap ORS: create root user, a department, and a department admin."

    def add_arguments(self, parser):
        parser.add_argument("--root-username", default="root")
        parser.add_argument("--root-password", default="root123456")
        parser.add_argument("--dept-name", default="手术室")
        parser.add_argument("--dept-code", default="ors")
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--admin-password", default="admin123456")
        parser.add_argument("--admin-name", default="科室管理员")

    def handle(self, *args, **opts):
        User = get_user_model()

        root, created = User.objects.get_or_create(username=opts["root_username"], defaults={"is_superuser": True, "is_staff": True})
        if created:
            root.set_password(opts["root_password"])
            root.name = "root"
            root.save()
            self.stdout.write(self.style.SUCCESS(f"Created root: {root.username} / {opts['root_password']}"))
        else:
            self.stdout.write(f"Root exists: {root.username}")

        dept, dept_created = Department.objects.get_or_create(
            code=opts["dept_code"],
            defaults={"name": opts["dept_name"], "is_active": True, "created_by": root},
        )
        if dept_created:
            self.stdout.write(self.style.SUCCESS(f"Created department: {dept.name} ({dept.code})"))
        else:
            self.stdout.write(f"Department exists: {dept.name} ({dept.code})")

        admin_user, admin_created = User.objects.get_or_create(username=opts["admin_username"], defaults={"is_staff": True})
        if admin_created:
            admin_user.set_password(opts["admin_password"])
            admin_user.name = opts["admin_name"]
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created dept admin user: {admin_user.username} / {opts['admin_password']}"))
        else:
            self.stdout.write(f"Dept admin user exists: {admin_user.username}")

        DepartmentMember.objects.update_or_create(
            department=dept,
            user=admin_user,
            defaults={"role_in_department": DepartmentMember.Role.ADMIN, "is_active": True, "created_by": root},
        )
        self.stdout.write(self.style.SUCCESS("Linked dept admin membership."))

