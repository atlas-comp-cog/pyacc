"""
Citation:
Upham, N. S., J. A. Esselstyn, and W. Jetz. 2019.
Inferring the mammal tree:
species-level sets of phylogenies for questions in ecology, evolution, and conservation.
PLOS Biology. https://doi.org/10.1371/journal.pbio.3000494

Downloaded MCC consensus trees of the completed trees from
https://github.com/n8upham/MamPhy_v1/blob/master/_DATA/MamPhy_fullPosterior_BDvr_Completed_5911sp_topoCons_NDexp_MCC_v2_target.tre

import dendropy

tree = dendropy.Tree.get_from_path("mammals.tre", "nexus")
pdm = tree.phylogenetic_distance_matrix()
hs = [n for n in tree.taxon_namespace if 'sapiens' in n.label][0]
ordered = [tax.label for tax in sorted(tree.taxon_namespace, key=lambda t: pdm(hs, t))
with open('mammals_ordered.csv', 'w', encoding='utf8') as fp:
    for t in ordered:
        comps = t.strip().split()
        if len(comps) >= 3:
            fp.write('{},{},{}\n'.format(' '.join(comps[:-2]), comps[-2], comps[-1]))

"""
import string
import collections

from clldutils.clilib import PathType
from clldutils.jsonlib import dump
from csvw.dsv import reader


def register(parser):
    parser.add_argument('ordered', type=PathType(type='file'))


def run(args):
    ordered = [d['species'].lower() for d in reader(args.ordered, dicts=True)]
    ranks = ['phylum', 'klass', 'order', 'family', 'genus']

    ordered_ranks = {r: {} for r in ranks}
    seen = {}
    augmented_species = []
    for ex in args.api.experiments:
        species = ex.gbif.cname
        if species not in seen:
            seen[species] = (ex.gbif.classification, ex.species_latin)
            skey = species.lower()
            if skey not in ordered:
                skey = ' '.join(skey.split()[:2])
            if skey not in ordered:
                skey = [n for n in ordered if n.split()[0] == skey.split()[0]]
                if skey:
                    skey = skey[0]

            if skey in ordered:
                augmented_species.append((species, ordered.index(skey)))
            else:
                augmented_species.append((species, len(ordered) + 1))

    for s, i in sorted(augmented_species, key=lambda t: t[1], reverse=True):
        for r in ranks:
            ordered_ranks[r][getattr(seen[s][0], r)] = i

    fully_augmented_species = {
        s: (
            ordered_ranks['phylum'][seen[s][0].phylum],
            ordered_ranks['klass'][seen[s][0].klass],
            ordered_ranks['order'][seen[s][0].order],
            ordered_ranks['family'][seen[s][0].family],
            ordered_ranks['genus'][seen[s][0].genus],
            i)
        for s, i in sorted(augmented_species, key=lambda t: t[1])
    }
    clf = collections.defaultdict(lambda: [-1, None])
    prefix = {}
    for k, _ in sorted(fully_augmented_species.items(), key=lambda i: i[1], reverse=True):
        for j, a in enumerate(ranks):
            if clf[a][1] != getattr(seen[k][0], a):
                for aa in ranks[j + 1:]:
                    clf[aa][0] = -1
                if a == 'genus':
                    # reset prefix index for all deeper taxonomy ranks:
                    clf['species'][0] = -1
                clf[a][0] += 1
                clf[a][1] = getattr(seen[k][0], a)
                node_name = '_'.join(getattr(seen[k][0], aa) for aa in ranks[:j + 1])
                prefix[node_name] = string.ascii_lowercase[clf[a][0]]
        if clf['species'][1] != k:
            clf['species'][0] += 1
            clf['species'][1] = k
            prefix[k.lower()] = string.ascii_lowercase[clf['species'][0]]
    dump(prefix, args.api.path('taxa_sortkeys.json'), indent=4)
