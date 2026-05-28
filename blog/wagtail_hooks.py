from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from django.templatetags.static import static
from django.utils.html import format_html


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
