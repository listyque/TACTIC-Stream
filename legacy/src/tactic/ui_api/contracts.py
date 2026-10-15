"""Transport-independent input validation. No TACTIC or web-framework imports."""
import hashlib
import json
import math
import re
from datetime import date, datetime
from decimal import Decimal


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def fail(message, code="invalid_input"):
    raise ApiError(400, code, message)


def text(value, name, limit=200, empty=False):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        fail("Некорректное поле: %s" % name)
    if any(ord(c) < 32 for c in value):
        fail("Управляющие символы запрещены: %s" % name)
    return value.strip()


def project_code(value):
    value = text(value, "project", 80)
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", value):
        fail("Некорректный код проекта")
    return value


def search_type(value):
    value = text(value, "type", 180)
    if not re.fullmatch(r"[A-Za-z0-9_\-]+/[A-Za-z0-9_\-]+", value):
        fail("Ожидается базовый SearchType без параметров")
    return value


def view_name(value):
    value = text(value or "table", "view", 120)
    if not re.fullmatch(r"[A-Za-z0-9_@.\-]+", value):
        fail("Некорректное имя представления")
    return value


def integer(value, name, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        fail("%s: ожидается целое число от %s до %s" % (name, low, high))
    return value


def json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, int) and abs(value) > 9007199254740991:
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def revision(values):
    raw = json.dumps(json_safe(values), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


SENSITIVE = re.compile(r"(^|_)(password|passwd|secret|ticket|token|private_key|api_key|salt|hash)(_|$)", re.I)
SYSTEM_FIELDS = {"id", "code", "search_code", "search_type", "search_id", "project_code", "timestamp", "s_status"}


def safe_field(name):
    return isinstance(name, str) and bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)) and not SENSITIVE.search(name)


def safe_element(name):
    """Configured virtual identifiers are NOT database column identifiers."""
    return isinstance(name, str) and len(name) <= 200 and bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:@-]*", name)) and not SENSITIVE.search(name.replace('.', '_'))


def coerce_value(field, value):
    kind = field["kind"]
    if value is None:
        if not field.get("nullable", True):
            fail("Поле «%s» не может быть null" % field["label"])
        return None
    if kind in ("integer", "number"):
        if isinstance(value, bool):
            fail("Поле «%s» должно быть числом" % field["label"])
        try:
            decimal = Decimal(str(value))
            if not decimal.is_finite():
                raise ValueError()
            if kind == "integer":
                if decimal != decimal.to_integral_value():
                    raise ValueError()
                return int(decimal)
            return str(decimal)  # preserve decimal precision across JSON and DB boundaries
        except (ValueError, ArithmeticError):
            fail("Некорректное число: %s" % field["label"])
    if kind == "boolean":
        if not isinstance(value, bool):
            fail("Ожидается логическое значение: %s" % field["label"])
        return value
    if kind == "json":
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                fail("Некорректный JSON: %s" % field["label"])
        try:
            return json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (ValueError, TypeError):
            fail("Некорректный JSON: %s" % field["label"])
    if not isinstance(value, str):
        fail("Ожидается строка: %s" % field["label"])
    maximum = min(int(field.get("max_length") or 200000), 200000)
    if len(value) > maximum or "\x00" in value:
        fail("Слишком длинное или недопустимое значение: %s" % field["label"])
    if kind in ("date", "datetime") and value:
        try:
            (date.fromisoformat if kind == "date" else datetime.fromisoformat)(value.replace("Z", "+00:00"))
        except ValueError:
            fail("Некорректная дата: %s" % field["label"])
    if field.get("options") and value not in [str(x["value"]) for x in field["options"]]:
        fail("Значение отсутствует в списке: %s" % field["label"])
    return value


def clean_values(values, fields):
    if not isinstance(values, dict) or not values or len(values) > 100:
        fail("Нужен непустой объект values, максимум 100 полей")
    result = {}
    by_name = {f["name"]: f for f in fields}
    for name, value in values.items():
        field = by_name.get(name)
        allowed_virtual = field and field.get('virtual_write') and (name in ('password','password_reenter','password re-enter','add_to_project'))
        if not field or field.get("read_only", True) or (name in SYSTEM_FIELDS and not field.get('write_system')) or (not safe_field(name) and not allowed_virtual):
            raise ApiError(403, "field_read_only", "Запись в поле «%s» не разрешена" % name)
        result[name] = coerce_value(field, value)
    return result


def clean_query(data, fields, default_sort=None):
    configured_orders = default_sort or []
    by_name = {f["name"]: f for f in fields if f.get("storage", True)}
    sortable = {n:f for n,f in by_name.items() if f.get("sortable", True)}
    offset = integer(data.get("offset", 0), "offset", 0, 1000000)
    limit = integer(data.get("limit", 50), "limit", 1, 200)
    if not isinstance(configured_orders, list) or len(configured_orders) > 8 or any(not isinstance(o, dict) or o.get('field') not in sortable or o.get('direction') not in ('asc', 'desc') for o in configured_orders):
        fail("Недопустимая конфигурационная сортировка")
    default_sort = next((n for n in ("id", "code") if n in sortable), next(iter(sortable), None))
    sort = data.get("sort") or (configured_orders[0] if configured_orders else {"field": default_sort, "direction": "desc"})
    # A configured view may consist only of virtual widgets, or be empty.
    # No invented visible ID column: the backend adds an internal stable order.
    no_visible_storage = not sortable and not data.get("sort") and not configured_orders
    if not isinstance(sort, dict) or (sort.get("field") not in sortable and not no_visible_storage) or sort.get("direction") not in ("asc", "desc"):
        fail("Недопустимая сортировка")
    filters = data.get("filters", [])
    if not isinstance(filters, list) or len(filters) > 20:
        fail("Допустимо не более 20 фильтров")
    from tactic.core.query_model import normalize_tree, combine
    try:
        flat = normalize_tree({'op': 'and', 'children': filters}, fields, coerce_value, maximum=40)
        advanced = normalize_tree(data.get('where'), fields, coerce_value, maximum=40)
        where = normalize_tree(combine(flat, advanced), fields, coerce_value, maximum=40)
    except ValueError as exc:
        fail(str(exc), code='filter_tree')
    cleaned = flat['children']
    keyword = data.get("keyword") or ""
    if keyword:
        keyword = text(keyword, "keyword", 200)
        name = data.get("keyword_field") or next((n for n in ("name", "title", "description", "code") if n in by_name), None)
        if name not in by_name or by_name[name]["kind"] not in ("text", "textarea", "select"):
            fail("Выберите текстовое поле поиска")
        cleaned.append({"field": name, "op": "contains", "value": keyword})
    # Revalidate the aggregate including keyword; there is one total limit.
    try:
        where = normalize_tree(combine({'op': 'and', 'children': cleaned}, advanced), fields, coerce_value, maximum=40)
    except ValueError as exc:
        fail(str(exc), code='filter_tree')
    parent = data.get("parent_key")
    if parent:
        parent = text(parent, "parent_key", 1500)
    state = data.get('record_state', 'active')
    if state not in ('active', 'all', 'retired'): fail('Неизвестный режим архива')
    return {"offset": offset, "limit": limit, "sort": sort, "sorts": [sort] if data.get("sort") or not configured_orders else configured_orders, "filters": cleaned, "where": where, "parent_key": parent, 'record_state': state}
