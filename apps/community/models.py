from django.conf import settings
from django.db import models


class CommunityPost(models.Model):
    """Community discussion post / chat question."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_posts",
    )
    parent_post = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies_to",
    )
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    is_edited = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]


    def __str__(self):
        return f"Post by {self.author.full_name}: {self.title or self.content[:30]}"


class CommunityReply(models.Model):
    """Reply to a community discussion post / question."""

    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.CASCADE,
        related_name="replies",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_replies",
    )
    content = models.TextField()
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply by {self.author.full_name} on {self.post.pk}"


class Notification(models.Model):
    """System and chat notifications shown in topbar bell menu."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
    )
    message = models.TextField()
    url = models.CharField(max_length=255, default="/community/chat/")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.user.full_name}: {self.message[:30]}"

