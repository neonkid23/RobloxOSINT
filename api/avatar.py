from typing import Any

import logging

from api.client import RobloxApiError, request_json


AVATAR_BASE = "https://avatar.roblox.com/v1"
AVATAR_V2_BASE = "https://avatar.roblox.com/v2"
AVATAR_V3_BASE = "https://avatar.roblox.com/v3"
CATALOG_BASE = "https://catalog.roblox.com/v1"


def get_avatar_customization(user_id: int, cookie_header: str | None = None) -> dict[str, Any]:
    reason = None
    avatar_details_error = None
    currently_wearing_error = None
    try:
        payload = request_json("GET", f"{AVATAR_BASE}/users/{user_id}/avatar", cookie_header=cookie_header, retries=1)
    except RobloxApiError as exc:
        payload = {}
        avatar_details_error = str(exc)
        reason = "Used currently-wearing fallback because avatar details were unavailable."

    currently_wearing_asset_ids = []
    assets = _normalize_avatar_assets(payload.get("assets", []))
    if not assets:
        try:
            currently_wearing_asset_ids, assets = _get_currently_wearing_assets(user_id, cookie_header=cookie_header)
        except RobloxApiError as exc:
            currently_wearing_error = str(exc)
            assets = []
        if assets and reason is None:
            reason = "Used currently-wearing fallback because avatar details did not include asset objects."
        elif not assets:
            reason = "No public outfit objects were returned by Roblox for this avatar."
    else:
        currently_wearing_asset_ids = [asset["asset_id"] for asset in assets if asset.get("asset_id")]

    saved_outfits = _get_saved_outfits(user_id, cookie_header=cookie_header)

    object_names = [asset["name"] for asset in assets if asset.get("name")]
    return {
        "visible": True,
        "reason": reason,
        "cookie_mode": bool(cookie_header),
        "avatar_details_error": avatar_details_error,
        "currently_wearing_error": currently_wearing_error,
        "avatar_type": payload.get("playerAvatarType"),
        "currently_wearing_asset_ids": currently_wearing_asset_ids,
        "object_names": object_names,
        "outfit_object_names": object_names,
        "body_colors": payload.get("bodyColors") or {},
        "scales": payload.get("scales") or {},
        "assets": assets,
        "saved_outfits": saved_outfits,
    }


def _normalize_avatar_assets(raw_assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assets = []
    for asset in raw_assets:
        asset_type = asset.get("assetType") or {}
        assets.append(
            {
                "asset_id": asset.get("id"),
                "name": asset.get("name"),
                "asset_type_id": asset_type.get("id"),
                "asset_type": asset_type.get("name"),
                "current_version_id": asset.get("currentVersionId"),
            }
        )
    return assets


def _get_currently_wearing_assets(user_id: int, cookie_header: str | None = None) -> tuple[list[int], list[dict[str, Any]]]:
    payload = request_json("GET", f"{AVATAR_BASE}/users/{user_id}/currently-wearing", cookie_header=cookie_header)
    asset_ids = [asset_id for asset_id in payload.get("assetIds", []) if asset_id]
    if not asset_ids:
        return [], []

    assets = []
    for start in range(0, len(asset_ids), 100):
        batch = asset_ids[start : start + 100]
        try:
            details = _get_catalog_details(batch)
        except RobloxApiError as exc:
            logging.info("Catalog details unavailable for currently-wearing assets user_id=%s: %s", user_id, exc)
            details = [_asset_id_only(asset_id) for asset_id in batch]
        assets.extend(details)
    return asset_ids, assets


def _get_catalog_details(asset_ids: list[int]) -> list[dict[str, Any]]:
    payload = request_json(
        "POST",
        f"{CATALOG_BASE}/catalog/items/details",
        json_body={
            "items": [{"itemType": "Asset", "id": asset_id} for asset_id in asset_ids],
        },
    )
    assets = []
    for item in payload.get("data", []):
        assets.append(
            {
                "asset_id": item.get("id"),
                "name": item.get("name"),
                "asset_type_id": item.get("assetType") or item.get("assetTypeId"),
                "asset_type": item.get("assetTypeDisplayName") or item.get("itemType"),
                "current_version_id": None,
            }
        )
    return assets


def _get_saved_outfits(user_id: int, cookie_header: str | None = None) -> dict[str, Any]:
    try:
        payload = request_json("GET", f"{AVATAR_V2_BASE}/avatar/users/{user_id}/outfits", cookie_header=cookie_header)
    except RobloxApiError as exc:
        return {
            "visible": False,
            "reason": f"Saved outfits endpoint is not publicly accessible: {exc}",
            "items": [],
        }

    outfits = []
    for outfit in payload.get("data", []):
        outfit_id = outfit.get("id")
        outfit_record = {
            "outfit_id": outfit_id,
            "name": outfit.get("name"),
            "outfit_type": outfit.get("outfitType"),
            "is_editable": outfit.get("isEditable"),
            "assets": [],
            "object_names": [],
            "details_visible": False,
            "details_reason": None,
        }
        if outfit_id:
            details = _get_outfit_details(outfit_id, cookie_header=cookie_header)
            outfit_record.update(details)
        outfits.append(outfit_record)

    return {
        "visible": True,
        "reason": None,
        "items": outfits,
    }


def _get_outfit_details(outfit_id: int, cookie_header: str | None = None) -> dict[str, Any]:
    try:
        payload = request_json(
            "GET",
            f"{AVATAR_V3_BASE}/outfits/{outfit_id}/details",
            params={"checkAssetAvailability": "true"},
            cookie_header=cookie_header,
        )
    except RobloxApiError as exc:
        return {
            "details_visible": False,
            "details_reason": f"Outfit details endpoint is not publicly accessible: {exc}",
            "assets": [],
            "object_names": [],
        }

    assets = _normalize_avatar_assets(payload.get("assets", []))
    object_names = [asset["name"] for asset in assets if asset.get("name")]
    return {
        "details_visible": True,
        "details_reason": None,
        "assets": assets,
        "object_names": object_names,
        "body_colors": payload.get("bodyColors") or payload.get("bodyColor3s") or {},
        "scales": payload.get("scale") or {},
        "avatar_type": payload.get("playerAvatarType"),
    }


def _asset_id_only(asset_id: int) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "name": None,
        "asset_type_id": None,
        "asset_type": None,
        "current_version_id": None,
    }
