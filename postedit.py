import re
import sys
from datetime import datetime, timedelta
from post import Blog

from IPython.core.magic import Magics, magics_class, line_magic
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils.path import get_py_filename
from warnings import warn
import parse

blog = Blog()

known_tags = list(blog.get_all_tags().keys())

drafts = []
arg_container = '%==={}===%'
datemarker = ' {}-{}-{} '
timemarker = ' {}:{} '
postformat = '%=== {} {} ===%\n\n{}\n{}\n\n\n' #  for date, tags, title, content
oneminute = timedelta(minutes=1)

def format_post(post):
    f = postformat.format(post.date, ','.join(post.tags), post.title, post.content.replace('<br/>', '\n'))
    return f

def load_ipython_extension(ipython):
    """
    Any module file that define a function named `load_ipython_extension`
    can be loaded via `%load_ext module.path` or be configured to be
    autoloaded by IPython at startup time.
    """
    # You can register the class itself without instantiating it.  IPython will
    # call the default constructor on it.
    ipython.register_magics(MyMagics)

def get_timestamp(string, default=None):
    dt = parse.search(datemarker, string)
    tm = parse.search(timemarker, string)

    now = datetime.now()
    if not default:
        default = now.year, now.month, now.day, now.hour, now.minute

    without = string

    if not dt:
        year, month, day = default[:3]
    else:
        day, month, year = [a.strip() for a in dt.fixed]
        without = without.replace(datemarker.format(*dt.fixed), '')

    if not tm:
        hour, minute = default[3:]
    else:
        hour, minute = [a.strip() for a in tm.fixed]
        without = without.replace(timemarker.format(*tm.fixed), '')

    if len(str(year)) == 2:
        year = '20' + str(year)
    for x in [day, month, hour, minute]:
        if len(str(x)) == 1:
            x = '0' + str(x)

    return [str(x) for x in [year, month, day, hour, minute]], without

def parse_post(post, default=None):
    res = parse.search(arg_container, post)
    headers = res.fixed[0]
    headers = f' {headers} '
    span = res.spans[0]
    body = post[span[1]+5:]  # chop off the header

    try:
        raw_title, body = body.strip().split('\n',1) # already stripped, so we only get the first line.
    except Exception:
        body = False

    if not body or not raw_title:
        return

    # print(len(headers), headers, 1)

    # print(headers)
    timestamp, without = get_timestamp(headers, default=default)
    if without:
        post = without
    # print(timestamp, ' annnnd ', without)

    raw_tags = without.strip()  # what's left of header must be tags

    title = raw_title.title()
    tags = [t.strip().lower() for t in raw_tags.split(',') if t.strip()] if raw_tags else []
    return timestamp, tags, title, body

def split_postlist(postlist):
    posts = []
    allheaders = list(parse.findall(arg_container, postlist))
    for hix in range(len(allheaders)):
        post_ini = allheaders[hix].spans[0][0] - 4  # header length.

        if hix == len(allheaders)-1:
            post_end = len(postlist)
        else:
            post_end = allheaders[hix+1]
            post_end = post_end.spans[0][0] - 4

        # print(post_ini,post_end)
        post = postlist[post_ini:post_end]
        # print(post)
        post = post.strip()
        if post:
            posts.append(post)

    return posts

def parse_post_list(postlist):
    posts = split_postlist(postlist)
    parsed_posts = []
    previous_tstamp = None

    for post in posts:
        post = post.strip()
        parsed = parse_post(post, default=previous_tstamp)
        if not parsed:
            continue
        parsed = list(parsed)
        # timestamp, tags, title, body = parsed
        tstamp = parsed[0]
        # print(tstamp, previous_tstamp)
        if tstamp == previous_tstamp:
            year, month, day, hour, minute = tstamp
            dt = datetime(year=int(year), day=int(day), month=int(month), hour=int(hour), minute=int(minute))
            dt += oneminute
            tstamp = (str(dt.year), str(dt. month), str(dt.day), str(dt.hour), str(dt.minute))
            parsed[0] = tstamp
        previous_tstamp = tstamp  # becomes next default value
        parsed_posts.append(parsed)

    clean = []
    for p in parsed_posts:
        tstamp, tags, title, content = p
        y,m,d,h,mn = tstamp
        day = f'{y}-{m}-{d}'
        hour = f'{h}:{mn}'
        # print(tstamp, day, hour)
        clean.append((title, tags, content, day, hour))

    accepted = []
    rejected = []
    for a in clean:
        print(a)
        if input(f'{a}/n/n/t accept? ') in 'Yesyes':
            post = blog.new(*a)
            accepted.append(a)
        else:
            rejected.append(a)
    return rejected

@magics_class
class MyMagics(Magics):
    """Magics related to code management (loading, saving, editing, ...)."""

    def __init__(self, *args, **kwargs):
        self.saved_date = ''
        super(MyMagics, self).__init__(*args, **kwargs)

    def _edit_post(self, _title='', _tags='', _timestamp=None, _body='', multi=False):

        tstags = ', '.join(_tags) if _tags else ''
        data = """{}\n{}\n{}\n\n""".format(arg_container.format(tstags + ' ' + '{2}-{1}-{0} {3}:{4}'.format(*_timestamp)) ,_title, _body.replace('<br/>', '\n'))

        if multi:
            multi = multi if isinstance(multi, int) else 100
            for i in range(multi):
                data += """{}\n\n\n\n""".format(arg_container.format('  '))

        filename = self.shell.mktempfile(data)

        print('Editing...', end=' ')
        sys.stdout.flush()
        try:
            self.shell.hooks.editor(filename)
        except Exception:
            warn('Could not open editor')
            return

        print('done.')

        with open(filename, 'r') as f:
            data = f.read()

        data = data.strip()
        return parse_post_list(data)

    @skip_doctest
    @line_magic
    def post(self, parameter_s='', last_call=['', '']):
        """Bring up an editor and make a post out of the parsed input.
        if a timestamp is provided as argument, it will attached as default date to all future posts. Else, date will default to previous post's date."""

        multi = 'multi' in parameter_s
        if multi:
            n = ''
            try:
                multi, n = parameter_s.split(' ')
            except Exception:
                pass
            if n.strip():
                multi = int(n)
            else:
                multi = 100

        date, without = get_timestamp(parameter_s)

        output = self._edit_post(_timestamp=date, multi=multi)

        if not output:
            return

        processed = []
        X = 0
        for out in output:
            X += 1
            print('\nPost %d' % X)
            print(out)
            timestamp, tags, title, body = out

            clean_tags = []
            for tag in tags:
                found = False
                for ktag in known_tags:
                    if ktag == tag or ktag.lower() == tag:
                        clean_tags.append(ktag)
                        found = True
                    if found:
                        break
                if not found:
                    ktagsmap = {known_tags.index(t) : t for t in known_tags}
                    print('tag', tag, 'not known.')
                    print('known tags:')
                    for t,tg in ktagsmap.items():
                        print('\t', t, '\t', tg)

                    print()
                    confirm = False
                    candidate = None
                    while not confirm:
                        i = input('choose one, or press enter to create a new tag >>> ').strip()
                        if not i:
                            candidate = tag
                        elif i in known_tags:
                            candidate = i
                        else:
                            try:
                                i = int(i)
                                candidate = ktagsmap[i]
                            except Exception:
                                candidate = None
                                print('Nope. Try again.')

                        if candidate:
                            print('tagging with [{}]'.format(candidate))
                            i = input('confirm? (default:y)')
                            if i is None or i in 'Yesyes':
                                print('confirmed')
                                confirm = True
                                if candidate not in known_tags:
                                    known_tags.append(candidate)
                                    clean_tags.append(candidate)

            # print(clean_tags)
            body = body.strip().replace('\n', '<br/>')

            print(title, tags if tags else '[no tags]', timestamp, body, sep=', ')
            processed.append((title, tags, timestamp, body))

        return processed
