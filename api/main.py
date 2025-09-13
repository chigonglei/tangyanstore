from fastapi import FastAPI, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import requests
import hashlib
import time
import inspect
from fastapi.routing import APIRoute

# ✅ Allowed IPs and API keys
VALID_API_KEYS = {
    "12345": "49.47.144.33",   # PC
    "123456": "135.148.103.16",   # LOcal Host
    "rE3uK9tQXfW7L2nCz0vMdY8sGpA5JhZB": "15.206.215.172"  # lskyla
}

# ✅ Setup FastAPI
app = FastAPI()

# ✅ Rate limiter (per API key)
def api_key_func(request: Request):
    return request.query_params.get("api_key") or get_remote_address(request)

limiter = Limiter(key_func=api_key_func)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda r, e: JSONResponse(status_code=429, content={
        "code": 429,
        "status": False,
        "message": "Rate limit exceeded",
        "data": {}
    })
)
app.add_middleware(SlowAPIMiddleware)

# ✅ Dependency: API key + IP check
def verify_api_key(request: Request):
    api_key = request.query_params.get("api_key")
    client_ip = request.client.host

    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")

    allowed_ip = VALID_API_KEYS[api_key]
    if client_ip != allowed_ip:
        raise HTTPException(status_code=401, detail=f"API key not allowed from IP {client_ip}")

    return api_key

def safe_description(endpoint):
    try:
        desc = endpoint.__doc__
        if not desc:
            return ""
        # Strip whitespace and replace newlines with spaces
        return " ".join(desc.strip().split())
    except Exception:
        return ""

@app.get("/")
def root():
    endpoints = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            path = route.path
            methods = list(route.methods - {"HEAD", "OPTIONS"})

            # ✅ use safe function
            description = safe_description(route.endpoint)

            # --- Build example URL ---
            base_url = "https://tangyanstore.vercel.app"
            params = []

            # Add params based on function signature
            func_params = route.dependant.query_params
            for p in func_params:
                if p.name == "id":
                    params.append("id=xxxxxxxxxx")
                elif p.name == "zone":
                    params.append("zone=xxxx")

            # always append api_key
            params.append("api_key=xxxxx")

            example = f"{base_url}{path}?{'&'.join(params)}" if params else f"{base_url}{path}?api_key=xxxxx"

            endpoints.append({
                "path": path,
                "methods": methods,
                "description": description,
                "example": example
                
            })

    return {
        "version": "2.0",
        "code": 200,
        "author": "Sanjoy",
        "contact": "91 9862622104",
        "status": True,
        "message": "Game IGN Checker API running",
        "available_endpoints": endpoints
    }


# ✅ Helper response formatter
def format_response(success: bool, message: str, data: dict = None, code: int = 200):
    return {
        "code": code,
        "status": success,
        "message": message,
        "data": data or {}
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}





# ------------------------------
# MLbb Region Checker
# ------------------------------

@app.get("/check_region")
@limiter.limit("100/day")
def check_region(
    request: Request,
    id: str,
    zone: str,
    _: str = Depends(verify_api_key)
):
    """
    Check Mobile Legends Bang Bang Region
    """
    urls = [
        f"https://regionweb.vercel.app/api/validasi?id={id}&serverid={zone}",
        f"https://gameidcheckerenglish.vercel.app/api/game/check-region-mlbb?id={id}&zone={zone}",
        f"https://gameidcheckerenglish.vercel.app/api/game/cek-region-mlbb-m?id={id}&zone={zone}"
        
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()

            # ✅ Normalize response depending on which API answered
            if "data" in result:  
                # format like old APIs
                data = result["data"]
                return format_response(
                    True,
                    "ID Successfully Found",
                    {
                        "username": data.get("username") or data.get("nickname"),
                        "user_id": str(id),
                        "zone": str(zone),
                        "region": data.get("region") or data.get("country") or "Unknown"
                    },
                    200
                )
            elif result.get("status") == "success" and "result" in result:  
                # format regionweb.vercel.app response
                res = result["result"]
                return format_response(
                    True,
                    "ID Successfully Found",
                    {
                        "username": res.get("nickname"),
                        "user_id": str(id),
                        "zone": str(zone),
                        "region": res.get("country")
                    },
                    200
                )
        except Exception:
            continue

    return format_response(False, "All APIs failed", {}, 500)


# ==========================
# Your Smile.One credentials
# ==========================
UID = "1597136"
EMAIL = "romekiss028@gmail.com"
KEY = "5a0bc5483b7b714eaf2316a6e10d48a2"

# ================
# Helper Functions
# ================
def generate_sign(params: dict) -> str:
    """Generate Smile.One sign"""
    sorted_items = sorted(params.items())
    query_string = "&".join([f"{k}={v}" for k, v in sorted_items])
    raw = query_string + f"&{KEY}"
    return hashlib.md5(hashlib.md5(raw.encode()).hexdigest().encode()).hexdigest()

# ============================
# Mobile Legends Brazil (Smile.One)
# ============================
@app.get("/games/ml_role_brazil")
def check_ml_role_brazil(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Mobile Legends Bang Bang (smile Brazil/Global) ID.
    """

    url = "https://www.smile.one/br/smilecoin/api/getrole"

    payload = {
        "email": EMAIL,
        "uid": UID,
        "userid": id,
        "zoneid": zone,
        "product": "mobilelegends",
        "productid": "13",  # Brazil product ID
        "time": str(int(time.time()))
    }
    payload["sign"] = generate_sign(payload)

    try:
        response = requests.post(url, data=payload, timeout=10)
        res_json = response.json()

        if res_json.get("status") == 200:
            return {
                "code": 200,
                "status": True,
                "message": "ID Successfully Found",
                "data": {
                    "username": res_json.get("username"),
                    "user_id": id,
                    "zone": zone
                }
            }
        else:
            return {
                "code": res_json.get("status", 500),
                "status": False,
                "message": res_json.get("message", "Unknown Error"),
                "data": None
            }

    except Exception as e:
        return {"code": 500, "status": False, "message": str(e), "data": None}

# ------------------------------
# MLBB Brazil WKP (Smile.One)
# ------------------------------
@app.get("/games/ml_role_brazil_wkp")
def check_ml_role_brazil_wkp(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Mobile Legends Bang Bang (Bralin Weekly Pass Limit) ID.
    """
    url = "https://www.smile.one/br/smilecoin/api/getrole"

    payload = {
        "email": EMAIL,
        "uid": UID,
        "userid": id,
        "zoneid": zone,
        "product": "mobilelegends",
        "productid": "16642",  # WKP Brazil product id
        "time": str(int(time.time()))
    }
    payload["sign"] = generate_sign(payload)

    # Common translations for Smile.One error messages
    translations = {
        "Este produto atingiu o limite de compras, favor tente comprar outro produto！": 
            "This product has reached the purchase limit, please try another product!",
        "用户不存在": "User does not exist",
        "无效的参数": "Invalid parameters",
        "系统错误": "System error, please try again later",
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        res_json = response.json()

        message = res_json.get("message", "Unknown Error")
        # Translate if available
        message = translations.get(message, message)

        if res_json.get("status") == 200:
            return {
                "code": 200,
                "status": True,
                "message": "ID Successfully Found",
                "data": {
                    "username": res_json.get("username"),
                    "user_id": id,
                    "zone": zone
                }
            }
        else:
            return {
                "code": res_json.get("status", 500),
                "status": False,
                "message": message,
                "data": None
            }

    except Exception as e:
        return {"code": 500, "status": False, "message": str(e), "data": None}
    
# ------------------------------
# MLBB Philippines (Smile.One)
# ------------------------------
@app.get("/games/ml_role_php")
def check_ml_role_php(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Mobile Legends Bang Bang (Philippines) ID.
    """
    url = "https://www.smile.one/ph/smilecoin/api/getrole"

    payload = {
        "email": EMAIL,
        "uid": UID,
        "userid": id,
        "zoneid": zone,
        "product": "mobilelegends",
        "productid": "212",  # Philippines product id
        "time": str(int(time.time()))
    }
    payload["sign"] = generate_sign(payload)

    try:
        response = requests.post(url, data=payload, timeout=10)
        res_json = response.json()

        if res_json.get("status") == 200:
            return {
                "code": 200,
                "status": True,
                "message": "ID Successfully Found",
                "data": {
                    "username": res_json.get("username"),
                    "user_id": id,
                    "zone": zone
                }
            }
        else:
            return {
                "code": res_json.get("status", 500),
                "status": False,
                "message": res_json.get("message", "Unknown Error"),
                "data": None
            }

    except Exception as e:
        return {"code": 500, "status": False, "message": str(e), "data": None}

# ------------------------------
# MLBB Russia (Smile.One)
# ------------------------------
@app.get("/games/ml_role_ru")
def check_ml_role_ru(id: str, zone: str, _: str = Depends(verify_api_key)):

    """
    Check Mobile Legends Bang Bang (Russia) ID.
    """
    url = "https://www.smile.one/ru/smilecoin/api/getrole"

    payload = {
        "email": EMAIL,
        "uid": UID,
        "userid": id,
        "zoneid": zone,
        "product": "mobilelegends",
        "productid": "250",  # Russia product id
        "time": str(int(time.time()))
    }
    payload["sign"] = generate_sign(payload)

    try:
        response = requests.post(url, data=payload, timeout=10)
        res_json = response.json()

        if res_json.get("status") == 200:
            return {
                "code": 200,
                "status": True,
                "message": "ID Successfully Found",
                "data": {
                    "username": res_json.get("username"),
                    "user_id": id,
                    "zone": zone
                }
            }
        else:
            return {
                "code": res_json.get("status", 500),
                "status": False,
                "message": res_json.get("message", "Unknown Error"),
                "data": None
            }

    except Exception as e:
        return {"code": 500, "status": False, "message": str(e), "data": None}
    
# ------------------------------
# MLBB all regions (Custom API)
# ------------------------------

@app.get("/games/ml_ign")
@limiter.limit("100/day")
def check_mlbb(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Mobile Legends Bang Bang (all regions) ID
    """

    # ✅ API endpoints (fallback order)
    urls = [
        f"https://sanjoymrc.vercel.app/api/game/mobile-legends-mp?id={id}&zone={zone}",
        f"https://c-node-amber.vercel.app/api/game/mobile-legends-mp?id={id}&zone={zone}",
        f"https://cek-id-game.vercel.app/api/game/mobile-legends-mp?id={id}&zone={zone}",
        f"https://gameidcheckerenglish.vercel.app/api/game/mobile-legends-mp?id={id}&zone={zone}"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            result = response.json()

            # ✅ Success check
            if result.get("status") is True and "data" in result:
                return {
                    "code": 200,
                    "status": True,
                    "message": result.get("message", "ID Successfully Found"),
                    "data": {
                        "username": result["data"].get("username"),
                        "user_id": result["data"].get("user_id"),
                        "zone": result["data"].get("zone")
                    }
                }

        except Exception:
            continue

    # ❌ If all APIs fail
    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or MLBB API unavailable",
        "data": {}
    }

# ------------------------------
# MLBB Indo (Custom API)
# ------------------------------

@app.get("/games/ml_indo_id")
@limiter.limit("100/day")
def check_mlbb_indo(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Mobile Legends Bang Bang (Indonesia) ID.
    """

    url = f"https://cek-id-game.vercel.app/api/game/mobile-legends-bang-bang-vc?id={id}&zone={zone}"

    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        if result.get("status") is True and "data" in result:
            return {
                "code": 200,
                "status": True,
                "message": result.get("message", "ID Successfully Found"),
                "data": {
                    "username": result["data"].get("username"),
                    "user_id": result["data"].get("user_id"),
                    "zone": result["data"].get("zone")
                }
            }

    except Exception:
        pass

    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or MLBB Indo API unavailable",
        "data": {}
    }

# ------------------------------
# Mobile legends adventure (Custom API)
# ------------------------------

@app.get("/games/mobile_legends_adventure")
@limiter.limit("100/day")
def check_mobile_legends_adventure(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Mobile Legends Adventure ID with multiple fallback APIs.
    """

    # ✅ API endpoints to try
    urls = [
        f"https://gameidcheckerenglish.vercel.app/api/game/mobile-legends-adventure?id={id}&zone={zone}",
        f"https://cek-id-game.vercel.app/api/game/mobile-legends-adventure?id={id}&zone={zone}",
        f"https://c-node-amber.vercel.app/api/game/mobile-legends-adventure?id={id}&zone={zone}",
        f"https://sanjoymrc.vercel.app/api/game/mobile-legends-adventure?id={id}&zone={zone}"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            result = response.json()

            # ✅ Success check
            if result.get("status") is True and "data" in result:
                return {
                    "code": 200,
                    "status": True,
                    "message": result.get("message", "ID Successfully Found"),
                    "data": {
                        "username": result["data"].get("username"),
                        "user_id": result["data"].get("user_id"),
                        "zone": result["data"].get("zone")
                    }
                }

        except Exception:
            continue

    # ❌ If all failed
    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or Mobile Legends Adventure API unavailable",
        "data": {}
    }

# ------------------------------
# Magic Chess Go Go (Custom API)
# ------------------------------

@app.get("/games/magic_chess_go_go")
@limiter.limit("100/day")
def check_magic_chess_gogo(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Magic Chess Go Go ID with multiple fallback APIs.
    """

    # ✅ API endpoints to try (fallback system)
    urls = [
        f"https://gameidcheckerenglish.vercel.app/api/game/magic-chess-go-go?id={id}&zone={zone}",
        f"https://c-node-amber.vercel.app/api/game/magic-chess-go-go?id={id}&zone={zone}",
        f"https://sanjoymrc.vercel.app/api/game/magic-chess-go-go?id={id}&zone={zone}"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            result = response.json()

            # ✅ Success check
            if result.get("status") is True and "data" in result:
                return {
                    "code": 200,
                    "status": True,
                    "message": result.get("message", "ID Successfully Found"),
                    "data": {
                        "username": result["data"].get("username"),
                        "user_id": result["data"].get("user_id"),
                        "zone": result["data"].get("zone")
                    }
                }

        except Exception:
            continue

    # ❌ If all failed
    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or Magic Chess Go Go API unavailable",
        "data": {}
    }


# ------------------------------
# MLBB Double Diamonds (Custom API)
# ------------------------------
@app.get("/check_double_diamonds")
def check_double_diamonds(id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check mlbb double diamonds ID.
    """
    url = f"https://doublediamonds.vercel.app/?id={id}&zone={zone}"

    try:
        response = requests.get(url, timeout=10)
        res_json = response.json()

        # If username found, success
        if res_json.get("username"):
            return {
                "code": 200,
                "status": True,
                "message": "ID Successfully Found",
                "data": {
                    "author": res_json.get("author"),
                    "mobile": res_json.get("mobile"),
                    "username": res_json.get("username"),
                    "region": res_json.get("region"),
                    "products": res_json.get("products", [])
                }
            }
        else:
            return {
                "code": 404,
                "status": False,
                "message": "User not found",
                "data": None
            }

    except Exception as e:
        return {"code": 500, "status": False, "message": str(e), "data": None}

# ------------------------------
# Bgmi
# ------------------------------

@app.get("/games/bgmi")
@limiter.limit("100/day")
def check_bgmi_username(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check bgmi ID .
    """
    url = f"https://bgmi-nine.vercel.app/getUsername?id={id}"
    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        if result.get("message") == "SUCCESS":
            return format_response(
                True,
                "ID found successfully",
                {
                    "user_id": id,
                    "username": result.get("username"),
                    "zone": None
                },
                200
            )
        else:
            return format_response(False, "ID not found", None, 404)
    except Exception as e:
        return {
            "code": 500,
            "status": False,
            "message": "An error occurred while retrieving the data",
            "error": str(e)
        }
    
# ------------------------------
# Pubg Global
# ------------------------------

@app.get("/games/pubg_mobile_global")
@limiter.limit("100/day")
def check_pubg_mobile_global(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check pubg mobile global ID.
    """
    urls = [
        f"https://gameidcheckerenglish.vercel.app/api/game/pubg-mobile-tp?id={id}",
        f"https://gameidcheckerenglish.vercel.app/api/game/pubg-mobile-global-vc?id={id}",
        f"https://gameidcheckerenglish.vercel.app/api/game/pubg-mobile-vc?id={id}"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()

            # ✅ If one API works, return the same structure
            if result.get("status") is True:
                return result
        except Exception:
            continue

    return {
        "code": 500,
        "status": False,
        "message": "All PUBG Global APIs failed",
        "data": {}
    }

# ------------------------------
# Honor of Kings
# ------------------------------ 

@app.get("/games/honor_of_kings")
@limiter.limit("100/day")
def check_honor_of_kings(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check Honor of Kings ID.
    """
    urls = [
        f"https://gameidcheckerenglish.vercel.app/api/game/honor-of-kings-tp?id={id}",
        f"https://gameidcheckerenglish.vercel.app/api/game/honor-of-kings-vc?id={id}",
        f"https://gameidcheckerenglish.vercel.app/api/game/honor-of-kings?id={id}"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()

            # ✅ If success, return response as-is
            if result.get("status") is True:
                return result
        except Exception:
            continue

    # ❌ If all fail
    return {
        "code": 500,
        "status": False,
        "message": "All Honor of Kings APIs failed",
        "data": {}
    }

# ------------------------------
# 8 Ball Pool
# ------------------------------

@app.get("/games/8_ball_pool")
@limiter.limit("100/day")
def check_8ball_pool(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check 8 Ball Pool ID.
    """
    url = f"https://c-node-amber.vercel.app/api/game/8-ball-pool?id={id}"
    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        # ✅ If API failed with 500/404 → return clean Wrong ID
        if not result.get("status"):
            return {
                "code": 404,
                "status": False,
                "message": "Wrong ID",
                "data": {}
            }

        # ✅ Success → return as-is
        return result

    except Exception:
        return {
            "code": 500,
            "status": False,
            "message": "8 Ball Pool API unavailable",
            "data": {}
        }

# ------------------------------
# Blood Strike
# ------------------------------

@app.get("/games/blood_strike")
@limiter.limit("100/day")
def check_blood_strike(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check Blood Strike ID.
    """
    url = f"https://gameidcheckerenglish.vercel.app/api/game/blood-strike?id={id}&zone=-1"
    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        # ❌ Wrong ID case
        if not result.get("status"):
            return {
                "code": 404,
                "status": False,
                "message": "Wrong ID",
                "data": {}
            }

        # ✅ Success case
        return {
            "code": 200,
            "status": True,
            "message": "ID Successfully Found",
            "data": result.get("data", {})
        }

    except Exception:
        return {
            "code": 500,
            "status": False,
            "message": "Blood Strike API unavailable",
            "data": {}
        }

# ------------------------------
# Honkai Impact 3
# ------------------------------

@app.get("/games/honkai_impact_3")
@limiter.limit("100/day")
def check_honkai_impact_3(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check Honkai Impact 3 ID.
    """
    url = f"https://gameidcheckerenglish.vercel.app/api/game/honkai-impact-3?id={id}"
    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        # ❌ Wrong ID case
        if not result.get("status"):
            return {
                "code": 404,
                "status": False,
                "message": "Wrong ID",
                "data": {}
            }

        # ✅ Success case
        return {
            "code": 200,
            "status": True,
            "message": "ID Successfully Found",
            "data": result.get("data", {})
        }

    except Exception:
        return {
            "code": 500,
            "status": False,
            "message": "Honkai Impact 3 API unavailable",
            "data": {}
        }

# ------------------------------
# Super Sus
# ------------------------------

@app.get("/games/super_sus")
@limiter.limit("100/day")
def check_super_sus(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check Super Sus ID .
    """
    urls = [
        f"https://gameidcheckerenglish.vercel.app/api/game/super-sus?id={id}",
        f"https://gameidcheckerenglish.vercel.app/api/game/super-sus-vc?id={id}"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            result = response.json()

            # ❌ Wrong ID case
            if not result.get("status"):
                continue  

            # ✅ Success
            return {
                "code": 200,
                "status": True,
                "message": "ID Successfully Found",
                "data": result.get("data", {})
            }

        except Exception:
            continue  

    # ❌ If both fail
    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or Super Sus API unavailable",
        "data": {}
    }

# ------------------------------
# Arena of Valor
# ------------------------------

# ✅ Arena of Valor
@app.get("/games/arena_of_valor")
@limiter.limit("100/day")
def check_arena_of_valor(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check Arena of Valor ID .
    """
    url = f"https://c-node-amber.vercel.app/api/game/arena-of-valor?id={id}"

    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        # ❌ Wrong ID
        if not result.get("status"):
            return {
                "code": 404,
                "status": False,
                "message": "Wrong ID",
                "data": {}
            }

        # ✅ Success
        return {
            "code": 200,
            "status": True,
            "message": "ID Successfully Found",
            "data": result.get("data", {})
        }

    except Exception:
        return {
            "code": 500,
            "status": False,
            "message": "Arena of Valor API unavailable",
            "data": {}
        }
    
# ------------------------------
# Undawn
# ------------------------------

@app.get("/games/undawn")
@limiter.limit("100/day")

def check_undawn(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check Undawn ID .
    """
    url = f"https://c-node-amber.vercel.app/api/game/undawn?id={id}"

    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        # ❌ Wrong ID
        if not result.get("status"):
            return {
                "code": 404,
                "status": False,
                "message": "Wrong ID",
                "data": {}
            }

        # ✅ Success
        return {
            "code": 200,
            "status": True,
            "message": "ID Successfully Found",
            "data": result.get("data", {})
        }

    except Exception:
        return {
            "code": 500,
            "status": False,
            "message": "Undawn API unavailable",
            "data": {}
        }

# ------------------------------
# Sausage Man
# ------------------------------

@app.get("/games/sausage_man")
@limiter.limit("100/day")
def check_sausage_man(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check Sausage Man ID.
    """
    url = f"https://gameidcheckerenglish.vercel.app/api/game/sausage-man?id={id}"

    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        # ❌ Wrong ID
        if not result.get("status"):
            return {
                "code": 404,
                "status": False,
                "message": "Wrong ID",
                "data": {}
            }

        # ✅ Success
        return {
            "code": 200,
            "status": True,
            "message": "ID Successfully Found",
            "data": result.get("data", {})
        }

    except Exception:
        return {
            "code": 500,
            "status": False,
            "message": "Sausage Man API unavailable",
            "data": {}
        }

# ------------------------------
# Clash of Clans
# ------------------------------

@app.get("/games/clash_of_clan")
@limiter.limit("100/day")
def check_clash_of_clan(request: Request, id: str, _: str = Depends(verify_api_key)):
    """
    Check Clash of Clans ID.
    """
    url = f"https://cek-id-game.vercel.app/api/game/clash-of-st?id={id}"

    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        # ❌ Wrong ID
        if not result.get("status"):
            return {
                "code": 404,
                "status": False,
                "message": "Wrong ID",
                "data": {}
            }

        # ✅ Normalize Success Response
        return {
            "code": 200,
            "status": True,
            "message": "ID Successfully Found",
            "data": {
                "username": result["data"].get("username"),
                "user_id": result["data"].get("user_id"),
                "zone": result["data"].get("zone"),
                "th_level": result["data"].get("th_level"),
                "exp_level": result["data"].get("exp_level"),
                "throphies": result["data"].get("throphies"),
            }
        }

    except Exception:
        return {
            "code": 500,
            "status": False,
            "message": "Clash of ST API unavailable",
            "data": {}
        }

# ------------------------------
# Clash Royale
# ------------------------------

@app.get("/games/clash_royale")
@limiter.limit("100/day")
def check_clash_royale(request: Request, id: str, _: str = Depends(verify_api_key)):

    """
    Check Clash Royale ID.
    """
    url = f"https://gameidcheckerenglish.vercel.app/api/game/clash-royale-st?id={id}"

    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        # ❌ Wrong ID
        if not result.get("status"):
            return {
                "code": 404,
                "status": False,
                "message": "Wrong ID",
                "data": {}
            }

        # ✅ Normalize Success Response
        return {
            "code": 200,
            "status": True,
            "message": "ID Successfully Found",
            "data": {
                "username": result["data"].get("username"),
                "user_id": result["data"].get("user_id"),
                "zone": result["data"].get("zone"),
                "level": result["data"].get("level"),
                "throphies": result["data"].get("throphies"),
            }
        }

    except Exception:
        return {
            "code": 500,
            "status": False,
            "message": "Clash Royale API unavailable",
            "data": {}
        }

# ✅ Zone mapping for Genshin Impact
GENSHIN_ZONES = {
    "os_usa": "America",
    "os_euro": "Europe",
    "os_asia": "Asia",
    "os_cht": "TW, HK, MO",
    # allow shorthand too
    "america": "America",
    "europe": "Europe",
    "asia": "Asia",
    "tw": "TW, HK, MO",
    "hk": "TW, HK, MO",
    "mo": "TW, HK, MO",
}

# ------------------------------
# Genshin Impact
# ------------------------------

@app.get("/games/genshin_impact")
@limiter.limit("100/day")
def check_genshin_impact(
    request: Request,
    id: str,
    zone: str = "asia",
    _: str = Depends(verify_api_key)
):
    """
    Check Genshin Impact ID.
    """
    

    zone_key = zone.lower()
    # Map shorthand to full zoneId
    if zone_key in ["america", "usa", "na"]:
        zone_id, zone_name = "os_usa", "America"
    elif zone_key in ["europe", "eu"]:
        zone_id, zone_name = "os_euro", "Europe"
    elif zone_key in ["asia"]:
        zone_id, zone_name = "os_asia", "Asia"
    elif zone_key in ["tw", "hk", "mo", "cht", "tw_hk_mo"]:
        zone_id, zone_name = "os_cht", "TW, HK, MO"
    else:
        return {
            "code": 400,
            "status": False,
            "message": f"Invalid zone '{zone}'. Allowed: Asia, Europe, America, TW/HK/MO",
            "data": {}
        }

    urls = [
        f"https://cek-id-game.vercel.app/api/game/genshin-impact-vc?id={id}&zone={zone_id}",
        f"https://c-node-amber.vercel.app/api/game/genshin-impact?id={id}&zone={zone_id}",
        f"https://gameopenworld.vercel.app/genshin?characterId={id}&serverId={zone_id}"
    ]

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            result = response.json()

            # ✅ First two APIs
            if result.get("status") is True and "data" in result:
                return {
                    "code": 200,
                    "status": True,
                    "message": "ID Successfully Found",
                    "data": {
                        "username": result["data"].get("username"),
                        "user_id": result["data"].get("user_id"),
                        "zone": zone_name
                    }
                }

            # ✅ Third API
            if result.get("success") is True and "data" in result:
                return {
                    "code": 200,
                    "status": True,
                    "message": "ID Successfully Found",
                    "data": {
                        "username": result["data"].get("nickname") or result["data"].get("name"),
                        "user_id": result["data"].get("uid"),
                        "zone": zone_name
                    }
                }

        except Exception:
            continue

    # ❌ All sources failed
    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or Genshin Impact API unavailable",
        "data": {}
    }

# ------------------------------
# Honkai: Star Rail
# ------------------------------

@app.get("/games/honkai_star_rail")
@limiter.limit("100/day")
def check_honkai_star_rail(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Honkai: Star Rail ID.
    """

    # ✅ Zone mappings (official IDs → display names)
    zone_map = {
        "prod_official_usa": "America",
        "prod_official_asia": "Asia",
        "prod_official_eur": "Europe",
        "prod_official_cht": "TW,HK,MO",
        "os_usa": "America",
        "os_asia": "Asia",
        "os_euro": "Europe",
        "os_cht": "TW,HK,MO",
    }

    # ✅ Accept user-friendly input → multiple possible API zones
    user_zone_map = {
        "america": ["prod_official_usa", "os_usa"],
        "asia": ["prod_official_asia", "os_asia"],
        "europe": ["prod_official_eur", "os_euro"],
        "tw": ["prod_official_cht", "os_cht"],
        "tw,hk,mo": ["prod_official_cht", "os_cht"],
    }

    zone_key = zone.lower()
    if zone_key not in user_zone_map:
        return {
            "code": 400,
            "status": False,
            "message": f"Invalid zone '{zone}'. Allowed zones: {list(user_zone_map.keys())}",
            "data": {}
        }

    # ✅ Try both official + os zones
    possible_zone_ids = user_zone_map[zone_key]

    for zone_api in possible_zone_ids:
        zone_display = zone_map[zone_api]

        # ✅ APIs to try
        urls = [
            f"https://cek-id-game.vercel.app/api/game/honkai-star-rail?id={id}&zone={zone_api}",
            f"https://gameopenworld.vercel.app/honkai-starrail?characterId={id}&serverId={zone_api}",
            f"https://gameidcheckerenglish.vercel.app/api/game/honkai-star-rail?id={id}&zone={zone_api}"
        ]

        for url in urls:
            try:
                response = requests.get(url, timeout=10)
                result = response.json()

                # 🔹 API #1 (cek-id-game)
                if "status" in result and result.get("status") is True and "data" in result:
                    return {
                        "code": 200,
                        "status": True,
                        "message": "ID Successfully Found",
                        "data": {
                            "username": result["data"].get("username"),
                            "user_id": result["data"].get("user_id"),
                            "zone": zone_display
                        }
                    }

                # 🔹 API #2 (gameopenworld)
                if "success" in result and result.get("success") is True and "data" in result:
                    return {
                        "code": 200,
                        "status": True,
                        "message": "ID Successfully Found",
                        "data": {
                            "username": result["data"].get("nickname") or result["data"].get("name"),
                            "user_id": result["data"].get("uid"),
                            "zone": zone_display
                        }
                    }

                # 🔹 API #3 (gameidcheckerenglish)
                if "code" in result and result.get("code") == 200 and "data" in result:
                    return {
                        "code": 200,
                        "status": True,
                        "message": result.get("message", "ID Successfully Found"),
                        "data": {
                            "username": result["data"].get("username"),
                            "user_id": result["data"].get("user_id"),
                            "zone": zone_display
                        }
                    }

            except Exception:
                continue

    # ❌ If all failed
    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or Honkai: Star Rail API unavailable",
        "data": {}
    }

# ------------------------------
# Zenless Zone Zero (Custom API)
# ------------------------------

@app.get("/games/zenless_zone_zero")
@limiter.limit("100/day")
def check_zenless_zone_zero(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Zenless Zone Zero ID .
    """

    # ✅ Zone mappings (API zones → display names)
    zone_map = {
        "prod_gf_us": "America",
        "prod_gf_jp": "Asia",
        "prod_gf_eu": "Europe",
        "prod_gf_sg": "TW,HK,MO",
        "os_usa": "America",
        "os_asia": "Asia",
        "os_euro": "Europe",
        "os_cht": "TW,HK,MO",
    }

    # ✅ Accept user-friendly input
    user_zone_map = {
        "america": ["prod_gf_us", "os_usa"],
        "asia": ["prod_gf_jp", "os_asia"],
        "europe": ["prod_gf_eu", "os_euro"],
        "tw": ["prod_gf_sg", "os_cht"],
        "tw,hk,mo": ["prod_gf_sg", "os_cht"],
    }

    zone_key = zone.lower()
    if zone_key not in user_zone_map:
        return {
            "code": 400,
            "status": False,
            "message": f"Invalid zone '{zone}'. Allowed zones: {list(user_zone_map.keys())}",
            "data": {}
        }

    # Pick first as primary zone, second as alternative
    zone_api_list = user_zone_map[zone_key]
    primary_zone = zone_api_list[0]
    alt_zone = zone_api_list[1] if len(zone_api_list) > 1 else None

    # Display zone name
    zone_display = zone_map[primary_zone]

    # ✅ APIs to try
    urls = [
        f"https://cek-id-game.vercel.app/api/game/zenless-zone-zero?id={id}&zone={primary_zone}",
        f"https://gameidcheckerenglish.vercel.app/api/game/zenless-zone-zero?id={id}&zone={primary_zone}",
    ]

    # Add gameopenworld (needs os_* format)
    if alt_zone and alt_zone.startswith("os_"):
        urls.append(f"https://gameopenworld.vercel.app/zzz?characterId={id}&serverId={alt_zone}")

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            result = response.json()

            # 🔹 API #1 & #2 (cek-id-game + gameidcheckerenglish)
            if "status" in result and result.get("status") is True and "data" in result:
                return {
                    "code": 200,
                    "status": True,
                    "message": result.get("message", "ID Successfully Found"),
                    "data": {
                        "username": result["data"].get("username"),
                        "user_id": result["data"].get("user_id"),
                        "zone": zone_display
                    }
                }

            # 🔹 API #3 (gameopenworld)
            if "success" in result and result.get("success") is True and "data" in result:
                return {
                    "code": 200,
                    "status": True,
                    "message": "ID Successfully Found",
                    "data": {
                        "username": result["data"].get("nickname") or result["data"].get("name"),
                        "user_id": result["data"].get("uid"),
                        "zone": result["data"].get("region", zone_display)
                    }
                }

        except Exception:
            continue

    # ❌ If all failed
    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or Zenless Zone Zero API unavailable",
        "data": {}
    }

# ------------------------------
# Wuthering Waves (Custom API)
# ------------------------------

@app.get("/games/wuthering_waves")
@limiter.limit("100/day")
def check_wuthering_waves(request: Request, id: str, zone: str, _: str = Depends(verify_api_key)):
    """
    Check Wuthering Waves ID .
    """

    # ✅ Zone mappings
    zone_map = {
        "os_usa": "America",
        "os_euro": "Europe",
        "os_asia": "Asia",
        "os_sea": "SEA",
        "os_cht": "HMT",
    }

    # ✅ Accept user-friendly input
    user_zone_map = {
        "america": "os_usa",
        "europe": "os_euro",
        "asia": "os_asia",
        "sea": "os_sea",
        "hmt": "os_cht",
    }

    zone_key = zone.lower()
    if zone_key not in user_zone_map:
        return {
            "code": 400,
            "status": False,
            "message": f"Invalid zone '{zone}'. Allowed zones: {list(user_zone_map.keys())}",
            "data": {}
        }

    # API-compatible zone
    zone_api = user_zone_map[zone_key]
    zone_display = zone_map[zone_api]

    # ✅ API call
    url = f"https://gameopenworld.vercel.app/wuthering?characterId={id}&serverId={zone_api}"

    try:
        response = requests.get(url, timeout=10)
        result = response.json()

        if "success" in result and result.get("success") is True and "data" in result:
            return {
                "code": 200,
                "status": True,
                "message": "ID Successfully Found",
                "data": {
                    "username": result["data"].get("name"),
                    "user_id": result["data"].get("openid"),
                    "zone": zone_display
                }
            }

    except Exception:
        pass

    # ❌ If failed
    return {
        "code": 404,
        "status": False,
        "message": "Wrong ID or Wuthering Waves API unavailable",
        "data": {}
    }

# Add more routes and logic as needed for your application.
