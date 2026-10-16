"""Validated operational settings. Provider credentials belong to official clients."""
from dataclasses import dataclass, field, InitVar
import json
import math
import os
from pathlib import Path
import tempfile


DEFAULT_MODELS = {
    'easy': {'model': 'haiku-5.5', 'effort': 'medium'},
    'medium': {'model': 'sonnet-5.5', 'effort': 'high'},
    'hard': {'model': 'sonnet-5.5', 'effort': 'xhigh'},
    'qa': {'model': 'sonnet-5.5', 'effort': 'high'},
    'exceptional': {'model': 'opus-5.5', 'effort': 'max'},
}


@dataclass
class Settings:
    data_dir: Path
    roots: tuple[Path, ...] = ()
    validate_roots: InitVar[bool] = True
    max_active_jobs: int = 3
    max_ai_calls: int = 2
    max_opus_calls: int = 1
    scan_interval: float = 5.0
    stable_seconds: float = 10.0
    attempt_timeout: float = 1200.0
    gateway_url: str = 'http://localhost:20128/v1'
    default_difficulty: str = 'auto'
    individual_output: bool = False
    individual_destination: str | None = None
    retry_seconds: float = 60.0
    shutdown_seconds: float = 10.0
    output_timeout: float = 120.0
    gateway_model: str = ''
    gateway_effort: str = 'high'
    models: dict = field(default_factory=lambda: {k: dict(v) for k, v in DEFAULT_MODELS.items()})

    def __post_init__(self, validate_roots=True):
        self.data_dir = Path(self.data_dir).expanduser().resolve()
        try:
            self.roots = tuple(dict.fromkeys(Path(p).expanduser().resolve(strict=validate_roots) for p in self.roots))
        except OSError as exc:
            raise ValueError('Source root does not exist') from exc
        if validate_roots and any(not root.is_dir() for root in self.roots):
            raise ValueError('Source roots must be directories')
        for name, maximum in [('max_active_jobs', 3), ('max_ai_calls', 3), ('max_opus_calls', 1)]:
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f'{name} must be an integer between 1 and {maximum}')
        for name in ('scan_interval', 'stable_seconds', 'attempt_timeout', 'retry_seconds', 'shutdown_seconds', 'output_timeout'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be positive and finite')
        if self.default_difficulty not in {'auto', 'easy', 'medium', 'hard'}:
            raise ValueError('Unsupported difficulty')
        if type(self.individual_output) is not bool:
            raise ValueError('individual_output must be boolean')
        if self.individual_destination is not None:
            destination = Path(self.individual_destination).expanduser().resolve(strict=validate_roots)
            if validate_roots and not destination.is_dir():
                raise ValueError('Individual destination must be a directory')
            self.individual_destination = str(destination)
        if not isinstance(self.gateway_model, str) or len(self.gateway_model) > 200 or any(ord(c) < 32 for c in self.gateway_model):
            raise ValueError('Invalid gateway model')
        if self.gateway_effort not in {'medium','high','xhigh','max'}:
            raise ValueError('Unsupported gateway effort')
        from urllib.parse import urlsplit
        parsed = urlsplit(self.gateway_url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('gateway_url must be a credential-free HTTP URL')
        if set(self.models) != set(DEFAULT_MODELS):
            raise ValueError('Models must configure easy, medium, hard, qa and exceptional')
        if self.models.get('qa') != DEFAULT_MODELS['qa']:
            raise ValueError('Independent Claude QA requires sonnet-5.5/high')
        for entry in self.models.values():
            if set(entry) != {'model', 'effort'} or entry['model'] not in {'haiku-5.5', 'sonnet-5.5', 'opus-5.5'} or entry['effort'] not in {'medium', 'high', 'xhigh', 'max'}:
                raise ValueError('Unsupported model or effort')

    def public_dict(self) -> dict:
        return {
            'roots': [str(root) for root in self.roots],
            **{name: getattr(self, name) for name in ('max_active_jobs', 'max_ai_calls', 'max_opus_calls', 'scan_interval', 'stable_seconds', 'attempt_timeout', 'gateway_url', 'default_difficulty', 'individual_output', 'individual_destination', 'retry_seconds', 'shutdown_seconds', 'gateway_model', 'gateway_effort', 'output_timeout')},
            'models': {key: dict(value) for key, value in self.models.items()},
        }

    def save(self) -> Path:
        # Revalidate objects that have been changed by the settings API.
        self.__post_init__()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        destination = self.data_dir / 'settings.json'
        fd, temporary = tempfile.mkstemp(prefix='.settings-', dir=self.data_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(self.public_dict(), stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return destination

    @classmethod
    def load(cls, data_dir: Path, *, validate_roots: bool = True) -> 'Settings':
        directory = Path(data_dir).expanduser().resolve()
        path = directory / 'settings.json'
        return cls(data_dir=directory, validate_roots=validate_roots, **(json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}))
