"""
Retrieve and display information from GBIF for all species in the dataset
"""
def register(parser):
    parser.add_argument('-U', '--update', default=False, action='store_true')


def run(args):
    if args.update:
        args.api.update_gbif()
    args.api.tree()
