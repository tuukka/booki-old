from django import template
from django.template.loader import render_to_string
import re

register = template.Library()

###############################################################################################################

class FormatBookiNode(template.Node):
    def __init__(self, booki_data):
        self.booki_data = template.Variable(booki_data)

    def render(self, context):
        chapter =  self.booki_data.resolve(context)

        if chapter.content.find('##') == -1:
            return chapter.content

        lns = []

        for ln in chapter.content.split("\n"):
            macro_re = re.compile(r'##([\w\_]+)(\{[^\}]*\})?##')

            while True:
                mtch = macro_re.search(ln)
                
                if mtch:
                    try:
                        t = template.loader.get_template_from_string('{%% load booki_tags %%} {%% booki_%s book args %%}' % (mtch.group(1).lower(),))
                        con = t.render(template.Context({"content": chapter, 
                                                         "book": chapter.version.book,
                                                         "args": mtch.group(2)}))
                    except template.TemplateSyntaxError:
                        con = '<span style="background-color: red; color: white; font-weight: bold">ERROR WITH MACRO %s</span>' % (mtch.group(1).lower(), )

                    ln = ln[:mtch.start()]+con+ln[mtch.end():]
                else:
                    break

            lns.append(ln)

        return "\n".join(lns)

@register.tag(name="booki_format")
def booki_format(parser, token):
    try:
        tag_name, booki_data = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one argument" % token.contents.split()[0]

    return FormatBookiNode(booki_data)



###############################################################################################################

class FormatAuthorsNode(template.Node):
    def __init__(self, book, args):
        self.book = template.Variable(book)
        self.args = template.Variable(args)

    def render(self, context):
        book =  self.book.resolve(context)

        t = template.loader.get_template('authors.html')

        from booki.editor import models
        from django.contrib.auth import models as auth_models

        chapters = []

        # this should be book version, not book

        for chapter in models.BookToc.objects.filter(book=book).order_by("-weight"):
            if not chapter: continue
            if not chapter.chapter: continue

            authors = {}

            for us_id in models.ChapterHistory.objects.filter(chapter=chapter.chapter).distinct():
                if not us_id: continue

                usr = auth_models.User.objects.get(id=us_id.user.id)

                modified_year = us_id.modified.strftime('%Y')

                if authors.has_key(usr.username):
                    _years = authors[usr.username][1]

                    if modified_year not in _years:
                        authors[usr.username][1].append(modified_year)

                else:
                    authors[usr.username] = [usr, [modified_year]]

            chapters.append({"authors": authors.values(), 
                             "name": chapter.chapter.title})

        copyrightDescription = self.args.resolve(context) or ''

        return t.render(template.Context({'chapters': chapters, 
                                          "copyright": copyrightDescription[1:-1]}, 
                                         autoescape=context.autoescape))


@register.tag(name="booki_authors")
def booki_authors(parser, token):
    """
    Django Tag. Shows list of authors for this book. Accepts one argument, book. Reads template authors.html.
    Needs a lot of work.

        {% load booki_tags %}
        {% booki_authors book %}
    """

    try:
        tag_name, book, args = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly two argument" % token.contents.split()[0]

    return FormatAuthorsNode(book, args)
        
