---
title: Altitude Learned Support Knowledge
topic: learned_support
audience: public
document_type: support_procedure_collection
workflow: resolved_ticket_learning
version: 1.1
---

# Altitude Learned Support Knowledge

This file contains reusable troubleshooting procedures approved from resolved IT tickets.

## Learned Knowledge Rules

- Use a learned procedure only when the user's main device or service and the reported symptom both match the approved topic.
- Do not select a learned procedure only because one generic word matches, such as "laptop", "dock", "printer", "connect", or "restart".
- Follow the approved steps in order and write instructions directly to the user using second-person or imperative wording.
- Do not describe technician actions in first person.
- Do not expose ticket numbers, requester details, email addresses, credentials, or private technician notes.
- If the approved procedure does not match the current issue, ignore it and use the appropriate standard knowledge source instead.

---

## Topic: External Monitors Not Detected Through a USB-C Dock

**Intent Keywords:** external monitors not detected, second monitor not detected, dual monitors missing, usb-c dock display problem, docking station monitor no signal, dock monitors worked yesterday

**Target Audience:** Staff, Faculty, Students

**Platform:** Cross-platform

**Bot Instruction:** Use this procedure only when one or more external monitors are not detected through a USB-C docking station. Do not use it for laptop charging, keyboard, mouse, Ethernet, Wi-Fi, USB peripherals, or unrelated docking-station problems.

**Use this procedure when:**
The laptop connects to a USB-C docking station, but one or more external monitors are not detected or stop displaying.

**Direct Answer:**
Power-cycle the USB-C docking station, restore power to the dock first, allow it to initialize, and then reconnect the laptop before testing the external displays again.

**Troubleshooting Steps:**
1. Disconnect the USB-C cable from the laptop.
2. Unplug power from the docking station.
3. Wait approximately 30 seconds.
4. Reconnect power to the docking station first.
5. Wait for the docking station to fully initialize.
6. Reconnect the USB-C cable to the laptop.
7. Restart the laptop if the monitors are still not detected.
8. Confirm that all expected external monitors appear in the display settings.

**Escalation:**
If the monitors are still not detected after these approved steps, contact the IT Helpdesk.

---

## Topic: Windows Print Queue Stuck or Spooling Indefinitely

**Intent Keywords:** print job stuck, printer queue stuck, spooling forever, document stuck spooling, cannot cancel print job, print queue will not clear, printer online but nothing prints

**Target Audience:** Staff, Faculty, Students

**Platform:** Windows

**Bot Instruction:** Use this procedure only for a Windows print queue that is stuck, spooling indefinitely, or preventing jobs from printing. Do not use it for browser problems, computer boot loops, paper jams, PDF corruption, or unrelated printer hardware issues.

**Use this procedure when:**
The printer is already installed and appears available, but print jobs remain stuck in the Windows print queue or stay in a Spooling state.

**Direct Answer:**
Clear the stuck print jobs, restart the Windows Print Spooler, and re-add the approved school printer only if the queue remains unusable.

**Troubleshooting Steps:**
1. Open the printer queue and try to cancel the stuck print jobs.
2. Restart the Windows Print Spooler using the approved support method.
3. Open the printer queue again and confirm that the stuck jobs are gone.
4. If the queue is still unusable, remove the affected printer.
5. Add the printer again using the correct approved school print queue.
6. Print a test page or a simple document to confirm that printing works.

**Escalation:**
If the print queue cannot be cleared, the Print Spooler cannot be restarted without administrator access, or printing still fails after the approved steps, contact the IT Helpdesk.

## Topic: Altitude: help me create IT ticket
**Intent Keywords:** altitude: help me create it ticket, altitude, help, create, ticket, other, provided
**Target Audience:** Staff, Faculty, Students

**Bot Instruction:** Use this procedure only when the user's symptoms match this resolved issue. Do not invent missing steps, credentials, permissions, or administrator actions.

**Use this procedure when:**
Altitude: help me create IT ticket

**Direct Answer:**
Create ticket

**Troubleshooting Steps:**
1. No comments have been added to this ticket yet.

**Escalation:**
If these approved steps do not resolve the issue, contact the IT Helpdesk.
