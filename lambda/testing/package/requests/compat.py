"""
requests.compat
~~~~~~~~~~~~~~~

This module previously handled import compatibility issues between Python 2
and Python 3. It remains for backwards compatibility until the next major
version.
"""

import sys

# JSON/simplejson module import resolution
try:
    import simplejson as json  # noqa: F401
    from simplejson import JSONDecodeError  # noqa: F401
except ImportError:
    import json  # noqa: F401
    from json import JSONDecodeError  # noqa: F401

# Optional charset library for compatibility
try:
    import chardet  # noqa: F401
except ImportError:
    import charset_normalizer as chardet  # noqa: F401

# Keep OrderedDict for backwards compatibility
from collections import OrderedDict  # noqa: F401
from collections.abc import Callable, Mapping, MutableMapping  # noqa: F401
from http import cookiejar as cookielib  # noqa: F401
from http.cookies import Morsel  # noqa: F401
from io import StringIO  # noqa: F401

# Legacy urllib imports
from urllib.parse import (  # noqa: F401
    quote,
    quote_plus,
    unquote,
    unquote_plus,
    urldefrag,
    urlencode,
    urljoin,
    urlparse,
    urlsplit,
    urlunparse,
)
from urllib.request import (  # noqa: F401
    getproxies,
    getproxies_environment,
    parse_http_list,
    proxy_bypass,
    proxy_bypass_environment,
)

# --------
# Pythons
# --------

# Syntax sugar.
_ver = sys.version_info

#: Python 2.x?
is_py2 = _ver[0] == 2

#: Python 3.x?
is_py3 = _ver[0] == 3

# Did we get simplejson?
has_simplejson = 'simplejson' in sys.modules

# Type aliases for compatibility
builtin_str = str
str = str
bytes = bytes
basestring = (str, bytes)
numeric_types = (int, float)
integer_types = (int,)
