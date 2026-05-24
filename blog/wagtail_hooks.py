from wagtail import hooks
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

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
