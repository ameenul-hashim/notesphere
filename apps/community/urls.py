from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("chat/", views.community_chat, name="chat"),
    path("chat/reply/<int:post_pk>/", views.reply_create, name="reply_create"),
    path("chat/post/<int:post_pk>/edit/", views.post_edit, name="post_edit"),
    path("chat/post/<int:post_pk>/delete/", views.post_delete, name="post_delete"),
    path("chat/reply/<int:reply_pk>/delete/", views.reply_delete, name="reply_delete"),
    path("notifications/read/<int:notif_pk>/", views.notification_read, name="notification_read"),
    path("members/", views.active_members_view, name="members"),
    path("online-users/", views.online_users, name="online_users"),
]
