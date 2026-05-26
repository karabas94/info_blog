from wagtail import hooks

from blog.models import BlogDetailPage


@hooks.register('before_edit_page')
def before_edit_page(request, page):
    """
    запрещает обічномук автору редактировать чужие статьи. суперпользователи могут все
    """
    if request.user.is_superuser:
        return
    if request.user.groups.filter(name__in=["Editors", "Moderators"]).exists():
        return
    if isinstance(page, BlogDetailPage):
        if page.author_id and page.author_id != request.user.id:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied


@hooks.register('before_create_page')
def before_create_page(request, parent_page, page_class):
    """
    Обычный автор может создавать только BlogDetailPage.
    """
    if request.user.is_superuser:
        return
    if request.user.groups.filter(name__in=["Editors", "Moderators"]).exists():
        return
    allowed_page_types = {BlogDetailPage}
    if page_class not in allowed_page_types:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
