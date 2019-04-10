
import os
import shutil
import errno
import string
from settings import base_post_folder, base_tag_folder, tags_desc, tags_titles, post_layout, tag_layout, dblocation
from collections import Counter

curdir = os.path.dirname(os.path.realpath(__file__))
db_address = os.path.join(curdir, 'poetrydb.json')

def slugify(tag):
    if isinstance(tag, list):
        return [slugify(a) for a in tag]
    for p in string.punctuation+' ':
        tag = tag.replace(p,'-')
    tag = tag.lower()
    return tag


class Post:
    def __init__(self, content=None, tags=None, date=None, hour=None, title=None, id=None, location=None, blog=None):
        if id is None:
            raise ValueError()
        if not location:
            location = base_post_folder

        self.id = id
        self.date = date
        self.year = self.date[:4]
        self.month = self.date[5:7]
        self.hour = hour
        self.content = content
        self.title = title
        self.tags = tags
        self.location = location
        self.blog = blog

    def __str__(self):
        return '<Post {} :: {} of {}>'.format(self.id, self.title, self.date)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash((self.title, self.date, self.hour))

    def pprint(self):
        print(self.formatted())

    def delete(self):
        self.blog.delete(self)

    def formatted(self):
        tgs = '['
        for tag in self.tags:
            tgs += tag
            tgs += ','
        tgs += ']'
        return post_layout.format(self.title, tgs,self.date + ' ' + self.hour, self.content)

    def display(self):
        print(self.formatted())

    def generate_filename(self):
        title = self.title.lower().strip()
        for a in list(title):
            if a not in string.ascii_letters:
                title = title.replace(a,'')
        title = title[:30]
        return title

    def get_path(self):

        base = self.location
        y,m,d = self.date.split('-')
        pth = f'{base}{y}/{m}/'
        title = self.generate_filename()
        return f'{pth}{self.date}-{title}.md'

    def to_md(self):

        fullpth = self.get_path()
        print('creating', fullpth)
        if not os.path.exists(os.path.dirname(fullpth)):
            os.makedirs(os.path.dirname(fullpth))

        with open(fullpth, 'w+') as f:
            f.write(self.formatted())


class Blog:
    def __init__(self):
        self.all = {}
        self.load()

    def __str__(self):
        base = f"Blog: {len(self.all)} posts. Latest:\n"
        self.resort()
        m = max(self.all.keys())
        for i in range(10):
            base += '\t' + str(self.all[m]) + '\n'
            m -= 1
        return base

    def __repr__(self):
        return str(self)

    def __getitem__(self, item):
        return self.all.get(item)

    def __iter__(self):
        return (i for i in self.all.values())

    def get_all_tags(self):
        alltags = Counter()
        for p in self.all.values():
            alltags.update(p.tags)
        return dict(alltags)

    def generate_tag_pages(self):
        print('deleting existing tag pages...')
        base = base_tag_folder
        self.clear_dir(base=base)

        alltags = self.get_all_tags()

        ordering = sorted(alltags.keys(), key=lambda x: alltags[x], reverse=True)

        for tag in alltags:
            order = ordering.index(tag) + 1
            slug = slugify(tag)
            title = tags_titles.get(tag, tag)
            desc = tags_desc.get(tag,'')
            md = tag_layout.format(title, slug, order, desc)

            with open(base + slug + '.md', 'w+') as f:
                f.write(md)

            print('generated page for', tag)

    def new(self, title, tags, content, date, hour, idn=None):
        if not idn:
            idn = max(self.all.keys()) + 1
        newp = Post(title=title, tags=tags, content=content, date=date, hour=hour, id=idn)
        self.all[newp.id] = newp
        newp.blog = self
        return newp

    def delete(self, post):
        del self.all[post.id]

    def save(self):
        d = {}
        for id, post in self.all.items():

            if not post.content:
                print('skipped', id)
                continue

            d[id] = {'date' : post.date,
                'hour' : post.hour,
                'content': post.content,
                'title': post.title,
                'location': post.location,
                'tags': post.tags}

        import json
        with open(db_address, 'w') as f:
            f.write(json.dumps(d))
        print(f'blog saved: {len(d)} posts.')

    def search_by_title(self, kwd, exact=False):
        if exact:
            return [a for a in self.all.values() if kwd.lower() == a.title.lower()]
        return [a for a in self.all.values() if kwd.lower() in a.title.lower()]

    def search_by_content(self, kwd):
        return [a for a in self.all.values() if kwd.lower() in a.content.lower()]

    def search_by_tag(self, kwd):
        return [a for a in self.all.values() if kwd.lower() in a.tags]

    def get_id(self, kwd):
        kwd = str(kwd)
        return self.all.get(kwd, None)

    def get_duplicates(self, thresh = 5):
        crop = lambda x,y: x.content[:y]
        out = []
        for apost in self.all.values():
            for bpost in self.all.values():
                if apost is bpost:
                    continue
                if apost.title == bpost.title and crop(apost,thresh) == crop(bpost, thresh):
                    if apost in out or bpost in out:
                        continue
                    print(apost, bpost)
                    if apost.id < bpost.id:
                        out.append(apost)
                    else:
                        out.append(bpost)

        return out

    def resort(self):
        a = list(self.all.values())
        b = sorted(a, key=lambda x: x.date+x.hour)
        self.all = {}
        i = 1
        for x in b:
            self.all[i] = x
            x.id = i
            i += 1

    def load(self):
        self.all = {}
        import json
        print('opening', dblocation)
        with open(dblocation, 'r') as f:
            data = json.loads(f.read())

        for d,v in data.items():
            p = Post(**v, id=int(d), blog=self)
            # initialises new post
            self.all[int(d)] = p
        print('loaded {} posts'.format(len(self.all)))

    def regen(self, n=0):
        self.clear_dir()
        self.to_md(n)

    def to_md(self, n=0):
        print('dumping files...')
        allposts = [a[1] for a in sorted(list(self.all.items()), key=lambda x: x[0], reverse=True)]

        if n:
            print('prepping to dump {} files...'.format(n))
            allposts = allposts[:n]

        for p in allposts:
            p.to_md()

        print('all done')

    def clear_dir(self, base=None):
        print('deleting all files...')
        base = base or base_post_folder
        shutil.rmtree(base)
        os.makedirs(base)

        print('clear')
