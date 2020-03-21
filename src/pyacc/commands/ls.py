"""

"""
from clldutils.clilib import Table, add_format


def register(parser):
    add_format(parser)


def run(args):
    with Table(args, 'DOI', 'topic') as t:
        for ex in args.api.experiments:
            t.append([ex.doi, ex.parameter])
