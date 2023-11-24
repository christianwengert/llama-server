import os
# noinspection PyPep8Naming
import xml.etree.ElementTree as ET
import json

from bs4 import BeautifulSoup

# Parse the XML file


def strip_html(html_content):
    """ Strips HTML tags from the provided HTML content. """
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text()


def extract(filepath):

    outdir, _ = os.path.split(filepath)
    outdir = outdir.replace('dumps', 'out')

    # Convert the result to JSON

    if os.path.exists(f'{outdir}/data.json'):
        return

    os.makedirs(outdir, exist_ok=True)

    tree = ET.parse(filepath)  # '/Users/christianwengert/src/stackexchange-dataset/dumps/crypto.stackexchange.com/Posts.xml'
    root = tree.getroot()

    # Initialize the result JSON structure
    result = {}
    # Loop through each post
    for post in root.findall('row'):
        post_type = post.get('PostTypeId')
        post_id = post.get('Id')
        parent_id = post.get('ParentId')
        if not post_id:
            raise ValueError

        if post_type == '1':
            result[post_id] = dict(question=strip_html(post.get('Body')),
                                   title=post.get('Title'),
                                   score=post.get('Score'),
                                   tags=post.get('Tags'),
                                   views=post.get('ViewCount'),
                                   created=post.get('CreationDate'),
                                   answers=[]
                                   )

        elif post_type == '2' and post.get('ParentId') in result:
            result[parent_id]["answers"].append(strip_html(post.get('Body')))

    with open(f'{outdir}/data.json', 'w') as f:
        json.dump(result, f)
