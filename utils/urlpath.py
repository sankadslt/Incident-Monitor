from pathlib import Path
import configparser
import os
from urllib.parse import urljoin


class SingletonUrlPath:
    _configured = False
    _instance = None

    def __init__(self, environment: str, api_bases: dict[str, str]):
        self._environment = environment
        self._api_bases = {k.lower(): (v.strip() if isinstance(v, str) else '') for k, v in api_bases.items()}

    @classmethod
    def configure(cls):
        project_root = Path(__file__).resolve().parents[1]
        config_dir = project_root / 'config'
        corefig_path = config_dir / 'core_config.ini'

        if not corefig_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {corefig_path}")

        config = configparser.ConfigParser()
        config.read(str(corefig_path))

        if 'environment' not in config or 'current' not in config['environment']:
            raise ValueError("Missing [environment] section or 'current' key in core_config.ini")

        environment = config['environment']['current'].lower()
        api_section = f'api_urls_{environment}'

        if api_section not in config:
            raise ValueError(f"Missing section [{api_section}] in core_config.ini")

        # Load all key/value pairs from the section as API base URLs
        api_bases = {k: v for k, v in config[api_section].items()}

        # Basic validation for common keys if present
        for key, url in api_bases.items():
            if not isinstance(url, str) or not url.startswith('http'):
                # Allow empty placeholders but surface a clear error if used later
                pass

        cls._instance = SingletonUrlPath(environment=environment, api_bases=api_bases)
        cls._configured = True

    @classmethod
    def get(cls) -> 'SingletonUrlPath':
        if not cls._configured or cls._instance is None:
            raise ValueError("UrlPath not configured. Please call 'configure()' first.")
        return cls._instance

    # Convenience accessors
    def get_environment(self) -> str:
        return self._environment

    def get_base_url(self, key: str) -> str:
        val = self._api_bases.get(key.lower())
        if not val:
            raise ValueError(f"API base URL for key '{key}' not configured in section [api_urls_{self._environment}]")
        return val

    def build_url(self, key: str, path: str) -> str:
        base = self.get_base_url(key)
        return urljoin(base.rstrip('/') + '/', path.lstrip('/'))

    # Specific helpers for common APIs
    def get_email_api_url(self) -> str:
        env_override = os.getenv('EMAIL_API_URL', '').strip()
        if env_override:
            return env_override.rstrip('/')
        return self.get_base_url('EMAIL_API_URL')

    def get_sms_api_url(self) -> str:
        return self.get_base_url('SMS_API_URL')

    def build_email_url(self, path: str) -> str:
        return self.build_url('EMAIL_API_URL', path)

    def build_sms_url(self, path: str) -> str:
        return self.build_url('SMS_API_URL', path)

