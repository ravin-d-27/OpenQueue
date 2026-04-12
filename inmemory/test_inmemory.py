"""
In-Memory OpenQueue Test Example
"""

import asyncio
import httpx


async def main():
    base_url = "http://localhost:8001"

    async with httpx.AsyncClient(base_url=base_url) as client:
        print("=== Enqueue Jobs ===")

        res = await client.post(
            "/jobs",
            json={
                "queue_name": "emails",
                "payload": {"to": "user1@example.com", "subject": "Hello"},
                "priority": 5,
            },
        )
        print(f"Enqueue: {res.json()}")

        res = await client.post(
            "/jobs",
            json={
                "queue_name": "emails",
                "payload": {"to": "user2@example.com", "subject": "World"},
                "priority": 3,
            },
        )
        print(f"Enqueue: {res.json()}")

        await asyncio.sleep(0.1)

        print("\n=== List Jobs ===")
        res = await client.get("/jobs?queue_name=emails&status=pending")
        print(f"List: {res.json()}")

        print("\n=== Lease Job (Worker 1) ===")
        res = await client.post(
            "/queues/emails/lease",
            json={"worker_id": "worker-1", "lease_seconds": 30},
        )
        print(f"Lease: {res.json()}")

        print("\n=== Ack Job ===")
        if res.status_code == 200 and res.json().get("job"):
            job_data = res.json()
            job_id = job_data["job"]["id"]
            lease_token = job_data["lease_token"]

            res = await client.post(
                f"/jobs/{job_id}/ack",
                json={"lease_token": lease_token, "result": {"sent": True}},
            )
            print(f"Ack: {res.json()}")

        print("\n=== Lease Another Job ===")
        res = await client.post(
            "/queues/emails/lease",
            json={"worker_id": "worker-2", "lease_seconds": 30},
        )
        print(f"Lease: {res.json()}")

        if res.status_code == 200 and res.json().get("job"):
            job_data = res.json()
            job_id = job_data["job"]["id"]
            lease_token = job_data["lease_token"]

            print(f"\n=== Heartbeat ===")
            res = await client.post(
                f"/jobs/{job_id}/heartbeat",
                json={"lease_token": lease_token, "lease_seconds": 60},
            )
            print(f"Heartbeat: {res.json()}")

            print(f"\n=== Nack Job (with retry) ===")
            res = await client.post(
                f"/jobs/{job_id}/nack",
                json={"lease_token": lease_token, "error": "SMTP failed", "retry": True},
            )
            print(f"Nack: {res.json()}")

        print("\n=== Queue Stats ===")
        res = await client.get("/dashboard/queues")
        print(f"Stats: {res.json()}")

        print("\n=== Health Check ===")
        res = await client.get("/health")
        print(f"Health: {res.json()}")


if __name__ == "__main__":
    asyncio.run(main())