#Author: Zachary Migliorini

import sys
import urllib.request as ur
import requests
import re
from bs4 import BeautifulSoup as bs
import xml.etree.ElementTree as et


"""
Take a CIK or ticker and return the text representation of the filing as a string
"""
def get_raw_text(cik):

    #This link is specified with type=13F-HR to only bring up the appropriate documents
    #This line is way more than 80 chars
    url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={}&type=13F-HR&dateb=&owner=exclude&count=40'.format(cik)

    filing_list = ur.urlopen(url).read()
    soup = bs(filing_list, 'lxml')

    #Pull the first filing only, multiple could be grabbed with 'for url in soup.find_all(~~)'
    filing_url = soup.find('a', id='documentsbutton').get('href')

    #URL for the .txt filing is the same as the repository URL with a small change.
    filing_url = 'https://www.sec.gov{}'.format(filing_url.replace('-index.htm', '.txt'))

    return requests.get(filing_url).text

"""
Chop up the document to take just the holdings information,
   leaving out the primary_doc if present
Return information starting and ending with an <XML> tag
Could take txt and send it to upper/lowercase and do this, to
   avoid <xml> tags in lowercase, but I didn't see any such cases
"""
def preprocess_infotable(txt):
    txt = txt[txt.index('</XML>')+6:]
    txt = txt[txt.index('<XML>'):]
    txt = txt[:txt.index('</XML>')+6]

    #Some docs have <? xml version = "X.X" encoding = "XXX" ?>
    #   remove them
    p = re.compile(r'<\?.*?\?>')
    txt, n = re.subn(p, '', txt)

    return txt


"""
Takes a CIK/ticker and writes to a .txt file the holding information
   given in their most recently-filed 13F-HR. Does not take 13F-HR/A
   filings into account
"""
def write_holdings(cik):

    #Get the string of the filing
    txt = get_raw_text(cik)

    #Cut just the holding information out
    text_infotable = preprocess_infotable(txt)

    #Build our string to be written, if we want to change the tags to be more human-readable
    #   such as Issuer Name instead of nameOfIssuer, we can run a string replace on (''.join(output))
    #   which will be cleaner-looking than checking each tag as we parse it and writing it differently
    output = []

    #Construct Element with the first child of <XML> as the root
    #   root should be <informationTable>
    root = et.fromstring(text_infotable)[0]

    #Each infoTable is a holding listing
    for infoTable in root:
        #Each child is a part of that listing, such as nameOfIssuer, CUSIP, etc
        for child in infoTable:
            #Some docs have purely empty tags, rather than '\n'
            #Each tag has a style info URL prepended, which we remove
            if child.text is not None:
                output.append('{} {}\n'.format(child.tag.replace(\
                    '{http://www.sec.gov/edgar/document/thirteenf/informationtable}', ''), child.text.rstrip()))
            else:
                output.append('{}\n'.format(child.tag.replace(\
                    '{http://www.sec.gov/edgar/document/thirteenf/informationtable}', '')))
            for sub_child in child:
                if sub_child.text is not None:
                    output.append('\t {} {}\n'.format(sub_child.tag.replace(\
                        '{http://www.sec.gov/edgar/document/thirteenf/informationtable}', ''), sub_child.text.rstrip()))
                else:
                    output.append('\t {}\n'.format(sub_child.tag.replace(\
                        '{http://www.sec.gov/edgar/document/thirteenf/informationtable}', '')))

        #Deliminate listing with newline
        output.append('\n')

    output = ''.join(output).rstrip()
    
    with open('{}_holdings.txt'.format(cik), 'w') as f:
        f.write(output)

def main(cik = sys.argv[1]):
    write_holdings(cik)

if __name__ == '__main__':
    main()
