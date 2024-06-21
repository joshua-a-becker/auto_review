key_sc = 'your_scopus_api_key'
profile = 'your_ebsco_api_profile'
password = 'your_ebsco_api_password'

import pandas as pd
import xmltodict
from pyscopus import Scopus
import requests
import json
import sys

# Example: interdisciplinary collaboration AND negotiation OR policy
query = sys.argv[1]

sc = Scopus(key_sc)
# KEY = keywords
# TITLE-ABS-KEY = query words foundin title, abstract, keywords
# ALL = anywhere in the article

# DOCTYPE(ar) = article
# SRCTYPE(j) = source is journal 
scquery = f"ALL({query}) " + "AND DOCTYPE(ar)" + " AND SRCTYPE(j)"

def get_total_count(key_sc,query):
    index = 0
    view = 'COMPLETE'
    import requests
    par = {'apikey': key_sc, 'query': query, 'start': index,
           'httpAccept': 'application/json', 'view': view}
    r = requests.get("http://api.elsevier.com/content/search/scopus", params=par)
    return int(r.json()['search-results']['opensearch:totalResults'])

# total count can be limited if it creates issues (pagination is automatically resolved)
search_df = sc.search(scquery,count=get_total_count(key_sc,scquery),view='COMPLETE')

def retrieve_authors(lst,key_sc=key_sc):
    import requests
    import pandas as pd

    def transform_author_list(auth):
        if len(auth)>25:
            return str(auth[:25]).replace("'","").replace('[','').replace(']','').replace(' ','')
        else:
            return str(auth).replace("'","").replace('[','').replace(']','').replace(' ','')
    
    if len(lst)==1:
        d = pd.json_normalize(requests.get(f"https://api.elsevier.com/content/author/author_id/{lst[0]}?apiKey={key_sc}&view=STANDARD&httpAccept=application/json").json()['author-retrieval-response'])
    else:
        d = pd.json_normalize(data=requests.get(f"https://api.elsevier.com/content/author/author_id/{transform_author_list(lst)}?apiKey={key_sc}&view=STANDARD&httpAccept=application/json").json()['author-retrieval-response-list'],record_path=['author-retrieval-response'])

    d = d[d.columns[(d.columns.str.contains(pat='id') & d.columns.str.contains(pat='dc')) | (d.columns.str.contains(pat = 'author-profile.preferred-name') & ~(d.columns.str.contains(pat='@')))]]
    d.rename(columns={'coredata.dc:identifier':'author_id'},inplace=True)
    d.loc[:,('author_id')] = d.loc[:,('author_id')].str.replace('AUTHOR_ID:','')
    return d

search_df.loc[:,"authors_df"] = pd.Series([retrieve_authors(search_df.loc[i,'authors']) for i in range(len(search_df.loc[:,'scopus_id']))])

abst = list()
for id in search_df['scopus_id']:
    try:
        abst.append(sc.retrieve_abstract(id))
    except:
        None

abst_df = pd.DataFrame(abst)
abst_df.rename(columns={'scopus-id':'scopus_id'},inplace=True)
scopus_data = pd.merge(search_df,abst_df,how='left')

ebsco_info_url = f"http://eit.ebscohost.com/Services/SearchService.asmx/Info?prof={profile}&pwd={password}"
ebsco_info_db = pd.DataFrame(xmltodict.parse(requests.get(ebsco_info_url).content)['info']['dbInfo']['db'])

equery = query.replace(' ','+')
equery
database = str(list(ebsco_info_db['@shortName'])).replace("'","").replace("[","&db=").replace(", ","&db=").replace(']','')
numrec = 1
form = 'detailed'
count = 1

# if you want full text as well you can add:
## AND+FT+Y
# OR
## AND+(FM+P+OR+FM+T+OR+FM+C)
### FM + P is for pdfs
### FM + T is for HTML text
### FM + C is for HTML text with Graphics
# the RV+Y stands for peer-reviewed yes

def get_ebsco_link(profile,password,query,database,numrec,form,count):
    return f"http://eit.ebscohost.com/Services/SearchService.asmx/Search?prof={profile}&pwd={password}&query={query}+AND+RV+Y{database}&numrec={numrec}&format={form}&startrec={count}"

def ebsco_search_limit(ebsco_search_url):
    import xmltodict
    import requests
    return int(xmltodict.parse(requests.get(ebsco_search_url).content)['searchResponse']['Hits']['#text'])

def get_links(profile,password,query,database,numrec,form):
    if form=='full' and numrec>50:
        numrec = 50
    lim = ebsco_search_limit(get_ebsco_link(profile,password,query,database,1,form,1))//numrec + 1
    link = [get_ebsco_link(profile,password,query,database,numrec,form,(count*numrec+1)) for count in range(lim)]
    return link

links = get_links(profile,password,equery,database,numrec,form)
pd.DataFrame(xmltodict.parse(requests.get(get_ebsco_link(profile,password,equery,database,20,form,1)).content)['searchResponse']['Statistics']['Statistic'])

def ebsco_article_search(ebsco_search_url):
    import pandas as pd
    import xmltodict
    import requests
    import time

    response = requests.get(ebsco_search_url)
    x = xmltodict.parse(response.content)
    
    def get_single_article_data(x):
        return{
            'index': x['searchResponse']['SearchResults']['records']['rec']['@recordID'] if '@recordID' in x['searchResponse']['SearchResults']['records']['rec'] else str(None),
            'plink': x['searchResponse']['SearchResults']['records']['rec']['plink'] if 'plink' in x['searchResponse']['SearchResults']['records']['rec'] else str(None),
            'pdf_link': x['searchResponse']['SearchResults']['records']['rec']['pdfLink'] if 'pdfLink' in x['searchResponse']['SearchResults']['records']['rec'] else str(None),
            'db_short': x['searchResponse']['SearchResults']['records']['rec']['header']['@shortDbName'] if '@shortDbName' in x['searchResponse']['SearchResults']['records']['rec']['header'] else str(None),
            'db_long': x['searchResponse']['SearchResults']['records']['rec']['header']['@longDbName'] if '@longDbName' in x['searchResponse']['SearchResults']['records']['rec']['header'] else str(None),
            'ui': x['searchResponse']['SearchResults']['records']['rec']['header']['@uiTerm'] if '@uiTerm' in x['searchResponse']['SearchResults']['records']['rec']['header'] else str(None),
            'issn': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['jinfo']['issn'] if 'issn' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['jinfo'] else str(None),
            'doi':x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['ui'][1]['#text'] if '#text' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['ui'][1] else str(None),
            'date_year': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['pubinfo']['dt']['@year'] if '#text' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['pubinfo']['dt'] else str(None),
            'date_month': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['pubinfo']['dt']['@month'] if '#text' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['pubinfo']['dt'] else str(None),
            'date_day': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['pubinfo']['dt']['@day'] if '#text' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['pubinfo']['dt'] else str(None),
            'doctype': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['doctype'] if 'doctype' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo'] else str(None),
            'pubtype': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['pubtype'] if 'pubtype' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo'] else str(None),
            'language': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['language'] if 'language' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo'] else str(None),
            'keywords_list': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['sug'] if 'sug' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo'] else str(None),
            'subjects_list': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['keyword'] if 'keyword' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo'] else str(None),
            'authors_list': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['aug']['au'] if 'aug' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo'].keys() and x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['aug']!=None else str(None),
            'title': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['tig']['atl'] if 'atl' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['tig'] else str(None),
            'abstract': x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo']['ab'] if 'ab' in x['searchResponse']['SearchResults']['records']['rec']['header']['controlInfo']['artinfo'] else str(None),
            'full_text': x['searchResponse']['SearchResults']['records']['rec']['abody'] if 'abody' in x['searchResponse']['SearchResults']['records']['rec'] else str(None)
            }
    
    def get_article_data(x,i):
        return{
            'index': x['searchResponse']['SearchResults']['records']['rec'][i]['@recordID'] if '@recordID' in x['searchResponse']['SearchResults']['records']['rec'][i] else str(None),
            'plink': x['searchResponse']['SearchResults']['records']['rec'][i]['plink'] if 'plink' in x['searchResponse']['SearchResults']['records']['rec'][i] else str(None),
            'pdf_link': x['searchResponse']['SearchResults']['records']['rec'][i]['pdfLink'] if 'pdfLink' in x['searchResponse']['SearchResults']['records']['rec'][i] else str(None),
            'db_short': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['@shortDbName'] if '@shortDbName' in x['searchResponse']['SearchResults']['records']['rec'][i]['header'] else str(None),
            'db_long': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['@longDbName'] if '@longDbName' in x['searchResponse']['SearchResults']['records']['rec'][i]['header'] else str(None),
            'ui': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['@uiTerm'] if '@uiTerm' in x['searchResponse']['SearchResults']['records']['rec'][i]['header'] else str(None),
            'issn': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['jinfo']['issn'] if 'issn' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['jinfo'] else str(None),
            'doi':x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['ui'][1]['#text'] if '#text' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['ui'][1] else str(None),
            'date_year': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['pubinfo']['dt']['@year'] if '#text' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['pubinfo']['dt'] else str(None),
            'date_month': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['pubinfo']['dt']['@month'] if '#text' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['pubinfo']['dt'] else str(None),
            'date_day': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['pubinfo']['dt']['@day'] if '#text' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['pubinfo']['dt'] else str(None),
            'doctype': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['doctype'] if 'doctype' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'] else str(None),
            'pubtype': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['pubtype'] if 'pubtype' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'] else str(None),
            'language': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['language'] if 'language' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo'] else str(None),
            'keywords_list': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['sug'] if 'sug' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'] else str(None),
            'subjects_list': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['keyword'] if 'keyword' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'] else str(None),
            'authors_list': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['aug']['au'] if 'aug' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'].keys() and x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['aug']!=None else str(None),
            'title': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['tig']['atl'] if 'atl' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['tig'] else str(None),
            'abstract': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['ab'] if 'ab' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'] else str(None),
            'full_text': x['searchResponse']['SearchResults']['records']['rec'][i]['abody'] if 'abody' in x['searchResponse']['SearchResults']['records']['rec'][i] else str(None)
            }
    
    if 'searchResponse' in x.keys():
        if type(x['searchResponse']['SearchResults']['records']['rec'])!=list:
            # time.sleep(1)
            return pd.DataFrame([get_single_article_data(x)])
        else:
            # time.sleep(1)
            return pd.DataFrame([get_article_data(x,i) for i in range(len(x['searchResponse']['SearchResults']['records']['rec']))])

    return pd.DataFrame()

# ibid to scopus count
results = [ebsco_article_search(link) for link in links]
ebsco_data = pd.concat(results,ignore_index=True)

# Prep and merge the 2 dataframes

ebsco_data['date'] = ebsco_data.loc[:,'date_year'] + '-' + ebsco_data.loc[:,'date_month'] + '-' + ebsco_data.loc[:,'date_day']
ebsco_data['db'] = 'ebsco_host'
ebsco_data.rename({'doctype':'srctype'},axis='columns',inplace=True)

scopus_data.rename({'scopus_id':'ui','authors':'authors_list','cover_date':'date'},axis='columns',inplace=True)
scopus_data['srctype']=scopus_data['srctype'].transform(lambda x: 'Journal Article' if x=='j' else x)
scopus_data['db'] = 'scopus'

data = pd.concat([scopus_data.loc[:,['db','srctype','title','authors_list','authors_df','abstract','date','doi','issn','ui']],ebsco_data.loc[:,['db','srctype','title','authors_list','abstract','date','date_year','doi','issn','subjects_list','keywords_list','ui']]],ignore_index=True)
data.to_csv('ebscopus.csv')
