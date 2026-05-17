from pathlib import Path
import os
import logging
import logging.config
import configparser
import platform

class SingletonLogger:
    _instances = {}
    _configured = False

    @classmethod
    def configure(cls):
        project_root = Path(__file__).resolve().parents[1]
        config_dir = project_root / 'config'
        core_config_path = config_dir / 'core_config.ini'
        logger_ini_path = config_dir / 'logger.ini'

        if not core_config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {core_config_path}")
        if not logger_ini_path.exists():
            raise FileNotFoundError(f"Logger configuration file not found: {logger_ini_path}")

        # Load config
        config = configparser.ConfigParser()
        config.read(str(core_config_path))

        environment = config['environment']['current'].lower()
        logger_section = f'logger_path_{environment}'

        if logger_section not in config:
            raise ValueError(f"Missing section [{logger_section}] in core_config.ini")

        system = platform.system()
        log_dir_key = 'WIN_LOG_DIR' if system == 'Windows' else 'LIN_LOG_DIR'

        section = config[logger_section]
        log_dir_value = section.get(log_dir_key, section.get('log_dir'))
        if not log_dir_value:
            raise ValueError(f"Missing key '{log_dir_key}' or 'log_dir' under section [{logger_section}]")

        # Prepare directory
        log_dir = Path(log_dir_value)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Full paths
        info_log_file_path = (log_dir / "drs_incident_monitor_info.log").as_posix()
        error_log_file_path = (log_dir / "drs_case_monitor_error.log").as_posix()

        print(f"[DEBUG] Environment: {environment}")
        print(f"[DEBUG] System: {system}")
        print(f"[DEBUG] Log directory: {log_dir}")
        print(f"[DEBUG] Info log file path: {info_log_file_path}")
        print(f"[DEBUG] Error log file path: {error_log_file_path}")

        # Load logger.ini and pass dynamic file name
        try:
            logging.config.fileConfig(
                str(logger_ini_path),
                defaults={
                    'logfilename': info_log_file_path,
                    'logfilename_info': info_log_file_path,
                    'logfilename_error': error_log_file_path,
                },
                disable_existing_loggers=False
            )
        except Exception as e:
            print(f"[ERROR] Failed to configure logging: {e}")
            raise

        cls._configured = True
        print(
            f"[SingletonLogger] Logger configured → {info_log_file_path} / {error_log_file_path} "
            f"(env: {environment})"
        )
        # --- Reduce noisy loggers ---
        logging.getLogger("pymongo").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

  

    @classmethod
    def get_logger(cls, logger_name='appLogger'):
        if not cls._configured:
            cls.configure()
        if logger_name not in cls._instances:
            cls._instances[logger_name] = logging.getLogger(logger_name)
        return cls._instances[logger_name]


