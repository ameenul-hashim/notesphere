from django.test import TestCase
from accounts.models import User, Avatar

class UserModelTest(TestCase):
    def setUp(self):
        self.avatar = Avatar.objects.create(
            name="Test Avatar",
            gender="male",
            is_active=True,
            display_order=1
        )
        self.admin = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            full_name="Admin Test User",
            password="testpassword123",
            role=User.Role.ADMIN,
            avatar=self.avatar
        )
        self.student = User.objects.create_user(
            username="student_test",
            email="student@test.com",
            full_name="Student Test User",
            password="testpassword123",
            role=User.Role.STUDENT,
            avatar=self.avatar
        )

    def test_user_roles(self):
        self.assertTrue(self.admin.is_admin)
        self.assertFalse(self.admin.is_student)
        self.assertTrue(self.student.is_student)
        self.assertFalse(self.student.is_admin)

    def test_user_string_representation(self):
        self.assertEqual(str(self.admin), "Admin Test User (admin_test)")
        self.assertEqual(str(self.student), "Student Test User (student_test)")
