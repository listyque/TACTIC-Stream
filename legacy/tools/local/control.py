"""Shared controller for three local TACTIC launchers. Standard library only; delegates to original tools.

Does not import TACTIC while displaying a menu, saving launch preferences or
planning a command. No database initialization/migration runs automatically.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
PROFILE_NAME = 'launcher.local.json'
PROFILE_KEYS = {'format', 'python', 'data_dir', 'config', 'port', 'workers', 'mode'}
BOOTSTRAP_ARGV = 'TACTIC_BOOTSTRAP_ARGV_JSON'
LAUNCH_FLAGS = {
    'check:env': '--check', 'check:db': '--check-local-db',
    'check:startup': '--check-startup', 'db:init': '--init-sqlite',
    'db:upgrade': '--upgrade-local', 'db:restore': '--restore-local',
}


def clean_path(value: str, root: Path = ROOT) -> str:
    """Paths are data, never shell commands. Relative paths follow the source root."""
    if not isinstance(value, str):
        raise ValueError('Путь должен быть строкой.')
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    if not value or any(ord(c) < 32 for c in value) or '"' in value:
        raise ValueError('Пустой путь, управляющие символы или кавычки внутри пути.')
    p = Path(value).expanduser()
    return os.path.abspath(p if p.is_absolute() else root / p)


def checked_int(value: object, name: str, low: int, high: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f'{name}: требуется целое число {low}..{high}.')
    try:
        result = int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{name}: требуется целое число {low}..{high}.') from exc
    if str(result) != str(value) or not low <= result <= high:
        raise ValueError(f'{name}: требуется целое число {low}..{high}.')
    return result


def validate_profile(value: object, root: Path = ROOT) -> dict:
    if not isinstance(value, dict) or set(value) - PROFILE_KEYS or type(value.get('format')) is not int or value.get('format') != 1:
        raise ValueError(f'Неверный формат {PROFILE_NAME}; файл не изменён. Нужен format=1 и только известные поля.')
    result = {'format': 1}
    for name in ('python', 'data_dir', 'config'):
        v = value.get(name)
        if v is not None:
            result[name] = clean_path(v, root)
    for name, low, high in (('port', 1024, 65535), ('workers', 2, 8)):
        if name in value:
            result[name] = checked_int(value[name], name, low, high)
    if 'mode' in value:
        if value['mode'] not in ('cluster', 'single', 'legacy'):
            raise ValueError('mode: cluster, single или legacy.')
        result['mode'] = value['mode']
    return result


def read_profile(root: Path = ROOT) -> tuple[dict, str | None]:
    path = root / PROFILE_NAME
    if not path.exists():
        return {'format': 1}, None
    if not path.is_file() or path.stat().st_size > 16384:
        raise ValueError(f'{PROFILE_NAME}: ожидался небольшой JSON-файл; ничего не перезаписано.')
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode('utf-8-sig'))
    except (ValueError, UnicodeError) as exc:
        raise ValueError(f'{PROFILE_NAME}: ошибка JSON; исправьте или переименуйте файл, не базу данных.') from exc
    return validate_profile(value, root), hashlib.sha256(raw).hexdigest()


def save_profile(root: Path, value: dict, expected: str | None) -> None:
    value = validate_profile(value, root)
    path = root / PROFILE_NAME
    current = path.read_bytes() if path.exists() else None
    digest = hashlib.sha256(current).hexdigest() if current is not None else None
    if digest != expected:
        raise ValueError('Параметры запуска изменены другим редактором. Перечитайте их перед сохранением.')
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    fd, temporary = tempfile.mkstemp(prefix='.launcher-', suffix='.tmp', dir=root)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        if current is not None:
            backup = root / (PROFILE_NAME + '.previous')
            with backup.open('wb') as stream:
                stream.write(current)
            try: backup.chmod(0o600)
            except OSError: pass
        # Recheck immediately before replace; not a distributed CAS guarantee.
        now = path.read_bytes() if path.exists() else None
        if now != current:
            raise ValueError('Параметры запуска изменились; новый файл не установлен.')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='MANAGE_TACTIC.bat', description='Общий контроллер START_TACTIC / SETUP_ENV / MANAGE_TACTIC. Без аргументов — меню обслуживания.', allow_abbrev=False)
    common = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    common.add_argument('--data-dir', help='Существующий каталог данных; для db init — новый пустой каталог')
    common.add_argument('--config', help='Существующий tactic-conf.xml; не переписывается')
    common.add_argument('--python', help='Путь к совместимому Python для дочерних команд')
    common.add_argument('--dry-run', action='store_true', help='Только показать команду, без запуска и записи файлов')
    sub = p.add_subparsers(dest='command')
    def runtime_options(parser):
        parser.add_argument('--port', type=int)
        parser.add_argument('--workers', type=int)
        parser.add_argument('--worker-base-port', type=int)
        parser.add_argument('--timeout', type=int)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--mode', choices=['cluster', 'single', 'legacy'])
        mode.add_argument('--single', action='store_true', help='Один процесс вместо группы')
        mode.add_argument('--legacy', action='store_true', help='Один процесс со старым веб-интерфейсом')
    start = sub.add_parser('start', parents=[common], help='Запустить сервер (по умолчанию 3 процесса)', allow_abbrev=False)
    runtime_options(start)
    menu = sub.add_parser('menu', parents=[common], help='Меню обслуживания; сервер автоматически не запускается', allow_abbrev=False)
    runtime_options(menu)
    check = sub.add_parser('check', parents=[common], help='Проверка: env, db или startup', allow_abbrev=False)
    check.add_argument('kind', nargs='?', default='env', choices=['env', 'db', 'startup'])
    db = sub.add_parser('db', parents=[common], help='Явное обслуживание managed SQLite', allow_abbrev=False)
    db.add_argument('kind', choices=['init', 'upgrade', 'restore'])
    config = sub.add_parser('configure', parents=[common], help='Настройки записи/загрузки/исполнения скриптов', allow_abbrev=False)
    for name in ('writes', 'uploads', 'scripts'): config.add_argument('--' + name, choices=['on', 'off'])
    settings = sub.add_parser('settings', parents=[common], help='Показать/сохранить пути и режим запуска', allow_abbrev=False)
    settings.add_argument('--port', type=int); settings.add_argument('--workers', type=int)
    settings.add_argument('--mode', choices=['cluster', 'single', 'legacy'])
    settings.add_argument('--save', action='store_true', help='Сохранить указанные параметры в launcher.local.json')
    setup = sub.add_parser('setup', help='Скачать локальное окружение, не трогая базы', allow_abbrev=False)
    setup.add_argument('--repair', '-Repair', action='store_true')
    setup.add_argument('--offline', '-Offline', action='store_true')
    setup.add_argument('--dry-run', action='store_true')
    build = sub.add_parser('build', help='Пересобрать уже включённый Vue (нужен Node)', allow_abbrev=False)
    build.add_argument('--dry-run', action='store_true')
    return p


def parse(argv: list[str]) -> argparse.Namespace:
    argv = list(argv)
    if argv and argv[0].lower() in ('help', '/?'):
        argv = ['--help']
    commands = ('start', 'menu', 'check', 'db', 'configure', 'settings', 'setup', 'build')
    if not argv:
        argv = ['menu']
    elif argv[0].lower() in commands:
        argv[0] = argv[0].lower()
    elif argv[0].startswith('--') and argv[0] != '--help':
        argv.insert(0, 'menu')
    return make_parser().parse_args(argv)


def effective(args: argparse.Namespace, profile: dict, root: Path = ROOT, env: dict | None = None) -> dict:
    env = os.environ if env is None else env
    selected_python = getattr(args, 'python', None) or env.get('TACTIC_PYTHON') or profile.get('python') or sys.executable
    explicit_data = getattr(args, 'data_dir', None)
    explicit_config = getattr(args, 'config', None)
    # An explicit new data directory must not silently retain an unrelated
    # old config path. With --config alone follow the original launcher rule.
    if explicit_data:
        data = clean_path(explicit_data, root)
    elif explicit_config:
        config_path = Path(clean_path(explicit_config, root))
        if config_path.parent.name.lower() != 'config':
            raise ValueError('Для внешнего --config вне папки config укажите --data-dir явно.')
        data = str(config_path.parent.parent)
    else:
        data = profile.get('data_dir', str(root / 'local_data'))
    config = clean_path(explicit_config, root) if explicit_config else (None if explicit_data else profile.get('config'))
    mode = 'legacy' if getattr(args, 'legacy', False) else 'single' if getattr(args, 'single', False) else getattr(args, 'mode', None) or profile.get('mode', 'cluster')
    result = {
        'python': clean_path(selected_python, root), 'data_dir': data,
        'config': config, 'mode': mode,
        'port': checked_int(getattr(args, 'port', None) if getattr(args, 'port', None) is not None else profile.get('port', 9123), 'port', 1024, 65535),
        'workers': checked_int(getattr(args, 'workers', None) if getattr(args, 'workers', None) is not None else profile.get('workers', 3), 'workers', 2, 8),
    }
    return result


@dataclass(frozen=True)
class Plan:
    argv: list[str]
    cwd: str
    note: str
    python: str | None = None


def plan_command(args: argparse.Namespace, cfg: dict, root: Path = ROOT) -> Plan:
    command = args.command
    python = cfg['python']
    prefix = [python, '-X', 'utf8', '-s']
    local = root / 'tools/local'
    scope = ['--data-dir', cfg['data_dir']]
    if cfg.get('config'): scope += ['--config', cfg['config']]
    if command == 'start':
        if cfg['mode'] == 'cluster':
            base = args.worker_base_port if args.worker_base_port is not None else cfg['port'] + 1
            checked_int(base, 'worker-base-port', 1024, 65535)
            if base + cfg['workers'] - 1 > 65535 or base <= cfg['port'] < base + cfg['workers']:
                raise ValueError('Порты шлюза и workers должны быть различны и не превышать 65535.')
            timeout = 300 if args.timeout is None else checked_int(args.timeout, 'timeout', 10, 3600)
            tail = scope + ['--port', str(cfg['port']), '--workers', str(cfg['workers']), '--timeout', str(timeout)]
            if args.worker_base_port is not None: tail += ['--worker-base-port', str(base)]
            return Plan(prefix + [str(local / 'cluster.py')] + tail, str(root), 'Три процесса по умолчанию. Остановка всей группы: Ctrl+C.', python)
        if any(getattr(args, x, None) is not None for x in ('workers', 'worker_base_port', 'timeout')):
            raise ValueError('--workers/--worker-base-port/--timeout относятся только к кластеру.')
        tail = scope + ['--port', str(cfg['port'])]
        if cfg['mode'] == 'legacy': tail += ['--legacy']
        return Plan(prefix + [str(local / 'launch.py')] + tail, str(root), 'Один исходный сервер. Остановка: Ctrl+C.', python)
    if command in ('check', 'db'):
        if command == 'db' and cfg.get('config'):
            raise ValueError('db init/upgrade/restore предназначены для managed SQLite без внешнего --config.')
        notes = {
            'check:env': 'Только импорты; это не проверка БД.',
            'check:db': 'Read-only проверка managed SQLite; код 3 означает, что структура не готова.',
            'check:startup': 'Оригинальная инициализация может писать в БД. Сервер должен быть остановлен.',
            'db:init': 'Только новый пустой каталог. Исходные CREATE и ввод пароля обязательны.',
            'db:upgrade': 'Исходный staged-upgrade с резервной копией и подтверждением UPGRADE.',
            'db:restore': 'Только восстановление прерванной публикации; исходное подтверждение RESTORE.',
        }
        key = command + ':' + args.kind
        return Plan(prefix + [str(local / 'launch.py'), LAUNCH_FLAGS[key]] + scope, str(root), notes[key], python)
    if command == 'configure':
        if cfg.get('config') and Path(cfg['config']) != Path(cfg['data_dir']) / 'config/tactic-conf.xml':
            raise ValueError('configure ожидает исходную конфигурацию в <data-dir>/config/tactic-conf.xml.')
        tail = ['--data-dir', cfg['data_dir']]
        for flag in ('writes', 'uploads', 'scripts'):
            if getattr(args, flag, None) is not None: tail += ['--' + flag, getattr(args, flag)]
        return Plan(prefix + [str(local / 'configure_native.py')] + tail, str(root), 'Изменение разрешений требует исходного ENABLE/DISABLE и остановленного сервера.', python)
    if command == 'setup':
        exe = shutil.which('powershell.exe') or (shutil.which('pwsh') if os.name != 'nt' else None) or 'powershell.exe'
        tail = []
        if args.offline: tail.append('-Offline')
        if args.repair: tail.append('-Repair')
        return Plan([exe, '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(local / 'setup_env.ps1')] + tail, str(root), 'Только локальное окружение. Базы не инициализируются и не обновляются.')
    if command == 'build':
        return Plan([shutil.which('node') or 'node', str(root / 'tools/native_ui/build.cjs')], str(root), 'Node нужен для пересборки, но не для запуска готового UI.')
    raise ValueError('Неизвестная операция: ' + str(command))


def display_plan(plan: Plan, dry_run: bool = False) -> None:
    if dry_run:
        print(json.dumps({'dry_run': True, 'argv': plan.argv, 'cwd': plan.cwd, 'note': plan.note}, ensure_ascii=False, indent=2))
    else:
        print('\n' + plan.note)
        print(subprocess.list2cmdline(plan.argv) if os.name == 'nt' else shlex.join(plan.argv), flush=True)


def execute(plan: Plan) -> int:
    """Inherit the console, not PIPEs. Preserve status and native confirmations.

Ctrl+C reaches the whole console/process group. Wait for the original launcher
and its workers to finish their cleanup; never kill/restart them automatically.
"""
    if plan.python and not Path(plan.python).is_file():
        raise ValueError('Python не найден: ' + plan.python + '. Используйте SETUP_ENV.bat или задайте TACTIC_PYTHON.')
    if plan.python and os.name == 'nt' and Path(plan.python).suffix.lower() != '.exe':
        raise ValueError('Нужен python.exe, не BAT/CMD-команда.')
    env = os.environ.copy()
    env.pop(BOOTSTRAP_ARGV, None)
    env.pop('TACTIC_LAUNCH_ENTRY', None)
    env['PYTHONUTF8'] = '1'
    display_plan(plan)
    child = subprocess.Popen(plan.argv, cwd=plan.cwd, env=env, shell=False)
    previous = {}
    def stop(signum, frame):
        if child.poll() is None:
            try: child.send_signal(signum)
            except ProcessLookupError: pass
    if os.name != 'nt':
        previous[signal.SIGTERM] = signal.signal(signal.SIGTERM, stop)
    interrupted = False
    try:
        while True:
            try:
                code = child.wait()
                return code if code >= 0 else 128 - code
            except KeyboardInterrupt:
                if not interrupted:
                    print('\nОжидаю штатную остановку дочернего процесса. Данные не удаляются.', flush=True)
                    interrupted = True
    finally:
        for sig, handler in previous.items(): signal.signal(sig, handler)


def update_profile(args, cfg, profile, digest, root):
    value = dict(profile)
    for key in ('python', 'data_dir', 'config', 'port', 'workers', 'mode'):
        if getattr(args, key, None) is not None:
            value[key] = cfg[key]
    if args.data_dir and not args.config:
        value.pop('config', None)
    if args.config and not args.data_dir:
        value['data_dir'] = cfg['data_dir']
    if args.save:
        if args.dry_run:
            print(json.dumps({'dry_run': True, 'path': str(root / PROFILE_NAME), 'profile': value}, ensure_ascii=False, indent=2))
        else:
            if 'python' in value and not Path(value['python']).is_file(): raise ValueError('Указанный Python не существует.')
            if value.get('config') and not Path(value['config']).is_file(): raise ValueError('Указанный XML-файл не существует.')
            save_profile(root, value, digest)
            print('Параметры запуска сохранены в', root / PROFILE_NAME)
            print('База, tactic-conf.xml и права записи не изменялись.')
    else:
        print(json.dumps({'profile_file': str(root / PROFILE_NAME), 'saved': profile, 'effective': cfg}, ensure_ascii=False, indent=2))


def settings_menu(cfg, root, read: Callable[[str], str] = input):
    """One explicit profile; no scanning Downloads or guessing another database."""
    original, digest = read_profile(root)
    result = dict(cfg)
    print('\nПараметры только запуска. ENTER оставляет значение; «-» сбрасывает внешний XML.')
    for key, label in [('python', 'Python'), ('data_dir', 'Каталог данных'), ('config', 'Внешний tactic-conf.xml')]:
        text = read(f'{label} [{result.get(key) or "по каталогу данных"}]: ').strip()
        if key == 'config' and text == '-': result[key] = None
        elif text:
            result[key] = clean_path(text, root)
            if key == 'data_dir' and result[key] != cfg['data_dir']:
                result['config'] = None
    for key, label, low, high in [('port', 'Порт', 1024, 65535), ('workers', 'Процессов в группе', 2, 8)]:
        text = read(f'{label} [{result[key]}]: ').strip()
        if text: result[key] = checked_int(text, key, low, high)
    text = read(f'Режим cluster/single/legacy [{result["mode"]}]: ').strip()
    if text: result['mode'] = text
    result = validate_profile(dict(result, format=1), root)
    if not Path(result['python']).is_file(): raise ValueError('Python не найден.')
    if result.get('config') and not Path(result['config']).is_file(): raise ValueError('XML-файл не найден.')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if read('Сохранить эти параметры? [y/N]: ').strip().lower() not in ('y', 'yes', 'д', 'да'):
        print('Отменено; параметры не изменены.'); return
    save_profile(root, result, digest)
    print('Сохранено. При обновлении исходников можно перенести только', PROFILE_NAME)
    print('При следующем запуске явные --python/--data-dir и TACTIC_PYTHON имеют приоритет над файлом.')
    return result


def interactive(args, root: Path = ROOT, read: Callable[[str], str] = input, run: Callable[[Plan], int] = execute) -> int:
    """Maintenance only. Daily startup and setup have their own BAT files.

    The original child processes still own all CREATE/UPGRADE/RESTORE/ENABLE
    confirmations. No default menu item starts a server or alters a database.
    """
    if not sys.stdin.isatty():
        raise ValueError('Меню требует терминала. Для скрипта используйте MANAGE_TACTIC.bat check/db/configure/settings.')
    session_profile = None
    while True:
        profile, _ = read_profile(root)
        cfg = effective(args, profile, root) if session_profile is None else effective(parse(['menu']), session_profile, root, {})
        print('\n' + '=' * 58)
        print('TACTIC — настройки и обслуживание')
        print('Данные:', cfg['data_dir'])
        print(f'Режим запуска: {cfg["mode"]}; порт: {cfg["port"]}; workers: {cfg["workers"]}')
        print('1  Параметры запуска (пути, порт, режим)\n2  Диагностика\n3  Разрешения записи / файлов / Python-скриптов\n4  База данных — инициализация, обновление, восстановление\n5  Пересобрать Vue (для разработчика, нужен Node)\n0  Выход')
        print('Сервер: START_TACTIC.bat   Окружение: SETUP_ENV.bat')
        try:
            choice = read('Выберите действие: ').strip()
            if choice == '0': return 0
            if choice == '1':
                updated = settings_menu(cfg, root, read)
                if updated is not None: session_profile = updated
                continue
            if choice == '2':
                print('\n1  Проверить окружение (импорты)\n2  Проверить managed SQLite (read-only)\n3  Проверить запуск (инициализация может писать; сервер остановить)\n0  Назад')
                selected = read('Проверка: ').strip()
                if selected not in ('1', '2', '3'): continue
                command = ['check', {'1': 'env', '2': 'db', '3': 'startup'}[selected]]
            elif choice == '3':
                print('\n1  Показать настройки\n2  Только чтение\n3  Разрешить запись\n4  Запись и файлы\n5  Запись и Python-скрипты (НЕ песочница)\n6  Отключить загрузку файлов\n7  Отключить запуск Python-скриптов\n0  Назад')
                policy = read('Разрешения: ').strip()
                flags = {'1': [], '2': ['--writes', 'off'], '3': ['--writes', 'on'],
                         '4': ['--writes', 'on', '--uploads', 'on'],
                         '5': ['--writes', 'on', '--scripts', 'on'],
                         '6': ['--uploads', 'off'], '7': ['--scripts', 'off']}
                if policy not in flags: continue
                command = ['configure', *flags[policy]]
            elif choice == '4':
                print('\nОстановите все процессы TACTIC перед обслуживанием базы.')
                print('1  Новая SQLite — ТОЛЬКО пустой каталог\n2  Обновить managed SQLite с резервной копией\n3  Восстановить ПРЕРВАННУТОЕ обновление\n0  Назад')
                selected = read('Операция: ').strip()
                if selected not in ('1', '2', '3'): continue
                command = ['db', {'1': 'init', '2': 'upgrade', '3': 'restore'}[selected]]
            elif choice == '5':
                command = ['build']
            else:
                print('Выберите номер из меню.'); continue
            action = parse(command)
            plan = plan_command(action, cfg, root)
            result = run(plan)
            print('Код завершения:', result)
            if command == ['check', 'db'] and result == 3:
                print('Структура не готова. Проверьте отчёт; обновление НЕ запускается автоматически.')
            read('ENTER — вернуться в меню. ')
        except KeyboardInterrupt:
            print('\nДействие меню отменено.')
        except (ValueError, OSError) as exc:
            print('Ошибка:', exc)
        except EOFError:
            return 0


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ['--bootstrap-argv']:
        raw = os.environ.pop(BOOTSTRAP_ARGV, '')
        try:
            argv = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise ValueError('Повреждён конверт параметров bootstrap.') from exc
        if not isinstance(argv, list) or any(not isinstance(x, str) for x in argv) or len(raw) > 65536:
            raise ValueError('Неверные параметры bootstrap.')
    args = parse(argv)
    profile, digest = ({'format': 1}, None) if args.command in ('setup', 'build') else read_profile(root)
    cfg = effective(args, profile, root)
    if args.command == 'settings':
        update_profile(args, cfg, profile, digest, root); return 0
    if args.command == 'menu':
        if args.dry_run:
            print(json.dumps({'dry_run': True, 'menu': True, 'effective': cfg}, ensure_ascii=False, indent=2)); return 0
        return interactive(args, root)
    plan = plan_command(args, cfg, root)
    if args.dry_run:
        display_plan(plan, True); return 0
    if args.command == 'setup' and getattr(args, 'repair', False) and Path(sys.executable).resolve().is_relative_to(root / '.runtime'):
        raise ValueError('Ремонт запущенного Python запрещён. Закройте меню и используйте SETUP_ENV.bat --repair.')
    return execute(plan)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nОтменено.'); raise SystemExit(130)
    except (ValueError, OSError) as exc:
        print('ERROR:', str(exc), file=sys.stderr); raise SystemExit(2)
