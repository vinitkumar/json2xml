"""Parallel processing utilities for json2xml using free-threaded Python."""
from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from json2xml import dicttoxml


def is_free_threaded() -> bool:
    """
    Check if running on free-threaded Python build (Python 3.13t).
    
    Returns:
        bool: True if running on free-threaded build, False otherwise.
    """
    return hasattr(sys, '_is_gil_enabled') and not sys._is_gil_enabled()


def get_optimal_workers(workers: int | None = None) -> int:
    """
    Get the optimal number of worker threads.
    
    Args:
        workers: Explicitly specified worker count. If None, auto-detect.
    
    Returns:
        int: Number of worker threads to use.
    """
    if workers is not None:
        return max(1, workers)

    cpu_count = os.cpu_count() or 4

    if is_free_threaded():
        return cpu_count
    else:
        return min(4, cpu_count)


_validation_cache: dict[str, bool] = {}
_validation_cache_lock = threading.Lock()


def key_is_valid_xml_cached(key: str) -> bool:
    """
    Thread-safe cached version of key_is_valid_xml.
    
    Args:
        key: The XML key to validate.
    
    Returns:
        bool: True if the key is valid XML, False otherwise.
    """
    with _validation_cache_lock:
        if key in _validation_cache:
            return _validation_cache[key]

    result = dicttoxml.key_is_valid_xml(key)

    with _validation_cache_lock:
        _validation_cache[key] = result

    return result


def make_valid_xml_name_cached(key: str, attr: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """
    Thread-safe cached version of make_valid_xml_name.
    
    Args:
        key: The key to validate.
        attr: The attributes dictionary.
    
    Returns:
        tuple: Valid XML key and updated attributes.
    """
    key = dicttoxml.escape_xml(key)

    if key_is_valid_xml_cached(key):
        return key, attr

    if isinstance(key, int) or key.isdigit():
        return f"n{key}", attr

    if key_is_valid_xml_cached(key.replace(" ", "_")):
        return key.replace(" ", "_"), attr

    if key_is_valid_xml_cached(key.replace(":", "").replace("@flat", "")):
        return key, attr

    attr["name"] = key
    key = "key"
    return key, attr


def _convert_dict_item(
    key: str,
    val: Any,
    ids: list[str],
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool
) -> str:
    """
    Convert a single dictionary item to XML (for parallel processing).
    
    Args:
        key: Dictionary key.
        val: Dictionary value.
        ids: List of unique IDs.
        parent: Parent element name.
        attr_type: Whether to include type attributes.
        item_func: Function to generate item names.
        cdata: Whether to wrap strings in CDATA.
        item_wrap: Whether to wrap list items.
        list_headers: Whether to repeat headers for lists.
    
    Returns:
        str: XML string for this item.
    """
    import datetime
    import numbers

    attr = {} if not ids else {"id": f"{dicttoxml.get_unique_id(parent)}"}
    key, attr = make_valid_xml_name_cached(key, attr)

    if isinstance(val, bool):
        return dicttoxml.convert_bool(key, val, attr_type, attr, cdata)

    elif isinstance(val, (numbers.Number, str)):
        return dicttoxml.convert_kv(
            key=key, val=val, attr_type=attr_type, attr=attr, cdata=cdata
        )

    elif hasattr(val, "isoformat"):
        return dicttoxml.convert_kv(
            key=key,
            val=val.isoformat(),
            attr_type=attr_type,
            attr=attr,
            cdata=cdata,
        )

    elif isinstance(val, dict):
        return dicttoxml.dict2xml_str(
            attr_type, attr, val, item_func, cdata, key, item_wrap,
            False,
            list_headers=list_headers
        )

    elif isinstance(val, Sequence):
        return dicttoxml.list2xml_str(
            attr_type=attr_type,
            attr=attr,
            item=val,
            item_func=item_func,
            cdata=cdata,
            item_name=key,
            item_wrap=item_wrap,
            list_headers=list_headers
        )

    elif not val:
        return dicttoxml.convert_none(key, attr_type, attr, cdata)

    else:
        raise TypeError(f"Unsupported data type: {val} ({type(val).__name__})")


def convert_dict_parallel(
    obj: dict[str, Any],
    ids: list[str],
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool = False,
    workers: int | None = None,
    min_items_for_parallel: int = 10
) -> str:
    """
    Parallel version of convert_dict that processes dictionary items concurrently.
    
    Args:
        obj: Dictionary to convert.
        ids: List of unique IDs.
        parent: Parent element name.
        attr_type: Whether to include type attributes.
        item_func: Function to generate item names.
        cdata: Whether to wrap strings in CDATA.
        item_wrap: Whether to wrap list items.
        list_headers: Whether to repeat headers for lists.
        workers: Number of worker threads (None for auto-detect).
        min_items_for_parallel: Minimum items to enable parallelization.
    
    Returns:
        str: XML string.
    """
    if len(obj) < min_items_for_parallel:
        return dicttoxml.convert_dict(
            obj, ids, parent, attr_type, item_func, cdata, item_wrap, list_headers
        )

    workers = get_optimal_workers(workers)
    items = list(obj.items())
    results: dict[int, str] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_idx = {
            executor.submit(
                _convert_dict_item,
                key, val, ids, parent, attr_type, item_func, cdata, item_wrap, list_headers
            ): idx
            for idx, (key, val) in enumerate(items)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()

    return "".join(results[idx] for idx in range(len(items)))


def _convert_list_chunk(
    items: Sequence[Any],
    ids: list[str] | None,
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool,
    start_offset: int
) -> str:
    """
    Convert a chunk of list items to XML (for parallel processing).
    
    Args:
        items: List chunk to convert.
        ids: List of unique IDs.
        parent: Parent element name.
        attr_type: Whether to include type attributes.
        item_func: Function to generate item names.
        cdata: Whether to wrap strings in CDATA.
        item_wrap: Whether to wrap list items.
        list_headers: Whether to repeat headers for lists.
        start_offset: Starting index for this chunk.
    
    Returns:
        str: XML string for this chunk.
    """
    return dicttoxml.convert_list(
        items, ids, parent, attr_type, item_func, cdata, item_wrap, list_headers
    )


def convert_list_parallel(
    items: Sequence[Any],
    ids: list[str] | None,
    parent: str,
    attr_type: bool,
    item_func: Callable[[str], str],
    cdata: bool,
    item_wrap: bool,
    list_headers: bool = False,
    workers: int | None = None,
    chunk_size: int = 100
) -> str:
    """
    Parallel version of convert_list that processes list chunks concurrently.
    
    Args:
        items: List to convert.
        ids: List of unique IDs.
        parent: Parent element name.
        attr_type: Whether to include type attributes.
        item_func: Function to generate item names.
        cdata: Whether to wrap strings in CDATA.
        item_wrap: Whether to wrap list items.
        list_headers: Whether to repeat headers for lists.
        workers: Number of worker threads (None for auto-detect).
        chunk_size: Number of items per chunk.
    
    Returns:
        str: XML string.
    """
    if len(items) < chunk_size:
        return dicttoxml.convert_list(
            items, ids, parent, attr_type, item_func, cdata, item_wrap, list_headers
        )

    workers = get_optimal_workers(workers)
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    results: dict[int, str] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_idx = {
            executor.submit(
                _convert_list_chunk,
                chunk, ids, parent, attr_type, item_func, cdata, item_wrap, list_headers, idx * chunk_size
            ): idx
            for idx, chunk in enumerate(chunks)
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            results[idx] = future.result()

    return "".join(results[idx] for idx in range(len(chunks)))
