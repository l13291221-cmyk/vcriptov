"""
Definizione centralizzata dei piani di abbonamento e delle crypto supportate.
Modifica qui prezzi, feature o simboli senza toccare il resto del codice.
"""

# Tutte le crypto gestite dal motore (coppie contro USDT).
ALL_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "DOGE/USDT",
    "BNB/USDT",
    "MATIC/USDT",
    "LINK/USDT",
    "DOT/USDT",
]

# Prezzi iniziali indicativi per la simulazione (paper trading).
SEED_PRICES = {
    "BTC/USDT": 68000.0,
    "ETH/USDT": 3500.0,
    "SOL/USDT": 165.0,
    "XRP/USDT": 0.52,
    "ADA/USDT": 0.45,
    "DOGE/USDT": 0.13,
    "BNB/USDT": 585.0,
    "MATIC/USDT": 0.72,
    "LINK/USDT": 14.5,
    "DOT/USDT": 6.8,
}

PLANS = {
    "starter": {
        "id": "starter",
        "name": "Starter",
        "price_eur": 10,
        "old_price_eur": None,
        "period": "mese",
        "lifetime": False,
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "sentiment": False,
        "telegram": False,
        "custom_strategy": False,
        "priority_signals": False,
        "features": [
            "Accesso base alla dashboard",
            "Segnali automatizzati su BTC ed ETH",
            "Storico operazioni e P&L",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_eur": 25,
        "old_price_eur": None,
        "period": "mese",
        "lifetime": False,
        "symbols": ALL_SYMBOLS,
        "sentiment": True,
        "telegram": True,
        "custom_strategy": False,
        "priority_signals": False,
        "features": [
            "Accesso completo a tutte le crypto",
            "Filtro notizie / sentiment per mercati ad alto rischio",
            "Notifiche Telegram",
            "Tutto ciò che è incluso in Starter",
        ],
    },
    "vip": {
        "id": "vip",
        "name": "VIP",
        "price_eur": 45,
        "old_price_eur": 60,
        "period": "mese",
        "lifetime": False,
        "symbols": ALL_SYMBOLS,
        "sentiment": True,
        "telegram": True,
        "custom_strategy": True,
        "priority_signals": True,
        "features": [
            "Tutte le funzioni Pro",
            "Parametri di strategia / rischio personalizzabili",
            "Segnali prioritari",
        ],
    },
    "lifetime": {
        "id": "lifetime",
        "name": "Lifetime",
        "price_eur": 200,
        "old_price_eur": None,
        "period": "una tantum",
        "lifetime": True,
        "symbols": ALL_SYMBOLS,
        "sentiment": True,
        "telegram": True,
        "custom_strategy": True,
        "priority_signals": True,
        "features": [
            "Accesso a vita a tutte le funzioni VIP",
            "Nessun canone mensile",
            "Aggiornamenti inclusi",
        ],
    },
}

# Ordine di visualizzazione nel paywall.
PLAN_ORDER = ["starter", "pro", "vip", "lifetime"]


def get_plan(plan_id: str) -> dict | None:
    return PLANS.get(plan_id)


def plan_symbols(plan_id: str) -> list[str]:
    plan = PLANS.get(plan_id)
    return plan["symbols"] if plan else []
