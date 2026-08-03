from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from community.models import CommunityPost, Notification

class CommunityModelTest(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(
            username="sender",
            email="sender@test.com",
            full_name="Sender User",
            password="password123"
        )
        self.recipient = User.objects.create_user(
            username="recipient",
            email="recipient@test.com",
            full_name="Recipient User",
            password="password123"
        )

    def test_community_post_creation(self):
        post = CommunityPost.objects.create(
            author=self.sender,
            content="Hello Community!"
        )
        self.assertEqual(post.content, "Hello Community!")
        self.assertEqual(post.author, self.sender)

    def test_notification_auto_cleanup(self):
        # Recent notification (2 days old)
        recent_notif = Notification.objects.create(
            user=self.recipient,
            sender=self.sender,
            message="Test recent notification",
            url="/community/chat/"
        )
        recent_notif.created_at = timezone.now() - timedelta(days=2)
        recent_notif.save()

        # Old notification (8 days old)
        old_notif = Notification.objects.create(
            user=self.recipient,
            sender=self.sender,
            message="Test old notification",
            url="/community/chat/"
        )
        Notification.objects.filter(id=old_notif.id).update(created_at=timezone.now() - timedelta(days=8))

        # Cleanup query (older than 7 days)
        cutoff = timezone.now() - timedelta(days=7)
        deleted_count, _ = Notification.objects.filter(created_at__lt=cutoff).delete()

        self.assertEqual(deleted_count, 1)
        self.assertTrue(Notification.objects.filter(id=recent_notif.id).exists())
        self.assertFalse(Notification.objects.filter(id=old_notif.id).exists())
