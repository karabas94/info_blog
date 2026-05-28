from django.shortcuts import render
from django.utils.translation import gettext as _
from wagtail.models import Locale
from wagtail.contrib.search_promotions.models import Query

from blog.models import BlogDetailPage


def search(request):
    search_query = request.GET.get("query", "").strip()
    search_results = BlogDetailPage.objects.none()

    if search_query:
        search_results = (
            BlogDetailPage.objects.live()
            .public()
            .filter(locale=Locale.get_active())
            .search(search_query)
        )

        query = Query.get(search_query)
        query.add_hit()

    breadcrumbs = [
        {
            "title": _("Home"),
            "url": f"/{Locale.get_active().language_code}/",
        },
        {
            "title": _("Search"),
            "url": request.path,
        },
    ]

    return render(
        request,
        "search/search.html",
        {
            "search_query": search_query,
            "search_results": search_results,
            "breadcrumbs": breadcrumbs,
        },
    )