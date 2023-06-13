import os
from time import sleep

import requests
import tqdm
from bs4 import BeautifulSoup

base_url = 'https://eprint.iacr.org/complete/'  # Replace with the actual base URL


def pdf_crawler(url: str):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        anchors = soup.find_all('a')

        for anchor in anchors:
            href = anchor.get('href')
            if href and href.endswith('.pdf'):
                _, year, paper = href.split('/')
                folder = f'/Users/christianwengert/Downloads/iacr/{year}'
                if not os.path.exists(folder):
                    os.mkdir(folder)

                paper_file = f'{folder}/{paper}'
                abstract_file = paper_file.replace('.pdf', '.txt')

                if os.path.exists(abstract_file):
                    continue
                header = anchor.find_parent("div", class_='mb-1')
                body = header.find_next('div', class_='mb-3')
                title = body.find('div', class_='papertitle')
                # author = body.find('div', class_='summaryauthors')
                # tags = body.find(class_='badge')
                abstract = body.find(class_='paper-abstract')

                print(f'Downloading {title.text}')
                if not os.path.exists(paper_file):
                    response = requests.get(f'https://eprint.iacr.org/{href}')
                    with open(f"{folder}/{paper}", "wb") as f:
                        f.write(response.content)

                with open(abstract_file, "w") as f:
                    f.write(abstract.text)
                print('Done')
                sleep(1)
    except Exception as e_:
        pass


for offset in tqdm.tqdm(range(13700, 20100 + 100, 100)):

    if not os.path.exists(f'{offset}'):

        pdf_crawler(f'{base_url}?offset={offset}')

        # with open(f'{offset}', 'w') as f:
        #     f.write("")

        sleep(10)
