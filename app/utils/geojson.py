import json
import math


def _clean_props(props: dict) -> dict:
    """Remplace NaN/Infinity par None pour la sérialisation JSON."""
    return {
        k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
        for k, v in props.items()
    }


def json_to_geojson(data, lon_key='longitude', lat_key='latitude'):
    features = []
    print("Tronçons reçus :", data)
    for item in data:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [item[lon_key], item[lat_key]]
            },
            "properties": _clean_props({k: v for k, v in item.items() if k not in (lon_key, lat_key)})
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


def troncons_to_geojson(data):
    features = []
    #print("Tronçons reçus :", data)
    for item in data:
        try:
            geom = json.loads(item["geom"])
        except (json.JSONDecodeError, KeyError):
            geom = None

        props = {k: v for k, v in item.items() if k != "geom"}

        if "idtronconh" in props:
            props["idtronconh"] = str(props["idtronconh"])

        feature = {
            "type": "Feature",
            "geometry": geom,
            "properties": _clean_props(props)
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }