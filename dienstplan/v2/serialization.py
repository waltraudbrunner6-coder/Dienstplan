"""Stabile Eingabefingerprints ohne Float- oder Mengenreihenfolgezufall."""
from dataclasses import fields,is_dataclass
from datetime import date,datetime,time
from fractions import Fraction
from hashlib import sha256
import json


def plain(value):
    if is_dataclass(value):return {f.name:plain(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,(datetime,date,time)):return value.isoformat()
    if isinstance(value,Fraction):return {'numerator':value.numerator,'denominator':value.denominator}
    if isinstance(value,dict):return {str(k):plain(v) for k,v in sorted(value.items(),key=lambda kv:str(kv[0]))}
    if isinstance(value,(set,frozenset)):
        return sorted((plain(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
    if isinstance(value,(tuple,list)):return [plain(v) for v in value]
    if value is None or type(value) in (str,int,bool):return value
    raise TypeError(f'Nicht unterstützter exakter Snapshotwert: {type(value).__name__}')


def fingerprint(value):
    return sha256(json.dumps(plain(value),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
