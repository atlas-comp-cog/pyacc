import urllib.parse
import urllib.request

from clldutils.misc import slug
from clldutils.source import Source


def doi2bibtex(doi):
    url = 'https://scipython.com/apps/doi2bib/?doi={}'.format(urllib.parse.quote_plus(doi))
    req = urllib.request.urlopen(url)
    bibtex, in_bibtex = [], False
    for line in req.read().decode('utf8').split('\n'):
        if line.strip().startswith('</textarea>'):
            break
        if in_bibtex:
            bibtex.append(line)
        if line.strip().startswith('<textarea'):
            in_bibtex = True
    bibtex = '\n'.join(bibtex).strip()
    if bibtex:
        src = Source.from_bibtex(bibtex, _check_id=False)
        src.id = slug(doi)
        src['key'] = doi
        return src.bibtex()
