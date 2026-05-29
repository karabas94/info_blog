from django import template
from django.utils.translation import get_language
from blog.models import Category, BlogCategoryPage
from wagtail.models import Locale, Page

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

    cache_attr = f"_language_switcher_cache_{getattr(page, 'id', 'none')}"

    cached = getattr(request, cache_attr, None)
    if cached is not None:
        return cached

    language_names = {
        "ru": "Русский",
        "ua": "Українська",
    }

    current_language = get_language()

    locales = list(
        Locale.objects.filter(language_code__in=["ru", "ua"])
        .order_by("language_code")
    )

    locale_ids = [locale.id for locale in locales]

    page_translations = {}

    if page and getattr(page, "translation_key", None):
        translations_qs = (
            Page.objects.live()
            .filter(
                translation_key=page.translation_key,
                locale_id__in=locale_ids,
            )
        )

        page_translations = {
            translation.locale_id: translation
            for translation in translations_qs
        }

    missing_locale_ids = [
        locale.id
        for locale in locales
        if locale.id not in page_translations
    ]

    root_translations = {}

    if missing_locale_ids and getattr(request, "site", None):
        root_page = request.site.root_page

        root_qs = (
            Page.objects.live()
            .filter(
                translation_key=root_page.translation_key,
                locale_id__in=missing_locale_ids,
            )
        )

        root_translations = {
            translation.locale_id: translation
            for translation in root_qs
        }

    result = []

    for locale in locales:
        target_page = page_translations.get(locale.id)

        if not target_page:
            target_page = root_translations.get(locale.id)

        if target_page:
            url = target_page.get_url(request)
        else:
            url = f"/{locale.language_code}/"

        result.append(
            {
                "lang_code": locale.language_code,
                "lang_name": language_names.get(
                    locale.language_code,
                    locale.language_code,
                ),
                "url": url,
                "is_active": locale.language_code == current_language,
            }
        )

    setattr(request, cache_attr, result)

    return result


@register.simple_tag(takes_context=True)
def get_category_pages(context):
    request = context.get("request")
    page = context.get("page")

    # Самый быстрый вариант:
    # если мы уже на Wagtail-странице, у неё уже есть locale_id.
    # Значит не надо делать Locale.get_active() и лезть в wagtailcore_locale.
    locale_id = getattr(page, "locale_id", None)

    # Запасной вариант, если page вдруг нет.
    # В обычных Wagtail-страницах он почти не должен срабатывать.
    if not locale_id:
        language_code = getattr(request, "LANGUAGE_CODE", None) if request else None

        if not language_code:
            from django.utils.translation import get_language
            language_code = get_language()

        locale = Locale.objects.only("id").get(language_code=language_code)
        locale_id = locale.id

    pages = (
        BlogCategoryPage.objects.live()
        .filter(locale_id=locale_id)
        .order_by("title")
        .specific()
    )

    return pages
