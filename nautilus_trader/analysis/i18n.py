# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------
"""
Internationalization (i18n) support for analysis reports.

This module provides translation loading from standard JSON locale files.
Translations are stored in the ``locales/`` directory as JSON files
(e.g., ``en.json``, ``zh_CN.json``).

Usage
-----
>>> from nautilus_trader.analysis.i18n import t
>>> t("equity_curve", locale="en")
'Equity Curve'
>>> t("equity_curve", locale="zh_CN")
'权益曲线'

"""

from __future__ import annotations

import json
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent / "locales"
_cache: dict[str, dict[str, str]] = {}


def _load_locale(locale: str) -> dict[str, str]:
    """
    Load a locale's translations from JSON file.

    Parameters
    ----------
    locale : str
        The locale code (e.g., "en", "zh_CN").

    Returns
    -------
    dict[str, str]
        The translation dictionary for the locale. Returns empty dict if not found.

    """
    path = _LOCALES_DIR / f"{locale}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def t(key: str, locale: str = "en", **kwargs: object) -> str:
    """
    Translate a key to the specified locale.

    If the key is not found in the specified locale, falls back to English,
    then returns the key itself as a last resort.

    Parameters
    ----------
    key : str
        The translation key (e.g., "equity_curve").
    locale : str, default "en"
        The locale code (e.g., "en", "zh_CN").
    **kwargs : object
        Optional format parameters for string interpolation.
        For example, ``t("rolling_sharpe_window", locale="zh_CN", window=60)``.

    Returns
    -------
    str
        The translated string.

    """
    if locale not in _cache:
        _cache[locale] = _load_locale(locale)

    value = _cache[locale].get(key)
    if value is None:
        # Fall back to English
        if "en" not in _cache:
            _cache["en"] = _load_locale("en")
        value = _cache["en"].get(key, key)

    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return value

    return value


def available_locales() -> list[str]:
    """
    List all available locale codes.

    Returns
    -------
    list[str]
        Sorted list of available locale codes (e.g., ["en", "zh_CN"]).

    """
    return sorted(p.stem for p in _LOCALES_DIR.glob("*.json"))


def clear_cache() -> None:
    """
    Clear the translation cache.

    This is useful for testing or when locale files have been updated at runtime.

    """
    _cache.clear()