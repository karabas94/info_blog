import json

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import RichTextField, StreamField
from wagtail.images.models import Image
from wagtail.models import (
    Locale,
    Page,
    TranslatableMixin,
)
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from .blocks import BlogBodyBlock
from slugify import slugify as unicode_slugify

from django.utils.text import slugify
from slugify import slugify as unicode_slugify

from slugify import slugify as unicode_slugify


class AutoSlugMixin:
    """Транслитерирует slug страницы из title перед сохранением в Wagtail."""

    def clean(self):
        super().clean()

        if not self.title:
            return

        # Если slug пустой или содержит кириллицу/не-ASCII символы
        try:
            self.slug.encode("ascii")
            slug_is_ascii = True
        except UnicodeEncodeError:
            slug_is_ascii = False

        if not self.slug or not slug_is_ascii:
            self.slug = unicode_slugify(self.title, allow_unicode=False)


# Category snippet (translatable)
class Category(TranslatableMixin, models.Model):
    """Blog category — translatable snippet."""
    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), max_length=100, allow_unicode=True)
    description = models.TextField(_("description"), blank=True)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("image"),
    )
    order = models.PositiveIntegerField(_("order"), default=0)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("description"),
        FieldPanel("image"),
        FieldPanel("order"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["order", "name"]
        unique_together = [("translation_key", "locale"), ("slug", "locale")]

    def __str__(self):
        return self.name


# # Home Page
# class HomePage(Page):
#     """Site root page"""
#
#     intro = RichTextField(_("intro"), blank=True)
#     featured_image = models.ForeignKey(
#         "wagtailimages.Image",
#         null=True,
#         blank=True,
#         on_delete=models.SET_NULL,
#         related_name="+",
#         verbose_name=_("featured image")
#     )
#
#     content_panels = Page.content_panels + [
#         FieldPanel("intro"),
#         FieldPanel("featured_image"),
#     ]
#
#     class Meta:
#         verbose_name = _("home page")
#
#     def get_context(self, request, *args, **kwargs):
#         context = super().get_context(request, *args, **kwargs)
#         # Последние 6 статей для главной страницы
#         context["recent_posts"] = (
#             BlogDetailPage.objects.live()
#             .public()
#             .filter(locale=Locale.get_active())
#             .select_related("category", "author", "main_image")
#             .order_by("-publication_date")[:6]
#         )
#         context["categories"] = (
#             Category.objects.filter(locale=Locale.get_active()).order_by("order", "name")
#         )
#         return context


# Blog Index Page
class BlogIndexPage(AutoSlugMixin, RoutablePageMixin, Page):
    """Blog listing page."""
    intro = RichTextField(_("intro"), blank=True)
    posts_per_page = models.PositiveIntegerField(_("posts per page"), default=12)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("posts_per_page")
    ]

    class Meta:
        verbose_name = _("blog index page")

    def get_posts(self):
        return (
            BlogDetailPage.objects.live()
            .public()
            .filter(locale=Locale.get_active())
            .select_related("category", "author", "main_image")
            .order_by("-publication_date")
        )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, args, kwargs)
        from django.core.paginator import Paginator

        page_number = request.GET.get("page", 1)
        posts = self.get_posts()
        paginator = Paginator(posts, self.posts_per_page)
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["paginator"] = paginator
        context["is_ajax"] = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        context["categories"] = Category.objects.filter(locale=Locale.get_active()).order_by("order")
        return context


# Blog Category Page

class BlogCategoryPage(AutoSlugMixin, RoutablePageMixin, Page):
    """Page for a single category listing."""

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pages",
        verbose_name=_("category"),
    )
    intro = RichTextField(_("intro"), blank=True)
    posts_per_page = models.PositiveIntegerField(_("posts per page"), default=12)

    content_panels = Page.content_panels + [
        FieldPanel("category"),
        FieldPanel("intro"),
        FieldPanel("posts_per_page"),
    ]

    class Meta:
        verbose_name = _("blog category page")

    def get_posts(self):
        return (
            BlogDetailPage.objects.live()
            .public()
            .filter(locale=Locale.get_active(), category=self.category)
            .select_related("category", "author", "main_image")
            .order_by("-publication_date")
        )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        from django.core.paginator import Paginator

        page_number = request.GET.get("page", 1)
        posts = self.get_posts()
        paginator = Paginator(posts, self.posts_per_page)
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["paginator"] = paginator
        context["categories"] = Category.objects.filter(locale=Locale.get_active()).order_by("order")
        return context


# Blog Detail Page (Article)
class BlogDetailPage(AutoSlugMixin, Page):
    """Blog article page."""
    # content
    intro = models.TextField(_("intro/excerpt"), blank=True, max_length=500)
    body = StreamField(
        BlogBodyBlock(),
        verbose_name=_("body"),
        use_json_field=True,
    )
    main_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("main image"),
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
        verbose_name=_("category"),
    )
    author = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    publication_date = models.DateTimeField(
        _("publication date"),
        null=True,
        blank=True,
    )
    # SEO / OG
    og_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("OG image"),
    )
    canonical_url = models.URLField(
        _("canonical URL"),
        blank=True,
        help_text=_("Leave blank to use the page's own URL."),
    )
    # Panels
    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("author"),
                FieldPanel("category"),
                FieldPanel("publication_date"),
            ],
            heading=_("Article info"),
        ),
        FieldPanel("intro"),
        FieldPanel("main_image"),
        FieldPanel("body"),
    ]
    promote_panels = Page.promote_panels + [
        FieldPanel("og_image"),
        FieldPanel("canonical_url"),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading=_("Content")),
            ObjectList(promote_panels, heading=_("SEO / Promote")),
            ObjectList(Page.settings_panels, heading=_("Settings")),
        ]
    )
    # Search index
    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
        index.FilterField("locale_id"),
        index.FilterField("category_id"),
        index.FilterField("publication_date"),
    ]

    class Meta:
        verbose_name = _("blog post")
        verbose_name_plural = _("blog posts")

    def get_breadcrumbs(self):
        crumbs = [{"title": "Home", "url": self.get_site().root_page.full_url}]
        blog_index = BlogIndexPage.objects.live().public().filter(locale=self.locale).first()
        if blog_index:
            crumbs.append({"title": blog_index.title, "url": blog_index.full_url})
        if self.category:
            cat_page = self.category.pages.live().public().filter(locale=self.locale).first()
            if cat_page:
                crumbs.append({"title": self.category.name, "url": cat_page.full_url})
        crumbs.append({"title": self.title, "url": self.full_url})
        return crumbs

    def get_breadcrumbs_json(self):
        items = []
        for i, crumb in enumerate(self.get_breadcrumbs(), 1):
            items.append({
                "@type": "ListItem",
                "position": i,
                "name": crumb["title"],
                "item": crumb["url"],
            })
        return json.dumps(
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": items,
            },
            ensure_ascii=False,
        )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["categories"] = Category.objects.filter(locale=Locale.get_active()).order_by("order")
        return context

    def get_canonical_url(self):
        if self.canonical_url:
            return self.canonical_url
        return self.full_url

    def get_schema_org(self):
        """Returns dict for schema.org BlogPosting JSON-LD."""
        data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.seo_title or self.title,
            "description": self.search_description or self.intro,
            "url": self.get_canonical_url(),
            "datePublished": self.publication_date.isoformat() if self.publication_date else None,
            "dateModified": self.latest_revision_created_at.isoformat()
            if self.latest_revision_created_at
            else None,
            "author": {
                "@type": "Person",
                "name": str(self.author) if self.author else "",
            },
        }
        if self.main_image:
            data["image"] = self.main_image.get_rendition("original").url
        return json.dumps(data, ensure_ascii=False)
