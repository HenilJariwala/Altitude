#!/usr/bin/env python3
"""Automated Altitude chatbot question runner.

Runs a fixed question set through the same assistant path used by the app:
    prepare_answer(question, history)
    stream_answer(question, history, plan)

Each question uses a fresh conversation. Results are written to TXT and JSON.
This script does not intentionally create tickets or submit feedback.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
REPORT_DIR = PROJECT_ROOT / "test_reports"

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

from core.assistant import prepare_answer, stream_answer

QUESTIONS = [
    (1, "Chromebook / charging / power", "My Chromebook won't charge even when the power adapter is securely plugged in."),
    (2, "OneDrive / deleted file recovery", "I accidentally deleted an important assignment from OneDrive and need help restoring it."),
    (3, "Software installation / administrator permissions", "Whenever I try to install a required program for my class, it asks for an administrator password."),
    (4, "Email / external mail delivery", "I am not receiving any external emails from outside the school domain in my inbox."),
    (5, "MFA / two-factor authentication", "The two-factor authentication app on my phone is not sending me the approval notification to log in."),
    (6, "Laptop keyboard / hardware", "Several keys on my laptop keyboard have stopped responding completely."),
    (7, "Operating system updates / restart control", "My computer keeps trying to force a system restart for updates right in the middle of a lesson."),
    (8, "Google Drive / shared folder", "I cannot find the shared department folder that used to be pinned to my Google Drive."),
    (9, "Projector / image quality", "The classroom projector image has a strange purple tint and the text looks fuzzy."),
    (10, "Guest Wi-Fi / visitor access", "How do I generate a guest Wi-Fi access code for a visiting presenter?"),
    (11, "Disk space / storage", "My computer is giving me a 'Disk Space Full' warning and won't let me save my project."),
    (12, "Browser / unwanted pop-ups / possible malware", "Every time I open my web browser, it opens several random pop-up tabs that I can't close."),
    (13, "Audio / built-in microphone", "My headphones are playing sound perfectly, but the built-in microphone isn't picking up my voice."),
    (14, "Laptop battery / battery health", "The battery on my school-issued laptop drains from fully charged to zero in less than an hour."),
    (15, "PDF / file opening", "I cannot open a PDF file my teacher sent me; it says the file format is unsupported or corrupted."),
    (16, "Touchscreen / stylus", "The interactive stylus pen for my touchscreen device is no longer drawing on the screen."),
    (17, "Boot failure / reboot loop", "My laptop is stuck in a continuous reboot loop and never makes it to the login screen."),
    (18, "School email calendar / mobile device", "How do I sync my school email calendar to the default calendar app on my personal phone?"),
    (19, "Copier / scan to email", "The scanner on the main office copier is no longer sending documents to my email address."),
    (20, "Excel / shared file locked", "When I try to open an Excel file from a shared link, it says the file is locked for editing by another user."),
    (21, "Network / certificate / privacy warning", "My laptop connects to the Wi-Fi just fine, but it keeps giving me a privacy warning about an invalid security certificate on almost every website I visit."),
    (22, "Projector / extended display / no signal", "The classroom projector works perfectly when I duplicate my screen, but if I switch to 'Extend', the projector just flashes and says 'No Signal'."),
    (23, "Google Docs / collaboration / editing", "I shared a Google Doc with a student, but when they try to type in it, their edits disappear immediately and the page constantly refreshes."),
    (24, "USB-C dock / external monitors", "My docking station charges my laptop and connects to the ethernet, but neither of my two external monitors are being detected today, even though they worked yesterday."),
    (25, "Zoom / screen sharing / application freeze", "Whenever I try to share a specific window on a Zoom call, the entire application freezes and I have to force quit it using Task Manager."),
    (26, "Printer / PDF / Adobe Acrobat", "I can print from Google Docs without any issues, but whenever I try to print a PDF from Adobe Acrobat, the printer just spits out pages with weird symbols on them."),
    (27, "Chromebook / Wi-Fi network selection", "My Chromebook keeps automatically connecting to the guest network instead of the staff network, and the system won't let me click 'forget' on the guest network."),
    (28, "Classroom audio / audio-video sync", "I'm trying to play a video for the class; the video plays smoothly on my laptop screen, but the audio coming out of the classroom speakers is about three seconds out of sync."),
    (29, "Microsoft Word / Microsoft 365 account", "Every time I open Microsoft Word, it says 'Account Error: There are problems with your account', but I can log into my school email online without any issues."),
    (30, "Windows performance / CPU / System Interrupts", "My computer's fan is running at maximum speed constantly, and when I look at the task manager, it says 'System Interrupts' is using 100% of my CPU."),
    (31, "Google Drive / shared files", "I moved a bunch of files into a shared Google Drive folder, but now none of my colleagues can see them, and they've completely disappeared from my own 'My Drive' as well."),
    (32, "Smartboard / touch calibration", "The smartboard touches register correctly on the left side of the screen, but when I draw on the right side, the digital ink appears three inches away from where the pen actually is."),
    (33, "Account lockout / cached network credentials", "I just changed my network password on my phone this morning, and now my laptop keeps randomly locking my account out because of 'too many failed login attempts'."),
    (34, "Laptop display / battery or power state", "Whenever I unplug my laptop from the charger, the screen flickers violently and then goes completely dim until I plug it back into the wall."),
    (35, "Educational software / local database", "I'm trying to run a specific educational software we use for math, but it keeps giving me an error saying 'Cannot connect to local database server' even though my internet works."),
    (36, "Outlook / email synchronization", "My Outlook inbox is suddenly showing hundreds of emails from three years ago as unread, and none of my new emails from today are downloading."),
    (37, "Printer / stuck spool queue", "The printer queue says my document is 'Spooling' but it's been stuck like that for twenty minutes, and it gives me an error when I try to right-click and cancel it."),
    (38, "USB microphone / device in use", "When I plug in my USB microphone, the computer recognizes it, but all my recording apps say the device is currently in use by another application."),
    (39, "VPN / internal network drives", "My computer connects to the school VPN successfully, but I still can't access any of the internal network drives I usually use from home."),
    (40, "Mouse / touchpad / pointer movement", "The mouse cursor keeps jumping to the top right corner of my screen completely on its own, even when I disconnect my external mouse and turn off Bluetooth."),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Altitude support questions automatically and save a report.")
    p.add_argument("--start", type=int, default=1, help="1-based question number to start from.")
    p.add_argument("--count", type=int, default=None, help="Number of questions to run.")
    p.add_argument("--delay", type=float, default=0.15, help="Delay between questions in seconds.")
    return p.parse_args()


def plan_dict(plan: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if plan is None:
        return data
    if is_dataclass(plan):
        try:
            data.update(asdict(plan))
        except Exception:
            pass
    for name in ("direct_answer", "context", "effective_question", "resource", "caption", "sources", "best_distance", "matched_chunks", "intent"):
        if name not in data:
            data[name] = getattr(plan, name, None)
    return data


def mode_for(plan: dict[str, Any]) -> str:
    if plan.get("direct_answer"):
        return "DIRECT"
    if plan.get("matched_chunks") or plan.get("sources"):
        return "RAG"
    if plan.get("context"):
        return "CONTEXT/FALLBACK"
    return "UNKNOWN"


def answer_text(question: str, plan: Any) -> str:
    chunks: list[str] = []
    for chunk in stream_answer(question, [], plan):
        if chunk is None:
            continue
        chunks.append(chunk if isinstance(chunk, str) else str(chunk))
    return "".join(chunks).strip()


def source_text(value: Any) -> str:
    if not value:
        return "(none)"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(map(str, value))
    return str(value)


def save_report(results: list[dict[str, Any]], started: datetime, txt: Path, js: Path) -> None:
    js.write_text(json.dumps({
        "started_at": started.isoformat(),
        "updated_at": datetime.now().isoformat(),
        "questions_run": len(results),
        "results": results,
    }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    lines = [
        "=" * 88,
        "ALTITUDE AUTOMATED QUESTION REPORT",
        "=" * 88,
        f"Started: {started.isoformat()}",
        f"Questions run: {len(results)}",
        "",
    ]
    for r in results:
        lines.extend([
            "=" * 88,
            f"QUESTION {r['id']}",
            "=" * 88,
            f"Expected topic: {r['expected_topic']}",
            f"Question: {r['question']}",
            "",
            "Diagnostics:",
            f"  Mode: {r['mode']}",
            f"  Intent: {r.get('intent') or '(none)'}",
            f"  Effective question: {r.get('effective_question') or '(none)'}",
            f"  Resource: {r.get('resource') or '(none)'}",
            f"  Sources: {source_text(r.get('sources'))}",
            f"  Matched chunks: {r.get('matched_chunks', 0)}",
            f"  Best distance: {r.get('best_distance')}",
            f"  Response time: {r.get('elapsed_seconds', 0):.3f}s",
            "",
            "Altitude answer:",
            r.get("answer", ""),
            "",
        ])
        if r.get("error"):
            lines.extend([f"ERROR: {r['error']}", ""])
    txt.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.start < 1 or args.start > len(QUESTIONS):
        raise SystemExit(f"--start must be between 1 and {len(QUESTIONS)}")
    selected = QUESTIONS[args.start - 1:]
    if args.count is not None:
        if args.count < 1:
            raise SystemExit("--count must be at least 1")
        selected = selected[:args.count]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now()
    stamp = started.strftime("%Y%m%d-%H%M%S")
    txt = REPORT_DIR / f"altitude-auto-questions-{stamp}.txt"
    js = REPORT_DIR / f"altitude-auto-questions-{stamp}.json"
    results: list[dict[str, Any]] = []

    print("=" * 88)
    print("ALTITUDE AUTOMATED QUESTION TEST")
    print("=" * 88)
    print(f"Questions selected: {len(selected)}")
    print("Fresh conversation history is used for every question.")
    print("No IT ticket is intentionally submitted.")

    for i, (qid, topic, question) in enumerate(selected, start=1):
        print(f"\n[{i}/{len(selected)}] Q{qid}: {question}")
        start = time.perf_counter()
        result = {
            "id": qid,
            "expected_topic": topic,
            "question": question,
            "mode": "ERROR",
            "intent": None,
            "effective_question": None,
            "resource": None,
            "sources": [],
            "matched_chunks": 0,
            "best_distance": None,
            "answer": "",
            "elapsed_seconds": 0.0,
            "error": "",
        }
        try:
            plan = prepare_answer(question, [])
            pd = plan_dict(plan)
            result.update({
                "mode": mode_for(pd),
                "intent": pd.get("intent"),
                "effective_question": pd.get("effective_question"),
                "resource": pd.get("resource"),
                "sources": pd.get("sources"),
                "matched_chunks": pd.get("matched_chunks") or 0,
                "best_distance": pd.get("best_distance"),
                "answer": answer_text(question, plan),
            })
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        result["elapsed_seconds"] = time.perf_counter() - start
        results.append(result)
        save_report(results, started, txt, js)
        print(f"  Mode: {result['mode']} | Source: {source_text(result.get('sources'))} | {result['elapsed_seconds']:.2f}s")
        if result["error"]:
            print(f"  ERROR: {result['error']}")
        if args.delay > 0:
            time.sleep(args.delay)

    print("\n" + "=" * 88)
    print("DONE")
    print("=" * 88)
    print(f"Text report: {txt}")
    print(f"JSON report: {js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
