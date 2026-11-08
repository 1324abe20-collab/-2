"""Проксі до API Delengine (довідник населених пунктів і відділень)."""

import logging
import urllib.parse

import aiohttp

import config

log = logging.getLogger(__name__)

DE_BASE = "https://api.delengine.com/v1.0"


async def _call(path, params):
    if not config.NP_API_KEY:
        return None
    params = dict(params or {})
    params["token"] = config.NP_API_KEY
    url = DE_BASE + path + "?" + urllib.parse.urlencode(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                data = await resp.json(content_type=None)
    except Exception:
        log.exception("Помилка запиту до Delengine")
        return None

    if not isinstance(data, dict) or data.get("status") not in ("success", "trial"):

        log.warning("Delengine: %s", data.get("error") if isinstance(data, dict) else data)
        return None
    return data.get("data")


async def search_cities(query, limit=20):
    data = await _call("/settlements", {"name": query, "per_page": str(limit)})
    if not data or not isinstance(data, list):
        # Delengine може повертати об'єкт із ключем data
        if isinstance(data, dict):
            data = data.get("data") or []
        if not isinstance(data, list):
            return []
    result = []
    for item in data[:limit]:
        region = (item.get("region") or {}).get("name_uk") or ""
        district = (item.get("district") or {}).get("name_uk") or ""
        sub = ", ".join(x for x in (district, region) if x)
        result.append(
            {
                "ref": item.get("uuid"),
                "name": item.get("name_uk"),
                "area": sub,
                "type": item.get("settlement_type", {}).get("name_uk")
                if isinstance(item.get("settlement_type"), dict)
                else item.get("settlement_type"),
            }
        )
    return result


async def get_companies():
    data = await _call("/companies", {})
    if not data or not isinstance(data, list):
        if isinstance(data, dict):
            data = data.get("data") or []
        if not isinstance(data, list):
            return []
    result = []
    for item in data:
        result.append(
            {
                "uuid": item.get("uuid"),
                "code": item.get("code"),
                "name": item.get("name_uk"),
            }
        )
    return result


async def get_companies():
    data = await _call("/companies", {})
    if not data or not isinstance(data, list):
        if isinstance(data, dict):
            data = data.get("data") or []
        if not isinstance(data, list):
            return []
    result = []
    for item in data:
        result.append(
            {
                "uuid": item.get("uuid"),
                "code": item.get("code"),
                "name": item.get("name_uk"),
            }
        )
    return result


async def get_warehouses(city_ref, kind=None, company_uuid=None):
    params = {"settlement_uuid": city_ref}
    if company_uuid:
        params["company_uuid"] = company_uuid
    data = await _call("/departments", params)
    if not data or not isinstance(data, list):
        if isinstance(data, dict):
            data = data.get("data") or []
        if not isinstance(data, list):
            return []
    result = []
    for item in data:
        company = (item.get("company") or {}).get("name_uk") or ""
        dtype = (item.get("department_type") or {}).get("name_uk") or ""
        is_postomat = "Поштомат" in dtype or "поштомат" in dtype.lower()
        if kind == "branch" and is_postomat:
            continue
        if kind == "postomat" and not is_postomat:
            continue
        number = item.get("number")
        address = item.get("address_uk") or ""
        label = "{} №{}{}".format(company, number, " — " + address if address else "")
        result.append(
            {
                "ref": item.get("uuid"),
                "number": number,
                "description": label.strip(" —"),
                "type": dtype,
                "company": company,
            }
        )
    return result
