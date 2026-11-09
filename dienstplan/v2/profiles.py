"""Explizite Profilversionen; fehlende betriebliche Freigabe bleibt sichtbar."""
from dataclasses import dataclass
import json

from .contracts import DateRange
from .errors import DomainError


@dataclass(frozen=True, slots=True)
class Source:
    reference: str
    location: str
    document_hash: str

    def __post_init__(self):
        if not self.reference or not self.location or len(self.document_hash)!=64 or any(c not in '0123456789abcdef' for c in self.document_hash):
            raise DomainError("Profilquelle benötigt Fundstelle und SHA-256 des Originaldokuments.")


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    kind: str
    scope: str
    dates: DateRange
    parameters_json: str
    sources: tuple[Source, ...] = ()
    confirmed: bool = False
    synthetic: bool = False

    def __post_init__(self):
        object.__setattr__(self,'sources',tuple(self.sources))
        if not self.id or not self.kind or not self.scope:
            raise DomainError("Profil benötigt Kennung, Art und konkreten Anwendungsbereich.")
        if type(self.confirmed) is not bool or type(self.synthetic) is not bool:
            raise DomainError("Profilstatus muss ausdrücklich boolesch angegeben werden.")
        try:
            values=json.loads(self.parameters_json,parse_float=lambda _: (_ for _ in ()).throw(ValueError('Float')),
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nicht endlich')))
        except (ValueError,TypeError) as exc:
            raise DomainError("Profilwerte als exaktes JSON mit Dezimaltext statt Float angeben.") from exc
        if not isinstance(values,dict):
            raise DomainError("Profilparameter müssen ein benanntes JSON-Objekt sein.")
        if self.confirmed and not self.synthetic and not self.sources:
            raise DomainError("Betriebliche Profilbestätigung benötigt belegte Quellen.")
        object.__setattr__(self,'parameters_json',json.dumps(values,ensure_ascii=False,sort_keys=True,separators=(',',':')))

    @property
    def parameters(self):
        return json.loads(self.parameters_json)


@dataclass(frozen=True, slots=True)
class Profiles:
    versions: tuple[Profile, ...]

    def __post_init__(self):
        object.__setattr__(self,'versions',tuple(self.versions))
        if len({p.id for p in self.versions})!=len(self.versions):
            raise DomainError("Profilkennungen müssen eindeutig sein.")
        for i,a in enumerate(self.versions):
            for b in self.versions[i+1:]:
                if (a.kind,a.scope)==(b.kind,b.scope) and a.dates.start<b.dates.end and b.dates.start<a.dates.end:
                    raise DomainError("Profilversionen gleicher Art und Anwendung dürfen sich nicht überlappen.")

    def select(self,kind,scope,day,*,allow_synthetic=False):
        matching=[p for p in self.versions if p.kind==kind and p.scope==scope and p.dates.includes(day)]
        if not matching:
            raise DomainError(f"Kein zeitgültiges Profil für {kind}/{scope} am {day}; Bewertung ungeklärt.")
        selected=matching[0]
        if selected.synthetic:
            if not allow_synthetic:
                raise DomainError("Synthetisches Testprofil ist keine produktive Freigabe.")
        elif not selected.confirmed:
            raise DomainError("Profil ist noch nicht betrieblich bestätigt; Bewertung ungeklärt.")
        return selected
