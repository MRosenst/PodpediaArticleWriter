import subprocess
import time
import urllib
import urllib2
from bs4 import BeautifulSoup
import datetime
import os
import sys
import feedparser
import editpage
import argparse
import pickle

# Use UTF-8
reload(sys)  
sys.setdefaultencoding('utf8')

def save_rss(obj, name):
    with open('rss/' + name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_rss(name):
    with open('rss/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)

def dl_rss(link):
    return feedparser.parse(link)

def fetch_rss(name, link, is_refresh):
    if is_refresh:
        feed = dl_rss(link)
        save_rss(feed, name)
    else:
        try:
            feed = load_rss(name)
        except IOError:
            feed = dl_rss(link)
            save_rss(feed, name)
    
    return feed

def calc_rss_index(feed, episode_num, specials):
    num = len(feed) - episode_num
    if specials != []:
        num -= sum(map(lambda sp: (1 if sp < episode_num else 0), specials))
    
    if num < 0:
        raise IndexError('Episode number out of range')
    
    return num

def fetch_timestamp(podcast, feed, ep_index):
    if podcast in ['cortex', 'tpa']:
        timestamp = feed['entries'][ep_index]['itunes_duration']
        return time.strftime('%H:%M:%S', time.gmtime(int(timestamp)))

    if podcast in ['hi', 'unmade']:
        ##return feed['entries'][ep_index]['itunes_duration']
        # TODO fix hi for episode 94
        return '1:53:57'

def fetch_html_desc(podcast, feed, ep_index):
    if podcast in ['cortex', 'tpa']:
        return feed['entries'][ep_index]['content'][1]['value']
    if podcast == 'unmade':
        return feed['entries'][ep_index]['summary']
    if podcast == 'hi':
        return feed['entries'][ep_index]['summary_detail']['value']

def convert_desc(html_desc):
    with open('desc.html', 'w') as f:
        f.write(html_desc)

    subprocess.call(['pandoc', '-f', 'html', '-t', 'mediawiki', 'desc.html', '-o', 'desc.mw'])

    with open('desc.mw', 'r') as f:
        desc = f.read()
    
    os.remove('desc.html')
    os.remove('desc.mw')

    return desc

def fetch_sponsors(podcast, html_desc):
    if podcast in ['cortex', 'tpa']:
        soup = BeautifulSoup(html_desc, 'html.parser')
        sponsors_tags = soup.find('ul').find_all('a')
        
        sponsors = []
        for tag in sponsors_tags:
            sponsors.append(tag.text)
        
        return sponsors
    if podcast == 'unmade':
        return []

    if podcast == 'hi':
        soup = BeautifulSoup(html_desc, 'html.parser')  
        shownotes = []
        for link in soup('a'):
            shownotes.append((link.text, link['href']))
        
        # Calculate where the first real shownote starts for later
        firstshownote = 0
        for i in range(len(shownotes)):
            if 'discuss' in shownotes[i][0].lower():
                firstshownote = i + 1
                break
        
        sponsors = []
        for note in shownotes[:firstshownote]:
            if 'listeners' not in note[0].lower() and 'patreon' not in note[0].lower() and 'rss' not in note[0].lower() and 'itunes' not in note[0].lower() and 'discuss' not in note[0].lower():
                name = ''
                for char in note[0]:
                    if char.isalnum() or char == '\'':
                        name += char
                    else:
                        break
                sponsors.append(name)

        return sponsors
# TODO add h.i. formatting tweaks code

def fetch_title(podcast, feed, ep_index):
    if podcast in ['cortex', 'tpa', 'unmade']:
        return feed['entries'][ep_index]['title']
    if podcast == 'hi':
        return feed['entries'][ep_index]['title'] # ['title_detail']['value']

def cut_title(title):
    if title.strip() == 'H.I. #89 -- A Swarm of Bad Emoji':
        return title.split('--', 2)[1].strip()
    return title.split(':', 2)[1].strip()

def fetch_dates(podcast, feed, ep_index):
    if podcast in ['cortex', 'tpa', 'unmade', 'hi']:
        date1 = time.strftime('%B %d, %Y', feed['entries'][ep_index]['published_parsed'])
        date2 = time.strftime('%Y|%B|%d', feed['entries'][ep_index]['published_parsed'])
        date3 = time.strftime('%-d %B %Y', time.gmtime())
        return [date1, date2, date3]

def fetch_link(podcast, feed, ep_index):
    if podcast in ['cortex', 'tpa', 'unmade']:
        return feed['entries'][ep_index]['link']
    if podcast == 'hi':
        return feed['entries'][ep_index]['links'][0]['href']

def fetch_prev_next(podcast, feed, ep_index, no):
    if ep_index > 0:
        nexttitle = cut_title(fetch_title(podcast, feed, ep_index - 1))
    else:
        nexttitle = ''

    if no > 1:
        prevtitle = cut_title(fetch_title(podcast, feed, ep_index + 1))
    else:
        prevtitle = ''

    return (prevtitle, nexttitle)

def fetch_youtube(name, title):
    textToSearch = name + ' ' + title
    query = urllib.quote(textToSearch)
    url = "https://www.youtube.com/results?search_query=" + query
    response = urllib2.urlopen(url)
    yt_html = response.read()
    soup = BeautifulSoup(yt_html, 'html.parser')

    return 'https://www.youtube.com' + soup.find(attrs={'class':'yt-uix-tile-link'})['href']

def fetch_itunes(podcast):
    return {
            'hi':'http://www.hellointernet.fm/itunes',
            'unmade':'https://itunes.apple.com/gb/podcast/the-unmade-podcast/id1274023400',
            'cortex':'https://itunes.apple.com/us/podcast/cortex/id1001591696',
            'tpa':'https://itunes.apple.com/us/podcast/id909109717'
            }[podcast]

def fetch_reddit(podcast, html_desc):
    return 'https://reddit.com' #TODO continue here

def bullet(line):
    if len(line) > 0 and line[0] == '[':
        return '*' + line
    else:
        return line 


def format_desc(podcast, desc):
    if podcast in ['cortex', 'tpa']:
        replacables = {'sponsored by':'== Sponsors ==', 'show notes':'== Show Notes =='}

        desc_formatted = ''
        for line in desc.splitlines():
            if line.strip()[:6] == '===== ':
                line = line.strip()[6:-6]
        
            for r in replacables:
                if r in line.lower():
                    line = replacables[r]

            line = bullet(line)
            desc_formatted += line + '\n'
        
        return desc_formatted
    
    if podcast in ['unmade', 'hi']:
        replacables = {'useful links':'== Show Notes =='}
        
        created_sponsors_header = False
        description_formatted = ''
        for line in desc.splitlines():
            if line.strip() == '' and not created_sponsors_header:
                line = '== Sponsors =='
                created_sponsors_header = True
            for r in replacables:
                if r in line.lower():
                    line = replacables[r]
            line = bullet(line)
            description_formatted += line + '\n'
        
        return description_formatted
    
    if podcast == 'hi':
        replacables = {'brought':'== Sponsors ==', 'sponsors':'== Sponsors ==', 'subscribe:':'== Show Notes ==', 'notees:':'== Show Notes =='}
        
        description_formatted = ''
        for line in desc.splitlines():
            for r in replacables:
                if r in line.lower():
                    line = replacables[r]
            description_formatted += line + '\n'
        
        return description_formatted
        
# The script


# Args
parser = argparse.ArgumentParser()
parser.add_argument('podcast', help='name of the podcst', choices=['hi', 'cortex', 'unmade', 'tpa'])
parser.add_argument('no', help='episode number to be processed', type=int)
parser.add_argument('-r', '--refresh', help='force new rss download', action='store_true')
parser.add_argument('-l', '--local', help='generate the article as a local file without posting to the wiki', action='store_true')
args = parser.parse_args()

specials = {
        'hi':[51],
        'cortex':[],
        'unmade':[],
        'tpa':[]
        }

rsslinks = {
        'hi':'http://www.hellointernet.fm/podcast?format=rss',
        'unmade':'http://www.unmade.fm/episodes?format=rss',
        'cortex':'https://www.relay.fm/cortex/feed', 
        'tpa':'https://www.relay.fm/penaddict/feed'
        }
feed = fetch_rss(args.podcast, rsslinks[args.podcast], args.refresh)

ep_index = calc_rss_index(feed['entries'], args.no, specials[args.podcast]) #TODO check if this still works for hi

title = fetch_title(args.podcast, feed, ep_index)
concise_title = cut_title(title)

full_name = {
        'hi':'Hello Internet',
        'unmade':'The Unmade Podcast',
        'cortex':'Cortex',
        'tpa':'The Pen Addict'
        }[args.podcast]

presenters = {
        'hi':['[[CGP Grey]]', '[[Brady Haran]]'],
        'cortex': ['[[Myke Hurley]]', '[[CGP Grey]]'],
        'unmade':['[[Tim Hein]]', '[[Brady Haran]]'],
        'tpa':['[[Myke Hurley]]', '[[Brad Dowdy]]']
        }

dates = fetch_dates(args.podcast, feed, ep_index)

timestamp = fetch_timestamp(args.podcast, feed, ep_index)

html_desc = fetch_html_desc(args.podcast, feed, ep_index)

sponsors = fetch_sponsors(args.podcast, html_desc)

link = fetch_link(args.podcast, feed, ep_index)

prevnext = fetch_prev_next(args.podcast, feed, ep_index, args.no)

website = {
        'hi':'Hello Internet',
        'cortex':'RelayFM',
        'unmade':'Unmade',
        'tpa':'RelayFM'
        }

desc = convert_desc(html_desc)

desc_formatted = format_desc(args.podcast, desc)

current_month = time.strftime('%B %Y', time.gmtime())

reddit = fetch_reddit(args.podcast, html_desc)

has_yt = ['hi', 'cortex', 'unmade']

article_name = {
        'hi':'H.I.',
        'cortex':'Cortex',
        'unmade':'The Unmade Podcast',
        'tpa':'The Pen Addict'
        }[args.podcast]

doc = ''
doc += '{{Infobox television episode\n'
doc += '| title = ' + concise_title + '\n'
doc += '| series = [[' + full_name + ']]\n'

if args.podcast in has_yt:
    doc += '| image = {{right|{{#widget:YouTube|id=' + fetch_youtube(full_name, title).split('v=', 1)[1] + '|height=188|width=336}}}}\n'
    doc += '| caption = Episode ' + str(args.no) + ' on the [[' + full_name + ' (YouTube channel)|podcast YouTube channel]]\n'
doc += '| episode = ' + str(args.no) + '\n'
doc += '| presenter = {{hlist|' + '|'.join(presenters[args.podcast]) + '}}\n'
doc += '| airdate = {{Start date|' + dates[1] + '}}\n'
doc += '| length = ' + timestamp + '\n'
doc += '| sponsors = {{hlist|' + '|'.join(sponsors) + '}}\n'
doc += '| reddit = [' + reddit + ' Link]'
doc += '| website = [' + link + ' Link]\n'

if prevnext[0] == '':
    doc += '| prev = \n'
else:
    doc += '| prev = [[' + article_name + ' No. ' + str(args.no - 1) + ': ' + prevnext[0] + '|' + prevnext[0] + ']]\n'

if prevnext[1] == '':
    doc += '| next = \n'
else:
    doc += '| next = [[' + article_name + ' No. ' + str(args.no + 1) + ': ' + prevnext[1] + '|' + prevnext[1] + ']]\n'


doc += '| episode_list = [[List of ' + full_name + ' episodes]]\n'
doc += '}}\n'


# https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement
ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])


intro = ''
intro += '\"\'\'\'' + title + '\'\'\'\" is the ' + ordinal(args.no)
if ep_index == 0:
    intro += ' and most recent'
intro += ' episode of \'\'[[' + full_name + ']]\'\', released on ' + dates[0] + '.<ref name="UP page">{{cite web|title= ' + title
intro += '|url=' + link + '|website=' + website[args.podcast] + '|publisher=\'\'' + full_name + '\'\'|accessdate='
intro += dates[2] + '}}</ref>\n\n'

doc += intro

doc += '== Official Description ==\n'
doc += desc_formatted

footer = '== Other ==\n'

if args.podcast == 'tpa':
    footer += '{{collapse top|title=Ask TPA}}\n{{Empty section|date=' + current_month +'}}\n{{collapse bottom}}\n\n'

footer += '{{collapse top|title=Fan Art}}\n{{Empty section|date=' + current_month +'}}\n{{collapse bottom}}\n\n'
footer += '{{collapse top|title=Flowchart}}\n{{Empty section|date=' + current_month +'}}\n{{collapse bottom}}\n\n'
footer += '{{collapse top|title=Summary}}\n{{Empty section|date=' + current_month +'}}\n{{collapse bottom}}\n\n'
footer += '{{collapse top|title=Transcript}}\n{{Empty section|date=' + current_month +'}}\n{{collapse bottom}}\n\n'
footer += '== References ==\n{{reflist}}\n\n'
footer += '[[Category:' + full_name + ' Episode]]\n[[Category:Article]]\n\n'
footer += '== Episode List ==\n{{' + full_name + ' episodes}}\n\n__NOTOC__\n'
doc += footer

if not args.local:
    name = article_name.replace(' ', '_') + '_No._' + str(args.no) + ':_' + concise_title.strip().replace(' ', '_')
    print('Uploading to ' + name + '\n')
    editpage.main(name, doc)
else:
    with open('local_articles/' + args.podcast + '_' + str(args.no) + '.mw', 'w') as f:
        f.write(doc)
