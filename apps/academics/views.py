"""Views for the academics module (semester, subject, and chapter management for admins,
interactive card browsing and PDF reading/downloading for students)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import admin_required

from .forms import ChapterForm, SemesterForm, SubjectForm
from .models import Chapter, Semester, Subject

SEMESTERS_PER_PAGE = 12
SUBJECTS_PER_PAGE = 12

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
        subjects = semester.subjects.annotate(chapter_count=Count("chapters"))
    else:
        semester = get_object_or_404(Semester, pk=pk, status=Semester.Status.ACTIVE)
        subjects = semester.subjects.filter(status=Subject.Status.ACTIVE).annotate(
            chapter_count=Count("chapters", filter=Q(chapters__status=Chapter.Status.ACTIVE))
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

    subjects = Subject.objects.select_related("semester").annotate(chapter_count=Count("chapters"))

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

    chapters = base_chapters.filter(language=selected_lang)

    return render(
        request,
        "academics/subject_detail.html",
        {
            "subject": subject,
            "semester": subject.semester,
            "chapters": chapters,
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


@login_required
def chapter_read(request, pk):
    """In-app PDF reader view for students and admins."""
    if request.user.is_admin:
        chapter = get_object_or_404(Chapter.objects.select_related("subject__semester"), pk=pk)
    else:
        chapter = get_object_or_404(
            Chapter.objects.select_related("subject__semester"),
            pk=pk,
            status=Chapter.Status.ACTIVE,
            subject__status=Subject.Status.ACTIVE,
            subject__semester__status=Semester.Status.ACTIVE,
        )

    return render(
        request,
        "academics/chapter_read.html",
        {
            "chapter": chapter,
            "subject": chapter.subject,
            "semester": chapter.subject.semester,
        },
    )
