---
title: Mac Basic Troubleshooting
topic: mac_support
platform: macos
audience: public
document_type: support_procedure
workflow: mac_basic_troubleshooting
version: 1.0
---

# Mac Basic Troubleshooting

This document contains approved Tier-1 troubleshooting procedures for common Mac and MacBook issues.

## Assistant Behaviour Rules

* Use this document only when the user confirms they are using a Mac.

* If the operating system is unknown, ask:

  > Are you using a Mac or a Windows device?

* Stop and wait for the user's answer before providing operating-system-specific steps.

* Do not provide both Mac and Windows instructions in the same response.

* Give only the procedure matching the current question.

* Do not combine unrelated troubleshooting topics.

* Begin with simple, low-risk troubleshooting.

* Do not ask users to run Terminal commands.

* Do not ask users to change protected file permissions.

* Do not instruct users to reset NVRAM, SMC, firmware, security settings, or recovery settings.

* Do not instruct users to erase, format, initialize, partition, reset, or reinstall macOS.

* Do not instruct users to bypass macOS security protections.

* Do not recommend third-party cleanup or recovery applications.

* Do not claim that hardware is faulty unless confirmed by IT.

* For school Wi-Fi issues, use the approved Student or Guest Wi-Fi workflow.

* For school-printer issues, use the approved printer-support workflow.

* If the approved steps do not resolve the issue, direct the user to the IT Helpdesk.

* Do not claim that a ticket was created unless the ticketing system confirms it.

---

## Topic: Mac Sound Uses the Wrong Output Device

**Intent Keywords:** Mac sound wrong device, sound from MacBook, HDMI sound, projector audio, monitor audio, switch sound output

**Target Audience:** Staff, Faculty, Students

**Direct Answer:**

The Mac may be sending audio to the wrong output device.

**Troubleshooting Steps:**

1. Open **Apple menu → System Settings → Sound**.
2. Under **Output**, select the intended device:

   * MacBook speakers
   * Headphones
   * HDMI display
   * Projector
   * External speakers
3. Confirm that the output volume is turned up.
4. Confirm that **Mute** is not enabled.
5. Play audio again to test it.

**Escalation:**

If the correct output device is selected but there is still no sound, restart the Mac. Contact the IT Helpdesk if the problem continues.

---

## Topic: Bluetooth Headphones Connected but Have No Sound

**Intent Keywords:** AirPods connected no sound, Bluetooth headphones no audio, headphones connected but not working, Mac Bluetooth sound

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Open **Apple menu → System Settings → Sound**.
2. Under **Output**, select the Bluetooth headphones.
3. Confirm that the volume is not muted.
4. Open **System Settings → Bluetooth**.
5. Confirm that the headphones show as connected.
6. Turn Bluetooth off and then back on.
7. If needed, select the information button beside the headphones and choose **Forget This Device**.
8. Put the headphones into pairing mode and reconnect them.
9. Restart the Mac if the issue continues.

**Escalation:**

If the headphones connect successfully to another device but still do not work with the Mac, contact the IT Helpdesk.

---

## Topic: Mac Has No Sound

**Intent Keywords:** Mac no sound, audio stopped, speakers not working, MacBook silent, audio not working

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Open **System Settings → Sound**.
2. Under **Output**, select **MacBook Speakers** or the correct external device.
3. Confirm that the volume is turned up.
4. Confirm that the device is not muted.
5. Disconnect any headphones, HDMI cables, docks, or external audio devices.
6. Test the MacBook speakers again.
7. Restart the Mac.

**Escalation:**

If there is still no sound after restarting, contact the IT Helpdesk.

---

## Topic: Mac Microphone Not Working

**Intent Keywords:** Mac microphone not working, mic not working, Teams microphone, Zoom microphone, FaceTime microphone, cannot be heard

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Open **Apple menu → System Settings → Privacy & Security → Microphone**.
2. Confirm that microphone access is enabled for the affected application.
3. Open Teams, Zoom, FaceTime, or the affected application.
4. Open its audio or device settings.
5. Select the correct microphone.
6. Confirm that the microphone is not muted.
7. Disconnect and reconnect any external headset or microphone.
8. Quit and reopen the application.
9. Restart the Mac if necessary.

**Escalation:**

If the microphone still does not work, contact the IT Helpdesk.

---

## Topic: Mac Will Not Turn On

**Intent Keywords:** Mac will not turn on, MacBook not starting, black screen, Mac no power, MacBook dead

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Connect the MacBook directly to a known working power outlet.
2. Confirm that the charging cable is securely connected.
3. Disconnect docks, USB devices, monitors, and other accessories.
4. Leave the Mac connected to power for at least five minutes.
5. Press and hold the power button for approximately ten seconds.
6. Release the button.
7. Press the power button normally.

**Escalation:**

If the Mac still does not turn on, stop troubleshooting and contact the IT Helpdesk.

---

## Topic: Mac Is Stuck at the Apple Logo

**Intent Keywords:** stuck at Apple logo, Mac not booting, Mac startup stuck, loading bar frozen, Mac boot problem

**Target Audience:** Staff, Faculty, Students

**Bot Instruction:**

Do not provide Recovery Mode, Disk Utility, Safe Mode, reinstall, firmware, or startup-security instructions through the public chatbot.

**Troubleshooting Steps:**

1. Disconnect external USB devices, drives, docks, and monitors.
2. Connect the Mac to power.
3. Wait several minutes to confirm that startup is not still progressing.
4. If there is no progress, hold the power button until the Mac turns off.
5. Wait 15 seconds.
6. Turn the Mac on normally.
7. Record any error message displayed.

**Escalation:**

If the Mac remains stuck at startup, contact the IT Helpdesk.

---

## Topic: Mac Battery Drains Quickly

**Intent Keywords:** Mac battery draining fast, poor battery life, MacBook battery issue, battery losing charge, battery dies quickly

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Open **Apple menu → System Settings → Battery**.
2. Review the battery-usage information.
3. Lower the screen brightness.
4. Close applications that are no longer needed.
5. Close unnecessary browser tabs.
6. Disconnect unused external devices.
7. Restart the Mac.
8. Open **System Settings → Battery → Battery Health**.
9. Record any message such as **Service Recommended**.

**Escalation:**

If Battery Health displays **Service Recommended**, or the battery continues draining unusually quickly, contact the IT Helpdesk.

---

## Topic: MacBook Is Not Charging

**Intent Keywords:** MacBook not charging, charger not recognized, battery not charging, MagSafe not charging, USB-C charging issue

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Connect the charger directly to a wall outlet.
2. Avoid using a dock, hub, or power bar while testing.
3. Confirm that the charger is connected securely.
4. Try another approved charging port on the MacBook, if available.
5. Inspect the cable and adapter for visible damage.
6. Disconnect the charger.
7. Restart the Mac.
8. Reconnect the charger after startup.
9. Try another approved charger if one is available.

**Safety Rule:**

Do not use a cable or adapter that is damaged, unusually hot, discoloured, or producing a burning smell.

**Escalation:**

If the MacBook still does not charge, contact the IT Helpdesk.

---

## Topic: Mac Shuts Down or Restarts Unexpectedly

**Intent Keywords:** Mac shuts down, random restart, Mac crashing, unexpected shutdown, MacBook restarts itself

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Save open work.
2. Disconnect external devices.
3. Restart the Mac.
4. Open **System Settings → General → Software Update**.
5. Install approved pending updates.
6. Confirm that the Mac has sufficient free storage.
7. Record any error message shown after restart.
8. Note what application was in use when the issue occurred.

**Escalation:**

If the Mac repeatedly shuts down or restarts, contact the IT Helpdesk and provide any displayed error message.

---

## Topic: Mac Wi-Fi Is Not Connecting

**Intent Keywords:** Mac Wi-Fi not working, Mac cannot connect, Mac no internet, Mac Wi-Fi disconnecting, wireless problem

**Target Audience:** Staff, Faculty, Students

**Bot Instruction:**

Use the approved Student or Guest Wi-Fi procedure. Do not provide a Wi-Fi password as plain text.

**Approved Steps:**

1. Confirm whether the user is connecting to Student Wi-Fi or Guest Wi-Fi.
2. Confirm that Wi-Fi is turned on.
3. Confirm that Airplane Mode is not active.
4. Forget the existing school network.
5. Turn Wi-Fi off and back on.
6. Restart the Mac.
7. Confirm that the date, time, and time zone are correct.
8. Scan the correct approved Wi-Fi QR code again.

**Prohibited Actions:**

Do not instruct the user to:

* Change DNS settings
* Change proxy settings
* Modify certificates
* Run Terminal network commands
* Reset all network settings

**Escalation:**

If the issue continues, contact the IT Helpdesk.

---

## Topic: Mac Bluetooth Device Will Not Connect

**Intent Keywords:** Mac Bluetooth not working, Bluetooth device not pairing, Bluetooth disconnecting, AirPods not connecting, mouse not pairing

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Confirm that Bluetooth is turned on.
2. Confirm that the device is charged or has a working battery.
3. Turn the Bluetooth device off and back on.
4. Open **System Settings → Bluetooth**.
5. Select the information button beside the device.
6. Choose **Forget This Device**, if appropriate.
7. Put the device into pairing mode.
8. Reconnect it.
9. Restart the Mac if the problem continues.

**Escalation:**

If the device works with another computer but not the Mac, contact the IT Helpdesk.

---

## Topic: Mac VPN Is Connected but Does Not Work

**Intent Keywords:** Mac VPN not working, VPN connected no internet, cannot reach work resources, VPN connection issue

**Target Audience:** Staff, Faculty

**Bot Instruction:**

Do not provide VPN server addresses, shared secrets, certificates, administrator credentials, DNS changes, or Terminal commands.

**Troubleshooting Steps:**

1. Disconnect the VPN.
2. Confirm that normal internet access works without the VPN.
3. Restart the Mac.
4. Reconnect the VPN.
5. Record any error message.
6. Confirm that the correct approved VPN profile is selected.

**Escalation:**

If the VPN still does not work, contact the IT Helpdesk.

---

## Topic: AirDrop Is Not Working

**Intent Keywords:** AirDrop not working, cannot AirDrop, AirDrop missing, file will not send, AirDrop device not visible

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Confirm that Wi-Fi is turned on on both devices.
2. Confirm that Bluetooth is turned on on both devices.
3. Open **Control Centre → AirDrop**.
4. Temporarily select **Everyone for 10 Minutes**, if appropriate.
5. Confirm that Personal Hotspot is turned off.
6. Keep both devices nearby and unlocked.
7. Try sending the file again.
8. Restart both devices if necessary.

**Privacy Note:**

After testing, change AirDrop visibility back to **Contacts Only** or **Receiving Off**.

---

## Topic: Mac External Display Is Not Detected

**Intent Keywords:** Mac second monitor not detected, external display missing, monitor black, Mac display not working, HDMI monitor Mac

**Target Audience:** Staff, Faculty

**Troubleshooting Steps:**

1. Confirm that the monitor is turned on.
2. Check for a monitor power light.
3. Disconnect the video cable from both the Mac and monitor.
4. Reconnect the cable securely.
5. Disconnect and reconnect any dock or adapter.
6. Open **Apple menu → System Settings → Displays**.
7. Confirm that the external display appears.
8. Put the Mac to sleep and wake it again.
9. Try another approved cable, adapter, or port if available.

**Escalation:**

If the display is still not detected, contact the IT Helpdesk.

---

## Topic: Mac External Display Is Blurry or Incorrectly Sized

**Intent Keywords:** Mac monitor blurry, wrong resolution, display stretched, text too small, external screen blurry, Mac scaling

**Target Audience:** Staff, Faculty

**Troubleshooting Steps:**

1. Open **System Settings → Displays**.
2. Select the affected external display.
3. Select the recommended resolution.
4. Adjust the text-size or scaling option.
5. Disconnect and reconnect the display cable.
6. Restart the Mac if the problem continues.

**Escalation:**

If the display remains blurry, contact the IT Helpdesk with the monitor and adapter details.

---

## Topic: Mac Windows Are Stuck on a Disconnected Display

**Intent Keywords:** window off screen, app on missing monitor, windows trapped on second display, cannot find app window

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Reconnect the external display temporarily, if possible.
2. Open the affected application.
3. From the application's **Window** menu, choose an available option such as:

   * Bring All to Front
   * Zoom
4. Close and reopen the application.
5. Restart the Mac if the window still does not return.

**Escalation:**

If the application window remains inaccessible, contact the IT Helpdesk.

---

## Topic: Mac Dock or Menu Bar Is Missing

**Intent Keywords:** Mac Dock missing, menu bar disappeared, taskbar missing Mac, Dock hidden, menu bar not showing

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Move the pointer to the bottom edge of the screen to reveal the Dock.
2. Press **Escape** to leave full-screen mode.
3. Press **Command + Tab** and switch to another application.
4. Open **System Settings → Desktop & Dock**.
5. Review **Automatically hide and show the Dock**.
6. Review the menu-bar visibility settings.
7. Restart the Mac if the Dock or menu bar remains missing.

**Escalation:**

If the Dock or menu bar repeatedly disappears, contact the IT Helpdesk.

---

## Topic: Mac Says You Do Not Have Permission to Open a File

**Intent Keywords:** permission denied Mac, cannot open file, no permission, access denied, file permission Mac

**Target Audience:** Staff, Faculty, Students

**Direct Answer:**

The file may belong to another user, be stored in a restricted location, or require permission from its owner.

**Approved Steps:**

1. Confirm that the user is signed into the correct account.
2. Confirm that the file is stored in an expected location.
3. If the file came from Google Drive, OneDrive, or another shared service, confirm that access was granted.
4. Ask the file owner to share the file again.
5. Do not change ownership or permissions on school-managed files.

**Escalation:**

If the file should be accessible but remains blocked, contact the IT Helpdesk.

---

## Topic: Mac File Will Not Delete

**Intent Keywords:** Mac cannot delete file, item in use, file will not delete, Trash error, file locked

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Close the application that may be using the file.
2. Close Finder windows displaying the file.
3. Wait several seconds.
4. Try moving the file to Trash again.
5. Restart the Mac.
6. Try deleting the file after restart.

**Escalation:**

If the file still cannot be deleted, contact the IT Helpdesk.

Do not provide Terminal commands, ownership changes, or protected-file removal instructions.

---

## Topic: Mac File Was Accidentally Deleted

**Intent Keywords:** deleted file Mac, recover deleted file, accidentally deleted document, restore file, missing file

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Open **Trash**.
2. Locate the deleted file.
3. Right-click or Control-click it.
4. Select **Put Back**.
5. Check Google Drive, OneDrive, or iCloud trash if the file was stored in a synchronized folder.
6. Check Time Machine only if it was previously configured and the user knows how to use it.
7. Avoid creating or downloading new files if the deleted data is especially important.

**Escalation:**

If the file cannot be found, contact the IT Helpdesk as soon as possible.

Do not recommend third-party recovery applications.

---

## Topic: Finder Is Frozen or Not Responding

**Intent Keywords:** Finder frozen, Finder not responding, Finder crashing, cannot open Finder, Finder stuck

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Press **Option + Command + Escape**.
2. Select **Finder**.
3. Select **Relaunch**.
4. Wait for Finder to reopen.
5. Disconnect external drives or network shares temporarily.
6. Restart the Mac if Finder continues freezing.

**Escalation:**

If Finder repeatedly freezes, contact the IT Helpdesk.

Do not provide Terminal commands for deleting Finder preferences.

---

## Topic: Mac Trackpad Is Not Clicking or Responding

**Intent Keywords:** Mac trackpad not working, trackpad not clicking, cursor not moving, MacBook trackpad frozen

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Connect the MacBook to power.
2. Restart the Mac.
3. Open **System Settings → Trackpad**.
4. Confirm that trackpad settings are enabled as expected.
5. Disconnect external mice or input devices.
6. Check whether the trackpad surface is visibly raised or uneven.

**Safety Warning:**

A raised trackpad may indicate a swollen battery. Stop using the MacBook, disconnect power if safe, and contact the IT Helpdesk immediately.

---

## Topic: Mac Keyboard Is Not Responding

**Intent Keywords:** Mac keyboard not working, MacBook keyboard not typing, keys unresponsive, external keyboard not working

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Restart the Mac.
2. For a USB keyboard:

   * Disconnect it.
   * Wait five seconds.
   * Reconnect it.
   * Try another port.
3. For a Bluetooth keyboard:

   * Confirm that it is charged.
   * Turn it off and back on.
   * Reconnect it through **System Settings → Bluetooth**.
4. Open the on-screen keyboard through:

   * **System Settings → Accessibility → Keyboard**
5. Check whether only one application is affected.

**Escalation:**

If the physical keyboard remains unresponsive, contact the IT Helpdesk.

---

## Topic: Mac Keyboard Types the Wrong Characters

**Intent Keywords:** Mac wrong keyboard layout, wrong characters, keyboard language Mac, keys do not match, input source wrong

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Check the input-source icon in the menu bar.
2. Select the correct keyboard layout.
3. Open **System Settings → Keyboard → Text Input**.
4. Review installed input sources.
5. Remove unnecessary layouts only if the user recognizes them.
6. Test the keyboard again.

**Escalation:**

If the keyboard continues typing incorrect characters, contact the IT Helpdesk.

---

## Topic: Mac Keyboard Shortcuts Are Not Working

**Intent Keywords:** Mac shortcut not working, keyboard shortcuts broken, Command key not working, shortcut conflict

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Confirm that the correct application is active.
2. Try the shortcut in another application.
3. Open **System Settings → Keyboard → Keyboard Shortcuts**.
4. Confirm that the shortcut is enabled.
5. Check whether another action uses the same shortcut.
6. Restart the Mac.

**Escalation:**

If standard shortcuts remain unavailable, contact the IT Helpdesk.

---

## Topic: Mac Is Frozen or Shows a Spinning Beachball

**Intent Keywords:** spinning beachball, Mac frozen, Mac not responding, application frozen, MacBook stuck, force quit Mac, close frozen app Mac, Option Command Escape

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Wait approximately 30 seconds.
2. Try switching to another application.
3. Press **Option + Command + Escape**.
4. Select the unresponsive application.
5. Select **Force Quit**.
6. Reopen the application.
7. Restart the Mac if freezing continues.

**Important:**

Unsaved work in a force-quit application may be lost.

**Escalation:**

If the Mac freezes repeatedly, contact the IT Helpdesk.

---

## Topic: Mac Is Running Slowly

**Intent Keywords:** Mac slow, MacBook slow, Mac lagging, poor performance, high CPU, Mac freezing

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Save open work.
2. Close applications that are no longer needed.
3. Close unnecessary browser tabs.
4. Restart the Mac through **Apple menu → Restart**.
5. Open **Activity Monitor**.
6. Review the **CPU** and **Memory** tabs.
7. Close only applications the user recognizes and no longer needs.
8. Open **System Settings → General → Software Update**.
9. Install approved pending updates.
10. Confirm that sufficient storage is available.

**Prohibited Actions:**

Do not instruct the user to:

* Delete system caches
* Disable security services
* Remove system files
* Run Terminal cleanup commands
* Install cleanup utilities

**Escalation:**

If the Mac remains slow after restarting and updating, contact the IT Helpdesk.

---

## Topic: Mac Is Running Hot or the Fans Are Loud

**Intent Keywords:** Mac hot, MacBook overheating, fans loud, fan spinning, Mac temperature

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Place the MacBook on a hard, flat surface.
2. Confirm that ventilation openings are not blocked.
3. Disconnect unnecessary external devices.
4. Close unused applications and browser tabs.
5. Open **Activity Monitor → CPU**.
6. Look for an application using unusually high CPU.
7. Close only applications the user recognizes and no longer needs.
8. Restart the Mac.

**Safety Warning:**

If the Mac is extremely hot, smells unusual, shows battery swelling, or shuts down repeatedly, stop using it and contact the IT Helpdesk immediately.

---

## Topic: Mac Storage Is Almost Full

**Intent Keywords:** Mac storage full, disk almost full, no storage space, startup disk full, MacBook out of space

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Open **Apple menu → System Settings → General → Storage**.
2. Review the storage categories.
3. Empty Trash after confirming that its contents are no longer needed.
4. Delete unneeded files from Downloads.
5. Remove applications the user installed and no longer needs.
6. Move large personal files to an approved cloud-storage service.
7. Restart the Mac after freeing space.

**Prohibited Actions:**

Do not instruct the user to:

* Delete Library folders
* Delete system caches
* Delete unknown system files
* Install disk-cleanup utilities

**Escalation:**

If the user cannot safely identify files to remove, contact the IT Helpdesk.

---

## Topic: Mac Application Will Not Open

**Intent Keywords:** Mac app will not open, application damaged, app blocked, cannot launch app, unidentified developer

**Target Audience:** Staff, Faculty, Students

**Bot Instruction:**

Do not provide quarantine-removal commands, security-bypass commands, or instructions for overriding school security policies.

**Troubleshooting Steps:**

1. Confirm that the application came from an approved source.
2. Quit the application.
3. Restart the Mac.
4. Open **System Settings → General → Software Update**.
5. Install approved pending updates.
6. Check whether an approved newer version of the application is available.
7. Record the exact error message.

**Escalation:**

If macOS reports that the application is damaged, blocked, or from an unidentified developer, contact the IT Helpdesk.

---

## Topic: macOS Update Is Stuck or Will Not Install

**Intent Keywords:** macOS update stuck, Mac update failed, update will not install, macOS download stuck, software update error

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Connect the MacBook to power.
2. Confirm that the internet connection is stable.
3. Save all work.
4. Confirm that at least 20 GB of storage is available.
5. Restart the Mac.
6. Open **System Settings → General → Software Update**.
7. Try the update again.
8. Allow sufficient time for the update to complete.
9. Record any displayed error message.

**Prohibited Actions:**

Do not instruct the user to:

* Run Terminal update commands
* Reinstall macOS
* Use Recovery Mode
* Erase the Mac
* Remove update files manually

**Escalation:**

If the update remains stuck or shows an error, contact the IT Helpdesk.

---

## Topic: Mac App Store Will Not Download or Update Applications

**Intent Keywords:** App Store not downloading, Mac app update stuck, cannot install App Store app, App Store error

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Confirm that the internet connection works.
2. Confirm that the date, time, and time zone are correct.
3. Quit and reopen the App Store.
4. Confirm that the correct Apple Account is signed in.
5. Restart the Mac.
6. Try downloading or updating the application again.
7. Record any displayed error message.

**Escalation:**

If the App Store continues failing, contact the IT Helpdesk.

Do not provide cache-deletion or Terminal commands.

---

## Topic: Mac USB Device Is Not Recognized

**Intent Keywords:** Mac USB not recognized, USB device missing, USB error Mac, external device not detected, USB-C device not working

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Disconnect the USB device.
2. Wait five seconds.
3. Reconnect it.
4. Try another port.
5. Avoid using a dock or USB hub while testing.
6. Try another approved cable.
7. Restart the Mac.
8. Test the device on another computer if available.

**Escalation:**

If the device works on another computer but not the Mac, contact the IT Helpdesk.

---

## Topic: Mac External Drive Is Not Showing

**Intent Keywords:** external drive missing Mac, hard drive not mounting, USB drive not showing, external disk missing, flash drive missing Mac

**Target Audience:** Staff, Faculty, Students

**Troubleshooting Steps:**

1. Disconnect and reconnect the drive.
2. Try another port.
3. Avoid using a dock or USB hub while testing.
4. Open **Finder → Settings → General**.
5. Confirm that **External disks** is enabled.
6. Restart the Mac.
7. Test the drive on another computer if available.

**Critical Warning:**

Do not format, initialize, erase, partition, or repair the drive through the public chatbot.

**Escalation:**

If the drive contains important data and is not detected, stop troubleshooting and contact the IT Helpdesk.

---

## Topic: Mac Printer Is Not Responding

**Intent Keywords:** Mac printer not responding, printer paused Mac, print job stuck, printer offline Mac, cannot print Mac

**Target Audience:** Staff, Faculty, Students

**Bot Instruction:**

Use the approved school-printer workflow when the user refers to a school printer.

**Troubleshooting Steps:**

1. Confirm that the Mac is connected to the approved school Wi-Fi network.
2. Open **System Settings → Printers & Scanners**.
3. Select the correct printer.
4. Open the print queue.
5. Confirm that the job is not paused.
6. Delete only the user's failed print job, if appropriate.
7. Try printing again.
8. Restart the Mac if necessary.

**Prohibited Actions:**

Do not instruct the user to reset the entire printing system or remove all printers.

**Escalation:**

If the printer remains unavailable, contact the IT Helpdesk.

---

## Topic: Mac Requires Administrator Credentials

**Intent Keywords:** Mac administrator password, admin credentials Mac, installation asks for password, administrator permission, Mac admin required

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
* Security-bypass instructions
* Instructions for creating another administrator account
* Instructions for disabling macOS security controls
