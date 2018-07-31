#! /usr/bin/env python

import mwclient
import sys
import wikicreds

def replace_page(wikiname,
                 wikibasepath,
                 pagename,
                 username,
                 password,
                 contents):
    site = mwclient.Site(wikiname,
                         wikibasepath,
                         force_login=True)
    site.login(username, password)
    page = site.Pages[pagename]
    some = page.text()
    page.save(contents, summary='This edit was generated and posted by an automated script. The script is still a WIP.')

def main(pagename, contents):
    wikiname='podpedia.miraheze.org'
    wikibasepath="/w/"
    
    #pagename=sys.argv[1]

    username = wikicreds.username
    password = wikicreds.password
    #contents = sys.stdin.read()
    replace_page(wikiname,
                 wikibasepath,
                 pagename,
                 username,
                 password,
                 contents)
    print('Page edit complete.\n')

# Usage: cat some_file.txt | editpage.py
# if __name__ == "__main__":
#     main()

