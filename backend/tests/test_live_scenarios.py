import asyncio
import pytest
import httpx
import websockets
import json
import socket

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

def _is_live_server_active():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.3)
        s.connect(("127.0.0.1", 8000))
        s.close()
        return True
    except Exception:
        return False

pytestmark = pytest.mark.skipif(
    not _is_live_server_active(),
    reason="Requires active VECTOR backend server running at http://127.0.0.1:8000"
)

@pytest.mark.asyncio
async def test_scenario_autonomous():
    print("\n--- Test 1: Autonomous Local Media (Approval Unchecked) ---")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        res = await client.post("/api/missions", json={
            "task": "open d drive and play video in movies",
            "require_approval_for_high_risk": False,
            "demo_mode": False
        })
        assert res.status_code == 200, res.text
        m_id = res.json()["mission_id"]
        print(f"Created mission: {m_id}")

        # Connect WebSocket to verify replay and real-time events without crashing
        ws_uri = f"{WS_URL}/ws/missions/{m_id}"
        events_received = []
        async with websockets.connect(ws_uri) as ws:
            for _ in range(30):
                m_info = (await client.get(f"/api/missions/{m_id}")).json()
                status = m_info.get("status")
                print(f"Status: {status}, Steps: {len(m_info.get('steps', []))}")
                try:
                    ev_raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    ev = json.loads(ev_raw)
                    events_received.append(ev.get("event_type"))
                except asyncio.TimeoutError:
                    pass

                if status in ["completed", "failed"]:
                    break
                await asyncio.sleep(1.0)

        print(f"Final Status: {status}")
        print(f"Events received via WS: {set(events_received)}")
        assert status == "completed", f"Expected completed, got {status}"
        print("Test 1 PASSED!")

@pytest.mark.asyncio
async def test_scenario_with_approval():
    print("\n--- Test 2: Local Storage with Operator Authorization (Approval Checked) ---")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        res = await client.post("/api/missions", json={
            "task": "open d drive and play video in movies",
            "require_approval_for_high_risk": True,
            "demo_mode": False
        })
        assert res.status_code == 200, res.text
        m_id = res.json()["mission_id"]
        print(f"Created mission: {m_id}")

        # Connect WebSocket
        ws_uri = f"{WS_URL}/ws/missions/{m_id}"
        approved = False
        async with websockets.connect(ws_uri) as ws:
            for i in range(35):
                m_info = (await client.get(f"/api/missions/{m_id}")).json()
                status = m_info.get("status")
                print(f"Status: {status}, Steps: {len(m_info.get('steps', []))}")

                if status == "awaiting_approval" and not approved:
                    print("Mission correctly paused on awaiting_approval! Granting approval via API...")
                    approve_res = await client.post(f"/api/missions/{m_id}/approve")
                    assert approve_res.status_code == 200
                    approved = True

                if status in ["completed", "failed"]:
                    break
                await asyncio.sleep(1.0)

        print(f"Final Status: {status}")
        assert approved, "Expected mission to request approval"
        assert status == "completed", f"Expected completed, got {status}"
        print("Test 2 PASSED!")

@pytest.mark.asyncio
async def test_apps_launch():
    print("\n--- Test 3: Launch Local App (WhatsApp / Epic Games) ---")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        res = await client.post("/api/missions", json={
            "task": "open epic games home",
            "require_approval_for_high_risk": False,
            "demo_mode": False
        })
        m_id = res.json()["mission_id"]
        for _ in range(35):
            m_info = (await client.get(f"/api/missions/{m_id}")).json()
            if m_info["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(1.0)
        print(f"Epic Games mission status: {m_info['status']}")
        assert m_info["status"] == "completed"
        print("Test 3 PASSED!")

@pytest.mark.asyncio
async def test_ram_cleanup():
    print("\n--- Test 4: Clear RAM & Optimize PC ---")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        res = await client.post("/api/missions", json={
            "task": "my pc is slow then clear extra ram stop unnecessary processes",
            "require_approval_for_high_risk": False,
            "demo_mode": False
        })
        m_id = res.json()["mission_id"]
        for _ in range(20):
            m_info = (await client.get(f"/api/missions/{m_id}")).json()
            if m_info["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(1.0)
        print(f"RAM Cleanup status: {m_info['status']}")
        assert m_info["status"] == "completed"
        print("Test 4 PASSED!")

async def main():
    await test_scenario_autonomous()
    await test_scenario_with_approval()
    await test_apps_launch()
    await test_ram_cleanup()
    print("\n================ ALL LIVE TESTS PASSED! ================\n")

if __name__ == "__main__":
    asyncio.run(main())
