---

title: Windows Basic Troubleshooting
topic: windows_support
platform: windows
audience: public
document_type: support_procedure
workflow: windows_basic_troubleshooting
version: 1.0
---

# Windows Basic Troubleshooting

This document contains approved Tier-1 troubleshooting procedures for common Windows laptop and desktop issues.

## Assistant Behaviour Rules

* Use this document only when the user confirms they are using Windows.

* If the operating system is unknown, ask:

  > Are you using a Windows device or a Mac?

* Stop and wait for the user's answer before giving operating-system-specific instructions.

* Do not provide both Windows and Mac instructions in the same response.

* Give only the steps for the topic that matches the current question.

* Do not combine unrelated troubleshooting procedures.

* Start with simple, low-risk steps.

* Do not ask users to edit the registry, BIOS, Group Policy, protected system folders, or advanced network settings.

* Do not ask users to run administrator commands unless the procedure explicitly allows it.

* Do not recommend resetting or reinstalling Windows.

* Do not tell users to disable security software.

* Do not claim that hardware is faulty without confirmation from IT.

* If the approved steps do not resolve the issue, direct the user to the IT Helpdesk.

* Do not claim that a ticket was created unless the ticketing system confirms it.

---

## Topic: Windows Has No Sound or Uses the Wrong Speaker

**Intent Keywords:** no sound, audio not working, wrong speaker, sound from laptop, HDMI audio, projector sound, monitor sound, speakers not working

**Target Audience:** Staff, Faculty, Students

**Direct Answer:**

Windows may be sending sound to the wrong output device.

**Troubleshooting Steps:**

1. Select the **speaker icon** in the Windows taskbar.
2. Select the audio-output button or arrow beside the volume control.
3. Choose the correct device, such as:

   * Laptop speakers
   * Headphones
   * HDMI monitor
   * Projector
   * Television
4. Confirm that the volume is not muted.
5. Open **Settings → System → Sound**.
6. Under **Output**, confirm that the correct device is selected.
7. Play audio again to test it.

**Escalation:**

If the correct device is selected but there is still no sound, restart the computer. If the problem continues, contact the IT Helpdesk.

---

## Topic: Windows Microphone Not Working

**Intent Keywords:** microphone not working, mic not working, Teams microphone, Zoom microphone, cannot be heard, microphone permission

**Target Audience:** Staff, Faculty, Students

**Direct Answer:**

The application may be using the wrong microphone or may not have permission to access it.

**Troubleshooting Steps:**

1. Open **Settings → Privacy & security → Microphone**.
2. Confirm that **Microphone access** is turned on.
3. Confirm that **Let apps access your microphone** is turned on.
4. Open the affected application, such as Teams or Zoom.
5. Open the application's audio or device settings.
6. Select the correct microphone.
7. Use the application's microphone test, if available.
8. Confirm that the microphone is not muted on the headset, keyboard, or laptop.

**Escalation:**

Restart the application and computer. If the microphone still does not work, contact the IT Helpdesk.

---

## Topic: Windows Blue Screen Error

**Intent Keywords:** blue screen, BSOD, stop code, computer crashed, Windows blue screen, PAGE_FAULT, critical process died

**Target Audience:** Staff, Faculty, Students

**Bot Instruction:**

Do not provide driver rollback, Event Viewer, Safe Mode, BIOS, recovery-console, or administrator-command instructions. Ask the user to record the stop code and contact IT.

**Direct Answer:**

A Windows blue screen may indicate a driver, update, hardware, or system problem.

**Approved Steps:**

1. Take a photo of the blue-screen message.
2. Record the displayed **stop code**, if one appears.
3. Allow the computer to restart.
4. Save any work after Windows starts.
5. Contact the IT Helpdesk and provide:

   * The stop code
   * A photo of the screen
   * What the user was doing when the issue occurred
   * Whether it has happened more than once

**Escalation:**

If the computer repeatedly shows a blue screen or cannot start normally, stop troubleshooting and contact the IT Helpdesk immediately.

---

## Topic: Windows Will Not Start or Is Stuck in a Boot Loop

**Intent Keywords:** Windows will not start, boot loop, stuck starting, automatic repair, black screen at startup, fails to boot, startup problem

**Target Audience:** Staff, Faculty, Students

**Bot Instruction:**

Do not instruct the user to interrupt startup repeatedly, reset Windows, reinstall Windows, change BIOS settings, or use advanced recovery tools.

**Troubleshooting Steps:**

1. Disconnect external devices such as:

   * USB drives
   * External hard drives
   * Docks
   * Adapters
2. Connect the laptop to power.
3. Hold the power button until the device turns off.
4. Wait 15 seconds.
5. Turn the computer on normally.
6. Record any error message displayed.

**Escalation:**

If Windows still does not start, contact the IT Helpdesk. Do not continue restarting the computer repeatedly.

---

## Topic: Windows Connected to Wi-Fi but Has No Internet

**Intent Keywords:** no internet secured, connected no internet, Windows Wi-Fi not working, cannot connect to Wi-Fi, network not working

**Target Audience:** Staff, Faculty, Students

**Bot Instruction:**

Use the approved Student or Guest Wi-Fi workflow when the issue concerns school Wi-Fi. Do not reveal Wi-Fi passwords.

**Troubleshooting Steps:**

1. Confirm that Airplane Mode is turned off.
2. Turn Wi-Fi off and then back on.
3. Select the school Wi-Fi network.
4. Choose **Forget**.
5. Restart the computer.
6. Confirm that the date, time, and time zone are correct.
7. Reconnect using the approved Student or Guest Wi-Fi QR code.
8. Try opening another website.

**Prohibited Actions:**

Do not instruct the user to:

* Change DNS settings
* Change proxy settings
* Run network-reset commands
* Modify certificates
* Reset the entire network configuration

**Escalation:**

If the approved steps do not work, contact the IT Helpdesk.

---

## Topic: Windows External Monitor Is Not Detected

**Intent Keywords:** second monitor not detected, external monitor not working, display not detected, second screen black, dual monitors, extend display

**Target Audience:** Staff, Faculty

**Troubleshooting Steps:**

1. Confirm that the monitor is turned on.
2. Check for a power light on the monitor.
3. Disconnect the HDMI, DisplayPort, or USB-C cable from both ends.
4. Reconnect the cable securely.
5. Press **Windows key + P**.
6. Select **Extend**.
7. Open **Settings → System → Display**.
8. Select **Multiple displays**.
9. Select **Detect**, if that option is available.

**Escalation:**

If the monitor is still not detected, try another approved cable or port if available. Contact the IT Helpdesk if the issue continues.

---

## Topic: Windows External Monitor Is Blurry or Has the Wrong Resolution

**Intent Keywords:** blurry monitor, wrong resolution, screen stretched, display too large, text too small, external display blurry

**Target Audience:** Staff, Faculty

**Troubleshooting Steps:**

1. Open **Settings → System → Display**.
2. Select the affected monitor.
3. Find **Display resolution**.
4. Select the option marked **Recommended**.
5. Find **Scale**.
6. Select the recommended scaling value.
7. Sign out and back in only if Windows asks you to do so.

**Escalation:**

If the image remains blurry, contact the IT Helpdesk and provide the monitor model and cable type.

---

## Topic: Windows Keyboard Is Not Responding

**Intent Keywords:** keyboard not working, keyboard not typing, keys not responding, laptop keyboard broken, USB keyboard not working

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Restart the computer.
2. For a USB keyboard:

   * Disconnect it.
   * Wait five seconds.
   * Reconnect it.
   * Try another USB port if available.
3. Press **Windows key + Ctrl + O** to open the On-Screen Keyboard.
4. Test whether the On-Screen Keyboard works.
5. Check whether only one application is affected.

**Escalation:**

If the physical keyboard remains unresponsive, contact the IT Helpdesk. Do not remove keyboard drivers unless instructed by IT.

---

## Topic: Windows Keyboard Types the Wrong Characters

**Intent Keywords:** wrong keyboard layout, wrong characters, numbers instead of letters, keyboard language, Num Lock, keys acting strange

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Press **Windows key + Space**.
2. Select the correct keyboard language.
3. If a compact keyboard types numbers instead of letters, press:

   * **Num Lock**, or
   * **Fn + Num Lock**
4. Open **Settings → Time & language → Language & region**.
5. Confirm that the correct language and keyboard are installed.

**Escalation:**

If keys continue producing incorrect characters, contact the IT Helpdesk.

---

## Topic: Windows Mouse or Bluetooth Mouse Disconnects

**Intent Keywords:** mouse not working, Bluetooth mouse disconnecting, wireless mouse not connecting, cursor not moving

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Confirm that the mouse is turned on.
2. Replace or recharge the battery.
3. For a USB mouse:

   * Disconnect it.
   * Reconnect it.
   * Try another USB port.
4. For Bluetooth:

   * Open **Settings → Bluetooth & devices**.
   * Turn Bluetooth off and then back on.
   * Select the mouse.
   * Remove and reconnect it if necessary.
5. Restart the computer.

**Escalation:**

If the mouse continues disconnecting, contact the IT Helpdesk.

---

## Topic: Windows Computer Is Running Slowly

**Intent Keywords:** Windows slow, PC slow, laptop slow, computer lagging, high CPU, high memory, freezing, Windows performance

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Save all work.
2. Close applications that are no longer needed.
3. Close unnecessary browser tabs.
4. Restart the computer using **Start → Power → Restart**.
5. After restarting, open **Task Manager** with **Ctrl + Shift + Esc**.
6. Look for an application using unusually high:

   * CPU
   * Memory
   * Disk
7. Close only applications the user recognizes and no longer needs.
8. Open **Settings → Windows Update**.
9. Install approved pending updates.
10. Restart if required.

**Prohibited Actions:**

Do not instruct the user to:

* Disable antivirus
* Disable Windows services
* Change virtual-memory settings
* Delete Windows system folders
* Modify startup services without IT approval

**Escalation:**

If the computer remains slow after a restart and updates, contact the IT Helpdesk.

---

## Topic: Windows Application Is Frozen

**Intent Keywords:** app frozen, application not responding, program will not close, software frozen, app stuck, force quit Windows, force close app, End task, Task Manager

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Wait approximately 30 seconds in case the application is processing.
2. Try closing the application normally.
3. Press **Ctrl + Shift + Esc** to open Task Manager.
4. Select the frozen application.
5. Select **End task**.
6. Reopen the application.
7. Restart Windows if the application continues freezing.

**Important:**

Unsaved work in the frozen application may be lost when using **End task**.

**Escalation:**

If the same application freezes repeatedly, contact the IT Helpdesk with the application name and any displayed error message.

---

## Topic: Windows Update Is Not Completing

**Intent Keywords:** Windows Update stuck, update failed, pending update, Windows update error, update will not install

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Connect the computer to power.
2. Confirm that the device has a stable internet connection.
3. Save all work.
4. Restart the computer.
5. Open **Settings → Windows Update**.
6. Select **Check for updates**.
7. Allow the update process time to complete.
8. Record any displayed error code.

**Prohibited Actions:**

Do not instruct the user to:

* Delete the SoftwareDistribution folder
* Stop Windows Update services
* Remove updates
* Run administrator repair commands
* Reset Windows

**Escalation:**

If the update remains stuck or shows an error code, contact the IT Helpdesk and provide the error code.

---

## Topic: Windows USB Device Is Not Recognized

**Intent Keywords:** USB not recognized, unknown USB device, USB device not working, flash drive not detected, USB error

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Disconnect the USB device.
2. Wait five seconds.
3. Reconnect it.
4. Try another USB port.
5. Avoid using a USB hub during testing.
6. Restart the computer.
7. Test the device on another computer if available.

**Escalation:**

If the device works on another computer but not the original computer, contact the IT Helpdesk.

Do not uninstall USB controllers or change power-management settings unless instructed by IT.

---

## Topic: Windows External Drive Is Not Showing

**Intent Keywords:** external drive missing, hard drive not showing, USB drive missing, flash drive missing, drive not detected

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Disconnect and reconnect the drive.
2. Try another USB port.
3. Avoid using a dock or USB hub while testing.
4. Restart the computer.
5. Test the drive on another computer if available.

**Critical Warning:**

Do not format, initialize, erase, or partition the drive.

**Escalation:**

If the drive contains important files and is still not detected, stop troubleshooting and contact the IT Helpdesk.

---

## Topic: Windows File Will Not Delete

**Intent Keywords:** cannot delete file, file is open, folder will not delete, file in use, another program is using the file

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Close the application that may be using the file.
2. Close File Explorer windows displaying the file.
3. Wait a few seconds and try again.
4. Restart the computer.
5. Try deleting the file after restart.

**Escalation:**

If the file still cannot be deleted, contact the IT Helpdesk.

Do not provide ownership, permission, administrator-command, or protected-system-file instructions.

---

## Topic: Windows File Was Accidentally Deleted

**Intent Keywords:** deleted file, accidentally deleted, recover file, missing document, restore deleted file

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Open the **Recycle Bin**.
2. Locate the deleted file.
3. Right-click it.
4. Select **Restore**.
5. Check OneDrive or Google Drive trash if the file was stored in a synchronized folder.
6. Do not save new files to the same drive if the deleted file is especially important.

**Escalation:**

If the file is not in the Recycle Bin or cloud trash, contact the IT Helpdesk as soon as possible.

Do not recommend third-party recovery software.

---

## Topic: Windows File Explorer or Taskbar Is Not Responding

**Intent Keywords:** File Explorer crashing, taskbar missing, desktop icons missing, Windows Explorer not responding, Start menu not working

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Press **Ctrl + Shift + Esc**.
2. Open Task Manager.
3. Locate **Windows Explorer**.
4. Right-click it.
5. Select **Restart**.
6. Wait for the desktop and taskbar to reload.
7. Restart the computer if the issue continues.

**Escalation:**

If File Explorer, the Start menu, or the taskbar repeatedly stops working, contact the IT Helpdesk.

Do not provide PowerShell repair commands through the public chatbot.

---

## Topic: Microsoft Store Application Will Not Download

**Intent Keywords:** Microsoft Store not downloading, Store app stuck, cannot install Store app, Microsoft Store error

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Confirm that the internet connection is working.
2. Confirm that the date, time, and time zone are correct.
3. Close and reopen Microsoft Store.
4. Sign out of Microsoft Store and sign back in.
5. Restart the computer.
6. Open **Settings → Apps → Installed apps → Microsoft Store → Advanced options**.
7. Select **Repair**, if available.

**Escalation:**

If the Store still does not work, contact the IT Helpdesk.

Do not reset Microsoft Store or run PowerShell commands unless instructed by IT.

---

## Topic: Windows Activation Error

**Intent Keywords:** Windows not activated, activation error, activate Windows, license error, Windows license

**Target Audience:** Staff, Faculty, Students

**Bot Instruction:**

Do not provide activation keys, licensing credentials, or methods for bypassing Windows activation.

**Troubleshooting Steps:**

1. Open **Settings → System → Activation**.
2. Record the displayed activation message or error code.
3. Confirm that the computer is connected to the internet.
4. Restart the computer.

**Escalation:**

For school-owned devices, contact the IT Helpdesk and provide the activation error code.

---

## Topic: Windows Requires Administrator Credentials

**Intent Keywords:** administrator password, admin credentials, admin permission, asks for administrator, elevation required

**Target Audience:** Staff, Faculty, Students

**Direct Answer:**

Administrator credentials are restricted and cannot be provided through the chatbot.

**Approved Response:**

> Please contact or visit the IT Helpdesk. An authorized technician can review the request and complete the installation or configuration if it is approved.

**Prohibited Actions:**

Do not provide:

* Administrator usernames
* Administrator passwords
* Password hints
* Privilege-bypass instructions
* Instructions for creating another administrator account
