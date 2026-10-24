"""Static page contract: links/assets/shared config/admin guard; stdlib only.
Run `python frontend/tests/check_pages.py` from repository root.
Does not replace a rendered browser or an Aiven database acceptance test.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
        self.scripts = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'script' and attrs.get('src'):
            self.scripts.append(attrs['src'])
        attribute = ('src' if tag in ('script', 'img') else 'href'
                     if tag in ('a', 'link') else None)
        if attribute and attrs.get(attribute):
            self.resources.append((tag, attrs[attribute]))


def inspect_page(path):
    parsed = Page()
    parsed.feed(path.read_text(encoding='utf8'))
    problems = []
    for tag, resource in parsed.resources:
        target = urlsplit(resource)
        if target.scheme or target.netloc or not target.path or target.path.startswith('/'):
            continue
        if tag == 'a' and not target.path.endswith('.html'):
            continue
        if not (path.parent / target.path).resolve().is_file():
            problems.append(f'{tag}: broken local resource {resource}')
    scripts = [s for s in parsed.scripts if urlsplit(s).path.endswith('.js') and not s.startswith('http')]
    if not scripts or not scripts[0].endswith('config.js'):
        problems.append('shared config.js must precede local scripts')
    if 'admin' in path.parts and (len(scripts) < 2 or not scripts[1].endswith('admin-auth.js')):
        problems.append('missing early admin role guard')
    if 'footer-placeholder' in parsed.ids and not any(s.endswith('footer.js') for s in scripts):
        problems.append('footer placeholder must load shared footer.js')
    if path.name == 'login.html':
        for field in ('loginForm','registerForm','regUsername','regEmail','regPassword','authMessage'):
            if field not in parsed.ids:
                problems.append(f'missing authentication form field {field}')
    return problems


def main():
    pages = sorted(p for p in ROOT.rglob('*.html') if 'components' not in p.parts)
    errors = [(p.relative_to(ROOT), issue) for p in pages for issue in inspect_page(p)]
    for page, message in errors:
        print('ERROR:', page, message)
    assert not errors, f'{len(errors)} broken page contract(s)'
    print(f'PASS: {len(pages)} customer and admin pages: paths, early API config, admin guard, and shared components')


if __name__ == '__main__':
    main()
