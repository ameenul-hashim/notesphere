from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import CommunityPost, CommunityReply
from .utils import format_clean_name

User = get_user_model()


@login_required
def community_chat(request):
    """Community Chat / Discussion Forum view."""
    posts = (
        CommunityPost.objects.select_related("author", "author__avatar")
        .prefetch_related("replies__author", "replies__author__avatar")
        .all()
    )

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        title = request.POST.get("title", "").strip()
        if content:
            CommunityPost.objects.create(
                author=request.user,
                title=title,
                content=content,
            )
            messages.success(request, "Your question / note has been posted to the community!")
            return redirect("community:chat")
        else:
            messages.error(request, "Post content cannot be empty.")

    return render(
        request,
        "community/chat.html",
        {
            "posts": posts,
        },
    )


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

    students = list(students_qs)

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
