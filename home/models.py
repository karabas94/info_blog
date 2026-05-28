from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Locale, Page
from blog.models import AutoSlugMixin


class HomePage(AutoSlugMixin, Page):
    """Site root page"""

    intro = RichTextField(_("intro"), blank=True)
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("featured image"),
    )

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("featured_image"),
    ]

    class Meta:
        verbose_name = _("home page")

    def get_context(self, request, *args, **kwargs):
        from blog.models import BlogDetailPage, Category
        context = super().get_context(request, *args, **kwargs)
        context["recent_posts"] = (
            BlogDetailPage.objects.live()
            .public()
            .filter(locale=Locale.get_active())
            .select_related("category", "author", "main_image")
            .order_by("-publication_date")[:6]
        )
        context["categories"] = Category.objects.filter(
            locale=Locale.get_active()
        ).order_by("order", "name")
        return context
