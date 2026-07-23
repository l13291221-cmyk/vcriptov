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
    "AVAX/USDT",
    "TRX/USDT",
    "LTC/USDT",
    "BCH/USDT",
    "ATOM/USDT",
    "UNI/USDT",
    "XLM/USDT",
    "ETC/USDT",
    "FIL/USDT",
    "NEAR/USDT",
    "APT/USDT",
    "ARB/USDT",
    "OP/USDT",
    "INJ/USDT",
    "TON/USDT",
    "SUI/USDT",
]

# Prezzi iniziali indicativi, usati solo come valore di partenza prima che
# arrivino i prezzi reali dall'exchange (o in modalità offline).
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
    "AVAX/USDT": 35.0,
    "TRX/USDT": 0.13,
    "LTC/USDT": 85.0,
    "BCH/USDT": 480.0,
    "ATOM/USDT": 8.0,
    "UNI/USDT": 11.0,
    "XLM/USDT": 0.11,
    "ETC/USDT": 26.0,
    "FIL/USDT": 5.5,
    "NEAR/USDT": 6.0,
    "APT/USDT": 9.0,
    "ARB/USDT": 0.9,
    "OP/USDT": 2.2,
    "INJ/USDT": 25.0,
    "TON/USDT": 6.5,
    "SUI/USDT": 1.4,
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
    "trial": {
        "id": "trial",
        "name": "Prova gratuita",
        "price_eur": 0,
        "old_price_eur": None,
        "period": "3 giorni",
        "lifetime": False,
        "trial": True,
        "trial_days": 3,
        "symbols": ALL_SYMBOLS,
        "sentiment": True,
        "telegram": True,
        "custom_strategy": False,
        "priority_signals": False,
        "features": [
            "Prova TUTTO gratis per 3 giorni",
            "Accesso completo a tutte le crypto",
            "Notifiche Telegram incluse",
            "Nessun pagamento richiesto",
        ],
    },
}

# Ordine di visualizzazione nel paywall (la prova gratuita per prima).
PLAN_ORDER = ["trial", "starter", "pro", "vip", "lifetime"]


def get_plan(plan_id: str) -> dict | None:
    return PLANS.get(plan_id)


def plan_symbols(plan_id: str) -> list[str]:
    plan = PLANS.get(plan_id)
    return plan["symbols"] if plan else []
