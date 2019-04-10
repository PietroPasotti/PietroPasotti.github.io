import re
import sys
import os
import shlex, subprocess
from datetime import datetime, timedelta
from post import Blog
import argparse
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.testing.skipdoctest import skip_doctest
from IPython.utils.path import get_py_filename
from warnings import warn
import parse
from settings import oridir, workingdir, draftsdir, builddir, outputdir, draftname, arg_container, datemarker, timemarker, postformat, gempath, plugindir, sourcedir, layoutdir, gitusername, gitpwd


drafts = []

oneminute = timedelta(minutes=1)

blog = None

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
    dt = parse.search('{:d}-{:d}-{:d}', string)
    tm = parse.search('{:d}:{:d}', string)

    now = datetime.now()
    if not default:
        default = now.year, now.month, now.day, now.hour, now.minute

    without = string

    if not dt:
        year, month, day = default[:3]
    else:
        day, month, year = [a for a in dt.fixed]
        without = without.replace(datemarker.format(*dt.fixed), '')

    if not tm:
        hour, minute = default[3:]
    else:
        hour, minute = [a for a in tm.fixed]
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

    return clean

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
        clean =  parse_post_list(data)

        for a in clean:
            if input(f'{a}\n\n/t accept? ') in 'Yesyes':
                post = blog.new(*a)
                accepted.append(a)
            else:
                rejected.append(a)

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

        global blog, known_tags
        blog = Blog()
        known_tags = list(blog.get_all_tags().keys())

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


def new_file(suffix='.post', content=None):
    if not content:
        now = datetime.now()
        content = """{}\n\n\n""".format(arg_container.format(f' {now.day}-{now.month}-{now.year} {now.hour}:{now.minute} '))
        content += """{}\n\n\n""".format(arg_container.format('  ')) * 100

    files = os.listdir(draftsdir)
    mx = 0
    for f in files:
        if f.endswith(suffix):
            u = parse.search(draftname+suffix, f)
            n = int(u.fixed[0])
            mx = max(mx, n)

    num = mx + 1
    newfname = draftsdir+draftname.format(num)+suffix
    with open(newfname, 'w+') as f:
        f.write(content)
    if suffix == '.post':
        print(f'Created empty blog templates at {newfname}.')
    return newfname

def edit_draft(fpath):
    try:
        with open(fpath, 'r') as f:
            pass
    except FileNotFoundError as e:
        print(f'Draft {fpath} not found. Look up the options with "list".')
        return False
    script = f"kate {fpath}"
    args = shlex.split(script)
    process = subprocess.Popen(args)
    process.wait()
    return True

def delete_draft(fname):
    script = f"rm {fname}"
    args = shlex.split(script)
    process = subprocess.Popen(args)
    process.wait()

def parse_file(fname):
    with open(fname, 'r') as f:
        data = f.read()

    data = data.strip()
    return parse_post_list(data)

def post_edit(fname=None):
    if fname:
        create = True
        print('\nPOST EDIT MODE\n==============')
        fpath = draftsdir+fname
    if not fname:
        create = False
        print('\nPOST CREATION MODE\n==================')
        fpath = new_file()

    rejected = []
    accepted = []
    newposts = []

    allgood = edit_draft(fpath)
    if not allgood:
        return

    parsed = parse_file(fpath)

    if parsed:
        blog = Blog()

    for item in parsed:
        if not item:
            continue
        title, tags, ori_content, day, hour = item
        content = ori_content.replace('\n','<br/>')
        print(20*'=')
        text = ori_content.replace('<br/>','\n')
        print(f'''\n\nday: {day}\nhour: {hour}\ntags: {tags}\ntitle: {title}\n\ncontent:
        {text}\n\n''')
        print(20*'=')
        if input('Confirm?') in 'Yesyes':
            accepted.append(blog.new(title, tags, content, day, hour))
        else:
            rejected.append(text)

    if accepted:
        print(f'\n\n ACCEPTED\n========')
        for i in accepted:
            print(f'accepted: {i}')
        print('\n')
        if input('Save changes?') in 'Yesyes':
            blog.save()

    if rejected:
        dump = new_file(suffix='.rejected', content='\n'.join(rejected))
        print(f'Dumping rejections to {dump}.')

    if accepted:
        if input('Want to gen and push?') in 'Yesyes':
            gen_and_push(accepted=len(accepted))

    if not accepted and not rejected and create:
        delete_draft(fpath)
        print('Nothing to do.')

def gen_and_push(accepted=0):
    gen_blog(accepted)
    push_blog(accepted)

def gen_blog(accepted=0):
    print('\nBLOG GEN MODE\n==============')
    global blog
    if not blog:
        blog = Blog()

    print('Dumping all posts')
    blog.to_md()

    myenv = os.environ.copy()
    myenv['BUNDLE_GEMFILE'] = gempath
    line = [
        f'bundle exec jekyll build -d {outputdir} -s {sourcedir} -p {plugindir} --layouts {layoutdir}'
    ]

    args = shlex.split(line)
    process = subprocess.Popen(args, env=myenv)
    process.wait()

def push_blog(accepted=0, cmdtest=None):
    if not cmdtest:
        print('\nBLOG GEN MODE\n==============')
        global blog
        if not blog:
            blog = Blog()

        print('Dumping all posts')
        blog.to_md()

    script = [
        f'git --git-dir={outputdir}.git add -A',
        f'git --git-dir={outputdir}.git commit -m "automated blog push, ({accepted}) new"',
        f'git --git-dir={outputdir}.git status',
        f'git --git-dir={outputdir}.git push origin master',
        f'cd {oridir}' # go back to original working dir
    ]

    if cmdtest is not None:
        script = [script[cmdtest]]

    for line in script:
        print(f'running "{line}"...')
        os.system(line)

    print('exiting...')

def print_post_list():
    print('\nDRAFTS\n======')
    files = os.listdir(draftsdir)
    for f in files:
        print(f)

def shutdown():
    os.system('systemctl poweroff')

def parseargs():

    parser = argparse.ArgumentParser(description='Website generation and posting.')
    sub = parser.add_subparsers()

    postparser = sub.add_parser('edit', help='post creation and editing: opens a file to write posts, by default an empty, new one')
    postparser.set_defaults(func=post_edit)
    postparser.add_argument('-f', '-file', dest='file', nargs=1, default=None, type=str, help='file to open (to edit posts). When omitted will create a new one.', required=False)

    listparser = sub.add_parser('list',help='list all existing post filenames and exit')
    listparser.set_defaults(func=print_post_list)

    genparser = sub.add_parser('gen' ,help='build the site')
    genparser.set_defaults(gen=True)

    gitparser = sub.add_parser('push' ,help='push it all to github.')
    gitparser.add_argument('-h', '-halt', dest='halt', default=False, help='shuts down the computer after all commands are run.', required=False)
    gitparser.set_defaults(push=True)

    args = parser.parse_args()
    # print(args)
    file = getattr(args, 'file', None)
    halt = getattr(args, 'halt', False)
    func = getattr(args, 'func', None)
    gen = getattr(args, 'gen', None)
    push = getattr(args, 'push', None)
    if file and gen or push:
        print('incorrect usage. Cannot process file and gen or push.')
        return
    elif gen and push:
        func = gen_and_push
    elif gen:
        func = gen_blog
    elif push:
        func = push_blog

    if file:
        func(fname=file[0])
    elif func:
        func()
    else:
        parser.print_usage()
        return

    print('Done.\n')

    if halt:
        shutdown()

if __name__ == '__main__':
    parseargs()
