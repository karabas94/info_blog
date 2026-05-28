from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from django.templatetags.static import static
from django.utils.html import format_html
from django.contrib import messages
from wagtail import hooks
from wagtail.models import Locale

from blog.models import BlogDetailPage

from .models import Category


class CategoryViewSet(SnippetViewSet):
    model = Category
    icon = 'tag'
    menu_label = 'Categories'
    menu_order = 200
    list_display = ["name", "slug", "order"]
    search_fields = ["name", "slug"]
    list_filter = ["locale"]


register_snippet(CategoryViewSet)


@hooks.register('insert_global_admin_css')
def global_admin_css():
    return """
    <style>
      .sidebar-menu-item--active { font-weight: 600; }
    </style>
"""


@hooks.register("insert_editor_js")
def editor_js():
    return format_html(
        '<script src="{}?v=3"></script>',
        static("js/admin-slugify.js")
    )


def maybe_create_ua_draft(request, page):
    # Защита: чтобы за один request сообщение не появлялось много раз
    if getattr(request, "_ua_draft_hook_done", False):
        return

    page = page.specific

    if not isinstance(page, BlogDetailPage):
        return

    if page.locale.language_code != "ru":
        return

    if not page.create_ua_draft:
        return

    request._ua_draft_hook_done = True

    ua_locale = Locale.objects.filter(language_code="ua").first()
    already_exists = False

    if ua_locale and page.has_translation(ua_locale):
        already_exists = True

    ua_page = page.create_ua_translation_draft()

    # Сбрасываем галочку напрямую в базе, без повторного page.save()
    BlogDetailPage.objects.filter(pk=page.pk).update(create_ua_draft=False)

    if ua_page:
        if already_exists:
            messages.success(request, "Ukrainian draft was updated.")
        else:
            messages.success(request, "Ukrainian draft was created.")
    else:
        messages.warning(
            request,
            "Ukrainian draft was not created. Check that Ukrainian category page exists.",
        )


@hooks.register("after_create_page")
def after_create_blog_page(request, page):
    maybe_create_ua_draft(request, page)


@hooks.register("after_edit_page")
def after_edit_blog_page(request, page):
    maybe_create_ua_draft(request, page)
