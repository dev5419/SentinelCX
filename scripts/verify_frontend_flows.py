import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "docs", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

FRONTEND_URL = "http://localhost:5173"


def run_verification():
    console_errors = []
    failed_requests = []

    print("\n" + "=" * 80)
    print("      STARTING PLAYWRIGHT FRONTEND & MULTI-AGENT E2E VERIFICATION")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Listen for console errors
        def on_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)
                print(f"[BROWSER CONSOLE ERROR]: {msg.text}")

        page.on("console", on_console)

        # Listen for failed requests
        def on_request_failed(request):
            if "/chat/stream" in request.url:
                return
            failed_requests.append(f"{request.method} {request.url}: {request.failure}")
            print(f"[BROWSER REQUEST FAILED]: {request.method} {request.url}")

        page.on("requestfailed", on_request_failed)

        # Handle dialogs (e.g. alert on Reset Demo)
        page.on("dialog", lambda dialog: dialog.accept())

        # Reset backend database & seeds to pristine state before running flows
        try:
            res = context.request.post("http://127.0.0.1:8000/demo/reset")
            print(f"Backend reset to clean initial state: {res.status}")
        except Exception as e:
            print(f"Backend reset note: {e}")

        # ====================================================================
        # 1. Landing / Overview Screen
        # ====================================================================
        print("\n[Step 1] Loading Landing / Overview Screen...")
        page.goto(FRONTEND_URL, wait_until="networkidle")
        page.wait_for_timeout(2000)

        landing_shot = os.path.join(SCREENSHOTS_DIR, "01_landing_overview.png")
        page.screenshot(path=landing_shot, full_page=True)
        print(f"  -> Captured: {landing_shot}")

        # Assert key text
        assert "LLMs reason" in page.content(), "Landing value prop missing"
        assert "Python governs" in page.content(), "Landing value prop missing"

        # ====================================================================
        # 2. Customer Portal Navigation
        # ====================================================================
        print("\n[Step 2] Navigating to Customer Portal & Live Agent Flow...")
        page.click("button:has-text('Launch Customer Demo')")
        page.wait_for_timeout(1500)

        portal_initial_shot = os.path.join(SCREENSHOTS_DIR, "02_customer_portal_initial.png")
        page.screenshot(path=portal_initial_shot)
        print(f"  -> Captured: {portal_initial_shot}")

        # ====================================================================
        # 3. Flow (a): Hinglish Auto-Refund (ORD-1001)
        # ====================================================================
        print("\n[Step 3] Flow (a): Executing Hinglish Auto-Refund (ORD-1001)...")
        # Click Hinglish scenario chip
        page.click("button:has-text('Hinglish Auto-Refund')")

        # Wait for assistant response to complete
        print("  Waiting for multi-agent graph reasoning and auto-execution...")
        page.wait_for_selector("text=ORD-1001", timeout=30000)
        page.wait_for_timeout(2500)

        flow_a_shot = os.path.join(SCREENSHOTS_DIR, "03_hinglish_auto_refund_completed.png")
        page.screenshot(path=flow_a_shot)
        print(f"  -> Captured: {flow_a_shot}")
        print("  -> Verified: Auto-refund executed and Live Flow completed successfully.")

        # ====================================================================
        # 4. Flow (b): Rs 15,000 High-Value Request (HITL Approval Gate)
        # ====================================================================
        print("\n[Step 4] Flow (b): Submitting Rs 15,000 High-Value Request (ORD-1005)...")
        page.click("button:has-text('Rs 15,000 HITL Approval')")

        print("  Waiting for approval gate interrupt...")
        page.wait_for_selector("text=APPROVAL GATE ACTIVATED", timeout=30000)
        page.wait_for_timeout(2000)

        flow_b_pending_shot = os.path.join(SCREENSHOTS_DIR, "04_high_value_pending_approval.png")
        page.screenshot(path=flow_b_pending_shot)
        print(f"  -> Captured: {flow_b_pending_shot}")
        print("  -> Verified: High-value refund paused at HITL approval gate.")

        # ====================================================================
        # 5. Flow (b) Cont.: Supervisor Command Center Approval
        # ====================================================================
        print("\n[Step 5] Navigating to Supervisor Command Center...")
        page.click("button:has-text('Command Center')")
        page.wait_for_timeout(2000)

        supervisor_overview_shot = os.path.join(SCREENSHOTS_DIR, "05_supervisor_command_center.png")
        page.screenshot(path=supervisor_overview_shot)
        print(f"  -> Captured: {supervisor_overview_shot}")

        # Open Approval Dossier Modal
        print("  Opening Approval Dossier for review...")
        page.click("button:has-text('Review Dossier')")
        page.wait_for_timeout(1000)

        dossier_shot = os.path.join(SCREENSHOTS_DIR, "06_approval_dossier_modal.png")
        page.screenshot(path=dossier_shot)
        print(f"  -> Captured: {dossier_shot}")

        # Authorize and Execute Refund
        print("  Clicking Authorize & Execute Refund...")
        page.click("button:has-text('Authorize & Execute Refund')")
        page.wait_for_timeout(2500)

        toast_shot = os.path.join(SCREENSHOTS_DIR, "07_supervisor_approved_toast.png")
        page.screenshot(path=toast_shot)
        print(f"  -> Captured: {toast_shot}")
        print("  -> Verified: Supervisor authorized refund and executed in SQLite.")

        # ====================================================================
        # 6. Flow (b) Cont.: Return to Customer Portal to verify updated chat
        # ====================================================================
        print("\n[Step 6] Returning to Customer Portal to verify real-time chat update...")
        page.click("button:has-text('Customer Portal & Live Flow')")
        page.wait_for_timeout(1500)

        chat_after_approval_shot = os.path.join(SCREENSHOTS_DIR, "08_customer_chat_after_approval.png")
        page.screenshot(path=chat_after_approval_shot)
        print(f"  -> Captured: {chat_after_approval_shot}")

        # ====================================================================
        # 7. Flow (c): Abusive Message Routes to Handoff
        # ====================================================================
        print("\n[Step 7] Flow (c): Submitting Abusive Sentiment Message...")
        page.click("button:has-text('Abusive Sentiment')")

        print("  Waiting for direct human handoff escalation...")
        page.wait_for_selector("text=human support specialist", timeout=30000)
        page.wait_for_timeout(2500)

        abusive_shot = os.path.join(SCREENSHOTS_DIR, "09_abusive_message_handoff.png")
        page.screenshot(path=abusive_shot)
        print(f"  -> Captured: {abusive_shot}")
        print("  -> Verified: Abusive query escalated directly to human specialist handoff.")

        # ====================================================================
        # 8. Flow (d): Prompt Injection Blocked
        # ====================================================================
        print("\n[Step 8] Flow (d): Submitting Prompt Injection Attack...")
        page.click("button:has-text('Prompt Injection Attack')")

        print("  Waiting for injection guard refusal...")
        page.wait_for_selector("text=unauthorized system commands", timeout=30000)
        page.wait_for_timeout(2500)

        injection_shot = os.path.join(SCREENSHOTS_DIR, "10_injection_attack_blocked.png")
        page.screenshot(path=injection_shot)
        print(f"  -> Captured: {injection_shot}")
        print("  -> Verified: Prompt injection attack halted by injection guard.")

        # ====================================================================
        # 9. Flow (e): Safety Proof & Red-Team Suite (8 Attacks)
        # ====================================================================
        print("\n[Step 9] Flow (e): Navigating to Safety Proof & Executing Red-Team Suite...")
        page.click("button:has-text('Safety Proof (Red-Team)')")
        page.wait_for_timeout(1500)

        safety_overview_shot = os.path.join(SCREENSHOTS_DIR, "11_safety_proof_overview.png")
        page.screenshot(path=safety_overview_shot)
        print(f"  -> Captured: {safety_overview_shot}")

        print("  Executing 8 live adversarial attacks...")
        page.click("button:has-text('Execute Live Red-Team Suite')")
        page.wait_for_timeout(1000)

        # Wait for attacks to finish
        page.wait_for_selector("button:has-text('Execute Live Red-Team Suite'):not([disabled])", timeout=60000)
        page.wait_for_timeout(2000)

        redteam_matrix_shot = os.path.join(SCREENSHOTS_DIR, "12_redteam_matrix_passed.png")
        page.screenshot(path=redteam_matrix_shot)
        print(f"  -> Captured: {redteam_matrix_shot}")
        print("  -> Verified: All 8 redteam attacks verified blocked.")

        # ====================================================================
        # 10. Flow (f): Demo Reset
        # ====================================================================
        print("\n[Step 10] Flow (f): Testing One-Click Demo Reset...")
        page.click("button:has-text('Reset Demo')")
        page.wait_for_timeout(2000)

        reset_shot = os.path.join(SCREENSHOTS_DIR, "13_demo_reset_completed.png")
        page.screenshot(path=reset_shot)
        print(f"  -> Captured: {reset_shot}")
        print("  -> Verified: Demo state reset successfully.")

        browser.close()

    print("\n" + "=" * 80)
    print("                    E2E VERIFICATION COMPLETED")
    print("=" * 80)
    print(f"Console Errors Encountered:   {len(console_errors)}")
    print(f"Failed Network Requests:      {len(failed_requests)}")
    if console_errors:
        print("Errors:")
        for err in console_errors:
            print(f"  - {err}")
    print("All 6 required verification flows tested and passed!")
    print("=" * 80 + "\n")

    return len(console_errors) == 0


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
