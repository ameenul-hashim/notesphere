from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import CommunityPost, CommunityReply, Notification
from .utils import format_clean_name

User = get_user_model()


@login_required
def community_chat(request):
    """Community Chat / Discussion Forum view (WhatsApp continuous chat feed)."""
    posts = (
        CommunityPost.objects.select_related(
            "author", "author__avatar", "parent_post", "parent_post__author"
        )
        .all()
        .order_by("created_at")
    )

    # Include ALL users (Admin + Students) so their cards are pre-rendered in the sidebar
    # Firebase presence will dynamically show/hide them as they come online/offline
    # Order: ADMIN role first (alphabetically 'ADMIN' < 'STUDENT'), then by full_name
    active_users = list(User.objects.select_related("avatar").order_by("role", "full_name"))
    for u in active_users:
        u.clean_name = format_clean_name(u.full_name)



    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        parent_id = request.POST.get("parent_id", "").strip()
        
        if content:
            parent_post = None
            if parent_id and parent_id.isdigit():
                parent_post = CommunityPost.objects.filter(pk=int(parent_id)).first()

            new_post = CommunityPost.objects.create(
                author=request.user,
                content=content,
                parent_post=parent_post,
            )

            notified_user_ids = set()

            # Create notification for quoted user (once)
            if parent_post and parent_post.author != request.user:
                sender_name = format_clean_name(request.user.full_name)
                Notification.objects.create(
                    user=parent_post.author,
                    sender=request.user,
                    message=f"{sender_name} replied to your message in Community Chat: '{content[:50]}'",
                    url="/community/chat/",
                )
                notified_user_ids.add(parent_post.author.id)

            # Check for @mentions in content (once per user)
            for u in active_users:
                if u != request.user and u.id not in notified_user_ids:
                    if f"@{u.username}" in content or f"@{u.clean_name}" in content:
                        sender_name = format_clean_name(request.user.full_name)
                        Notification.objects.create(
                            user=u,
                            sender=request.user,
                            message=f"{sender_name} mentioned you in Community Chat: '{content[:50]}'",
                            url="/community/chat/",
                        )
                        notified_user_ids.add(u.id)

            messages.success(request, "Message sent to Community Chat!")
            return redirect("community:chat")
        else:
            messages.error(request, "Message content cannot be empty.")

    return render(
        request,
        "community/chat.html",
        {
            "posts": posts,
            "active_users": active_users,
        },
    )


@login_required
def notification_read(request, notif_pk):
    """Mark a notification as read and redirect to target URL."""
    notif = get_object_or_404(Notification, pk=notif_pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return redirect(notif.url or "community:chat")





@login_required
def reply_create(request, post_pk):
    """Create a reply on a community post."""
    post = get_object_or_404(CommunityPost, pk=post_pk)
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            CommunityReply.objects.create(
                post=post,
                author=request.user,
                content=content,
            )
            messages.success(request, "Reply added successfully.")
        else:
            messages.error(request, "Reply content cannot be empty.")
    return redirect("community:chat")


@login_required
def post_edit(request, post_pk):
    """Edit a community post. Allowed for author or admin."""
    post = get_object_or_404(CommunityPost, pk=post_pk)

    if not (request.user == post.author or request.user.is_admin):
        messages.error(request, "You do not have permission to edit this post.")
        return redirect("community:chat")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        title = request.POST.get("title", "").strip()
        if content:
            post.content = content
            post.title = title
            post.is_edited = True
            post.save(update_fields=["content", "title", "is_edited", "updated_at"])
            messages.success(request, "Post updated successfully.")
            return redirect("community:chat")
        else:
            messages.error(request, "Content cannot be empty.")

    return render(request, "community/post_edit.html", {"post": post})


@login_required
def post_delete(request, post_pk):
    """Delete a community post. Allowed for Admin or Author."""
    post = get_object_or_404(CommunityPost, pk=post_pk)

    if not (request.user == post.author or request.user.is_admin):
        messages.error(request, "You do not have permission to delete this post.")
        return redirect("community:chat")

    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted successfully.")

    return redirect("community:chat")


@login_required
def reply_delete(request, reply_pk):
    """Delete a reply. Allowed for Admin or Author."""
    reply = get_object_or_404(CommunityReply, pk=reply_pk)

    if not (request.user == reply.author or request.user.is_admin):
        messages.error(request, "You do not have permission to delete this reply.")
        return redirect("community:chat")

    if request.method == "POST":
        reply.delete()
        messages.success(request, "Reply deleted successfully.")

    return redirect("community:chat")


@login_required
def active_members_view(request):
    """Active Students & Community Members page (matching the user's screenshot layout).

    Displays all active students in rounded pill/badge cards, automatically
    formatting names with clean spacing.
    """
    query = request.GET.get("q", "").strip()
    students_qs = User.objects.filter(status=User.Status.ACTIVE).select_related("avatar")

    if query:
        students_qs = students_qs.filter(
            full_name__icontains=query
        ) | User.objects.filter(status=User.Status.ACTIVE, email__icontains=query)

    students = list(students_qs.order_by("role", "full_name"))

    # Attach formatted name property to each user object for crisp rendering
    for student in students:
        student.clean_name = format_clean_name(student.full_name)

    return render(
        request,
        "community/active_members.html",
        {
            "students": students,
            "total_count": len(students),
            "query": query,
        },
    )
