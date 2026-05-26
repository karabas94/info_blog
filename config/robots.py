from django.http import HttpResponse
from django.urls import path


def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /cms/",
        "Disallow: /ru/search/",
        "Disallow: /ua/search/",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    path("", robots_txt),
]
