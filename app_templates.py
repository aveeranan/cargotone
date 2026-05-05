from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def _fmt_date(value):
    if not value:
        return ""
    return str(value)[:10]


def _fmt_datetime(value):
    if not value:
        return ""
    v = str(value)
    return f"{v[:10]} {v[11:16]}" if len(v) > 10 else v


def _status_label(value):
    return (value or "").replace("_", " ")


def _status_css(value):
    return (value or "").replace(" ", "")


templates.env.filters["fmt_date"] = _fmt_date
templates.env.filters["fmt_datetime"] = _fmt_datetime
templates.env.filters["status_label"] = _status_label
templates.env.filters["status_css"] = _status_css
