import sys
import pandas as pd
import requests
import xmltodict

# set parameters from command line
profile = sys.argv[1] 
password = sys.argv[2]
query = sys.argv[3] # Example query: 'interdisciplinary collaboration AND negotiation OR policy'
query = query.replace(' ','+')
print(query)

# Link to the info database containing the information regarding what databases we have access to
ebsco_info_url = f"http://eit.ebscohost.com/Services/SearchService.asmx/Info?prof={profile}&pwd={password}"

ebsco_info_db = pd.DataFrame(xmltodict.parse(requests.get(ebsco_info_url).content)['info']['dbInfo']['db'])

print('View of the databases we currently have access to: \n' + ebsco_info_db)

# Search parameters
database = str(list(ebsco_info_db['@shortName'])).replace("'","").replace("[","&db=").replace(", ","&db=").replace(']','')
numrec = 200
form = 'detailed'
count = 1

# function to create a link for the EBSCOhost API
## The link is tailored to return all results that are peer-reviewed journal articles from all databases (duplicates are removed automatically)
def get_ebsco_link(profile,password,query,database,numrec,form,count):
    return f"http://eit.ebscohost.com/Services/SearchService.asmx/Search?prof={profile}&pwd={password}&query={query}+AND+RV+Y{database}&numrec={numrec}&format={form}&startrec={count}"

# Function to determine the number of search results
def ebsco_search_limit(ebsco_search_url):
    import xmltodict
    import requests
    return int(xmltodict.parse(requests.get(ebsco_search_url).content)['searchResponse']['Hits']['#text'])

# Function to deal with the pagination issue by creating a list of links to get all results of a search
def get_links(profile,password,query,database,numrec,form):
    if form=='full' and numrec>50:
        numrec = 50
    lim = ebsco_search_limit(get_ebsco_link(profile,password,query,database,1,form,1))//numrec + 1
    link = [get_ebsco_link(profile,password,query,database,numrec,form,(count*numrec+1)) for count in range(lim)]
    return link

links = get_links(profile,password,query,database,numrec,form)

print('The number of total hits is approximately: '+len(links)*numrec)

print('Detailed view of hits per database: \n' + pd.DataFrame(xmltodict.parse(requests.get(get_ebsco_link(profile,password,query,database,1,form,1)).content)['searchResponse']['Statistics']['Statistic']))

# Function to extract information from 
def ebsco_article_search(ebsco_search_url):
    import pandas as pd
    import xmltodict
    import requests
    response = requests.get(ebsco_search_url)
    x = xmltodict.parse(response.content)
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
            'keywords': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['sug'] if 'sug' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'] else str(None),
            'subjects': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['keyword'] if 'keyword' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'] else str(None),
            'authors_list': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['aug']['au'] if 'aug' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'].keys() and x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['aug']!=None else str(None),
            'title': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['tig']['atl'] if 'atl' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['tig'] else str(None),
            'abstract': x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo']['ab'] if 'ab' in x['searchResponse']['SearchResults']['records']['rec'][i]['header']['controlInfo']['artinfo'] else str(None),
            'full_text': x['searchResponse']['SearchResults']['records']['rec'][i]['abody'] if 'abody' in x['searchResponse']['SearchResults']['records']['rec'][i] else str(None)
            }

    return pd.DataFrame([get_article_data(x,i) for i in range(len(x['searchResponse']['SearchResults']['records']['rec']))])

results = [ebsco_article_search(link) for link in links]
data = pd.concat(results)
outfile = f'Results_for_query_{query}.json'
data.to_json(outfile)
