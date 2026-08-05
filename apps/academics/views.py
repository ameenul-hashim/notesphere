"""Views for the academics module (semester, subject, and chapter management for admins,
interactive card browsing and PDF reading/downloading for students)."""

import io
import os
import re
import urllib.request

import mammoth

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required
from config.integrations.cloudinary_storage import delete_image_by_url

from .forms import ChapterForm, SemesterForm, SubjectForm
from .models import Chapter, Semester, Subject

SEMESTERS_PER_PAGE = 12
SUBJECTS_PER_PAGE = 12

DOCUMENT_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
}

USER_AGENT = "Mozilla/5.0 (compatible; NoteSphere/1.0)"

DOCX_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NoteSphere Document</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: 'Segoe UI', Roboto, Arial, sans-serif; background: #f4f4f5; color: #1f2937; line-height: 1.7; -webkit-font-smoothing: antialiased; }
  .docx-body { max-width: 820px; margin: 24px auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 32px 40px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
  .docx-body p { margin: 0 0 1rem; }
  .docx-body h1, .docx-body h2, .docx-body h3, .docx-body h4, .docx-body h5, .docx-body h6 { margin: 1.5rem 0 0.75rem; font-weight: 700; line-height: 1.3; }
  .docx-body h1 { font-size: 1.75rem; }
  .docx-body h2 { font-size: 1.45rem; }
  .docx-body h3 { font-size: 1.2rem; }
  .docx-body h4 { font-size: 1.05rem; }
  .docx-body h5, .docx-body h6 { font-size: 1rem; }
  .docx-body ul, .docx-body ol { margin: 0 0 1rem 1.5rem; padding: 0; }
  .docx-body li { margin-bottom: 0.25rem; }
  .docx-body table { border-collapse: collapse; width: 100%; margin: 0 0 1rem; }
  .docx-body th, .docx-body td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; vertical-align: top; }
  .docx-body th { font-weight: 700; background: #f3f4f6; }
  .docx-body img { max-width: 100%; height: auto; }
  .docx-body a { color: #7c3aed; text-decoration: underline; }
  .docx-body blockquote { margin: 0 0 1rem; padding: 0.5rem 1rem; border-left: 3px solid #7c3aed; background: #f3f4f6; }
  .docx-body pre, .docx-body code { background: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 0.9em; }
  .docx-body pre { padding: 0.75rem 1rem; overflow-x: auto; margin-bottom: 1rem; }
  .docx-body pre code { padding: 0; background: transparent; }
  @media (max-width: 640px) {
    .docx-body { margin: 0; border-radius: 0; padding: 20px 18px; }
  }
</style>
</head>
<body>
  <div class="docx-body">{content}</div>
</body>
</html>"""

SEMESTER_SORTABLE_FIELDS = {
    "name": "name",
    "status": "status",
    "display_order": "display_order",
    "created_at": "created_at",
}
SUBJECT_SORTABLE_FIELDS = {
    "name": "name",
    "semester": "semester__name",
    "status": "status",
    "display_order": "display_order",
    "created_at": "created_at",
}


@login_required
@admin_required
def semester_list(request):
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip().upper()
    sort = request.GET.get("sort", "display_order")
    direction = request.GET.get("dir", "asc")

    semesters = Semester.objects.annotate(subject_count=Count("subjects"))

    if query:
        semesters = semesters.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if status_filter in Semester.Status.values:
        semesters = semesters.filter(status=status_filter)
    else:
        status_filter = ""

    sort_field = SEMESTER_SORTABLE_FIELDS.get(sort, "display_order")
    order = f"-{sort_field}" if direction == "desc" else sort_field
    semesters = semesters.order_by(order, "display_order")

    counts = {
        row["status"]: row["total"]
        for row in Semester.objects.values("status").annotate(total=Count("id"))
    }

    paginator = Paginator(semesters, SEMESTERS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    params.pop("sort", None)
    params.pop("dir", None)
    qs = params.urlencode()

    semester_list_url = reverse("academics:semester_list")

    return render(
        request,
        "academics/semester_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "status_filter": status_filter,
            "sort": sort,
            "direction": direction,
            "qs": qs,
            "counts": counts,
            "total_semesters": sum(counts.values()),
            "semester_list_url": semester_list_url,
            "inactive_list_url": f"{semester_list_url}?status=INACTIVE",
        },
    )


@login_required
@admin_required
def semester_create(request):
    form = SemesterForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Semester "{form.cleaned_data["name"]}" has been created.')
        return redirect("academics:semester_list")
    return render(request, "academics/semester_form.html", {"form": form, "title": "Create Semester"})


@login_required
@admin_required
def semester_edit(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    form = SemesterForm(request.POST or None, request.FILES or None, instance=semester)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Semester "{semester.name}" has been updated.')
        return redirect("academics:semester_list")
    return render(
        request,
        "academics/semester_form.html",
        {"form": form, "title": "Edit Semester", "semester": semester},
    )


@login_required
@admin_required
def semester_delete(request, pk):
    if request.method == "POST":
        semester = get_object_or_404(Semester, pk=pk)
        # Delete Cloudinary thumbnail before deleting record
        if semester.thumbnail:
            try:
                db_thumb = Semester.objects.filter(pk=semester.pk).values_list("thumbnail", flat=True).first()
                if db_thumb and "cloudinary.com" in str(db_thumb):
                    delete_image_by_url(str(db_thumb))
            except Exception:
                pass
        messages.success(
            request,
            f'Semester "{semester.name}" and its subjects have been deleted.',
        )
        semester.delete()
    return redirect("academics:semester_list")


@login_required
def semester_detail(request, pk):
    """View a semester and list its subject cards."""
    if request.user.is_admin:
        semester = get_object_or_404(Semester, pk=pk)
        subjects = semester.subjects.annotate(
            chapter_count=Count("chapters"),
            english_count=Count("chapters", filter=Q(chapters__language=Chapter.Language.ENGLISH)),
            malayalam_count=Count("chapters", filter=Q(chapters__language=Chapter.Language.MALAYALAM)),
        )
    else:
        semester = get_object_or_404(Semester, pk=pk, status=Semester.Status.ACTIVE)
        subjects = semester.subjects.filter(status=Subject.Status.ACTIVE).annotate(
            chapter_count=Count("chapters", filter=Q(chapters__status=Chapter.Status.ACTIVE)),
            english_count=Count(
                "chapters",
                filter=Q(
                    chapters__status=Chapter.Status.ACTIVE,
                    chapters__language=Chapter.Language.ENGLISH,
                ),
            ),
            malayalam_count=Count(
                "chapters",
                filter=Q(
                    chapters__status=Chapter.Status.ACTIVE,
                    chapters__language=Chapter.Language.MALAYALAM,
                ),
            ),
        )

    return render(
        request,
        "academics/semester_detail.html",
        {
            "semester": semester,
            "subjects": subjects,
            "is_admin": request.user.is_admin,
        },
    )


@login_required
@admin_required
def subject_list(request):
    query = request.GET.get("q", "").strip()
    semester_filter = request.GET.get("semester", "").strip()
    status_filter = request.GET.get("status", "").strip().upper()
    sort = request.GET.get("sort", "display_order")
    direction = request.GET.get("dir", "asc")

    subjects = Subject.objects.select_related("semester").annotate(
        chapter_count=Count("chapters"),
        english_count=Count("chapters", filter=Q(chapters__language=Chapter.Language.ENGLISH)),
        malayalam_count=Count("chapters", filter=Q(chapters__language=Chapter.Language.MALAYALAM)),
    )

    if query:
        subjects = subjects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if semester_filter.isdigit():
        subjects = subjects.filter(semester_id=int(semester_filter))
    else:
        semester_filter = ""

    if status_filter in Subject.Status.values:
        subjects = subjects.filter(status=status_filter)
    else:
        status_filter = ""

    sort_field = SUBJECT_SORTABLE_FIELDS.get(sort, "display_order")
    order = f"-{sort_field}" if direction == "desc" else sort_field
    subjects = subjects.order_by(order, "display_order")

    counts = {
        row["status"]: row["total"]
        for row in Subject.objects.values("status").annotate(total=Count("id"))
    }

    paginator = Paginator(subjects, SUBJECTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    params.pop("sort", None)
    params.pop("dir", None)
    qs = params.urlencode()

    return render(
        request,
        "academics/subject_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "semester_filter": semester_filter,
            "status_filter": status_filter,
            "semesters": Semester.objects.order_by("display_order"),
            "sort": sort,
            "direction": direction,
            "qs": qs,
            "counts": counts,
            "total_subjects": sum(counts.values()),
        },
    )


@login_required
@admin_required
def subject_create(request):
    initial = {}
    semester_id = request.GET.get("semester")
    selected_semester = None
    if semester_id and semester_id.isdigit():
        initial["semester"] = int(semester_id)
        selected_semester = Semester.objects.filter(pk=int(semester_id)).first()

    form = SubjectForm(request.POST or None, request.FILES or None, initial=initial)
    if selected_semester:
        form.fields["semester"].disabled = True

    if request.method == "POST" and form.is_valid():
        subject = form.save()
        messages.success(request, f'Subject "{subject.name}" has been created.')
        return redirect("academics:semester_detail", pk=subject.semester.pk)

    return render(
        request,
        "academics/subject_form.html",
        {
            "form": form,
            "title": "Create Subject",
            "selected_semester": selected_semester,
        },
    )


@login_required
def subject_detail(request, pk):
    """View a subject and list its English and Malayalam chapter/module cards."""
    selected_lang = request.GET.get("lang", Chapter.Language.ENGLISH).upper()
    if selected_lang not in Chapter.Language.values:
        selected_lang = Chapter.Language.ENGLISH

    if request.user.is_admin:
        subject = get_object_or_404(Subject.objects.select_related("semester"), pk=pk)
        base_chapters = subject.chapters.all()
    else:
        subject = get_object_or_404(
            Subject.objects.select_related("semester"),
            pk=pk,
            status=Subject.Status.ACTIVE,
            semester__status=Semester.Status.ACTIVE,
        )
        base_chapters = subject.chapters.filter(status=Chapter.Status.ACTIVE)

    english_count = base_chapters.filter(language=Chapter.Language.ENGLISH).count()
    malayalam_count = base_chapters.filter(language=Chapter.Language.MALAYALAM).count()

    selected_chapters = base_chapters.filter(language=selected_lang)
    modules = selected_chapters.filter(kind=Chapter.Kind.MODULE)
    chapters_only = selected_chapters.filter(kind=Chapter.Kind.CHAPTER)

    return render(
        request,
        "academics/subject_detail.html",
        {
            "subject": subject,
            "semester": subject.semester,
            "modules": modules,
            "chapters_only": chapters_only,
            "selected_lang": selected_lang,
            "english_count": english_count,
            "malayalam_count": malayalam_count,
            "is_admin": request.user.is_admin,
        },
    )


@login_required
@admin_required
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    form = SubjectForm(request.POST or None, request.FILES or None, instance=subject)
    if request.method == "POST" and form.is_valid():
        subject = form.save()
        messages.success(request, f'Subject "{subject.name}" has been updated.')
        return redirect("academics:semester_detail", pk=subject.semester.pk)

    return render(
        request,
        "academics/subject_form.html",
        {
            "form": form,
            "title": "Edit Subject",
            "subject": subject,
            "selected_semester": subject.semester,
        },
    )


@login_required
@admin_required
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    semester_pk = subject.semester.pk
    if request.method == "POST":
        name = subject.name
        # Delete Cloudinary thumbnail before deleting record
        if subject.thumbnail:
            try:
                db_thumb = Subject.objects.filter(pk=subject.pk).values_list("thumbnail", flat=True).first()
                if db_thumb and "cloudinary.com" in str(db_thumb):
                    delete_image_by_url(str(db_thumb))
            except Exception:
                pass
        subject.delete()
        messages.success(request, f'Subject "{name}" has been deleted.')
    return redirect("academics:semester_detail", pk=semester_pk)


@login_required
@admin_required
def chapter_create(request):
    initial = {}
    subject_id = request.GET.get("subject")
    language = request.GET.get("language", "").upper()
    if language in Chapter.Language.values:
        initial["language"] = language

    selected_subject = None
    if subject_id and subject_id.isdigit():
        initial["subject"] = int(subject_id)
        selected_subject = Subject.objects.select_related("semester").filter(pk=int(subject_id)).first()

    if selected_subject:
        lang = initial.get("language", Chapter.Language.ENGLISH)
        chapter_qs = Chapter.objects.filter(subject=selected_subject, language=lang)

        last_number = (
            chapter_qs.order_by("-chapter_number")
            .values_list("chapter_number", flat=True)
            .first()
        )
        initial["chapter_number"] = (last_number or 0) + 1

        last_order = (
            chapter_qs.order_by("-display_order")
            .values_list("display_order", flat=True)
            .first()
        )
        initial["display_order"] = (last_order if last_order is not None else -1) + 1

    form = ChapterForm(request.POST or None, request.FILES or None, initial=initial)
    if selected_subject:
        form.fields["subject"].disabled = True

    if request.method == "POST" and form.is_valid():
        chapter = form.save()
        messages.success(request, f'Chapter "{chapter.title}" ({chapter.get_language_display()}) has been created.')
        return redirect(f"{reverse('academics:subject_detail', kwargs={'pk': chapter.subject.pk})}?lang={chapter.language}")

    return render(
        request,
        "academics/chapter_form.html",
        {
            "form": form,
            "title": "Create Chapter / Module",
            "selected_subject": selected_subject,
        },
    )


@login_required
@admin_required
def chapter_next_number(request):
    """Return the next auto chapter number for a subject+language (AJAX helper)."""
    subject_id = request.GET.get("subject", "")
    language = request.GET.get("language", "").upper()
    if language not in Chapter.Language.values:
        language = Chapter.Language.ENGLISH

    next_number = 1
    if subject_id.isdigit():
        last_number = (
            Chapter.objects.filter(subject_id=int(subject_id), language=language)
            .order_by("-chapter_number")
            .values_list("chapter_number", flat=True)
            .first()
        )
        next_number = (last_number or 0) + 1
    return JsonResponse({"next": next_number})


@login_required
@admin_required
def chapter_edit(request, pk):
    chapter = get_object_or_404(Chapter.objects.select_related("subject"), pk=pk)
    form = ChapterForm(request.POST or None, request.FILES or None, instance=chapter)
    form.fields["subject"].disabled = True

    if request.method == "POST" and form.is_valid():
        chapter = form.save()
        messages.success(request, f'Chapter "{chapter.title}" has been updated.')
        return redirect(f"{reverse('academics:subject_detail', kwargs={'pk': chapter.subject.pk})}?lang={chapter.language}")

    return render(
        request,
        "academics/chapter_form.html",
        {
            "form": form,
            "title": "Edit Chapter / Module",
            "chapter": chapter,
            "selected_subject": chapter.subject,
        },
    )


@login_required
@admin_required
def chapter_delete(request, pk):
    chapter = get_object_or_404(Chapter.objects.select_related("subject"), pk=pk)
    subject_pk = chapter.subject.pk
    if request.method == "POST":
        title = chapter.title
        chapter.delete()
        messages.success(request, f'Chapter "{title}" has been deleted.')
    return redirect("academics:subject_detail", pk=subject_pk)


def _accessible_chapter(request, pk):
    """Return a chapter the current user is allowed to view/download."""
    if request.user.is_admin:
        return get_object_or_404(Chapter.objects.select_related("subject__semester"), pk=pk)
    return get_object_or_404(
        Chapter.objects.select_related("subject__semester"),
        pk=pk,
        status=Chapter.Status.ACTIVE,
        subject__status=Subject.Status.ACTIVE,
        subject__semester__status=Semester.Status.ACTIVE,
    )


def _document_source(chapter):
    """Return (raw_bytes, hint) where hint is the file name or remote Content-Type.

    Raises Http404 if the chapter has no document or the remote source is unreachable.
    """
    if chapter.pdf_file:
        fh = chapter.pdf_file.open("rb")
        try:
            return fh.read(), chapter.pdf_file.name
        finally:
            fh.close()

    url = chapter.document_url
    if not url:
        raise Http404

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as remote:
            return remote.read(), remote.headers.get("Content-Type") or url
    except Exception:
        raise Http404


@login_required
def chapter_view(request, pk):
    """Open the document directly in a new tab. PDFs are served inline for the
    browser's native viewer; DOCX files are rendered to HTML server-side so they
    open in the browser instead of downloading."""
    chapter = _accessible_chapter(request, pk)

    if chapter.is_docx:
        try:
            data, _hint = _document_source(chapter)
            result = mammoth.convert_to_html(io.BytesIO(data))
        except Exception:
            raise Http404
        return HttpResponse(DOCX_HTML_PAGE.replace("{content}", result.value), content_type="text/html; charset=utf-8")

    data, hint = _document_source(chapter)
    ext = chapter.file_extension
    if ext in DOCUMENT_CONTENT_TYPES:
        content_type = DOCUMENT_CONTENT_TYPES[ext]
    elif "/" in hint:
        content_type = hint.split(";")[0].strip()
    else:
        content_type = "application/octet-stream"

    filename = chapter.download_name(ext)
    response = HttpResponse(data, content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def chapter_download(request, pk):
    """Stream the document as a forced download (remote URLs are proxied through
    the server so the browser downloads instead of opening the file)."""
    chapter = _accessible_chapter(request, pk)

    ext = chapter.file_extension
    filename = chapter.download_name(ext)
    fallback_type = DOCUMENT_CONTENT_TYPES.get(ext, "application/octet-stream")

    if chapter.pdf_file:
        return FileResponse(
            chapter.pdf_file.open("rb"),
            as_attachment=True,
            filename=filename,
            content_type=fallback_type,
        )

    url = chapter.document_url
    if not url:
        raise Http404

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as remote:
            content_type = remote.headers.get("Content-Type") or fallback_type
            response = HttpResponse(remote.read(), content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
    except Exception:
        raise Http404
