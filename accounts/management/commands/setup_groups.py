"""
Management command: создаёт группы Wagtail.

Использование:
  python manage.py setup_groups
"""
from django.core.management.base import BaseCommand
from wagtail.models import GroupPagePermission, Page


class Command(BaseCommand):
    help = "Create user groups with page permissions."

    def handle(self, *args, **options):
        self._create_groups()
        self.stdout.write(self.style.SUCCESS("Groups configured successfully!"))

    def _create_groups(self):
        from django.contrib.auth.models import Group, Permission

        authors_group, created = Group.objects.get_or_create(name="Authors")
        if created:
            self.stdout.write("Created group: Authors")

        root_page = Page.objects.filter(depth=1).first()
        if not root_page:
            self.stdout.write(self.style.WARNING("Root page not found."))
            return

        for codename in ("add_page", "change_page"):
            permission = Permission.objects.get(codename=codename)
            GroupPagePermission.objects.get_or_create(
                group=authors_group,
                page=root_page,
                permission=permission,
            )
            self.stdout.write(f"Permission {codename} assigned to Authors.")
