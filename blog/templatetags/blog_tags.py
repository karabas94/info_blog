from django import template
from django.utils.translation import get_language

from blog.models import Category
from wagtail.models import Locale

register = template.Library()


@register.simple_tag(takes_context=True)
def get_site_root(context):
    """Returns the site root page for the current request."""
    request = context.get('request')
    if request:
        return request.site_page
    return None


@register.simple_tag
def get_categories():
    """Returns categories for the current locale."""
    return Category.objects.filter(locale=Locale.get_active()).order_by('order', 'name')


@register.simple_tag(takes_context=True)
def get_language_switcher(context):
    """
    Language switcher.

    Логика:
    1. Если у текущей страницы есть перевод — ведём на перевод.
    2. Если перевода нет — ведём на главную этого языка.
    """
    page = context.get("page")
    request = context.get("request")

    if not request:
        return []

    language_names = {
        "ru": "Русский",
        "ua": "Українська",
    }

    result = []

    for locale in Locale.objects.all():
        url = None

        # 1. Пробуем найти перевод текущей страницы
        if page:
            try:
                translation = page.get_translation(locale)

                if translation and translation.live and translation.url:
                    url = translation.url
            except Exception:
                url = None

        # 2. Если перевода нет — ведём на главную этого языка
        if not url:
            try:
                root_page = request.site.root_page.get_translation(locale)

                if root_page and root_page.url:
                    url = root_page.url
            except Exception:
                url = f"/{locale.language_code}/"

        result.append(
            {
                "lang_code": locale.language_code,
                "lang_name": language_names.get(
                    locale.language_code,
                    locale.language_code,
                ),
                "url": url,
                "is_active": locale.language_code == get_language(),
            }
        )

    return result


@register.simple_tag(takes_context=True)
def get_category_pages(context):
    from wagtail.models import Locale
    from blog.models import BlogCategoryPage
    request = context.get("request")
    locale = Locale.get_active()
    pages = (
        BlogCategoryPage.objects.live()
        .public()
        .filter(locale=locale)
    )
    site = getattr(request, "site", None) if request else None
    if site and site.root_page:
        try:
            root_page = site.root_page.get_translation(locale)
            pages = pages.descendant_of(root_page)
        except Exception:
            pass
    return pages.specific().order_by("title")
