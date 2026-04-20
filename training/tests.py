from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from orgs.models import Department, DepartmentMember

from .models import Course


class CourseAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client = Client()
        self.member_user = User.objects.create_user(username="member1", password="pass123456")
        self.admin_user = User.objects.create_user(username="admin1", password="pass123456")
        self.other_user = User.objects.create_user(username="other1", password="pass123456")
        self.department = Department.objects.create(name="手术室", code="ors", is_active=True)
        DepartmentMember.objects.create(
            department=self.department,
            user=self.member_user,
            role_in_department=DepartmentMember.Role.MEMBER,
            is_active=True,
        )
        DepartmentMember.objects.create(
            department=self.department,
            user=self.admin_user,
            role_in_department=DepartmentMember.Role.ADMIN,
            is_active=True,
        )

    def _make_course(self, **kwargs) -> Course:
        data = {
            "department": self.department,
            "title": "课程A",
            "content_html": "<p>课程正文</p>",
            "status": Course.Status.PUBLISHED,
            "visibility": Course.Visibility.DEPARTMENT,
        }
        data.update(kwargs)
        return Course.objects.create(**data)

    def test_department_course_requires_login_membership(self):
        course = self._make_course(visibility=Course.Visibility.DEPARTMENT)
        url = reverse("course_detail", kwargs={"dept_code": self.department.code, "course_id": course.id})

        anon_resp = self.client.get(url)
        self.assertEqual(anon_resp.status_code, 302)

        self.client.login(username="other1", password="pass123456")
        non_member_resp = self.client.get(url)
        self.assertEqual(non_member_resp.status_code, 403)

        self.client.logout()
        self.client.login(username="member1", password="pass123456")
        member_resp = self.client.get(url)
        self.assertEqual(member_resp.status_code, 200)
        self.assertContains(member_resp, "课程正文")

    def test_public_course_without_password_can_be_visited_anonymously(self):
        course = self._make_course(visibility=Course.Visibility.PUBLIC)
        url = reverse("course_public_detail", kwargs={"dept_code": self.department.code, "course_id": course.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "课程正文")

    def test_public_course_with_password_needs_verification(self):
        course = self._make_course(visibility=Course.Visibility.PUBLIC)
        course.set_public_access_password("abc123")
        course.save(update_fields=["public_access_password_hash"])
        url = reverse("course_public_detail", kwargs={"dept_code": self.department.code, "course_id": course.id})

        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, 200)
        self.assertContains(get_resp, "访问密码")

        wrong_resp = self.client.post(url, {"access_password": "wrong"})
        self.assertEqual(wrong_resp.status_code, 200)
        self.assertContains(wrong_resp, "访问密码错误")

        ok_resp = self.client.post(url, {"access_password": "abc123"})
        self.assertEqual(ok_resp.status_code, 302)

        final_resp = self.client.get(url)
        self.assertEqual(final_resp.status_code, 200)
        self.assertContains(final_resp, "课程正文")

    def test_course_edit_requires_department_admin_or_higher(self):
        course = self._make_course()
        edit_url = reverse("course_edit", kwargs={"dept_code": self.department.code, "course_id": course.id})

        self.client.login(username="member1", password="pass123456")
        member_resp = self.client.get(edit_url)
        self.assertEqual(member_resp.status_code, 403)
        self.client.logout()

        self.client.login(username="admin1", password="pass123456")
        admin_resp = self.client.get(edit_url)
        self.assertEqual(admin_resp.status_code, 200)
