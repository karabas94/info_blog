"""
Management command: заполняет блог тестовыми данными под текущую структуру.

Новая структура:
  HomePage RU
  └── BlogCategoryPage RU
      └── BlogDetailPage RU

  HomePage UA
  └── BlogCategoryPage UA
      └── BlogDetailPage UA

Использование:
  python manage.py seed_blog
  python manage.py seed_blog --clear
  python manage.py seed_blog --posts-per-category 100

По умолчанию создаёт:
  - 5 RU категорий x 2000 постов = 10 000 RU постов
  - 5 UA категорий x 2000 постов = 10 000 UA постов
  - всего 20 000 постов

Важно:
  - BlogIndexPage НЕ создаётся.
  - Посты создаются внутри BlogCategoryPage.
  - Категории создаются внутри HomePage соответствующего языка.
"""

import random
import uuid
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from PIL import Image as PILImage, ImageDraw
from slugify import slugify as unicode_slugify
from wagtail.images.models import Image as WagtailImage
from wagtail.models import Locale, Site

from blog.models import BlogCategoryPage, BlogDetailPage, Category
from home.models import HomePage


User = get_user_model()

FAKERS = {
    "ru": Faker("ru_RU"),
    "ua": Faker("uk_UA"),
}

CATEGORIES_BY_LANGUAGE = {
    "ru": [
        {"name": "Категория 1", "slug": "kategoriya-1", "description": "Тестовые материалы первой категории.", "order": 1, "color": "#4f86e8"},
        {"name": "Категория 2", "slug": "kategoriya-2", "description": "Тестовые материалы второй категории.", "order": 2, "color": "#e9574f"},
        {"name": "Категория 3", "slug": "kategoriya-3", "description": "Тестовые материалы третьей категории.", "order": 3, "color": "#2ecc71"},
        {"name": "Категория 4", "slug": "kategoriya-4", "description": "Тестовые материалы четвёртой категории.", "order": 4, "color": "#9b59b6"},
        {"name": "Категория 5", "slug": "kategoriya-5", "description": "Тестовые материалы пятой категории.", "order": 5, "color": "#e67e22"},
    ],
    "ua": [
        {"name": "Категорія 1", "slug": "kategoriya-1", "description": "Тестові матеріали першої категорії.", "order": 1, "color": "#4f86e8"},
        {"name": "Категорія 2", "slug": "kategoriya-2", "description": "Тестові матеріали другої категорії.", "order": 2, "color": "#e9574f"},
        {"name": "Категорія 3", "slug": "kategoriya-3", "description": "Тестові матеріали третьої категорії.", "order": 3, "color": "#2ecc71"},
        {"name": "Категорія 4", "slug": "kategoriya-4", "description": "Тестові матеріали четвертої категорії.", "order": 4, "color": "#9b59b6"},
        {"name": "Категорія 5", "slug": "kategoriya-5", "description": "Тестові матеріали пʼятої категорії.", "order": 5, "color": "#e67e22"},
    ],
}

AUTHOR_DATA = [
    {"username": "author1", "email": "author1@example.com", "first_name": "Author", "last_name": "One"},
    {"username": "author2", "email": "author2@example.com", "first_name": "Author", "last_name": "Two"},
]

POSTS_PER_CATEGORY_DEFAULT = 2000
BATCH_SIZE = 500

SEED_AUTHOR_USERNAMES = [author["username"] for author in AUTHOR_DATA]
ALL_CATEGORY_SLUGS = sorted({category["slug"] for categories in CATEGORIES_BY_LANGUAGE.values() for category in categories})

TITLE_PATTERNS = {
    "ru": [
        "{topic}: что важно знать в 2026 году",
        "Как разобраться в теме «{topic}» без лишней теории",
        "Практическое руководство: {topic}",
        "Главные ошибки в теме «{topic}» и как их избежать",
        "Пошаговый разбор: {topic}",
        "Почему {topic} важна для современного проекта",
    ],
    "ua": [
        "{topic}: що важливо знати у 2026 році",
        "Як розібратися в темі «{topic}» без зайвої теорії",
        "Практичний посібник: {topic}",
        "Головні помилки в темі «{topic}» і як їх уникнути",
        "Покроковий розбір: {topic}",
        "Чому {topic} важлива для сучасного проєкту",
    ],
}


class Command(BaseCommand):
    help = "Seed blog with 10k RU posts and 10k UA posts without BlogIndexPage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete seeded test data before creating new data.",
        )
        parser.add_argument(
            "--posts-per-category",
            type=int,
            default=POSTS_PER_CATEGORY_DEFAULT,
            help=(
                "How many posts to create per category for each language. "
                f"Default: {POSTS_PER_CATEGORY_DEFAULT}."
            ),
        )

    def handle(self, *args, **options):
        posts_per_category = options["posts_per_category"]

        if posts_per_category < 0:
            self.stdout.write(self.style.ERROR("--posts-per-category must be >= 0"))
            return

        if options["clear"]:
            self._clear_data()

        authors = self._get_or_create_authors()
        images_by_slug = self._get_or_create_images()

        for language_code in ("ru", "ua"):
            locale = self._get_or_create_locale(language_code)
            home_page = self._get_or_create_home_page(locale)

            self.stdout.write(self.style.WARNING(f"Seeding {language_code.upper()} branch under: {home_page.title}"))

            categories = self._get_or_create_categories(locale=locale, images_by_slug=images_by_slug)
            category_pages = self._get_or_create_category_pages(home_page=home_page, categories=categories, locale=locale)
            self._create_posts(category_pages=category_pages, authors=authors, images_by_slug=images_by_slug, locale=locale, posts_per_category=posts_per_category)

        self.stdout.write(self.style.SUCCESS("Seeding complete!"))

    def _get_or_create_locale(self, language_code):
        locale, _ = Locale.objects.get_or_create(language_code=language_code)
        return locale

    def _get_or_create_home_page(self, locale):
        """
        Находит или создаёт HomePage нужной локали.
        Если HomePage уже есть — используем её.
        Если нет — создаём рядом с текущим site.root_page.
        """
        existing = HomePage.objects.filter(locale=locale).first()
        if existing:
            return existing.specific

        site = Site.objects.filter(is_default_site=True).first()
        if not site:
            self.stdout.write(self.style.ERROR("No default site found."))
            raise SystemExit(1)

        site_root = site.root_page.specific

        if locale.language_code != "ru":
            ru_locale = Locale.objects.filter(language_code="ru").first()
            ru_home = HomePage.objects.filter(locale=ru_locale).first() if ru_locale else None

            if ru_home:
                try:
                    translated_home = ru_home.copy_for_translation(locale, copy_parents=False, alias=False).specific
                    translated_home.title = "Головна"
                    translated_home.slug = "golovna"
                    translated_home.live = True
                    translated_home.first_published_at = timezone.now()
                    translated_home.save()
                    self.stdout.write(self.style.SUCCESS(f"Created translated HomePage for {locale.language_code}."))
                    return translated_home
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"Could not copy HomePage translation: {exc}"))

        parent = site.root_page
        if isinstance(site_root, HomePage):
            parent = site.root_page.get_parent()

        title = "Home" if locale.language_code == "ru" else "Головна"
        slug = "home" if locale.language_code == "ru" else "golovna"

        home_page = HomePage(title=title, slug=slug, locale=locale, live=True, first_published_at=timezone.now())
        parent.add_child(instance=home_page)
        self.stdout.write(self.style.SUCCESS(f"Created HomePage for {locale.language_code}: {title}"))
        return home_page

    def _get_or_create_authors(self):
        authors = []

        for data in AUTHOR_DATA:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "is_staff": True,
                },
            )

            changed = False
            for field in ("email", "first_name", "last_name"):
                if getattr(user, field) != data[field]:
                    setattr(user, field, data[field])
                    changed = True

            if not user.is_staff:
                user.is_staff = True
                changed = True

            if created:
                user.set_password("author_dev_password")
                changed = True
                self.stdout.write(f"Created author: {user.username}")

            if changed:
                user.save()

            authors.append(user)

        return authors

    def _create_image_file(self, title, color, filename):
        """Создаёт PNG-плейсхолдер, чтобы Wagtail renditions работали стабильно."""
        width = 1200
        height = 800
        image = PILImage.new("RGB", (width, height), color=color)
        draw = ImageDraw.Draw(image)
        text = filename.replace(".png", "")
        draw.text((width // 2 - 100, height // 2), text, fill="white")

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return ImageFile(buffer, name=filename)

    def _get_or_create_images(self):
        """Создаёт 5 общих тестовых картинок для RU и UA."""
        images_by_slug = {}

        for category_data in CATEGORIES_BY_LANGUAGE["ru"]:
            title = f"Seed {category_data['name']}"
            slug = category_data["slug"]
            filename = f"{slug}.png"

            existing = WagtailImage.objects.filter(title=title).first()
            if existing:
                images_by_slug[slug] = existing
                self.stdout.write(f"Image exists: {title}")
                continue

            image_file = self._create_image_file(title=title, color=category_data["color"], filename=filename)
            image = WagtailImage(title=title)
            image.file.save(filename, image_file, save=True)
            images_by_slug[slug] = image
            self.stdout.write(f"Created image: {title}")

        return images_by_slug

    def _get_or_create_categories(self, locale, images_by_slug):
        """Создаёт Category snippets для конкретного языка."""
        categories = []
        language_code = locale.language_code

        for data in CATEGORIES_BY_LANGUAGE[language_code]:
            category, created = Category.objects.get_or_create(
                slug=data["slug"],
                locale=locale,
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "image": images_by_slug.get(data["slug"]),
                    "order": data["order"],
                },
            )

            category.name = data["name"]
            category.description = data["description"]
            category.image = images_by_slug.get(data["slug"])
            category.order = data["order"]
            category.save()
            categories.append(category)

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} {language_code.upper()} category snippet: {category.name}")

        return categories

    def _get_or_create_category_pages(self, home_page, categories, locale):
        """Создаёт BlogCategoryPage внутри HomePage конкретного языка."""
        category_pages = []

        for category in categories:
            category_page = (
                BlogCategoryPage.objects.child_of(home_page)
                .filter(locale=locale, slug=category.slug)
                .first()
            )

            if category_page:
                category_page = category_page.specific
                category_page.title = category.name
                category_page.intro = category.description
                category_page.category = category
                category_page.seo_title = category.name
                category_page.search_description = category.description[:255]
                category_page.live = True
                category_page.save()
                category_pages.append(category_page)
                self.stdout.write(f"Category page exists: {locale.language_code.upper()} / {category_page.title}")
                continue

            category_page = BlogCategoryPage(
                title=category.name,
                slug=category.slug,
                intro=category.description,
                category=category,
                seo_title=category.name,
                search_description=category.description[:255],
                locale=locale,
                live=True,
                show_in_menus=True,
                first_published_at=timezone.now(),
            )

            home_page.add_child(instance=category_page)
            category_pages.append(category_page)
            self.stdout.write(f"Created category page: {locale.language_code.upper()} / {category_page.title}")

        return category_pages

    def _create_posts(self, category_pages, authors, images_by_slug, locale, posts_per_category):
        language_code = locale.language_code
        fake = FAKERS[language_code]
        total_needed = posts_per_category * len(category_pages)

        existing_seeded_posts = BlogDetailPage.objects.filter(
            locale=locale,
            author__username__in=SEED_AUTHOR_USERNAMES,
        ).count()

        if existing_seeded_posts >= total_needed:
            self.stdout.write(f"{language_code.upper()} already has {existing_seeded_posts} seeded posts. Skipping. Use --clear to reset.")
            return

        self.stdout.write(f"Creating up to {total_needed} {language_code.upper()} seeded posts...")
        now = timezone.now()
        created_count = 0

        for category_page in category_pages:
            category_page = category_page.specific
            category = category_page.category
            image = images_by_slug.get(category.slug)

            existing_in_category = (
                BlogDetailPage.objects.child_of(category_page)
                .filter(locale=locale, author__username__in=SEED_AUTHOR_USERNAMES)
                .count()
            )
            to_create = posts_per_category - existing_in_category

            if to_create <= 0:
                self.stdout.write(f"{language_code.upper()} / {category_page.title} already has enough posts.")
                continue

            self.stdout.write(f"Creating {to_create} posts for {language_code.upper()} / {category_page.title}...")

            for index in range(to_create):
                publication_date = now - timedelta(days=random.randint(0, 730), hours=random.randint(0, 23), minutes=random.randint(0, 59))
                title = self._make_title(topic=category.name, language_code=language_code, fake=fake)
                slug = self._make_unique_slug(parent_page=category_page, title=title, fallback=f"{language_code}-{category.slug}-post-{index + 1}")
                intro = fake.paragraph(nb_sentences=2)[:500]
                body = self._make_body(topic=category.name, language_code=language_code, fake=fake)
                author = random.choice(authors)

                post = BlogDetailPage(
                    title=title,
                    slug=slug,
                    intro=intro,
                    body=body,
                    category=category,
                    author=author,
                    owner=author,
                    publication_date=publication_date,
                    main_image=image,
                    og_image=image,
                    seo_title=title[:255],
                    search_description=intro[:255],
                    locale=locale,
                    live=True,
                    first_published_at=publication_date,
                    show_in_menus=False,
                )

                if hasattr(post, "create_ua_draft"):
                    post.create_ua_draft = False

                category_page.add_child(instance=post)
                created_count += 1

                if created_count % BATCH_SIZE == 0:
                    self.stdout.write(f"{language_code.upper()} ... {created_count} posts created")

        self.stdout.write(self.style.SUCCESS(f"{language_code.upper()} total posts created: {created_count}"))

    def _make_title(self, topic, language_code, fake):
        pattern = random.choice(TITLE_PATTERNS[language_code])
        suffix = fake.sentence(nb_words=random.randint(3, 6)).rstrip(".")
        return f"{pattern.format(topic=topic)}: {suffix}"[:255]

    def _make_unique_slug(self, parent_page, title, fallback):
        base_slug = unicode_slugify(title, allow_unicode=False)[:180]
        if not base_slug:
            base_slug = unicode_slugify(fallback, allow_unicode=False)

        slug_candidate = base_slug
        counter = 1

        while BlogDetailPage.objects.child_of(parent_page).filter(slug=slug_candidate).exists():
            slug_candidate = f"{base_slug}-{counter}"
            counter += 1

        return slug_candidate

    def _make_body(self, topic, language_code, fake):
        if language_code == "ua":
            intro = f"{topic} — це тема, де важливо дивитися не тільки на теорію, але й на практичне застосування в реальних проєктах."
            outro = "Головна рекомендація — перевіряти гіпотези на практиці, порівнювати результати та регулярно оновлювати підхід."
        else:
            intro = f"{topic} — это тема, где важно смотреть не только на теорию, но и на практическое применение в реальных проектах."
            outro = "Главная рекомендация — проверять гипотезы на практике, сравнивать результаты и регулярно обновлять подход."

        paragraphs = [f"<p>{intro}</p>"]

        for _ in range(random.randint(3, 6)):
            paragraphs.append(f"<p>{fake.paragraph(nb_sentences=random.randint(3, 5))}</p>")

        paragraphs.append(f"<p>{outro}</p>")

        return [
            {
                "type": "richtext",
                "value": "".join(paragraphs),
                "id": str(uuid.uuid4()),
            }
        ]

    def _clear_data(self):
        """
        Удаляет seeded-данные:
        - посты author1/author2
        - тестовые страницы категорий с нашими slug
        - тестовые Category snippets с нашими slug
        """
        self.stdout.write(self.style.WARNING("Clearing seeded data..."))

        posts = BlogDetailPage.objects.filter(author__username__in=SEED_AUTHOR_USERNAMES)
        posts_count = posts.count()

        for post in posts.specific().iterator(chunk_size=100):
            post.delete()

        self.stdout.write(f"Deleted seeded posts: {posts_count}")

        category_pages = BlogCategoryPage.objects.filter(slug__in=ALL_CATEGORY_SLUGS)
        category_pages_count = category_pages.count()

        for page in category_pages.specific().iterator(chunk_size=50):
            page.delete()

        self.stdout.write(f"Deleted seeded category pages: {category_pages_count}")

        categories_deleted, _ = Category.objects.filter(slug__in=ALL_CATEGORY_SLUGS).delete()
        self.stdout.write(f"Deleted seeded category snippets: {categories_deleted}")
        self.stdout.write(self.style.SUCCESS("Cleared."))
