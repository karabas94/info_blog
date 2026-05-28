import json
import copy

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


from .blocks import BlogBodyBlock


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
    parent_page_types = []
    subpage_types = []
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
        context["breadcrumbs"] = self.get_breadcrumbs()
        return context

    def get_breadcrumbs(self):
        return [
            {
                "title": "Home",
                "url": self.get_site().root_page.full_url,
            },
            {
                "title": self.title,
                "url": self.full_url,
            },
        ]


# Blog Category Page

class BlogCategoryPage(AutoSlugMixin, RoutablePageMixin, Page):
    """Page for a single category listing."""

    parent_page_types = ["home.HomePage"]
    subpage_types = ["blog.BlogDetailPage"]

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
            .child_of(self)
            .filter(locale=self.locale)
            .select_related("author", "main_image")
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
        context["breadcrumbs"] = self.get_breadcrumbs()
        return context

    def get_breadcrumbs(self):
        """Returns list of {title, url} for breadcrumbs."""
        crumbs = []

        site = self.get_site()

        if site and site.root_page:
            crumbs.append(
                {
                    "title": "Home",
                    "url": site.root_page.full_url,
                }
            )

        crumbs.append(
            {
                "title": self.title,
                "url": self.full_url,
            }
        )

        return crumbs


# Blog Detail Page (Article)
class BlogDetailPage(AutoSlugMixin, Page):
    """Blog article page."""

    parent_page_types = ["blog.BlogCategoryPage"]
    subpage_types = []

    # Content
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

    # Оставляем поле в базе, но в админке не показываем.
    # Оно будет автоматически подтягиваться из родительской BlogCategoryPage.
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

    create_ua_draft = models.BooleanField(
        _("create Ukrainian draft"),
        default=False,
        help_text=_(
            "Create a Ukrainian draft copy after saving this Russian article. "
            "The Ukrainian category page must already exist."
        ),
    )

    # Panels
    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("author"),
                FieldPanel("publication_date"),
                FieldPanel("create_ua_draft"),
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

    def get_category_page(self):
        """
        Возвращает родительскую страницу категории.

        Home
        └── BlogCategoryPage
            └── BlogDetailPage
        """
        try:
            parent = self.get_parent()
        except Exception:
            return None

        if not parent:
            return None

        parent = parent.specific

        if isinstance(parent, BlogCategoryPage):
            return parent

        return None

    def get_category_name(self):
        """
        Возвращает название категории для вывода на сайте.
        """
        category_page = self.get_category_page()

        if not category_page:
            return ""

        if category_page.category:
            return category_page.category.name

        return category_page.title

    def sync_category_from_parent(self):
        """
        Автоматически записывает Category snippet из родительской BlogCategoryPage
        в поле category самого поста.
        """
        category_page = self.get_category_page()

        if category_page and category_page.category_id:
            self.category = category_page.category

    def clean(self):
        super().clean()
        self.sync_category_from_parent()

    def get_breadcrumbs(self):
        """Returns list of {title, url} for breadcrumbs."""
        crumbs = []

        site = self.get_site()

        if site and site.root_page:
            crumbs.append(
                {
                    "title": "Home",
                    "url": site.root_page.full_url,
                }
            )

        category_page = self.get_category_page()

        if category_page:
            crumbs.append(
                {
                    "title": self.get_category_name(),
                    "url": category_page.full_url,
                }
            )

        crumbs.append(
            {
                "title": self.title,
                "url": self.full_url,
            }
        )

        return crumbs

    def get_breadcrumbs_json(self):
        items = []

        for i, crumb in enumerate(self.get_breadcrumbs(), 1):
            items.append(
                {
                    "@type": "ListItem",
                    "position": i,
                    "name": crumb["title"],
                    "item": crumb["url"],
                }
            )

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

        context["categories"] = Category.objects.filter(
            locale=Locale.get_active()
        ).order_by("order")

        context["category_page"] = self.get_category_page()
        context["category_name"] = self.get_category_name()
        context["breadcrumbs"] = self.get_breadcrumbs()

        return context

    def get_canonical_url(self):
        if self.canonical_url:
            return self.canonical_url

        return self.full_url

    def get_schema_org(self):
        """Returns schema.org BlogPosting JSON-LD."""
        data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.seo_title or self.title,
            "description": self.search_description or self.intro,
            "url": self.get_canonical_url(),
            "datePublished": self.publication_date.isoformat()
            if self.publication_date
            else None,
            "dateModified": self.latest_revision_created_at.isoformat()
            if self.latest_revision_created_at
            else None,
            "author": {
                "@type": "Person",
                "name": str(self.author) if self.author else "",
            },
        }

        category_name = self.get_category_name()

        if category_name:
            data["articleSection"] = category_name

        if self.main_image:
            data["image"] = self.main_image.get_rendition("original").url

        return json.dumps(data, ensure_ascii=False)

    def create_ua_translation_draft(self):
        """
        Создаёт или обновляет украинский черновик этой статьи.

        Работает если:
        - текущая статья на русском;
        - локаль ua существует;
        - украинская категория уже существует.
        """
        if self.locale.language_code != "ru":
            return None

        ua_locale = Locale.objects.filter(language_code="ua").first()

        if not ua_locale:
            return None

        # Берём актуальную сохранённую ревизию, чтобы body точно был с данными.
        try:
            source_page = self.get_latest_revision_as_object().specific
        except Exception:
            source_page = self

        # Если UA-перевод уже есть — обновляем его, если он ещё черновик.
        if self.has_translation(ua_locale):
            ua_page = self.get_translation(ua_locale).specific

            # Если украинская версия уже опубликована, не перезаписываем её.
            if ua_page.live:
                return ua_page
        else:
            try:
                ua_page = source_page.copy_for_translation(
                    ua_locale,
                    copy_parents=False,
                    alias=False,
                    exclude_fields=["create_ua_draft"],
                )
            except Exception:
                return None

            ua_page = ua_page.specific

        # Копируем основные поля вручную
        ua_page.title = source_page.title
        ua_page.slug = source_page.slug
        ua_page.intro = source_page.intro
        ua_page.main_image = source_page.main_image
        ua_page.author = source_page.author
        ua_page.publication_date = source_page.publication_date
        ua_page.og_image = source_page.og_image

        # ВАЖНО: StreamField копируем через raw_data
        if source_page.body:
            ua_page.body = copy.deepcopy(source_page.body.raw_data)

        # canonical лучше не копировать
        ua_page.canonical_url = ""

        # На украинской копии галочка не нужна
        ua_page.create_ua_draft = False

        ua_page.sync_category_from_parent()

        ua_page.save()
        ua_page.save_revision()

        return ua_page

    def save(self, *args, **kwargs):
        self.sync_category_from_parent()
        super().save(*args, **kwargs)
