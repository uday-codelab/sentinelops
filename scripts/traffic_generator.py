import time
import random
import requests

USER_SERVICE_URL = "http://localhost:8001"
ORDER_SERVICE_URL = "http://localhost:8002"
PAYMENT_SERVICE_URL = "http://localhost:8003"

def simulate_traffic():
    print("🚀 Starting traffic generator for SentinelOps microservices...")
    print("Press Ctrl+C to stop.\n")
    
    req_count = 0
    while True:
        try:
            # 1. User service request
            user_id = random.randint(1, 100)
            u_res = requests.get(f"{USER_SERVICE_URL}/users/{user_id}", timeout=5)
            
            # 2. Order service request
            order_payload = {
                "user_id": user_id,
                "item_id": random.randint(101, 150),
                "quantity": random.randint(1, 4),
                "total_amount": round(random.uniform(20.0, 500.0), 2)
            }
            o_res = requests.post(f"{ORDER_SERVICE_URL}/orders", json=order_payload, timeout=5)
            
            order_id = random.randint(1000, 9999)
            if o_res.status_code == 201:
                order_id = o_res.json().get("order_id", order_id)
            
            # 3. Payment service request
            pay_payload = {
                "order_id": order_id,
                "user_id": user_id,
                "amount": order_payload["total_amount"],
                "payment_method": random.choice(["credit_card", "upi", "debit_card"])
            }
            p_res = requests.post(f"{PAYMENT_SERVICE_URL}/payments/process", json=pay_payload, timeout=5)
            
            req_count += 1
            if req_count % 5 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] Sent batch #{req_count} | "
                      f"User: {u_res.status_code} | Order: {o_res.status_code} | Payment: {p_res.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Connection error (is a service down/starting?): {e}")

        # Sleep between 0.5s and 1.5s to mimic realistic user browsing
        time.sleep(random.uniform(0.5, 1.5))

if __name__ == "__main__":
    simulate_traffic()
