import requests
from bs4 import BeautifulSoup
import json

def search_paper1(query):
    session = requests.Session()
    endpoint = f"https://www.studyflo.com/search/?abstract_query={query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    response = session.get(endpoint, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    papers = []
    paper_cards = soup.find_all('div', class_='bg-white card w-full font-mono toggle-card retro1 border-4 border-black')

    for card in paper_cards:
        title_tag = card.find('h2', class_='text-xl font-bold text-gray-800 article-title')
        title = title_tag.text.strip() if title_tag else "No Title"

        doi = card.get('data-doi', 'No DOI')

        date_tag = card.find('span', text="Published:")
        publication_date = date_tag.find_next_sibling(text=True).strip() if date_tag else "Unknown"

        journal_tag = card.find('span', class_='journal-title')
        journal = journal_tag.text.strip() if journal_tag else "Unknown"

        authors_list = []
        authors_tag = card.find('ul', class_='list-disc list-inside text-sm text-gray-600 authors-list')
        if authors_tag:
            authors_list = [author.text.strip() for author in authors_tag.find_all('li')]

        read_button = card.find('button', class_='read-button')
        read_link = f"https://sci-hub.ru/{doi}" if read_button else "No Link"

        papers.append({
            "Title": title,
            "DOI": doi,
            "Publication Date": publication_date,
            "Journal": journal,
            "Authors": authors_list,
            "Read Link": read_link
        })

    return json.dumps(papers, indent=4)


def SciHubLink(doi):
    session = requests.Session()
    endpoint = f"https://sci-hub.ru/{doi}"
   
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept-Encoding": "gzip, deflate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    response = session.get(endpoint, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    result = {}

    article_div = soup.find('div', id='article')
    if article_div:
        pdf_embed = article_div.find('embed', type='application/pdf')
        if pdf_embed:
            pdf_link = pdf_embed['src'].split('#')[0]
            if pdf_link.startswith('/'):
                pdf_link = 'https://sci-hub.ru' + pdf_link
                result['pdf_link'] = pdf_link
            elif pdf_link.startswith('//'):
                pdf_link = 'https:' + pdf_link
                result['pdf_link'] = pdf_link
            else:
                result['pdf_link'] = pdf_link
            
    citation_div = soup.find('div', id='citation')
    if citation_div:
        result['citation'] = citation_div.get_text(strip=True)
    
    return json.dumps(result, indent=4)

def analyze_pdf(pdf_link):
    try:
        response = requests.get(pdf_link)
        with open("temp.pdf", "wb") as f:
            f.write(response.content)
        
        with pdfplumber.open("temp.pdf") as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        return f"Error analyzing PDF: {str(e)}"
