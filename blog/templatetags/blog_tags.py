from django import template
from django.utils.translation import get_language

from blog.models import Category
from wagtail.models import Locale

register = template.Library()


@register.simple_tag(takes_context=True)
def get_site_root(context):
    """Returns the site root page for the current request."""
    request = context('request')
    if request:
        return request.site_page
    return None


@register.simple_tag
def get_categories():
    """Returns categories for the current locale."""
    return Category.objects.filter(locale=Locale.get_active()).order_by('order', 'name')


@register.simple_tag(takes_context=True)
def get_language_switcher(context):
    """Returns list of dicts {lang_code, lang_name, url} for the language switcher."""
    page = context.get("page")
    request = context.get("request")
    if not page or not request:
        return []

    result = []
    for locale in Locale.objects.all():
        try:
            translation = page.get_translation(locale)
            url = translation.full_url
        except Exception:
            url = None

        result.append(
            {
                "lang_code": locale.language_code,
                "lang_name": dict([("ru", "Русский"), ("ua", "Українська")]).get(locale.language_code,
                                                                                 locale.language_code),
                "url": url,
                "is_active": locale.language_code == get_language(),
            }
        )
    return result
