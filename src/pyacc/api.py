import re
import urllib.parse

import openpyxl
from csvw import dsv
from clldutils.apilib import API
from clldutils.misc import slug, lazyproperty
from clldutils.source import Source
import attr
import nameparser

from pyacc import util


def clean_doi(s):
    s = urllib.parse.urlparse(s.strip()).path
    if s.startswith('/'):  # Remove leading / in case a DOI URL was passed:
        s = s[1:].strip()
    if s.endswith(','):  # Remove trailing comma - this cannot be part of a valid DOI:
        s = s[:-1].strip()
    return re.sub(r'\s+', '', s)  # Remove internal whitespace.


def valid_doi(instance, attribute, value):
    """
    See https://www.crossref.org/blog/dois-and-matching-regular-expressions/
    """
    if not re.match(r'^10.\d{4,9}/[-._;()/:A-Z0-9a-z]+$', value):
        raise ValueError('Invalid DOI: {}'.format(value))


@attr.s
class Experiment:
    reviewer = attr.ib(converter=nameparser.HumanName)  # Contribution
    paper_number = attr.ib()
    experiment_number = attr.ib()
    species = attr.ib()  # Language
    species_latin = attr.ib()
    doi = attr.ib(converter=clean_doi, validator=valid_doi)  # Source
    parameter = attr.ib()  # Parameter
    sample_size = attr.ib()
    type = attr.ib(validator=attr.validators.in_(['experimental', 'observational', 'other']))
    year = attr.ib(converter=lambda s: int(s) if s else None)
    source = attr.ib(default=None)

    @property
    def contributor_id(self):
        return slug(self.reviewer.last + self.reviewer.first)

    @property
    def contribution_id(self):
        return '{0}-{1}-{2}'.format(self.contributor_id, slug(self.doi), self.experiment_number)

    @property
    def contribution_name(self):
        return '{0} experiment {1} reviewed by {2}'.format(
            self.doi, self.experiment_number, self.reviewer)

    @property
    def species_id(self):
        return slug(self.species_latin)

    @property
    def parameter_id(self):
        return slug(self.parameter)

    @property
    def id(self):
        return '{0}-{1}'.format(self.contribution_id, self.species_id)

    @classmethod
    def from_dict(cls, d, sources):
        res = cls(
            reviewer=d['Reviewer'],
            paper_number=d['Paper #'],
            experiment_number=d['Experiment #'],
            species=d['Species   (common name)'],
            species_latin=d['Species         (latin name)'],
            doi=d['DOI'],
            parameter=d['Topic'],
            sample_size=d['Sample size'],
            type=d['Research Kind'],
            year=d['Publication Year']
        )
        res.source = sources.get(res.doi)
        if res.source:
            res.source.setdefault('year', str(res.year))
        return res


class ACC(API):
    def dump(self):
        def _excel_value(x):
            if x is None:
                return ""
            if isinstance(x, float):
                return '{0}'.format(int(x))
            return '{0}'.format(x).strip()

        res = {}
        outdir = self.repos
        wb = openpyxl.load_workbook(str(self.path('COMBINED.xlsx')), data_only=True)
        for sname in wb.sheetnames:
            sheet = wb[sname]
            path = outdir.joinpath('data.' + slug(sname, lowercase=False) + '.csv')
            with dsv.UnicodeWriter(path) as writer:
                for row in sheet.rows:
                    writer.writerow([_excel_value(col.value) for col in row])
            res[sname] = path
        return res

    def write_bib(self):
        #
        # FIXME: keep old records, only update new stuff
        #
        seen = set()
        with self.path('sources.bib').open('w', encoding='utf8') as fp:
            for ex in self.experiments:
                if ex.doi not in seen:
                    bibtex = util.doi2bibtex(ex.doi)
                    if bibtex:
                        fp.write('\n\n{}\n\n'.format(bibtex))
                    else:
                        fp.write('\n\n% FIXME: {}\n\n'.format(ex.doi))
                    seen.add(ex.doi)

    def check(self):
        eids = set()
        for ex in self.experiments:
            if ex.id in eids:
                raise ValueError('duplicate experiment ID: {}'.format(ex.id))
            eids.add(ex.id)

    @lazyproperty
    def sources(self):
        srcs = [
            Source.from_bibtex('@' + s)
            for s in self.path('sources.bib').read_text(encoding='utf8').split('@') if s.strip()]
        return {src['key']: src for src in srcs}

    @lazyproperty
    def experiments(self):
        return [
            Experiment.from_dict(d, self.sources)
            for d in list(dsv.reader(self.path('data.Sheet1.csv'), dicts=True))[1:]]
