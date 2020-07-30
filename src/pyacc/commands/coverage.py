"""
Compare ACC coverage against the GBIF backbone taxonomy.

GBIF Secretariat (2019). GBIF Backbone Taxonomy. Checklist dataset https://doi.org/10.15468/39omei
accessed via GBIF.org on 2020-06-18.

Notes:
- download the source archive (https://hosted-datasets.gbif.org/datasets/backbone/backbone-current.zip)
- extract
- pass path to Taxon.tsv as "taxa" argument.
"""
import collections

import attr
from clldutils.clilib import PathType

from clldutils import jsonlib
from pyacc.api import Classification


class Taxa(dict):
    def add(self, t):
        if isinstance(t, Classification):
            t = attr.asdict(t)
            t['class'] = t.pop('klass')
        if t['phylum'] not in self:
            self[t['phylum']] = {}
        if t['class'] not in self[t['phylum']]:
            self[t['phylum']][t['class']] = {}
        if t['order'] not in self[t['phylum']][t['class']]:
            self[t['phylum']][t['class']][t['order']] = {}
        if t['family'] not in self[t['phylum']][t['class']][t['order']]:
            self[t['phylum']][t['class']][t['order']][t['family']] = {}
        if t['genus'] not in self[t['phylum']][t['class']][t['order']][t['family']]:
            self[t['phylum']][t['class']][t['order']][t['family']][t['genus']] = 0
        self[t['phylum']][t['class']][t['order']][t['family']][t['genus']] += 1


def register(parser):
    parser.add_argument('taxa', type=PathType(type='file'))


def run(args):
    acc = Taxa()
    seen = set()
    for ex in args.api.experiments:
        species = ex.gbif.name
        if species not in seen:
            seen.add(species)
            acc.add(ex.gbif.classification)
    #print(acc)
    gbif, head = Taxa(), None
    for i, line in enumerate(args.taxa.open(encoding='utf8').readlines()):
        if i == 0:
            head = line.strip().split('\t')
            continue
        cols = line.strip().split('\t')
        d = dict(zip(head, cols))

        if d['kingdom'] != 'Animalia':
            continue
        if d['taxonomicStatus'] != 'accepted':
            continue
        if d['taxonRank'] != 'species':
            continue
        if 'genus' in d:
            gbif.add(d)

    coverage = collections.OrderedDict()
    for phylum, classes in acc.items():
        print('Phylum {}: {}/{} classes'.format(phylum, len(classes), len(gbif[phylum])))
        coverage[(phylum,)] = (len(classes), len(gbif[phylum]))
        for klass, orders in classes.items():
            print('  Class {}: {}/{} orders'.format(klass, len(orders), len(gbif[phylum][klass])))
            coverage[(phylum, klass)] = (len(orders), len(gbif[phylum][klass]))
            for order, families in orders.items():
                print('    Order {}: {}/{} families'.format(order, len(families), len(gbif[phylum][klass][order])))
                coverage[(phylum, klass, order)] = (len(families), len(gbif[phylum][klass][order]))
                for family, genera in families.items():
                    print('      Family {}: {}/{} genera'.format(family, len(genera), len(gbif[phylum][klass][order][family])))
                    coverage[(phylum, klass, order, family)] = (len(genera), len(gbif[phylum][klass][order][family]))
                    for genus, nspec in genera.items():
                        print('        Genus {}: {}/{} species'.format(
                            genus, nspec, gbif[phylum][klass][order][family].get(genus)))
                        coverage[(phylum, klass, order, family, genus)] = (nspec, gbif[phylum][klass][order][family][genus])
    coverage = collections.OrderedDict([('_'.join(k), v) for k, v in coverage.items()])
    jsonlib.dump(coverage, args.api.path('gbif_coverage.json'), indent=4)
