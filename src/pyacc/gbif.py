"""
Functionality to retrieve data from GBIF.
"""
import requests


class GBIF:
    api_url = 'https://api.gbif.org/v1'

    def _req(self, path, **params):
        return requests.get(self.api_url + path, params=params).json()

    def species_key(self, name):
        return self._req('/species/match/', name=name)['usageKey']

    def species_data(self, species):
        if isinstance(species, str):
            species = self.species_key(species)
        return species, self._req('/species/{}'.format(species))
