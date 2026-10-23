"""Prepare only a new server package's config; never switch an existing database."""
import os
from importlib.resources import files
from pathlib import Path
from xml.etree import ElementTree as ET

from pyasm.common.config import read_config_file, save_config_file


def prepare(data_dir):
    data_dir = Path(data_dir).resolve()
    path = data_dir / 'config/tactic-conf.xml'
    if path.exists():
        text, _ = read_config_file(path)
        if ET.fromstring(text).findtext('./database/vendor') == 'PostgreSQL':
            return
        raise FileExistsError('Existing non-PostgreSQL configuration: use migration; initialization will not replace it')
    if (data_dir / 'db').exists():
        raise FileExistsError('Existing server data/configuration: use upgrade or restore; initialization will not replace it')
    text = files('tactic_stream').joinpath('config/tactic-conf.xml').read_text(encoding='utf-8')
    root = ET.fromstring(text, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    database = root.find('database')
    database.clear()
    for name, value in dict(vendor='PostgreSQL', sobject_database='sthpw', host='postgres',
                            port='5432', user='stream', password_file='/run/secrets/postgres_password').items():
        ET.SubElement(database, name).text = value
    root.find('./install/hostname').text = '0.0.0.0'
    root.find('./checkin/asset_base_dir').text = (data_dir / 'assets').as_posix()
    path.parent.mkdir(parents=True, exist_ok=True)
    save_config_file(path, ET.tostring(root, encoding='unicode'), expected_revision=None)


if __name__ == '__main__':
    prepare(os.environ['TACTIC_DATA_DIR'])
