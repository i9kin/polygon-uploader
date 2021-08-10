# authentication using polygon_cli config
# https://github.com/niyaznigmatullin/polygon-uploader/blob/master/polygon_uploader/common/authentication.py
# https://github.com/kunyavskiy/polygon-cli/blob/master/polygon_cli/config.py
# TODO: ADD LKSH
import os

import yaml
from polygon_api import Polygon

MAIN_POLYGON_URL = 'https://polygon.codeforces.com'


def authenticate():
    polygon_name = 'main'
    authentication_file = os.path.join(
        os.path.expanduser('~'),
        '.config',
        'polygon-cli',
        'auth.yaml',
    )
    if os.path.exists(authentication_file):
        with open(authentication_file, 'r') as cfg:
            auth_data = yaml.load(cfg, Loader=yaml.BaseLoader)
        if auth_data.get('version') is None:
            with open(authentication_file, 'w') as fo:
                auth_data = {
                    'version': 1,
                    'polygons': {
                        'main': {
                            'url': MAIN_POLYGON_URL,
                            'login': auth_data.get('login'),
                            'password': auth_data.get('password'),
                            'api_key': auth_data.get('api_key'),
                            'api_secret': auth_data.get('api_secret'),
                        },
                    },
                }
                yaml.dump(auth_data, fo, default_flow_style=False)
        auth_data_by_name = auth_data.get('polygons').get(polygon_name)
        if auth_data_by_name:
            polygon_url = auth_data_by_name.get('url')
            api_key = auth_data_by_name.get('api_key')
            api_secret = auth_data_by_name.get('api_secret')
        return Polygon(polygon_url + '/api', api_key, api_secret)
