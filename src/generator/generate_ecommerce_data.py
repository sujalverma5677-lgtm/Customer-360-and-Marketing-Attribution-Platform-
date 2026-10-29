"""
Customer 360 & Marketing Attribution Platform
Dataset Generator: GA4 Obfuscated Sample E-Commerce + CRM + Ad Spend
Generates high-fidelity, production-grade synthetic data matching BigQuery schemas.
"""

import os
import json
import random
import hashlib
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Set deterministic seed for reproducible results
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley",
    "Casey", "Jamie", "Avery", "Logan", "Cameron", "Reese", "Quinn", "Skyler",
    "Emma", "Liam", "Olivia", "Noah", "Sophia", "Jackson", "Ava", "Lucas",
    "Mia", "Ethan", "Harper", "Oliver", "Evelyn", "Aiden", "Amelia", "Elijah"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"
]

DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "proton.me", "techcorp.io"]

CITIES_DATA = [
    {"city": "New York", "region": "New York", "country": "United States"},
    {"city": "Los Angeles", "region": "California", "country": "United States"},
    {"city": "Chicago", "region": "Illinois", "country": "United States"},
    {"city": "Austin", "region": "Texas", "country": "United States"},
    {"city": "Seattle", "region": "Washington", "country": "United States"},
    {"city": "Miami", "region": "Florida", "country": "United States"},
    {"city": "Toronto", "region": "Ontario", "country": "Canada"},
    {"city": "London", "region": "England", "country": "United Kingdom"},
]

CHANNELS = [
    {
        "channel": "Paid Search - Brand",
        "source": "google",
        "medium": "cpc",
        "campaign": "brand_exact_match_core",
        "cost_per_click": (0.80, 1.40),
        "daily_budget": 120.0,
        "funnel_stage": "bottom"
    },
    {
        "channel": "Paid Search - Generic",
        "source": "google",
        "medium": "cpc",
        "campaign": "nonbrand_category_intent",
        "cost_per_click": (2.10, 3.80),
        "daily_budget": 350.0,
        "funnel_stage": "top"
    },
    {
        "channel": "Paid Social - Meta Prospecting",
        "source": "facebook",
        "medium": "paid_social",
        "campaign": "meta_lookalike_top_buyers",
        "cost_per_click": (1.10, 2.20),
        "daily_budget": 450.0,
        "funnel_stage": "top"
    },
    {
        "channel": "Paid Social - Meta Retargeting",
        "source": "facebook",
        "medium": "paid_social",
        "campaign": "meta_dpa_dynamic_retargeting",
        "cost_per_click": (1.50, 2.90),
        "daily_budget": 200.0,
        "funnel_stage": "bottom"
    },
    {
        "channel": "Paid Video - TikTok Ads",
        "source": "tiktok",
        "medium": "paid_social",
        "campaign": "tiktok_ugc_viral_spring",
        "cost_per_click": (0.60, 1.30),
        "daily_budget": 300.0,
        "funnel_stage": "top"
    },
    {
        "channel": "Email Marketing",
        "source": "klaviyo",
        "medium": "email",
        "campaign": "klaviyo_abandoned_cart_flow",
        "cost_per_click": (0.05, 0.15),
        "daily_budget": 40.0,
        "funnel_stage": "bottom"
    },
    {
        "channel": "Organic Search",
        "source": "google",
        "medium": "organic",
        "campaign": "(organic)",
        "cost_per_click": (0.0, 0.0),
        "daily_budget": 0.0,
        "funnel_stage": "middle"
    },
    {
        "channel": "Direct",
        "source": "(direct)",
        "medium": "(none)",
        "campaign": "(direct)",
        "cost_per_click": (0.0, 0.0),
        "daily_budget": 0.0,
        "funnel_stage": "bottom"
    }
]

PRODUCTS = [
    {"sku": "SKU-PRO-001", "name": "Ergonomic Mechanical Keyboard", "price": 149.0, "category": "Hardware"},
    {"sku": "SKU-PRO-002", "name": "Ultra-Wide Gaming Monitor 34in", "price": 499.0, "category": "Displays"},
    {"sku": "SKU-PRO-003", "name": "Active Noise Cancelling Headset", "price": 229.0, "category": "Audio"},
    {"sku": "SKU-PRO-004", "name": "Ergonomic Mesh Task Chair", "price": 379.0, "category": "Furniture"},
    {"sku": "SKU-PRO-005", "name": "USB-C Dual 4K Thunderbolt Dock", "price": 189.0, "category": "Accessories"},
    {"sku": "SKU-PRO-006", "name": "Smart Desk Mat with Qi Charger", "price": 69.0, "category": "Accessories"},
]


def sha256_hash(text: str) -> str:
    """Hash email/identifiers according to privacy standards (GDPR/CCPA)."""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def generate_dataset(start_date="2026-08-01", end_date="2026-10-28", num_crm_customers=1200):
    """
    Generates consistent raw tables:
    1. raw_crm_customers
    2. raw_crm_orders
    3. raw_ga4_events
    4. raw_ad_spend
    """
    print(f"Generating realistic dataset from {start_date} to {end_date}...")
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end_dt - start_dt).days + 1

    # 1. GENERATE CRM CUSTOMERS
    crm_customers = []
    used_emails = set()

    for i in range(1, num_crm_customers + 1):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        domain = random.choice(DOMAINS)
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(10, 9999)}@{domain}"
        while email in used_emails:
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(10000, 99999)}@{domain}"
        used_emails.add(email)

        loc = random.choice(CITIES_DATA)
        signup_offset = random.randint(0, total_days - 10)
        signup_date = start_dt + timedelta(days=signup_offset, seconds=random.randint(0, 86400))
        cust_id = f"CUST-{10000 + i}"

        crm_customers.append({
            "customer_id": cust_id,
            "email": email,
            "email_hash": sha256_hash(email),
            "first_name": first_name,
            "last_name": last_name,
            "phone": f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "signup_timestamp": signup_date.strftime("%Y-%m-%d %H:%M:%S"),
            "signup_date": signup_date.strftime("%Y-%m-%d"),
            "country": loc["country"],
            "region": loc["region"],
            "city": loc["city"],
            "lifecycle_stage": "customer"
        })

    df_crm_customers = pd.DataFrame(crm_customers)

    # 2. GENERATE AD SPEND (Daily per channel)
    ad_spend_records = []
    for d in range(total_days):
        current_day = start_dt + timedelta(days=d)
        date_str = current_day.strftime("%Y-%m-%d")
        for ch in CHANNELS:
            if ch["daily_budget"] > 0:
                # Add day-of-week seasonality (weekends have 20% higher traffic)
                dow_mult = 1.2 if current_day.weekday() >= 5 else 1.0
                spend = round(ch["daily_budget"] * random.uniform(0.85, 1.25) * dow_mult, 2)
                cpc = random.uniform(ch["cost_per_click"][0], ch["cost_per_click"][1])
                clicks = max(1, int(spend / cpc))
                impressions = int(clicks * random.uniform(22.0, 45.0))
                
                ad_spend_records.append({
                    "date": date_str,
                    "channel_name": ch["channel"],
                    "utm_source": ch["source"],
                    "utm_medium": ch["medium"],
                    "utm_campaign": ch["campaign"],
                    "daily_spend": spend,
                    "clicks": clicks,
                    "impressions": impressions,
                    "cpc": round(spend / clicks, 2) if clicks > 0 else 0.0,
                    "ctr_percent": round((clicks / impressions) * 100, 2) if impressions > 0 else 0.0
                })

    df_ad_spend = pd.DataFrame(ad_spend_records)

    # 3. GENERATE GA4 EVENTS & MULTI-TOUCH JOURNEYS & CRM ORDERS
    ga4_events = []
    crm_orders = []

    # Map each customer to devices & anonymous IDs
    devices = [
        {"category": "mobile", "os": "iOS", "browser": "Safari"},
        {"category": "desktop", "os": "Macintosh", "browser": "Chrome"},
        {"category": "desktop", "os": "Windows", "browser": "Chrome"},
        {"category": "mobile", "os": "Android", "browser": "Chrome"},
        {"category": "tablet", "os": "iOS", "browser": "Safari"}
    ]

    order_seq = 1001
    
    # Also simulate pure anonymous visitors who bounce or never convert (realistic bounce rate ~60%)
    pure_anonymous_count = 600

    print("Generating customer journeys & touchpoints...")
    for idx, cust in df_crm_customers.iterrows():
        cust_id = cust["customer_id"]
        email_hash = cust["email_hash"]
        signup_dt = datetime.strptime(cust["signup_timestamp"], "%Y-%m-%d %H:%M:%S")

        # Customer has 1 to 3 distinct devices/cookies in their lifetime
        num_devices = random.choices([1, 2, 3], weights=[0.45, 0.40, 0.15])[0]
        cust_devices = []
        for dev_i in range(num_devices):
            pseudo_id = f"{random.randint(100000000, 999999999)}.{int(signup_dt.timestamp()) + dev_i * 1000}"
            dev_meta = random.choice(devices)
            cust_devices.append({"user_pseudo_id": pseudo_id, "device": dev_meta})

        # Number of conversions / orders for this customer (Pareto distribution for RFM)
        # 60% have 1 order, 25% have 2 orders, 10% have 3 orders, 5% VIPs have 4-7 orders
        num_orders = random.choices([1, 2, 3, 4, 5, 6], weights=[0.58, 0.24, 0.10, 0.05, 0.02, 0.01])[0]

        last_journey_time = signup_dt - timedelta(days=random.randint(1, 14))
        if last_journey_time < start_dt:
            last_journey_time = start_dt + timedelta(days=1)

        for ord_i in range(num_orders):
            # A conversion journey contains 1 to 5 marketing touchpoints
            touchpoint_count = random.choices([1, 2, 3, 4, 5], weights=[0.25, 0.35, 0.22, 0.12, 0.06])[0]
            
            # Select channels along funnel (e.g. top of funnel -> retargeting/email/brand)
            journey_channels = []
            if touchpoint_count == 1:
                journey_channels.append(random.choice(CHANNELS))
            else:
                # First touch: Top of funnel
                top_channels = [c for c in CHANNELS if c["funnel_stage"] in ["top", "middle"]]
                journey_channels.append(random.choice(top_channels))
                # Intermediate touchpoints
                for _ in range(touchpoint_count - 2):
                    journey_channels.append(random.choice(CHANNELS))
                # Last touch: Bottom of funnel
                bottom_channels = [c for c in CHANNELS if c["funnel_stage"] in ["bottom", "middle"]]
                journey_channels.append(random.choice(bottom_channels))

            order_dt = last_journey_time + timedelta(days=random.randint(1, 20), hours=random.randint(1, 12))
            if order_dt > end_dt:
                break
            last_journey_time = order_dt

            # Distribute touchpoints backwards from order date
            touchpoint_times = []
            curr_tp_time = order_dt
            for tp_idx in range(touchpoint_count):
                touchpoint_times.insert(0, curr_tp_time)
                curr_tp_time = curr_tp_time - timedelta(days=random.randint(0, 4), hours=random.randint(1, 8))

            # Simulate GA4 sessions for each touchpoint
            order_id = f"ORD-{order_seq}"
            order_seq += 1

            for tp_i, (tp_time, ch_info) in enumerate(zip(touchpoint_times, journey_channels)):
                assigned_dev = random.choice(cust_devices)
                pseudo_id = assigned_dev["user_pseudo_id"]
                dev_meta = assigned_dev["device"]
                session_id = f"sess_{int(tp_time.timestamp())}_{random.randint(100, 999)}"
                is_conversion_session = (tp_i == touchpoint_count - 1)

                # Events in session
                # 1. session_start
                ga4_events.append({
                    "event_date": tp_time.strftime("%Y%m%d"),
                    "event_timestamp": int(tp_time.timestamp() * 1000000),
                    "event_name": "session_start",
                    "user_pseudo_id": pseudo_id,
                    "user_id": cust_id if (tp_time >= signup_dt or is_conversion_session) else None,
                    "ga_session_id": session_id,
                    "ga_session_number": tp_i + 1,
                    "source": ch_info["source"],
                    "medium": ch_info["medium"],
                    "campaign": ch_info["campaign"],
                    "page_location": f"https://shop.example.com/landing?utm_source={ch_info['source']}&utm_medium={ch_info['medium']}&utm_campaign={ch_info['campaign']}",
                    "page_title": "Premium Developer & Creator Workspace Gear",
                    "country": cust["country"],
                    "region": cust["region"],
                    "city": cust["city"],
                    "device_category": dev_meta["category"],
                    "operating_system": dev_meta["os"],
                    "browser": dev_meta["browser"],
                    "transaction_id": None,
                    "event_value_usd": 0.0,
                    "email_hash": email_hash if (tp_time >= signup_dt or is_conversion_session) else None
                })

                # 2. page_view / view_item
                prod = random.choice(PRODUCTS)
                item_time = tp_time + timedelta(seconds=random.randint(15, 60))
                ga4_events.append({
                    "event_date": item_time.strftime("%Y%m%d"),
                    "event_timestamp": int(item_time.timestamp() * 1000000),
                    "event_name": "view_item",
                    "user_pseudo_id": pseudo_id,
                    "user_id": cust_id if (tp_time >= signup_dt or is_conversion_session) else None,
                    "ga_session_id": session_id,
                    "ga_session_number": tp_i + 1,
                    "source": ch_info["source"],
                    "medium": ch_info["medium"],
                    "campaign": ch_info["campaign"],
                    "page_location": f"https://shop.example.com/products/{prod['sku']}",
                    "page_title": prod["name"],
                    "country": cust["country"],
                    "region": cust["region"],
                    "city": cust["city"],
                    "device_category": dev_meta["category"],
                    "operating_system": dev_meta["os"],
                    "browser": dev_meta["browser"],
                    "transaction_id": None,
                    "event_value_usd": 0.0,
                    "email_hash": email_hash if (tp_time >= signup_dt or is_conversion_session) else None
                })

                # If this is the conversion session, trigger add_to_cart, begin_checkout, purchase
                if is_conversion_session:
                    cart_time = item_time + timedelta(seconds=random.randint(20, 90))
                    ga4_events.append({
                        "event_date": cart_time.strftime("%Y%m%d"),
                        "event_timestamp": int(cart_time.timestamp() * 1000000),
                        "event_name": "add_to_cart",
                        "user_pseudo_id": pseudo_id,
                        "user_id": cust_id,
                        "ga_session_id": session_id,
                        "ga_session_number": tp_i + 1,
                        "source": ch_info["source"],
                        "medium": ch_info["medium"],
                        "campaign": ch_info["campaign"],
                        "page_location": "https://shop.example.com/cart",
                        "page_title": "Shopping Cart",
                        "country": cust["country"],
                        "region": cust["region"],
                        "city": cust["city"],
                        "device_category": dev_meta["category"],
                        "operating_system": dev_meta["os"],
                        "browser": dev_meta["browser"],
                        "transaction_id": None,
                        "event_value_usd": prod["price"],
                        "email_hash": email_hash
                    })

                    purch_time = cart_time + timedelta(seconds=random.randint(45, 180))
                    
                    # Order value calculation
                    items_in_order = random.choices([1, 2, 3], weights=[0.65, 0.25, 0.10])[0]
                    chosen_prods = random.sample(PRODUCTS, items_in_order)
                    subtotal = sum(p["price"] for p in chosen_prods)
                    discount = round(subtotal * (0.10 if ch_info["source"] == "klaviyo" else 0.0), 2)
                    tax = round((subtotal - discount) * 0.08, 2)
                    shipping = 0.0 if (subtotal - discount) > 150 else 15.0
                    total_rev = round(subtotal - discount + tax + shipping, 2)

                    ga4_events.append({
                        "event_date": purch_time.strftime("%Y%m%d"),
                        "event_timestamp": int(purch_time.timestamp() * 1000000),
                        "event_name": "purchase",
                        "user_pseudo_id": pseudo_id,
                        "user_id": cust_id,
                        "ga_session_id": session_id,
                        "ga_session_number": tp_i + 1,
                        "source": ch_info["source"],
                        "medium": ch_info["medium"],
                        "campaign": ch_info["campaign"],
                        "page_location": "https://shop.example.com/checkout/success",
                        "page_title": "Order Confirmation",
                        "country": cust["country"],
                        "region": cust["region"],
                        "city": cust["city"],
                        "device_category": dev_meta["category"],
                        "operating_system": dev_meta["os"],
                        "browser": dev_meta["browser"],
                        "transaction_id": order_id,
                        "event_value_usd": total_rev,
                        "email_hash": email_hash
                    })

                    crm_orders.append({
                        "order_id": order_id,
                        "customer_id": cust_id,
                        "order_timestamp": purch_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "order_date": purch_time.strftime("%Y-%m-%d"),
                        "subtotal": subtotal,
                        "discount_amount": discount,
                        "tax_amount": tax,
                        "shipping_amount": shipping,
                        "total_revenue": total_rev,
                        "order_status": "completed",
                        "payment_method": random.choice(["credit_card", "apple_pay", "paypal", "klarna"]),
                        "conversion_session_id": session_id,
                        "last_touch_source": ch_info["source"],
                        "last_touch_medium": ch_info["medium"],
                        "last_touch_campaign": ch_info["campaign"]
                    })

    # Add pure anonymous bouncing visits
    for anon_i in range(pure_anonymous_count):
        anon_time = start_dt + timedelta(days=random.randint(0, total_days - 1), seconds=random.randint(0, 86400))
        anon_pseudo = f"{random.randint(100000000, 999999999)}.{int(anon_time.timestamp())}"
        ch_info = random.choice(CHANNELS)
        dev = random.choice(devices)
        loc = random.choice(CITIES_DATA)
        sess_id = f"sess_anon_{int(anon_time.timestamp())}_{anon_i}"

        ga4_events.append({
            "event_date": anon_time.strftime("%Y%m%d"),
            "event_timestamp": int(anon_time.timestamp() * 1000000),
            "event_name": "session_start",
            "user_pseudo_id": anon_pseudo,
            "user_id": None,
            "ga_session_id": sess_id,
            "ga_session_number": 1,
            "source": ch_info["source"],
            "medium": ch_info["medium"],
            "campaign": ch_info["campaign"],
            "page_location": "https://shop.example.com/",
            "page_title": "Home - Premium Tech Gear",
            "country": loc["country"],
            "region": loc["region"],
            "city": loc["city"],
            "device_category": dev["category"],
            "operating_system": dev["os"],
            "browser": dev["browser"],
            "transaction_id": None,
            "event_value_usd": 0.0,
            "email_hash": None
        })

    df_ga4_events = pd.DataFrame(ga4_events)
    df_crm_orders = pd.DataFrame(crm_orders)

    # Sort events by timestamp
    df_ga4_events = df_ga4_events.sort_values(by="event_timestamp").reset_index(drop=True)
    df_crm_orders = df_crm_orders.sort_values(by="order_timestamp").reset_index(drop=True)

    print(f"Generated:")
    print(f" - CRM Customers: {len(df_crm_customers):,}")
    print(f" - CRM Orders: {len(df_crm_orders):,} (Total Revenue: ${df_crm_orders['total_revenue'].sum():,.2f})")
    print(f" - GA4 Events: {len(df_ga4_events):,}")
    print(f" - Ad Spend Records: {len(df_ad_spend):,} (Total Ad Spend: ${df_ad_spend['daily_spend'].sum():,.2f})")

    return df_crm_customers, df_crm_orders, df_ga4_events, df_ad_spend


def save_datasets(output_dir="data/raw"):
    os.makedirs(output_dir, exist_ok=True)
    df_crm_cust, df_crm_ord, df_ga4, df_ad = generate_dataset()

    df_crm_cust.to_csv(os.path.join(output_dir, "raw_crm_customers.csv"), index=False)
    df_crm_ord.to_csv(os.path.join(output_dir, "raw_crm_orders.csv"), index=False)
    df_ga4.to_csv(os.path.join(output_dir, "raw_ga4_events.csv"), index=False)
    df_ad.to_csv(os.path.join(output_dir, "raw_ad_spend.csv"), index=False)
    
    print(f"All raw datasets successfully saved to {output_dir}")


if __name__ == "__main__":
    import sys
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = os.path.join(base_path, "data", "raw")
    save_datasets(out_dir)
