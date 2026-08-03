from django.contrib import admin

from .models import CommunityPost, CommunityReply


class CommunityReplyInline(admin.TabularInline):
    model = CommunityReply
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ["id", "author", "title", "is_pinned", "is_edited", "created_at"]
    list_filter = ["is_pinned", "is_edited", "created_at"]
    search_fields = ["title", "content", "author__full_name", "author__email"]
    inlines = [CommunityReplyInline]


@admin.register(CommunityReply)
class CommunityReplyAdmin(admin.ModelAdmin):
    list_display = ["id", "post", "author", "created_at"]
    search_fields = ["content", "author__full_name", "author__email"]
