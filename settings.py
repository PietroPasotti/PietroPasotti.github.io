import os

gitusername = 'PietroPasotti'
gitpwd = 'Spacoinainoc1'

arg_container = '%==={}===%'
datemarker = '{}-{}-{}'
timemarker = '{}:{}'
postformat = '%=== {} {} ===%\n\n{}\n{}\n\n\n' #  for date, tags, title, content
oridir = os.getcwd()
basedir = os.path.dirname(os.path.realpath(__file__))
workingdir = basedir+'/build/'
draftsdir = basedir+'/drafts/'
builddir = workingdir+'_site/'

#  jekyll build options
gempath = workingdir+'Gemfile'
plugindir = workingdir+'_plugins/'
sourcedir = workingdir
layoutdir = workingdir+'_layouts/'
dblocation = basedir + '/poetrydb.json'

outputdir = os.path.dirname(os.path.realpath(__file__))+'/PietroPasotti.github.io/'
draftname = 'draft{}'

base_post_folder = workingdir+'all/_posts/'
base_tag_folder = workingdir+'tags/'

tags_desc = {
    'speciale' : "My favourites.",
    '25 carezze': '25 poems I once wrote for someone I loved.',
    'a-n-v': 'I honestly forgot what that meant.',
    'bouquet': 'Floral poems I wrote for someone I loved.',
    'c h s m': 'Something about chasms and opposites and inverting them at some point. Something deep.',
    'danze di disillusione': 'A collection of ballad-rhyming, long poems.',
    'dutch': 'Yeah, I know... At least I try.',
    'english': 'My poems in English.',
    'fuggire dal cerchio': 'A massive collection of poems, meant to be a book of sorts. It has secrets.',
    'haha': "Poems for the lols. There aren't many, but they are beloved",
    'i cinque punti': 'I forgot what this one was about.',
    'keleden': 'Well, I was writing poems to an imaginary person. One I would love.',
    'lily': 'Poems about... Lilies?',
    'onestar': 'My favourites among my favourites.',
    "scheggia d'essenza": 'Poems in which I thought I had discovered something about myself that I did not really know before. Or that captured somehow somewhat very deep and important.',
    'the chapters': 'Titles of chapters of my life. And my blog. And valleys and mountaintops of my mood swings.',
    'threestars': 'The ones I really really really (three times) like.',
    'topeng': 'Favourite evah English poems.',
    'tradotta': 'Poems I translated or back or forth between the one language and the other.',
    'twostars': 'The favourites among the favourites among my favourites... You get the yeast of the idea.'}

tags_titles = {
    'speciale' : 'Speciale',
    '25 carezze': '25 Carezze',
    'a-n-v': 'A-N-V',
    'bouquet': 'Bouquet',
    'c h s m': 'C H S M',
    'danze di disillusione': 'Danze di Disillusione',
    'dutch': 'Dutch',
    'english': 'English',
    'fuggire dal cerchio': 'Fuggire dal Cerchio',
    'haha': 'HAHA',
    'i cinque punti': 'I Cinque Punti',
    'keleden': 'Keleden',
    'lily': 'Lily',
    'onestar': 'Onestar',
    "scheggia d'essenza" : "Scheggia d'essenza",
    'the chapters': 'The Chapters',
    'threestars': 'Threestars',
    'topeng': 'Topeng',
    'tradotta': 'Tradotte',
    'twostars': 'Twostars'}

post_layout = """---\nlayout: post\ntitle: {}\ntags: {}\ndate: {}\nauthor: pietro\n---\n{}\n"""

tag_layout = """---\nlayout: list\ntitle: {}\nslug: {}\norder: {}\ndescription: {}\n---\n\n"""
