from wagtail.blocks import (
    CharBlock,
    RichTextBlock,
    StreamBlock,
    StructBlock,
    TextBlock,
    URLBlock,
)
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock


class CaptionedImageBlock(StructBlock):
    image = ImageChooserBlock(required=True)
    caption = CharBlock(required=False)
    attribution = CharBlock(required=False)

    class Meta:
        icon = "image"
        label = "Image"
        template = "blog/blocks/captioned_image.html"


class QuoteBlock(StructBlock):
    text = TextBlock(required=True)
    attribution = CharBlock(required=False)

    class Meta:
        icon = "openquote"
        label = "Quote"
        template = "blog/blocks/quote.html"


class BlogBodyBlock(StreamBlock):
    richtext = RichTextBlock(
        features=["h2", "h3", "bold", "italic", "link", "ol", "ul", "blockquote", "image"],
    )
    image = CaptionedImageBlock()
    quote = QuoteBlock()
    embed = EmbedBlock(max_width=800, max_height=400)
