import json
from datetime import date, datetime
from decimal import Decimal

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def _tojson(value):
    def _default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    return json.dumps(value, default=_default)


templates.env.filters["tojson"] = _tojson
templates.env.globals["now"] = datetime.now
