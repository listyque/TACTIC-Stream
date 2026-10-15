"""Headless projection of Handler MatchTemplate/FileObject and snapshot chips.

Check-in metadata is authoritative; filenames alone never imply a sequence or UDIM.
Ranges stay compressed instead of allocating every frame as the desktop model does.
"""
import collections
import re

from pyasm.common import Config, jsonloads


def frame_ranges(values):
    intervals = []
    count = 0
    for value in values:
        if not isinstance(value, str) or not re.fullmatch(r'\d+(?:-\d+)?', value):
            raise ValueError('Invalid frame range')
        ends = value.split('-')
        start, end = int(ends[0]), int(ends[-1])
        if end < start:
            continue
        count += end - start + 1
        intervals.append((start, end))
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return ', '.join(str(start) if start == end else f'{start}-{end}' for start, end in merged), count


def metadata_display(metadata):
    """The fields consumed by native _snapshot_display/_snapshot_chips."""
    if not isinstance(metadata, dict) or not metadata.get('template'):
        return {}
    template = metadata.get('new_template')
    if not isinstance(template, str):
        return {}
    tokens = re.split(r'[.|_]', template)
    if any(token not in ('$FILENAME', '$EXT', '$UDIM', '$UV', '$FRAME', '$LAYER') for token in tokens):
        return {}
    kind = metadata.get('type')
    tiled = kind in ('uv', 'udim', 'layer_uv', 'layer_udim', 'uv_sequence', 'udim_sequence', 'layer_uv_sequence', 'layer_udim_sequence')
    sequence = kind in ('sequence', 'layer_sequence', 'uv_sequence', 'udim_sequence', 'layer_uv_sequence', 'layer_udim_sequence')
    if not tiled and not sequence and kind not in ('file', 'no_ext', 'layer_file'):
        return {}
    values = {'$FILENAME': metadata.get('new_filename'), '$EXT': metadata.get('new_file_ext'), '$LAYER': metadata.get('layer')}
    if any(not isinstance(values.get(token), str) for token in tokens if token in values):
        return {}
    if '$LAYER' in tokens and not re.fullmatch(r'[A-z0-9]*[A-z]+[A-z0-9]*', values['$LAYER']):
        return {}
    if '$EXT' in tokens and not re.fullmatch(r'[0-9A-z]+', values['$EXT']):
        return {}
    result = {}
    if sequence:
        padding = metadata.get('new_padding')
        if not isinstance(padding, int) or not 1 <= padding <= 64:
            return {}
        values['$FRAME'] = '[' + '#' * padding + ']'
        ranges = metadata.get('frameranges')
        if not isinstance(ranges, list):
            return {}
        if tiled:
            counts, labels = collections.defaultdict(list), []
            groups = collections.defaultdict(list)
            for tile, frames in ranges:
                if not isinstance(frames, list):
                    return {}
                groups[str(tile)].extend(frames)
            for tile, frames in sorted(groups.items(), key=lambda pair: tuple(int(part) if part.isdigit() else part.casefold() for part in re.split(r'(\d+)', pair[0])), reverse=True):
                if not re.fullmatch(r'u\d{1,2}_v\d{1,2}' if '$UV' in tokens else r'\d{4}', tile):
                    return {}
                label, count = frame_ranges(frames)
                if label:
                    counts[str(tile)].append(count)
                    labels.append(f'[{label} ({tile})]')
            total = sum(count[0] for count in counts.values())
            result.update(Range=', '.join(labels), Frames=str(counts), Tiles=len(counts))
        else:
            label, total = frame_ranges(ranges)
            result.update(Range='[' + label + ']' if label else '', Frames=total)
        if total <= 1:
            return {}
    elif tiled:
        tiles = metadata.get('udims')
        if not isinstance(tiles, list) or len(tiles) <= 1:
            return {}
        if any(not isinstance(tile, str) or not re.fullmatch(r'u\d{1,2}_v\d{1,2}' if '$UV' in tokens else r'\d{4}', tile) for tile in tiles):
            return {}
        result['Tiles'] = len(tiles)
    if tiled:
        values.update({'$UDIM': '[UUVV]', '$UV': '[u<>_v<>]'})
    if '$LAYER' in tokens and metadata.get('layer'):
        result['Layer'] = metadata['layer']
    title = re.sub(r'\$[A-Z]+', lambda match: values[match.group()], template)
    result['title'] = title.replace('\\', '/').rsplit('/', 1)[-1]
    return result


def metadata_members(metadata, offset=0, limit=50):
    """Page authoritative group members without expanding every frame in memory."""
    if not metadata_display(metadata):
        return []
    tiled = '$UDIM' in metadata['new_template'] or '$UV' in metadata['new_template']
    sequence = '$FRAME' in metadata['new_template']
    if tiled and sequence:
        groups = metadata['frameranges']
    elif tiled:
        groups = [(tile, []) for tile in metadata['udims']]
    else:
        groups = [('', metadata['frameranges'] if sequence else [])]
    groups = sorted(groups, key=lambda pair: pair[0])
    output = []
    for tile, ranges in groups:
        intervals = sorted((int(part.split('-')[0]), int(part.split('-')[-1])) for part in ranges) if sequence else [(0, 0)]
        padding = metadata.get('new_padding', 1)
        if sequence and any(end >= 10 ** padding for _, end in intervals):
            # Handler sorts filenames lexically, including frames wider than their padding.
            def count_prefix(prefix):
                total = 0
                for digits in range(max(padding, len(prefix)), max(len(str(end)) for _, end in intervals) + 1):
                    if prefix.startswith('0') and digits > padding:
                        continue
                    factor = 10 ** (digits - len(prefix))
                    low, high = int(prefix) * factor, (int(prefix) + 1) * factor - 1
                    total += sum(max(0, min(end, high) - max(start, low) + 1) for start, end in intervals)
                return total
            frames = []
            def visit(prefix):
                nonlocal offset
                count = count_prefix(prefix)
                if offset >= count:
                    offset -= count; return
                if len(prefix) >= padding:
                    copies = sum(start <= int(prefix) <= end for start, end in intervals)
                    for _ in range(copies):
                        if offset:
                            offset -= 1
                        else:
                            frames.append(int(prefix))
                            if len(frames) == limit - len(output):
                                return
                for digit in '0123456789':
                    visit(prefix + digit)
                    if len(frames) == limit - len(output):
                        return
            for digit in '0123456789':
                visit(digit)
                if len(frames) == limit - len(output):
                    break
            intervals = [(frame, frame) for frame in frames]
        for start, end in intervals:
            count = max(0, end - start + 1)
            if offset >= count:
                offset -= count; continue
            for frame in range(start + offset, min(end + 1, start + offset + limit - len(output))):
                values = {'$FILENAME': metadata['new_filename'], '$EXT': metadata.get('new_file_ext', ''),
                          '$LAYER': metadata.get('layer', ''), '$FRAME': str(frame).zfill(metadata.get('new_padding', 1)),
                          '$UDIM': tile, '$UV': tile}
                name = re.sub(r'\$[A-Z]+', lambda match: values[match.group()], metadata['new_template'])
                if '/' in name or '\\' in name or ':' in name or name in ('.', '..') or '\x00' in name:
                    raise ValueError('Invalid metadata member filename')
                output.append(name)
            offset = 0
            if len(output) == limit:
                return output
    return output


def metadata_paths(file):
    """All owned Handler group members, for replacement and native repository deletion."""
    from pathlib import Path
    metadata = file.get_json_value('metadata', default={})
    directory = Path(file.get_lib_path()).parent
    offset = 0
    while names := metadata_members(metadata, offset=offset, limit=1000):
        for name in names:
            yield directory / name
        offset += len(names)
    if not offset:
        yield Path(file.get_lib_path())


def file_display(file, context=''):
    try:
        metadata = file.get_json_value('metadata', default={}) if file else {}
    except (ValueError, TypeError):
        metadata = {}
    try:
        meta = metadata_display(metadata)
    except (ValueError, TypeError, KeyError):
        meta = {}
    chips = [dict(label='Context', value=context, url='')] if context else []
    for label in ('Range', 'Frames', 'Layer', 'Tiles'):
        value = meta.get(label)
        if value not in (None, '', 0):
            chips.append(dict(label=label, value=str(value), url=''))
    app_info = metadata.get('app_info') if isinstance(metadata, dict) else None
    if isinstance(app_info, dict) and app_info.get('p'):
        chips.append(dict(label='Maya', value=str(app_info['p']), url=''))
    return dict(title=meta.get('title') or (file.get_value('file_name') if file else ''), infoChips=chips)


def repository_display(alias):
    # Default labels/colors are the Handler Environment.get_base_dirs catalog.
    defaults = {'base': ('General', '#808080'), 'web': ('Web', '#808080'),
                'sandbox': ('Sandbox', '#804040'), 'client': ('Client', '#1f8f00'),
                'local': ('Local', '#ff8c28'), 'client_handoff': ('Handoff', '#607d8b'),
                'server_handoff': ('Handoff', '#607d8b')}
    title, color = defaults.get(alias, (alias, '#607d8b'))
    try:
        overrides = jsonloads(Config.get_value('checkin', 'repository_display') or '{}')
        entry = overrides.get(alias, {}) if isinstance(overrides, dict) else {}
        if isinstance(entry, dict):
            title = entry.get('title') or title
            value = entry.get('color')
            if isinstance(value, str) and re.fullmatch(r'#?[\da-fA-F]{6}', value):
                color = '#' + value.lstrip('#')
            elif isinstance(value, (list, tuple)) and len(value) == 3:
                color = '#{:02x}{:02x}{:02x}'.format(*[max(0, min(255, int(channel))) for channel in value])
    except (ValueError, TypeError):
        pass
    return dict(repository=title, repositoryColor=color)
