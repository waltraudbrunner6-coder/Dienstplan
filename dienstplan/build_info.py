"""Offline lesbare Paketkennung; im Quellcheckout ohne Git-Aufruf nutzbar."""
import json
from importlib.resources import files

from . import __version__


def build_info():
    try:
        value=json.loads(files('dienstplan').joinpath('build-info.json').read_text(encoding='utf-8'))
        if (value.get('version')!=__version__ or not isinstance(value.get('commit'),str)
                or len(value['commit'])!=40 or any(c not in '0123456789abcdef' for c in value['commit'])
                or type(value.get('dirty')) is not bool):
            raise ValueError('Ungültige Paketkennung')
        return value
    except (OSError,ValueError,TypeError):
        return dict(version=__version__,commit=None,dirty=None,build_time_utc=None)


def build_label():
    info=build_info()
    stand=('Build '+info['commit'][:7]+(' mit lokalen Änderungen' if info['dirty'] else '')) if info['commit'] else 'Quellcode – kein Paketbuild'
    return f'Dienstplan V2 · Version {info["version"]} · {stand}'
