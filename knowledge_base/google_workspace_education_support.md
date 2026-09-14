---
title: Google Workspace for Education Basic Support
topic: google_workspace_support
platform: web
audience: public
document_type: support_procedure
workflow: google_workspace_basic_support
version: 1.1
---

# Google Workspace for Education Basic Support

This document covers safe, day-to-day troubleshooting for school-managed Google Workspace services, including Google Docs, Sheets, Slides, Gmail, Calendar, Drive, Classroom, Meet, Forms, Groups, and related account access.

## Global Support Rules

- Use these procedures only for school-managed Google Workspace accounts.
- Never ask a user to share a password, verification code, recovery code, backup code, or authenticator code.
- The school does not allow users to reset their own Google Workspace password.
- All password-reset requests must be handled in person at the IT Helpdesk after identity verification.
- Do not claim that a password, account, class role, group membership, sharing permission, grade, or admin setting was changed unless an approved tool confirms it.
- Do not advise users to create a second school account.
- Do not advise users to bypass school security, content filtering, device management, or sharing restrictions.
- Begin with low-risk steps such as checking the account, refreshing, signing out and back in, using a private browser window, trying another supported browser, and restarting the application or device.
- If several users report the same issue, do not state that Google is down unless the outage is officially confirmed.
- Protect student, parent, and staff privacy. Do not ask users to paste private school records, grades, student information, email contents, or confidential files into chat.
- For teacher-controlled Classroom content, assignments, grades, due dates, comments, and class membership, contact the teacher first unless the problem is clearly technical.
- For admin-controlled settings, access, roles, groups, external sharing, suspended accounts, or service availability, contact the IT Helpdesk.

---

## Topic: Cannot Sign In to School Google Account

**Intent Keywords:** cannot sign in google, school google login, gmail login not working, google workspace sign in, account login failed, wrong password, school email login

**Direct Answer:**

Confirm that you are signing in with your school-managed Google account, not a personal Gmail account.

**Troubleshooting Steps:**

1. Open a private or incognito browser window.
2. Enter the full school email address.
3. Confirm that the account domain belongs to the school.
4. Check that Caps Lock is off.
5. Try signing in to Gmail or Google Drive using the same account.
6. If the password is rejected, stop repeated attempts.

**Escalation:**

Visit the IT Helpdesk in person if the password is not accepted, the account is locked, or the account is disabled.

**Bot Instruction:** Do not offer self-service password reset for school accounts. Do not ask for the password.


## Topic: Forgot or Need to Reset School Google Password

**Intent Keywords:** forgot google password, reset school password, gmail password reset, change school password, cannot remember password, google classroom password, school account password, forgot email password

**Direct Answer:**

School Google Workspace passwords must be reset in person by the IT Helpdesk after identity verification.

**Required Steps:**

1. Stop repeated sign-in attempts.
2. Bring your school-issued device or school ID if available.
3. Visit the IT Helpdesk and provide the technician with your school email address.
4. After IT resets the password, sign in again using the new password.

**Bot Instruction:** Keep this answer concise. Do not offer Google self-service password recovery. Do not ask for an old password, new password, verification code, or recovery code. Do not add a second escalation paragraph because the required action is already stated.

## Topic: School Google Account Is Locked or Disabled

**Intent Keywords:** google account locked, account disabled, too many attempts, school account suspended, gmail account blocked, cannot access google account

**Direct Answer:**

A locked, suspended, or disabled school Google account must be reviewed by the IT Helpdesk.

**Troubleshooting Steps:**

1. Stop repeated sign-in attempts.
2. Confirm that the correct school email address is being used.
3. Try the account once in a private browser window.
4. Record the exact error message.
5. Do not create another account.

**Escalation:**

Visit or contact the IT Helpdesk and provide the exact error message.

**Bot Instruction:** Do not claim to unlock, reactivate, or unsuspend an account.


## Topic: Wrong Google Account Opens

**Intent Keywords:** wrong google account, personal gmail opens, switch google account, wrong classroom account, wrong drive account, multiple google accounts

**Direct Answer:**

The browser may be using a personal Google account instead of the school account.

**Troubleshooting Steps:**

1. Select the profile picture in the upper-right corner.
2. Confirm which account is active.
3. Choose the school account if it is already listed.
4. If it is not listed, select **Add another account** and use the school email address.
5. For a clean test, open a private or incognito window and sign in only with the school account.
6. Reopen Gmail, Drive, Classroom, or Calendar.

**Escalation:**

Contact the IT Helpdesk if the school account is missing, disabled, or repeatedly redirects to the wrong account.

**Bot Instruction:** Do not ask the user to remove a managed school profile from the device.


## Topic: Two-Step Verification or Verification Code Problem

**Intent Keywords:** two-step verification, two factor authentication, 2fa, mfa, authenticator app, google authenticator, approval notification, approval prompt, push notification, verification code, verification prompt, phone approval not arriving, lost phone, changed phone

**Direct Answer:**

If an approval notification or verification code is not arriving, first confirm that the phone and school account are using the expected verification method.

**Troubleshooting Steps:**

1. Confirm that the phone has internet access and that Airplane Mode is off.
2. Open the authenticator app directly instead of waiting only for a notification.
3. Confirm that the approval request belongs to the correct school Google account.
4. Check that the phone's date, time, and time zone are set automatically and are correct.
5. Use the newest approval request or verification code; older requests may expire.
6. If Google offers another approved verification method, use it.
7. Stop repeated attempts if approvals or codes continue to fail.

**Escalation:**

Contact the IT Helpdesk if the phone was replaced, the authenticator method is unavailable, no approved verification method works, or the school account cannot complete two-step verification.

**Bot Instruction:** Never ask the user to paste a verification code, backup code, recovery code, authenticator code, or approval number into chat. Do not answer this topic with file-upload, Gmail attachment, or unrelated account instructions.

## Topic: Google Workspace Service May Be Down

**Intent Keywords:** google down, gmail down, drive outage, classroom outage, google workspace outage, everyone cannot access google, known issue

**Direct Answer:**

If several users are affected, the issue may be a school network problem or a Google Workspace service incident.

**Troubleshooting Steps:**

1. Confirm whether other websites work.
2. Ask whether multiple users are experiencing the same issue.
3. Try another Google Workspace service.
4. Try another device or network when permitted.
5. Record the service name, time, and exact error.
6. Check the official Google Workspace Status Dashboard and Google Workspace Known Issues page.

**Escalation:**

Contact the IT Helpdesk so the school can confirm the network and Google service status.

**Bot Instruction:** Do not state that Google is experiencing an outage unless it is officially confirmed.


## Topic: Google Workspace Page Is Slow, Blank, or Not Loading

**Intent Keywords:** google page blank, google workspace slow, docs not loading, gmail blank, drive spinning, classroom page stuck, google server error

**Direct Answer:**

The problem may be caused by the browser, an extension, the network, or a temporary service issue.

**Troubleshooting Steps:**

1. Wait a few minutes and reload the page once.
2. Confirm that the internet connection works.
3. Close extra browser tabs.
4. Open the same page in a private or incognito window.
5. Try another supported browser.
6. Temporarily disable nonessential browser extensions for testing.
7. Restart the browser.
8. Restart the device if the issue continues.

**Escalation:**

Contact the IT Helpdesk if the issue occurs in multiple browsers or affects several users.

**Bot Instruction:** Do not tell the user to reset the entire browser or delete all browser data as the first step.


## Topic: Google Workspace Storage Is Full

**Intent Keywords:** google storage full, drive storage full, gmail storage full, cannot create file, cannot send email storage, quota exceeded

**Direct Answer:**

When the school account reaches its storage limit, Gmail, Drive, Docs, Sheets, Slides, and other services may stop accepting new content.

**Troubleshooting Steps:**

1. Open Google Drive and review large files.
2. Empty Drive Trash only after confirming the files are no longer needed.
3. In Gmail, search for large messages and unnecessary attachments.
4. Empty Gmail Trash and Spam only after reviewing them.
5. Remove duplicate or unneeded videos and large files.
6. Wait for the storage total to update.

**Escalation:**

Contact the IT Helpdesk before deleting school records or if the quota appears incorrect.

**Bot Instruction:** Do not advise deleting school records, student work, shared-drive files, or unknown files.


## Topic: Gmail Message Is Missing

**Intent Keywords:** missing email, cannot find email, email disappeared, vendor email missing, gmail message not received, expected email not found

**Direct Answer:**

The message may be in Spam, Trash, another label, or a filtered location.

**Troubleshooting Steps:**

1. Search Gmail using the sender name, sender address, subject, or a keyword.
2. Check **Spam**.
3. Check **Trash**.
4. Check **All Mail**.
5. Check category tabs such as Promotions or Updates.
6. Review whether a filter or forwarding rule moved the message.
7. Confirm that the sender used the correct school email address.
8. Ask the sender whether they received a delivery failure.

**Escalation:**

Contact the IT Helpdesk if a known sender confirms delivery but the message cannot be found.

**Bot Instruction:** Do not confuse a missing expected email with a suspicious email.


## Topic: Gmail Is Not Receiving New Messages

**Intent Keywords:** gmail not receiving, no new email, inbox not updating, school email not receiving, messages delayed

**Direct Answer:**

Check the connection, storage, Spam, filters, and whether the problem affects all senders.

**Troubleshooting Steps:**

1. Refresh Gmail.
2. Confirm that the internet connection works.
3. Check the account storage.
4. Check Spam, Trash, and All Mail.
5. Review filters and blocked addresses.
6. Send a test message from another approved account.
7. Ask whether the sender received a bounce message.
8. Try Gmail in a private browser window.

**Escalation:**

Contact the IT Helpdesk if messages from multiple senders are missing or delayed.

**Bot Instruction:** Do not change routing, compliance, or admin-level Gmail settings.


## Topic: Gmail Message Bounced or Was Rejected

**Intent Keywords:** bounced email, rejected email, delivery failed, message not delivered, gmail error sending, recipient rejected

**Direct Answer:**

Read the automated delivery-failure message because it usually identifies the reason the email was rejected.

**Troubleshooting Steps:**

1. Open the bounce or delivery-status message.
2. Confirm the recipient address is spelled correctly.
3. Remove accidental spaces or punctuation from the address.
4. Check whether the message or attachments are too large.
5. Try sending a short message without attachments.
6. Confirm that the recipient mailbox still exists.
7. Save the exact error code or rejection text.

**Escalation:**

Contact the IT Helpdesk if the address is correct or the error mentions policy, authentication, reputation, routing, or blocking.

**Bot Instruction:** Do not promise delivery and do not change mail-routing settings.


## Topic: Gmail Attachment Will Not Send

**Intent Keywords:** attachment not sending, gmail upload stuck, file too large email, cannot attach file, attachment failed

**Direct Answer:**

The file may be too large, blocked by policy, or unable to upload because of the connection.

**Troubleshooting Steps:**

1. Confirm that the internet connection is stable.
2. Check the file name and file type.
3. Rename the file using a short name without unusual symbols.
4. Try attaching a smaller file.
5. For a large file, upload it to Google Drive and share an approved Drive link.
6. Try Gmail in a private browser window.
7. Do not repeatedly attach the same file while an upload is still processing.

**Escalation:**

Contact the IT Helpdesk if the file is school-related and appears to be blocked by policy.

**Bot Instruction:** Do not advise bypassing attachment restrictions or security scanning.


## Topic: Gmail Attachment Will Not Open or Download

**Intent Keywords:** cannot open gmail attachment, attachment download failed, gmail attachment missing, file blocked, attachment preview not working

**Direct Answer:**

Confirm the sender, file type, browser, and whether Google blocked the attachment for security.

**Troubleshooting Steps:**

1. Confirm that the sender is trusted.
2. Do not open unexpected or suspicious attachments.
3. Try the attachment preview.
4. Try downloading the file once.
5. Try Gmail in a private browser window.
6. Try another supported browser.
7. For an Office file, use the available option to open it in Google Docs, Sheets, or Slides.
8. Record any security warning.

**Escalation:**

Contact the IT Helpdesk if the file is required for school and Google blocks it or the attachment remains unavailable.

**Bot Instruction:** Never advise opening an attachment from an unknown or suspicious sender.


## Topic: Suspicious Email or Phishing Message

**Intent Keywords:** phishing, suspicious email, fake email, scam email, gift card email, strange email, unknown sender, password request

**Direct Answer:**

Do not click links, open attachments, reply, send money, or provide passwords or verification codes.

**Troubleshooting Steps:**

1. Check the full sender address.
2. Look for urgent requests, gift cards, money, passwords, or unusual links.
3. Do not interact with the message.
4. Use Gmail's phishing or spam reporting option when appropriate.
5. Keep the message available if IT needs to review it.

**Escalation:**

Contact the IT Helpdesk immediately if you clicked a link, opened an attachment, downloaded a file, or entered account information.

**Bot Instruction:** Treat interaction with a suspicious message as urgent. Never ask the user to paste credentials or confidential message contents.


## Topic: Gmail Filter, Label, or Inbox Category Problem

**Intent Keywords:** email going to wrong folder, gmail filter problem, label missing, inbox category, messages automatically archived, email skips inbox

**Direct Answer:**

A filter, label, category, or blocked-address setting may be changing where messages appear.

**Troubleshooting Steps:**

1. Search for the missing message in **All Mail**.
2. Open Gmail Settings.
3. Review **Filters and Blocked Addresses**.
4. Check whether a filter skips the inbox, deletes, forwards, or applies a label.
5. Review inbox category settings.
6. Test with one new message.

**Escalation:**

Contact the IT Helpdesk before changing a filter you do not recognize.

**Bot Instruction:** Do not delete filters in bulk or remove school-required routing rules.


## Topic: Google Drive File Is Missing

**Intent Keywords:** drive file missing, cannot find document, file disappeared, lost google file, missing folder, drive search

**Direct Answer:**

The file may be in another folder, Shared with me, Trash, a Shared Drive, or owned by another account.

**Troubleshooting Steps:**

1. Confirm that the correct school account is active.
2. Search Drive by file name, owner, type, or keyword.
3. Check **Recent**.
4. Check **Shared with me**.
5. Check **Trash**.
6. Check the relevant Shared Drive.
7. Review file activity if available.
8. Ask the owner whether the file was moved, renamed, or unshared.

**Escalation:**

Contact the IT Helpdesk if the file is school-critical, unexpectedly deleted, or missing for multiple users.

**Bot Instruction:** Do not claim that a missing file was permanently deleted without verification.


## Topic: Google Drive Access Denied or Request Access

**Intent Keywords:** drive access denied, need permission, request access, cannot open shared file, you need access, file permission

**Direct Answer:**

The file owner or a permitted manager must grant the correct access.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Check whether the file belongs to another Google account.
3. Select **Request access** if the option is available.
4. Include a brief reason for needing the file.
5. Ask the owner to share it with the correct school email address.
6. Reopen the link after access is granted.

**Escalation:**

Contact the teacher, file owner, department owner, or IT Helpdesk if ownership is unclear.

**Bot Instruction:** Do not claim to grant access or bypass sharing restrictions.


## Topic: Share a Google Drive File or Folder

**Intent Keywords:** share drive file, share folder, give edit access, viewer commenter editor, sharing settings

**Direct Answer:**

Share school files only with the minimum access required.

**Approved Steps:**

1. In Drive, select the file or folder.
2. Select **Share**.
3. Enter the approved school email address.
4. Choose **Viewer**, **Commenter**, or **Editor** as appropriate.
5. Add a message if needed.
6. Select **Send**.
7. Confirm that the correct person and permission were selected.

**Escalation:**

Contact the IT Helpdesk if external sharing is blocked or if the file contains sensitive school information.

**Bot Instruction:** Do not recommend public-link sharing for confidential, student, parent, staff, financial, or administrative records.


## Topic: Google Drive Upload Is Stuck or Fails

**Intent Keywords:** drive upload stuck, file upload failed, cannot upload to drive, upload taking too long, drive file not uploading

**Direct Answer:**

The upload may be affected by the connection, file size, browser, storage, or school policy.

**Troubleshooting Steps:**

1. Confirm that the internet connection is stable.
2. Check the available Google storage.
3. Keep the browser tab open until the upload finishes.
4. Rename the file using a short name without unusual symbols.
5. Try a smaller file.
6. Try Drive in a private browser window.
7. Try another supported browser.
8. Confirm that you have upload permission for the folder or Shared Drive.

**Escalation:**

Contact the IT Helpdesk if the upload is blocked by policy or repeatedly fails on different devices.

**Bot Instruction:** Do not advise uploading confidential school data to a personal account.


## Topic: Google Drive for Desktop Is Not Syncing

**Intent Keywords:** drive desktop not syncing, google drive sync stopped, files not syncing, drive icon error, desktop drive offline

**Direct Answer:**

Check the connection, Drive for desktop status, account, and available storage.

**Troubleshooting Steps:**

1. Confirm that the internet connection works.
2. Open the Drive for desktop status menu.
3. Confirm that it is signed in with the school account.
4. Pause and resume syncing if the option is available.
5. Quit and reopen Drive for desktop.
6. Restart the computer.
7. Check local disk space and Google storage.
8. Record any error message.

**Escalation:**

Contact the IT Helpdesk before disconnecting the managed school account or reinstalling Drive for desktop.

**Bot Instruction:** Do not remove managed Drive configuration or delete local sync folders.


## Topic: Deleted Google Drive File

**Intent Keywords:** deleted drive file, restore file, recover document, file in trash, accidentally deleted google file

**Direct Answer:**

Check Drive Trash first. Recovery options depend on ownership, retention, and school policy.

**Troubleshooting Steps:**

1. Open Google Drive.
2. Select **Trash**.
3. Search for the file.
4. Confirm the file name and owner.
5. Select **Restore** if the option is available.
6. Check the original folder after restoration.

**Escalation:**

Contact the IT Helpdesk promptly if the file is not in Trash or is a school-critical record.

**Bot Instruction:** Do not promise recovery and do not permanently empty Trash on behalf of the user.


## Topic: Docs, Sheets, or Slides File Will Not Open

**Intent Keywords:** google doc not opening, sheet not loading, slides not opening, server error docs, file stuck loading, document error

**Direct Answer:**

Try low-risk browser and connection troubleshooting before making a copy or downloading the file.

**Troubleshooting Steps:**

1. Wait five minutes and reload the page once.
2. Confirm that the internet connection is stable.
3. Open the file in a private browser window.
4. Try another supported browser.
5. Temporarily disable nonessential extensions.
6. Restart the browser.
7. Try opening the file from Google Drive.
8. Try another device.
9. If urgently needed and permitted, make a copy from Drive.

**Escalation:**

Contact the IT Helpdesk if the file fails on multiple devices or contains important school work.

**Bot Instruction:** Warn that making a copy may not preserve all version history or file features.


## Topic: Cannot Edit Google Docs, Sheets, or Slides

**Intent Keywords:** cannot edit google doc, view only, editing disabled, sheet read only, slides cannot type, no edit permission

**Direct Answer:**

The file may be view-only, owned by someone else, protected, too large, or opened with the wrong account.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Check whether the file says **View only** or **Comment only**.
3. Request edit access from the owner.
4. Try the file in a private browser window.
5. Try another supported browser.
6. Check whether the file is very large.
7. For Sheets, check whether the affected cells are protected.

**Escalation:**

Contact the file owner, teacher, or IT Helpdesk if the expected permission is missing.

**Bot Instruction:** Do not claim to change ownership, permissions, or protected ranges.


## Topic: Google Docs Formatting or Page Layout Problem

**Intent Keywords:** google docs formatting wrong, page breaks, margins, text moved, document layout, word document formatting, docs equivalent of word

**Direct Answer:**

Google Docs is the Google Workspace equivalent of Microsoft Word. Formatting can change when files are converted between Docs and Word formats.

**Troubleshooting Steps:**

1. Confirm whether the file is a Google Doc or Microsoft Word file.
2. Check **File → Page setup**.
3. Review margins, orientation, page size, and pageless mode.
4. Check paragraph spacing and line spacing.
5. Confirm that the expected font is available.
6. Use **Version history** to compare earlier formatting.
7. If the document was converted, compare it with the original file.

**Escalation:**

Contact the teacher or IT Helpdesk if a required template or school document format is damaged.

**Bot Instruction:** Do not overwrite the original file while testing conversion.


## Topic: Google Docs Comments, Suggestions, or Track Changes

**Intent Keywords:** google docs comments, suggestion mode, track changes, resolve comment, cannot comment, edits showing green

**Direct Answer:**

Use **Suggesting** when changes should be reviewed instead of immediately applied.

**Approved Steps:**

1. Open the document.
2. Confirm that you have Commenter or Editor access.
3. Select the editing-mode menu.
4. Choose **Editing**, **Suggesting**, or **Viewing**.
5. To comment, highlight text and select **Add comment**.
6. Mention a collaborator with `@` only when appropriate.
7. Resolve comments only after the issue is complete.

**Escalation:**

Contact the file owner if commenting or suggesting is unavailable.

**Bot Instruction:** Do not resolve, delete, or assign comments without the user's confirmation.


## Topic: Restore Earlier Google Docs, Sheets, or Slides Changes

**Intent Keywords:** undo old changes, version history, restore previous version, document changed, lost edits, recover earlier google doc

**Direct Answer:**

Use version history to review earlier saved versions and identify who made changes.

**Approved Steps:**

1. Open the file.
2. Select **File → Version history → See version history**.
3. Review the dated versions.
4. Open the version that contains the needed content.
5. Restore it only after confirming it is the correct version.
6. Consider making a copy before restoring a shared school file.

**Escalation:**

Contact the teacher, file owner, or IT Helpdesk before restoring a heavily shared or official school document.

**Bot Instruction:** Do not restore a version on behalf of the user or imply that all edits can always be recovered.


## Topic: Work on Docs, Sheets, or Slides Offline

**Intent Keywords:** google docs offline, sheets offline, slides offline, edit without internet, offline file not working

**Direct Answer:**

Offline access must be enabled in advance and may be restricted on managed school devices.

**Troubleshooting Steps:**

1. Confirm that Chrome or an approved browser is being used.
2. Confirm that the correct school account is active.
3. Open Google Drive settings.
4. Check whether offline access is enabled.
5. Confirm that the specific file is available offline.
6. Reconnect to the internet and allow pending changes to sync.
7. If offline access is malfunctioning, turn it off and back on only if permitted.

**Escalation:**

Contact the IT Helpdesk if offline access is disabled by school policy or changes do not sync.

**Bot Instruction:** Do not advise using a personal account to work around managed offline restrictions.


## Topic: Google Sheets Formula Error or Formula Not Calculating

**Intent Keywords:** sheets formula error, formula not working, ref error, value error, div error, formula not calculating, spreadsheet calculation

**Direct Answer:**

Check the formula syntax, referenced cells, number formats, and whether the expected cells contain text instead of numbers.

**Troubleshooting Steps:**

1. Select the cell with the error.
2. Review the formula bar.
3. Check for missing parentheses, commas, quotation marks, or sheet names.
4. Confirm that referenced cells still exist.
5. Check whether numbers are stored as text.
6. Confirm the decimal and date format.
7. Test the formula in a blank cell.
8. Use version history if the formula recently changed.

**Escalation:**

Ask the teacher or file owner to verify the expected formula logic. Contact IT only if Sheets itself is malfunctioning.

**Bot Instruction:** Do not invent grades, calculations, or school reporting formulas.


## Topic: Google Sheets Sort or Filter Changed the Data

**Intent Keywords:** sheet sorted wrong, rows mixed up, filter missing data, spreadsheet order changed, sort one column only

**Direct Answer:**

Sorting only one column can separate data from its related rows. Use version history before making further changes.

**Troubleshooting Steps:**

1. Stop editing the affected sheet.
2. Open **Version history**.
3. Compare the sheet before and after the sort.
4. Restore the correct version only after confirming it.
5. When sorting again, select the complete data range.
6. Use **Data → Sort range** or a filter view.
7. Confirm that headers are recognized.

**Escalation:**

Contact the file owner or teacher before restoring a shared gradebook, roster, or official spreadsheet.

**Bot Instruction:** Treat gradebooks, rosters, and administrative spreadsheets as sensitive records.


## Topic: Google Sheets Protected Range or Cell Cannot Be Edited

**Intent Keywords:** protected range, cannot edit cell, locked spreadsheet cell, sheet permission, warning when editing cell

**Direct Answer:**

The owner may have protected the cell, range, or sheet.

**Troubleshooting Steps:**

1. Confirm that the correct school account is active.
2. Check whether other cells can be edited.
3. Read the protection warning.
4. Ask the file owner whether the range should be editable.
5. Request the correct access if needed.

**Escalation:**

Contact the teacher or file owner. Contact IT only if the owner cannot manage the protection settings.

**Bot Instruction:** Do not advise bypassing protected ranges.


## Topic: Large Google Sheet Is Slow or Read-Only

**Intent Keywords:** large google sheet slow, sheet read only, spreadsheet too large, sheets freezing, too many cells, loading slowly

**Direct Answer:**

A very large spreadsheet, complex formulas, images, or many browser extensions can reduce performance.

**Troubleshooting Steps:**

1. Close unnecessary browser tabs.
2. Try the sheet in a private browser window.
3. Try another supported browser.
4. Reduce active filters and unnecessary conditional formatting.
5. Avoid applying formulas to entire unused columns.
6. Remove unnecessary images only with owner approval.
7. Split unrelated data into separate files when appropriate.
8. If the file becomes read-only, copy only the needed tabs to a new spreadsheet with owner approval.

**Escalation:**

Contact the file owner or IT Helpdesk before restructuring a shared school spreadsheet.

**Bot Instruction:** Do not alter an official gradebook, finance file, roster, or reporting sheet without authorization.


## Topic: Open or Convert Microsoft Office Files

**Intent Keywords:** word file in google docs, excel file in sheets, powerpoint in slides, docx xlsx pptx, office file conversion

**Direct Answer:**

Google Drive can open many Word, Excel, and PowerPoint files, but some formatting or advanced features may change.

**Troubleshooting Steps:**

1. Upload the Office file to Google Drive.
2. Open it with Google Docs, Sheets, or Slides.
3. Confirm whether it remains an Office file or is converted to Google format.
4. Compare fonts, page layout, formulas, charts, animations, and speaker notes.
5. Keep the original file until the converted version is verified.
6. Download a test copy in the required format before submitting it.

**Escalation:**

Contact the teacher or IT Helpdesk if a required feature or formatting element is lost.

**Bot Instruction:** Do not overwrite or delete the original Office file during testing.


## Topic: Google Slides Will Not Present

**Intent Keywords:** slides not presenting, slideshow not working, present button issue, presentation full screen, second display slides

**Direct Answer:**

Check the browser, pop-up permissions, display selection, and presentation mode.

**Troubleshooting Steps:**

1. Reload the presentation.
2. Try **Slideshow** again.
3. Allow the presentation window if the browser blocks a pop-up.
4. Confirm that the correct monitor or projector is selected.
5. Try presenting in the current tab.
6. Try another supported browser.
7. Restart the browser if presentation mode remains stuck.

**Escalation:**

Contact the IT Helpdesk if the projector, external display, or classroom presentation system is not working.

**Bot Instruction:** Do not change display-driver or administrator settings.


## Topic: Video or Audio Does Not Play in Google Slides

**Intent Keywords:** slides video not playing, youtube video blocked, audio not working slides, presentation media error

**Direct Answer:**

The media may require internet access, sharing permission, browser audio permission, or an approved source.

**Troubleshooting Steps:**

1. Confirm that the internet connection works.
2. Open the video or audio directly.
3. Confirm that the media file is shared with the audience.
4. Check the computer volume and selected output device.
5. Try presenting in Chrome or another supported browser.
6. Confirm that the video source is allowed by school filtering.
7. Test the presentation before class.

**Escalation:**

Contact the IT Helpdesk if approved school media is blocked or unavailable.

**Bot Instruction:** Do not suggest bypassing school filtering or copyright restrictions.


## Topic: Google Slides Formatting Changed

**Intent Keywords:** slides formatting wrong, powerpoint layout changed, fonts missing slides, images moved, presentation looks different

**Direct Answer:**

Formatting may change after converting between Google Slides and PowerPoint or when a font is unavailable.

**Troubleshooting Steps:**

1. Confirm the file format.
2. Check whether the required fonts are available.
3. Review slide size and theme.
4. Compare the file with the original version.
5. Use version history to review recent changes.
6. Keep the original PowerPoint file until the Slides version is verified.
7. Export a test copy and review it before presenting.

**Escalation:**

Contact the teacher or IT Helpdesk if a required template or presentation format is damaged.

**Bot Instruction:** Do not delete the original presentation during conversion.


## Topic: Google Calendar Invitation Is Missing

**Intent Keywords:** calendar invite missing, meeting invitation not received, event invite not showing, google calendar invitation, classroom calendar invite

**Direct Answer:**

The invitation may be in Gmail, Spam, or waiting for confirmation because the organizer is unfamiliar.

**Troubleshooting Steps:**

1. Search Gmail for the organizer or event title.
2. Check Spam.
3. Open Google Calendar and search for the event.
4. Check whether the event appears as an unconfirmed invitation.
5. Confirm that the organizer used the correct school email address.
6. Ask the organizer to resend the invitation.
7. Confirm that the correct Google account is active.

**Escalation:**

Contact the organizer first. Contact the IT Helpdesk if invitations from multiple organizers are missing.

**Bot Instruction:** Do not create or accept an event on behalf of the user.


## Topic: Calendar Event Is Missing or on the Wrong Calendar

**Intent Keywords:** calendar event missing, event disappeared, wrong calendar, cannot see event, meeting not on calendar

**Direct Answer:**

The event may be on another calendar, hidden, declined, deleted, or created under another Google account.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Check the calendar list on the left.
3. Ensure the relevant calendar is selected and visible.
4. Search for the event title.
5. Check declined events if applicable.
6. Ask the organizer whether the event was changed or cancelled.

**Escalation:**

Contact the organizer or calendar owner. Contact IT if the entire school calendar is missing.

**Bot Instruction:** Do not restore, move, or recreate official school events without authorization.


## Topic: Google Calendar Notifications Are Not Arriving

**Intent Keywords:** calendar notification missing, event reminder not working, no calendar email, no meeting reminder

**Direct Answer:**

Notification settings can be configured per calendar and per event.

**Troubleshooting Steps:**

1. Open Google Calendar settings.
2. Select the affected calendar.
3. Review event notifications and all-day event notifications.
4. Open the specific event and review its notification settings.
5. Check Gmail Spam and notification settings.
6. On mobile, confirm that Calendar notifications are allowed.
7. Confirm that battery-saving settings are not delaying the app.

**Escalation:**

Contact the IT Helpdesk if notifications fail across devices or school policy settings appear to be missing.

**Bot Instruction:** Do not promise that every event generates an email notification.


## Topic: Google Calendar Shows the Wrong Time

**Intent Keywords:** calendar wrong time, meeting one hour off, timezone wrong, event time incorrect, daylight saving calendar

**Direct Answer:**

Check the time zone in Google Calendar and on the device.

**Troubleshooting Steps:**

1. Confirm the device date, time, and time zone.
2. Open Google Calendar settings.
3. Review the primary time zone.
4. Open the event and check its time zone.
5. Confirm the organizer's time zone.
6. Reload Calendar after correcting the settings.

**Escalation:**

Contact the organizer if only one event is incorrect. Contact IT if the managed device time cannot be corrected.

**Bot Instruction:** Do not change the time of an official school event without organizer approval.


## Topic: Share a Google Calendar

**Intent Keywords:** share calendar, calendar permission, colleague cannot see calendar, make calendar visible, school calendar sharing

**Direct Answer:**

Calendar sharing may be limited by school policy and should use the minimum necessary permission.

**Approved Steps:**

1. Open Google Calendar settings.
2. Select the calendar.
3. Open **Share with specific people or groups**.
4. Add the approved school email address.
5. Choose the minimum required permission.
6. Confirm the recipient can see the calendar.

**Escalation:**

Contact the IT Helpdesk if external sharing or organization-wide sharing is restricted.

**Bot Instruction:** Do not recommend making a school calendar public when it contains private or internal information.


## Topic: Duplicate Google Calendar Events

**Intent Keywords:** duplicate calendar events, event appears twice, repeated invitations, calendar sync duplicates

**Direct Answer:**

Duplicates may come from multiple calendars, repeated imports, or duplicate subscriptions.

**Troubleshooting Steps:**

1. Open one duplicate and identify its calendar.
2. Compare the organizer and event details.
3. Hide one calendar temporarily to see whether the duplicate disappears.
4. Check for duplicate calendar subscriptions.
5. Do not delete both copies until the source is confirmed.
6. If duplicates came from an import, stop repeating the import.

**Escalation:**

Contact the calendar owner or IT Helpdesk if duplicates affect many events or users.

**Bot Instruction:** Do not mass-delete calendar events.


## Topic: Cannot Sign In to Google Classroom

**Intent Keywords:** classroom login not working, cannot sign in classroom, wrong classroom account, school classroom access

**Direct Answer:**

Use the school Google account assigned to Classroom.

**Troubleshooting Steps:**

1. Open Classroom in a private browser window.
2. Sign in with the full school email address.
3. Confirm that a personal Gmail account is not active.
4. Confirm that the internet connection works.
5. Try Gmail or Drive with the same school account.
6. If the password is rejected, stop repeated attempts.

**Escalation:**

Visit the IT Helpdesk for password or account access problems. Contact the teacher if Classroom has not been activated for the class.

**Bot Instruction:** Do not offer self-service password reset.


## Topic: Google Classroom Class Code Does Not Work

**Intent Keywords:** classroom code not working, invalid class code, cannot join class, class invitation missing, lost class code

**Direct Answer:**

Confirm the account, code, and whether the teacher has reset or disabled the code.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Re-enter the class code exactly.
3. Remove spaces before or after the code.
4. Confirm that the code came from the correct teacher.
5. Check Gmail for a class invitation.
6. Ask the teacher whether the code was reset.
7. Remember that a class code is normally needed only once.

**Escalation:**

Ask the teacher for a new code or invitation.

**Bot Instruction:** Do not invent a class code or add the student to a class.


## Topic: Google Classroom Class Is Missing

**Intent Keywords:** classroom class missing, course disappeared, cannot see class, archived class, wrong classroom

**Direct Answer:**

The class may be archived, joined under another account, or the user may not be enrolled.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Refresh Classroom.
3. Check **Archived classes**.
4. Search Gmail for the original class invitation.
5. Ask the teacher whether the class was archived or recreated.
6. Ask the teacher to confirm enrolment.

**Escalation:**

Contact the teacher first. Contact the IT Helpdesk if the teacher confirms the student is enrolled but the class remains missing.

**Bot Instruction:** Do not enroll users, unarchive classes, or change class membership.


## Topic: Google Classroom Assignment Is Missing

**Intent Keywords:** classroom assignment missing, cannot find homework, classwork not showing, assignment disappeared

**Direct Answer:**

The assignment may be in another topic, scheduled for later, returned, deleted, or not assigned to the user.

**Troubleshooting Steps:**

1. Confirm that the correct school account and class are open.
2. Open the **Classwork** tab.
3. Check the relevant topic.
4. Check **To-do**.
5. Review the due date.
6. Refresh Classroom.
7. Ask the teacher whether the assignment was published and assigned to the student.

**Escalation:**

Contact the teacher if the assignment is not published or assigned. Contact IT only if classmates can see it but the user cannot.

**Bot Instruction:** Do not create, publish, or change an assignment.


## Topic: Cannot Turn In a Google Classroom Assignment

**Intent Keywords:** turn in button not working, cannot submit classroom, assignment upload error, classroom submit failed, mark as done

**Direct Answer:**

Confirm that the correct account is active, the attachment is ready, and the assignment still accepts submissions.

**Troubleshooting Steps:**

1. Open the assignment from the **Classwork** tab.
2. Confirm that the work is attached.
3. Wait for uploads to finish.
4. Confirm that the assignment is not already turned in.
5. If an assigned copy is broken, save the work before removing it.
6. Try attaching a fresh copy when permitted.
7. Try Classroom in a private browser window.
8. Record the exact error message.

**Escalation:**

Tell the teacher immediately if the deadline is near or the Turn in button fails. Contact IT for a repeatable technical error.

**Bot Instruction:** Do not claim that work was submitted unless Classroom shows a successful submission.


## Topic: Classroom Attachment Will Not Open or Make a Copy

**Intent Keywords:** classroom attachment not opening, make a copy failed, assigned document broken, classroom file access denied

**Direct Answer:**

The attachment may have incorrect sharing permissions or the assigned copy may not have been created correctly.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Open the assignment from Classroom, not an old bookmark.
3. Try opening the attachment in a private browser window.
4. Check whether the file says **Request access**.
5. Save any work before removing a broken attachment.
6. Ask the teacher whether each student should receive a copy.
7. Do not edit the teacher's original file unless instructed.

**Escalation:**

Contact the teacher first. Contact IT if the teacher confirms the permissions are correct.

**Bot Instruction:** Do not alter the teacher's original attachment or sharing settings.


## Topic: Classroom Grade, Due Date, Feedback, or Comment Issue

**Intent Keywords:** classroom grade wrong, due date wrong, comment missing, teacher feedback, assignment marked late, grade not showing

**Direct Answer:**

Grades, due dates, feedback, and assignment status are controlled by the teacher.

**Troubleshooting Steps:**

1. Confirm that the correct class and assignment are open.
2. Refresh Classroom.
3. Check whether the assignment was returned.
4. Review private comments and teacher feedback.
5. Confirm the submission time shown by Classroom.
6. Contact the teacher with the assignment name and date.

**Escalation:**

Contact the teacher for grade, due-date, late-status, feedback, or content questions. Contact IT only if the page displays a technical error.

**Bot Instruction:** Do not change, interpret, dispute, or guess grades.


## Topic: Teacher Cannot Create a Class or Has the Wrong Classroom Role

**Intent Keywords:** cannot create classroom, teacher shown as student, wrong classroom role, create class missing

**Direct Answer:**

Class creation and teacher/student roles may be controlled by the Google Workspace administrator.

**Troubleshooting Steps:**

1. Confirm that the correct school account is active.
2. Sign out and back in.
3. Check whether **Create class** is available.
4. Confirm whether the user accidentally selected the student role.
5. Record the affected account and class.

**Escalation:**

Contact the IT Helpdesk. Only an authorized Classroom administrator can change the role or related settings.

**Bot Instruction:** Do not claim to change a Classroom role or enable class creation.


## Topic: Classroom Notifications Are Missing

**Intent Keywords:** classroom emails missing, no assignment notification, classroom notification not received, guardian summary missing

**Direct Answer:**

Classroom email notifications depend on account settings, class activity, and school configuration.

**Troubleshooting Steps:**

1. Open Classroom settings.
2. Review email notification preferences.
3. Check Gmail Spam and All Mail.
4. Confirm that Gmail is available for the school account.
5. Confirm that notifications are enabled for the relevant class.
6. For guardian summaries, ask the school or teacher to verify the invitation and email address.

**Escalation:**

Contact the teacher for class activity questions. Contact IT if account-wide Classroom notifications fail.

**Bot Instruction:** Do not promise that every class action creates an email.


## Topic: Google Meet Camera Is Not Working

**Intent Keywords:** meet camera not working, webcam blocked, video black, camera permission google meet

**Direct Answer:**

Confirm that Meet and the browser have permission to use the camera and that another application is not using it.

**Troubleshooting Steps:**

1. Close other applications that may use the camera.
2. Open Google Meet.
3. Check the camera permission in the browser address bar.
4. Allow camera access for Meet.
5. In Meet settings, select the correct camera.
6. Turn the camera off and back on.
7. Reload Meet.
8. Restart the browser or device if needed.

**Escalation:**

Contact the IT Helpdesk if no application can use the camera or the managed permission cannot be changed.

**Bot Instruction:** Do not advise disabling school device security or privacy controls.


## Topic: Google Meet Microphone Is Not Working

**Intent Keywords:** meet microphone not working, mic blocked, no one can hear me, google meet audio input

**Direct Answer:**

Check browser permission, the selected microphone, mute status, and whether another application is using the microphone.

**Troubleshooting Steps:**

1. Confirm that the Meet microphone button is not muted.
2. Close other applications using the microphone.
3. Check microphone permission in the browser address bar.
4. In Meet settings, select the correct microphone.
5. Speak and watch the input-level indicator.
6. Reload Meet.
7. Reconnect a headset if one is being used.
8. Restart the browser or device.

**Escalation:**

Contact the IT Helpdesk if the microphone fails in all applications.

**Bot Instruction:** Do not change operating-system privacy settings beyond normal user-accessible permissions.


## Topic: Cannot Hear Other People in Google Meet

**Intent Keywords:** meet no sound, cannot hear meeting, speakers not working meet, google meet audio output

**Direct Answer:**

Check the device volume, output device, browser tab audio, and Meet speaker selection.

**Troubleshooting Steps:**

1. Confirm that the device is not muted.
2. Increase the volume.
3. Check whether the browser tab is muted.
4. In Meet settings, select the correct speaker.
5. Disconnect unused Bluetooth or external audio devices.
6. Test another approved headset or speaker.
7. Reload Meet.
8. Restart the browser if needed.

**Escalation:**

Contact the IT Helpdesk if sound fails in Meet and other applications.

**Bot Instruction:** Do not assume the problem is Meet if all device audio is unavailable.


## Topic: Cannot Join a Google Meet

**Intent Keywords:** cannot join google meet, ask to join stuck, meet link not working, not allowed meeting, waiting to be admitted

**Direct Answer:**

Confirm the correct school account, meeting link, time, and whether the host must admit the user.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Reopen the current meeting link.
3. Check the event date and time.
4. Ask the organizer whether the meeting has started.
5. Wait for the host to admit you if required.
6. Try Meet in a private browser window.
7. Try another supported browser.
8. Record the exact error.

**Escalation:**

Contact the meeting organizer first. Contact IT if valid school meetings fail repeatedly.

**Bot Instruction:** Do not bypass host controls or create replacement meetings without authorization.


## Topic: Cannot Share Screen in Google Meet

**Intent Keywords:** meet screen share not working, present now missing, cannot present, share tab, share screen permission

**Direct Answer:**

Screen sharing may be limited by browser permission, operating-system privacy settings, host controls, or school policy.

**Troubleshooting Steps:**

1. Confirm that the meeting host allows presenting.
2. Select **Present now**.
3. Choose a tab, window, or screen.
4. Grant screen-recording permission if the device asks.
5. If sharing video audio, present a browser tab and enable tab audio when available.
6. Close confidential windows before sharing.
7. Rejoin the meeting after changing a required permission.

**Escalation:**

Contact the host or IT Helpdesk if presenting is disabled by policy or managed settings.

**Bot Instruction:** Warn users not to expose confidential student or staff information while sharing.


## Topic: External Guest Cannot Join School Google Meet

**Intent Keywords:** external guest cannot join meet, parent stuck ask to join, outside domain meet, guest admission problem

**Direct Answer:**

External participants may need the meeting creator to be present and approve the join request.

**Troubleshooting Steps:**

1. Confirm that the external guest has the correct link.
2. Confirm that the meeting has started.
3. Ask the meeting creator to remain in the meeting.
4. Ask the creator to watch for the admission request.
5. Confirm that external guests are permitted by school policy.
6. Try the link in a supported browser.

**Escalation:**

Contact the meeting organizer or IT Helpdesk if an approved external guest cannot join.

**Bot Instruction:** Do not change external-access policy or claim that all external guests are allowed.


## Topic: Google Meet Recording Is Unavailable

**Intent Keywords:** cannot record meet, recording option missing, meet recording not available, teacher recording

**Direct Answer:**

Recording availability depends on the account edition, user role, meeting type, and school policy.

**Troubleshooting Steps:**

1. Confirm that the correct school account is active.
2. Confirm that the user is the host or an approved co-host.
3. Check whether the meeting type supports recording.
4. Ask the school whether recording is enabled.
5. Do not use third-party recording tools without approval.

**Escalation:**

Contact the IT Helpdesk or school administrator for recording-policy questions.

**Bot Instruction:** Do not recommend bypassing recording restrictions or recording students without authorization.


## Topic: Google Form Will Not Open

**Intent Keywords:** google form not opening, form access denied, survey not loading, quiz link not working

**Direct Answer:**

The form may require the school account, may be closed, or may be restricted to approved users.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Open the current form link.
3. Try the link in a private browser window.
4. Confirm that the form is still accepting responses.
5. Check whether the form is restricted to the school organization.
6. Ask the form owner whether the link is correct.

**Escalation:**

Contact the teacher or form owner first. Contact IT if valid school forms fail across browsers.

**Bot Instruction:** Do not bypass sign-in or organization restrictions.


## Topic: Google Form Will Not Submit

**Intent Keywords:** form submit not working, quiz submission failed, response not recorded, google form error

**Direct Answer:**

Confirm that all required questions are complete and that file uploads have finished.

**Troubleshooting Steps:**

1. Review the form for unanswered required questions.
2. Check for validation errors.
3. Wait for file uploads to finish.
4. Confirm that the internet connection is stable.
5. Try the form in a private browser window.
6. Confirm that the form is still accepting responses.
7. Take a screenshot of the error without showing private answers.

**Escalation:**

Contact the teacher or form owner immediately if the form has a deadline. Contact IT for repeatable technical errors.

**Bot Instruction:** Do not claim that a response was submitted unless the confirmation page appears.


## Topic: Google Forms File Upload Does Not Work

**Intent Keywords:** forms file upload failed, cannot attach file form, upload question not working, google form attachment

**Direct Answer:**

File-upload questions usually require the correct school account, an allowed file type, enough storage, and permission from the form owner.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Check the allowed file type and size.
3. Rename the file using a short name.
4. Confirm that the upload is complete.
5. Try a smaller approved file.
6. Try the form in a private browser window.
7. Ask the form owner whether uploads are enabled.

**Escalation:**

Contact the teacher or form owner. Contact IT if approved uploads fail for multiple users.

**Bot Instruction:** Do not advise uploading school files to personal storage as a workaround.


## Topic: Google Forms Responses Are Missing

**Intent Keywords:** forms responses missing, teacher cannot see response, quiz answer missing, response spreadsheet not updating

**Direct Answer:**

Confirm the form, response destination, account, and whether responses are still being accepted.

**Troubleshooting Steps:**

1. Confirm that the correct form is open.
2. Open the **Responses** tab.
3. Check whether responses are enabled.
4. Confirm the linked spreadsheet.
5. Check whether a filter view hides rows.
6. Confirm that the respondent saw a submission confirmation.
7. Review the form activity and ownership.

**Escalation:**

Contact the form owner or IT Helpdesk if confirmed submissions are missing.

**Bot Instruction:** Do not invent responses, alter quiz results, or change grades.


## Topic: School Google Group Email Is Not Received

**Intent Keywords:** google group email missing, mailing list message missing, school group not receiving, distribution list email

**Direct Answer:**

The user may not be a member, the message may be moderated, or Gmail may have filtered it.

**Troubleshooting Steps:**

1. Search Gmail for the group address or subject.
2. Check Spam and All Mail.
3. Confirm the exact group email address.
4. Ask the group owner to confirm membership.
5. Ask whether the message is awaiting moderation.
6. Confirm that the sender is allowed to post.

**Escalation:**

Contact the group owner or IT Helpdesk for membership and posting permissions.

**Bot Instruction:** Do not add users to groups or change group settings.


## Topic: Cannot Send to a School Google Group

**Intent Keywords:** cannot email group, posting not allowed, message rejected group, distribution list blocked

**Direct Answer:**

Posting permissions may be limited to group members, staff, owners, or approved senders.

**Troubleshooting Steps:**

1. Confirm the group address.
2. Confirm that the school account is active.
3. Read any rejection message.
4. Check whether the sender is a group member.
5. Try a short message without an attachment.
6. Ask the group owner whether posting is restricted.

**Escalation:**

Contact the group owner or IT Helpdesk with the exact rejection message.

**Bot Instruction:** Do not bypass posting restrictions or reveal private group membership.


## Topic: Google Chat Is Missing or Unavailable

**Intent Keywords:** google chat missing, cannot use google chat, chat disabled, spaces unavailable, school chat not working

**Direct Answer:**

Google Chat availability, external messaging, and Spaces features may be controlled by school policy.

**Troubleshooting Steps:**

1. Confirm that the correct school account is active.
2. Open Gmail and check whether Chat is visible.
3. Try the standalone Google Chat page.
4. Refresh the browser.
5. Try a private browser window.
6. Confirm whether classmates or colleagues have the same access.

**Escalation:**

Contact the IT Helpdesk if Chat is required but unavailable.

**Bot Instruction:** Do not advise using an unapproved personal messaging service for school communication.


## Topic: Google Workspace Mobile App Is Not Syncing

**Intent Keywords:** gmail app not syncing, drive mobile not updating, calendar app sync, classroom app not working, google app mobile issue

**Direct Answer:**

Check the connection, active account, app version, notification permission, and available device storage.

**Troubleshooting Steps:**

1. Confirm that Wi-Fi or mobile data works.
2. Confirm that the school account is selected.
3. Refresh the application.
4. Close and reopen the application.
5. Update the application.
6. Restart the phone or tablet.
7. Check device storage.
8. Confirm that background data and notifications are allowed when required.

**Escalation:**

Contact the IT Helpdesk before removing a managed school account or device profile.

**Bot Instruction:** Do not advise deleting a managed profile or bypassing mobile-device management.


## Topic: Google Workspace Feature Is Missing or Restricted

**Intent Keywords:** feature missing google, option unavailable, cannot share externally, recording disabled, app not enabled, permission denied school google

**Direct Answer:**

Some Google Workspace features are controlled by school licensing, age settings, organizational units, security policy, or administrator configuration.

**Troubleshooting Steps:**

1. Confirm that the correct school account is active.
2. Confirm the expected role, class, group, or department.
3. Try the feature in a private browser window.
4. Ask whether another authorized user has the feature.
5. Record the exact missing option or error.
6. Do not use a personal account to bypass the restriction.

**Escalation:**

Contact the IT Helpdesk or the appropriate school administrator.

**Bot Instruction:** Do not promise that a restricted feature can be enabled.


## Topic: Lost or Stolen Device with School Google Account

**Intent Keywords:** lost laptop google account, stolen phone school gmail, device missing, sign out school account remotely

**Direct Answer:**

Report a lost or stolen device immediately so the school can protect the account and device.

**Approved Steps:**

1. Contact the IT Helpdesk immediately.
2. Provide the device type, asset tag if known, and last known location.
3. Do not share the account password.
4. Follow school reporting procedures.
5. If instructed by IT, change credentials through the approved school process.

**Escalation:**

This issue requires immediate IT Helpdesk involvement.

**Bot Instruction:** Do not attempt remote-wipe, tracking, password reset, or account suspension unless an approved administrator tool confirms the action.


## Topic: Google Workspace Issue Is Still Not Resolved

**Intent Keywords:** google still not working, same google issue, workspace problem continues, gmail still broken, drive still broken, classroom still broken

**Direct Answer:**

The approved troubleshooting steps did not resolve the issue.

**Escalation:**

Contact or visit the IT Helpdesk with:

- The affected Google service
- The school email address
- The device and browser
- The exact error message
- The approximate time
- Whether other users are affected
- A screenshot that does not expose private student or staff information

**Bot Instruction:** Do not repeat the same troubleshooting loop. Escalate after the approved steps fail.

## Topic: Create a New Google Form

**Intent Keywords:** create google form, make a form, new survey, create questionnaire, create school form, make registration form

**Direct Answer:**

You can create a Google Form from Google Drive or from the Google Forms home page.

**Approved Steps:**

1. Confirm that the school Google account is active.
2. Open Google Drive.
3. Select **New**.
4. Select **More → Google Forms**.
5. Choose a blank form or an approved school template.
6. Enter a clear form title and description.
7. Add the required questions.
8. Select the Preview icon to test the form before sharing it.

**Escalation:**

Contact the IT Helpdesk if Google Forms is unavailable for the school account or creation is restricted.

**Bot Instruction:** Do not create forms that collect confidential student, medical, financial, password, or authentication information without school approval.

## Topic: Add, Duplicate, Delete, or Reorder Questions in Google Forms

**Intent Keywords:** add form question, duplicate form question, move form question, reorder questions, delete form question, change question order

**Direct Answer:**

Questions can be added, duplicated, removed, and dragged into a different order from the form editor.

**Approved Steps:**

1. Open the form in editing mode.
2. Select the **Add question** button to create a new question.
3. Enter the question text.
4. Select the question-type menu and choose the required format.
5. Use **Duplicate** when creating a similar question.
6. Use the Delete icon only after confirming that the question is no longer needed.
7. To reorder questions, drag the question using the move handle at the top.
8. Preview the form after making changes.

**Escalation:**

Contact the form owner if editing controls are unavailable.

**Bot Instruction:** Warn the user that deleting a question may also affect how existing responses are interpreted.

## Topic: Choose the Correct Google Forms Question Type

**Intent Keywords:** form question type, short answer, paragraph question, multiple choice, checkboxes, dropdown, linear scale, question grid, date question, time question

**Direct Answer:**

Choose the question type that best matches the information being collected.

**Question Types:**

* **Short answer:** A name, ID, title, or brief response.
* **Paragraph:** Comments, explanations, reflections, or longer written answers.
* **Multiple choice:** One answer from a short list of options.
* **Checkboxes:** More than one answer can be selected.
* **Dropdown:** One answer from a longer list while saving screen space.
* **Linear scale:** A rating, such as 1 to 5.
* **Multiple-choice grid:** One response per row across a common set of columns.
* **Checkbox grid:** Multiple selections may be permitted in each row.
* **Date:** A date in a consistent format.
* **Time:** A specific time or duration.
* **File upload:** Allows an approved user to attach a file.

**Approved Steps:**

1. Select the question.
2. Open the question-type menu.
3. Choose the appropriate type.
4. Add answer options when required.
5. Enable **Required** only when the respondent must answer.
6. Preview and test the question.

**Escalation:**

Ask the teacher or form owner if the intended response format is unclear.

**Bot Instruction:** Recommend collecting only the minimum student or staff information required.

## Topic: Make a Google Forms Question Required

**Intent Keywords:** required form question, mandatory question, red star form, users skipping question, form question must be answered

**Direct Answer:**

Enable the **Required** setting when respondents must answer a question before continuing or submitting.

**Approved Steps:**

1. Open the form in editing mode.
2. Select the question.
3. Locate the **Required** toggle at the bottom of the question.
4. Turn it on.
5. Preview the form.
6. Confirm that the question displays a required indicator.
7. Test that the form prevents submission when the question is unanswered.

**Escalation:**

Contact the form owner if the Required setting cannot be changed.

**Bot Instruction:** Do not make sensitive or unnecessary personal-information questions required.

## Topic: Add Titles and Sections to a Google Form

**Intent Keywords:** form section, add page to form, split google form, form title block, organize long form, multi page form

**Direct Answer:**

A title organizes content on the current page, while a section normally creates another page in the form.

**Approved Steps:**

1. Open the form in editing mode.
2. Use **Add title and description** to label content on the current page.
3. Use **Add section** to create a new form page.
4. Enter a clear section name and description.
5. Drag sections or questions to arrange them.
6. Select **Preview**.
7. Test the **Next**, **Back**, and **Submit** buttons.
8. Confirm that all required questions behave correctly.

**Escalation:**

Contact the form owner if sections are controlled by conditional navigation that you do not understand.

**Bot Instruction:** Do not change section-routing logic on an active school form without owner approval.

## Topic: Preview and Test a Google Form Before Sharing

**Intent Keywords:** preview google form, test form, check form before sending, eye icon form, form preview

**Direct Answer:**

Always preview and submit a test response before distributing a school form.

**Approved Steps:**

1. Open the form in editing mode.
2. Select the Preview icon.
3. Confirm that the title and instructions are clear.
4. Check required questions.
5. Test every section.
6. Test file-upload questions when applicable.
7. Submit one approved test response.
8. Confirm that the response appears correctly.
9. Remove the test response only if the form owner approves.

**Escalation:**

Contact the IT Helpdesk if the preview works but the shared form does not.

**Bot Instruction:** Do not use real confidential student data for testing.

## Topic: Link Google Forms Responses to a Google Sheet

**Intent Keywords:** link form to sheet, form response spreadsheet, responses not in sheets, create response sheet, form data spreadsheet

**Direct Answer:**

A form owner can connect responses to a new or existing Google Sheet.

**Approved Steps:**

1. Open the form.
2. Select the **Responses** tab.
3. Select the Google Sheets icon or the response-destination option.
4. Choose **Create a new spreadsheet** or an approved existing spreadsheet.
5. Confirm the spreadsheet name and location.
6. Submit a test response.
7. Open the linked spreadsheet.
8. Confirm that the response appears with a timestamp.

**Escalation:**

Contact the form owner or IT Helpdesk if the response destination is missing, inaccessible, or owned by the wrong account.

**Bot Instruction:** Do not connect school-response data to a personal Google account or an unauthorized spreadsheet.

## Topic: View Google Forms Response Summaries and Individual Responses

**Intent Keywords:** view form responses, response summary, individual response, google form results, form charts, see submissions

**Direct Answer:**

Form owners can view response summaries, individual submissions, and linked spreadsheet data.

**Approved Steps:**

1. Open the form.
2. Select **Responses**.
3. Use **Summary** to view charts and combined results.
4. Use **Question** to review answers grouped by question when available.
5. Use **Individual** to review one submission at a time.
6. Use the navigation controls to move between submissions.
7. Open the linked Google Sheet for sorting or approved analysis.
8. Protect any student or staff response information.

**Escalation:**

Contact the form owner if responses are unavailable or the user does not have permission.

**Bot Instruction:** Do not display, summarize, or disclose confidential form responses to unauthorized users.

## Topic: Stop or Restart Google Forms Responses

**Intent Keywords:** stop accepting form responses, close google form, reopen form, form no longer accepting, disable submissions

**Direct Answer:**

The form owner can temporarily stop or restart response collection.

**Approved Steps:**

1. Open the form.
2. Select **Responses**.
3. Locate **Accepting responses**.
4. Turn it off to close submissions.
5. Add a clear closed-form message when available.
6. Turn it back on only when the form should reopen.
7. Test the respondent link after changing the setting.

**Escalation:**

Contact the form owner if the form was closed unexpectedly.

**Bot Instruction:** Do not reopen an assessment, registration, or official school form without owner approval.

## Topic: Google Forms Email Notifications for New Responses

**Intent Keywords:** form response email notification, notify me when form submitted, forms email alerts, new response notification

**Direct Answer:**

A form owner can enable email notifications when new responses are submitted.

**Approved Steps:**

1. Open the form.
2. Select **Responses**.
3. Open the response options menu.
4. Enable email notifications for new responses.
5. Submit an approved test response.
6. Confirm that the notification arrives.
7. Check Gmail Spam if it is missing.

**Escalation:**

Contact the IT Helpdesk if form notifications are enabled but consistently fail.

**Bot Instruction:** Do not promise immediate delivery of every notification.

## Topic: Download or Unlink Google Forms Responses

**Intent Keywords:** download form responses, csv form responses, unlink form sheet, disconnect spreadsheet, export form data

**Direct Answer:**

Form owners may download responses as a CSV file or disconnect the linked spreadsheet.

**Approved Steps:**

1. Open the form.
2. Select **Responses**.
3. Open the response options menu.
4. Choose the approved download or unlink action.
5. Store exported data only in an approved school location.
6. Confirm the correct form before unlinking its spreadsheet.
7. Remember that unlinking does not automatically delete existing spreadsheet data.

**Escalation:**

Contact the form owner or IT Helpdesk before exporting sensitive student or staff data.

**Bot Instruction:** Do not email or store confidential response exports in personal accounts or unapproved locations.

## Topic: Delete Google Forms Responses Safely

**Intent Keywords:** delete form response, remove test response, delete all form answers, clear form submissions

**Direct Answer:**

Deleting responses can be permanent and should be done only by the form owner or an authorized user.

**Approved Steps:**

1. Confirm the correct form.
2. Confirm whether one response or all responses must be removed.
3. Check whether responses are also stored in a linked Google Sheet.
4. Export or retain an approved backup when required.
5. Delete only the intended response.
6. Verify the remaining response count.
7. Remember that deleting a Form response may not remove its row from every previously linked or copied spreadsheet.

**Escalation:**

Contact the form owner before deleting assessment, registration, attendance, or official school responses.

**Bot Instruction:** Never recommend deleting all responses without clear authorization and confirmation.

## Topic: Configure Basic Google Forms Settings

**Intent Keywords:** form settings, collect email addresses, one response, edit response, progress bar, shuffle questions, confirmation message

**Direct Answer:**

Form settings control sign-in requirements, response limits, email collection, presentation, and respondent options.

**Approved Steps:**

1. Open the form.
2. Open **Settings**.
3. Review whether email addresses should be collected.
4. Decide whether respondents may receive response copies.
5. Enable one-response limits only when appropriate.
6. Decide whether respondents may edit submitted responses.
7. Add a progress bar for longer multi-section forms.
8. Use question shuffling only when question order is not important.
9. Add a clear confirmation message.
10. Test all settings with an approved account.

**Escalation:**

Contact the teacher, form owner, or IT Helpdesk if organization restrictions prevent a required setting.

**Bot Instruction:** Do not disable school-required sign-in, privacy, or organization restrictions.

## Topic: Share or Send a Google Form

**Intent Keywords:** share google form, send form link, email form, copy form link, embed form, add form collaborator

**Direct Answer:**

Forms can be distributed by email, an approved link, or an approved school webpage.

**Approved Steps:**

1. Open the form.
2. Select **Send** or the current publishing control.
3. Choose email or link sharing.
4. Confirm whether school-account sign-in is required.
5. Copy the respondent link, not the editing link.
6. Test the link in a private browser window.
7. Share it only with the intended audience.
8. Add collaborators separately and grant only the required editing permission.

**Escalation:**

Contact the IT Helpdesk if external respondents need access but organization policy blocks them.

**Bot Instruction:** Do not publish student-data collection forms publicly without authorization. Never share the form-editing link with respondents.

## Topic: Create a Quiz in Google Forms

**Intent Keywords:** make google forms quiz, answer key, quiz points, automatic grading, create classroom quiz

**Direct Answer:**

A form owner can turn a Google Form into a quiz and assign answers, points, and feedback.

**Approved Steps:**

1. Open the form.
2. Open **Settings**.
3. Enable **Make this a quiz**.
4. Choose whether grades are released immediately or later.
5. Decide what respondents may see after grading.
6. Open each gradable question.
7. Select **Answer key**.
8. Choose the correct answer or answers.
9. Assign the point value.
10. Preview and complete a test submission.

**Escalation:**

Contact the teacher for grading-policy, correct-answer, point-value, or release-time decisions.

**Bot Instruction:** Do not create answer keys, assign grades, or change assessment rules without teacher approval.

## Topic: Add Feedback to a Google Forms Quiz

**Intent Keywords:** quiz answer feedback, google form feedback, feedback for wrong answer, quiz explanation link

**Direct Answer:**

Teachers can add automatic feedback for correct and incorrect quiz responses.

**Approved Steps:**

1. Open the quiz in editing mode.
2. Select the question.
3. Open **Answer key**.
4. Select **Add answer feedback**.
5. Add separate feedback for correct and incorrect responses when appropriate.
6. Add an approved learning-resource link if needed.
7. Save the feedback.
8. Submit a test response and review what the student sees.

**Escalation:**

Contact the teacher if feedback content or answer correctness is uncertain.

**Bot Instruction:** Do not invent instructional feedback or disclose restricted answer keys.

## Topic: Release Google Forms Quiz Scores

**Intent Keywords:** release quiz scores, send google form grades, students cannot see score, release marks, form quiz results

**Direct Answer:**

Quiz scores may be released immediately or later, depending on the teacher's settings.

**Approved Steps:**

1. Open the quiz.
2. Select **Responses**.
3. Review the response summary and individual answers.
4. Manually grade written questions when required.
5. Confirm that the correct respondents are selected.
6. Select the score-release option.
7. Add an approved message if needed.
8. Release scores only after the teacher confirms grading is complete.

**Escalation:**

Contact the teacher for score, answer-key, grading, or release questions.

**Bot Instruction:** Do not release, modify, explain, or dispute student grades without teacher authorization.

## Topic: Manage File Upload Questions in Google Forms

**Intent Keywords:** create file upload form, where form uploads go, uploaded files folder, form owner drive, delete file response

**Direct Answer:**

Files submitted through a file-upload question are stored in the form owner's Google Drive and consume the owner's storage.

**Approved Steps:**

1. Add a **File upload** question.
2. Confirm that respondents must use an approved account.
3. Choose the permitted file types.
4. Set the maximum number and size of files.
5. Submit an approved test file.
6. Open the form's **Responses** section.
7. Open the automatically created response folder in Drive.
8. Confirm that uploaded files are organized under the correct form and question.
9. Monitor the form owner's available storage.

**Important Information:**

* Deleting a Form response may not delete the uploaded file from Drive.
* Uploaded files should be reviewed and deleted separately when permitted.
* File-upload forms should not collect unapproved confidential material.

**Escalation:**

Contact the IT Helpdesk if uploads are stored under the wrong account, exceed school limits, or expose sensitive information.

**Bot Instruction:** Do not advise moving submitted school files to personal storage.

## Topic: Delegate Access to a Google Calendar

**Intent Keywords:** delegate calendar, manage another calendar, assistant calendar access, give calendar permission, manage principal calendar

**Direct Answer:**

A calendar owner can share a calendar with another authorized staff member and choose the appropriate permission.

**Approved Steps:**

1. The calendar owner opens Google Calendar.
2. Open the affected calendar's settings.
3. Open **Share with specific people or groups**.
4. Add the authorized school email address.
5. Choose the minimum required permission:

   * See only free and busy information
   * See event details
   * Make changes to events
   * Make changes and manage sharing
6. Save the sharing change.
7. The delegate confirms that the calendar appears in their calendar list.
8. Use different calendar colours to reduce scheduling mistakes.

**Escalation:**

Contact the IT Helpdesk if delegation is blocked or if highly privileged sharing access is required.

**Bot Instruction:** Calendar delegation may expose private and confidential event details. Do not grant or recommend broad access without authorization.

## Topic: Delegated Google Calendar Is Missing

**Intent Keywords:** manager calendar missing, shared calendar not showing, delegated calendar disappeared, cannot see another calendar

**Direct Answer:**

The delegated calendar may be hidden, unchecked, removed, or shared with the wrong account.

**Troubleshooting Steps:**

1. Confirm that the correct school account is active.
2. Check **My calendars** and **Other calendars**.
3. Ensure the delegated calendar is selected and visible.
4. Refresh Google Calendar.
5. Try Calendar in a private browser window.
6. Ask the calendar owner to verify the shared email address and permission.
7. Remove and re-add access only with the owner's approval.

**Escalation:**

Contact the IT Helpdesk if the sharing permission is correct but the calendar remains unavailable.

**Bot Instruction:** Do not expose event details while testing delegated access.

## Topic: Respond to Invitations on Behalf of Another Calendar Owner

**Intent Keywords:** accept meeting for manager, decline event on behalf, respond delegated calendar, assistant respond calendar invite

**Direct Answer:**

An authorized calendar delegate may respond to invitations from the delegated calendar.

**Approved Steps:**

1. Confirm that the delegated calendar is selected.
2. Open the invitation on that calendar.
3. Verify that you are responding for the correct person.
4. Select **Yes**, **No**, or **Maybe**.
5. Add a response note when appropriate.
6. Save the response.
7. Inform the calendar owner separately when the response is important.

**Escalation:**

Contact the calendar owner if attendance is uncertain.

**Bot Instruction:** Do not accept or decline meetings without authorization from the calendar owner.

## Topic: Create an Event on Behalf of Another Calendar Owner

**Intent Keywords:** create meeting for manager, schedule on delegated calendar, event created on wrong calendar, assistant schedule meeting

**Direct Answer:**

When creating an event, confirm that the delegated calendar—not your own calendar—is selected.

**Approved Steps:**

1. Create a new event.
2. Open the calendar-selection field.
3. Select the correct delegated calendar.
4. Enter the event title, date, time, guests, and location.
5. Add only information that guests are permitted to see.
6. Mark sensitive meetings as private when required.
7. Review the organizer and calendar before saving.
8. Send invitations only after confirming the details.

**Escalation:**

Contact the calendar owner if privacy, guest access, or scheduling authority is unclear.

**Bot Instruction:** Do not place confidential details in the event description when guests should not see them.

## Topic: Receive Notifications for a Shared or Delegated Calendar

**Intent Keywords:** shared calendar notifications, manager calendar alerts, delegated event emails, notifications for another calendar

**Direct Answer:**

Notification settings for a shared calendar are usually controlled separately from the owner's notification settings.

**Approved Steps:**

1. Open Google Calendar.
2. Open the shared calendar's settings.
3. Review event and change notifications.
4. Enable only the notifications required for the user's role.
5. Submit or request an approved test event.
6. Confirm that the notification reaches the delegate.
7. Remember that enabling notifications for yourself may not enable them for the calendar owner.

**Escalation:**

Contact the IT Helpdesk if notifications remain unavailable for a properly shared calendar.

**Bot Instruction:** Do not assume that changing one person's notifications changes another person's settings.

## Topic: Find a Meeting Time for Guests

**Intent Keywords:** find meeting time, check guest availability, schedule staff meeting, calendar free busy, find available time

**Direct Answer:**

Use guest availability to find a time that works before sending the invitation.

**Approved Steps:**

1. Create or open the event.
2. Add the approved guests.
3. Open **Find a time** or the scheduling view.
4. Review available and busy periods.
5. Respect private events that show only free or busy status.
6. Choose an appropriate time.
7. Confirm the time zone.
8. Save and send the invitation.

**Escalation:**

Contact the participants directly if their calendars do not expose availability.

**Bot Instruction:** Do not reveal private event details discovered through elevated calendar access.

## Topic: Book a Room or School Calendar Resource

**Intent Keywords:** book meeting room, reserve classroom calendar, add room to event, room unavailable, calendar resource

**Direct Answer:**

Rooms and approved school resources can be added to Calendar events when configured by the Google Workspace administrator.

**Approved Steps:**

1. Create or open the event.
2. Confirm the date and time.
3. Open the room or resource selection.
4. Search for the room, classroom, projector, or approved resource.
5. Check whether it is available.
6. Add the available resource.
7. Save the event.
8. Confirm that the resource accepted the reservation.

**Escalation:**

Contact the IT Helpdesk or facilities team if the resource is missing, incorrectly configured, or declines every reservation.

**Bot Instruction:** Do not claim that a room is reserved until the resource shows an accepted booking.

## Topic: Create or Edit a Recurring Calendar Event

**Intent Keywords:** repeat calendar event, recurring meeting, weekly event, monthly meeting, change one event, edit series

**Direct Answer:**

Recurring events can repeat daily, weekly, monthly, or according to a custom schedule.

**Approved Steps:**

1. Create or open the event.
2. Select the recurrence setting.
3. Choose the repeat pattern.
4. Add an end date when appropriate.
5. Review the time zone.
6. Save the event.
7. When editing, carefully choose:

   * This event
   * This and following events
   * All events
8. Review guest notifications before confirming the update.

**Escalation:**

Contact the event owner before changing an official recurring school meeting.

**Bot Instruction:** Warn the user before applying a change to an entire recurring series.

## Topic: Update Guests After Changing a Calendar Event

**Intent Keywords:** send calendar update, changed meeting time, guests not notified, event update email, notify attendees

**Direct Answer:**

When an event with guests is changed, Calendar may ask whether updates should be sent.

**Approved Steps:**

1. Open the event.
2. Make the approved change.
3. Review the date, time, room, description, and guests.
4. Save the event.
5. Select the appropriate notification option.
6. Send an update when guests need to know about the change.
7. Confirm that the event displays the new details.

**Escalation:**

Contact the organizer if you are not authorized to notify all guests.

**Bot Instruction:** Do not suppress notifications for important time, room, or cancellation changes.

## Topic: Transfer Ownership of a Google Calendar Event

**Intent Keywords:** change event owner, transfer meeting ownership, new organizer calendar, recurring meeting new owner

**Direct Answer:**

An event organizer may be able to transfer ownership to another approved school account.

**Approved Steps:**

1. Open the event from the current owner's calendar.
2. Open the event options.
3. Select the ownership-transfer option when available.
4. Enter the approved new owner's school email address.
5. Review the notification message.
6. Confirm the transfer.
7. The new owner must accept the transfer when required.
8. Verify that the new owner can edit the event.

**Escalation:**

Contact the IT Helpdesk if ownership transfer is unavailable or crosses school-domain restrictions.

**Bot Instruction:** Do not transfer ownership of official school events without authorization.

## Topic: Google Calendar Is Slow Because Too Many Calendars Are Displayed

**Intent Keywords:** google calendar slow, too many calendars, calendar takes long to load, hide other calendars

**Direct Answer:**

Displaying many shared calendars at the same time can make Calendar slower and harder to read.

**Troubleshooting Steps:**

1. Review the calendars listed on the left.
2. Temporarily hide calendars that are not currently needed.
3. Keep only the required calendars visible.
4. Remove unused calendar subscriptions when permitted.
5. Refresh Calendar.
6. Try a private browser window.
7. Restart the browser if needed.

**Escalation:**

Contact the IT Helpdesk if Calendar remains slow with only one calendar visible.

**Bot Instruction:** Hiding a calendar does not delete it or remove access.

## Topic: Create, Rename, Copy, Move, or Star a Google Document

**Intent Keywords:** create google doc, rename document, make copy google doc, move document folder, star document

**Direct Answer:**

Basic Google Docs file management can be completed from Docs or Google Drive.

**Approved Steps:**

1. To create a document, open Drive and select **New → Google Docs**.
2. Rename it by selecting the file name at the top.
3. Use **File → Make a copy** to create a separate version.
4. Use the folder or move option to place it in the correct Drive folder.
5. Use the star icon to add an important document to **Starred**.
6. Confirm that the document shows **Saved to Drive** before closing.
7. Verify that the document is stored in an approved school location.

**Escalation:**

Contact the file owner if copying or moving is restricted.

**Bot Instruction:** Do not move, copy, or rename official shared documents without owner approval.

## Topic: Find and Replace Text or Check Word Count in Google Docs

**Intent Keywords:** find text google docs, replace word, word count google docs, count document words, search document

**Direct Answer:**

Google Docs includes built-in Find and replace and Word count tools.

**Approved Steps:**

1. Open the document.
2. Use **Edit → Find and replace** to locate text.
3. Enter the replacement text when needed.
4. Review matches before selecting **Replace all**.
5. Use **Tools → Word count** to view pages, words, characters, and characters excluding spaces.
6. Close the tool when finished.

**Escalation:**

Contact the document owner before replacing repeated terms in an official school document.

**Bot Instruction:** Warn the user that Replace all can change unintended text.

## Topic: Add Headers, Footers, Page Numbers, or a Page Break in Google Docs

**Intent Keywords:** docs page number, add header, add footer, insert page break, school essay page numbers

**Direct Answer:**

Page elements can be inserted from the Google Docs **Insert** menu.

**Approved Steps:**

1. Open the document.
2. Place the cursor where the page break should begin.
3. Use **Insert → Break → Page break** when needed.
4. Use **Insert → Headers and footers** to add a header or footer.
5. Use **Insert → Page numbers** to choose a numbering style.
6. Review the first-page and section options.
7. Confirm the layout in Print preview.

**Escalation:**

Ask the teacher if a specific assignment format is required.

**Bot Instruction:** Do not guess school formatting or citation requirements.

## Topic: Insert an Image, Link, Table, or Table of Contents in Google Docs

**Intent Keywords:** insert image google docs, add link docs, create table, table of contents google doc, document objects

**Direct Answer:**

Google Docs can include images, hyperlinks, tables, special characters, and an automatic table of contents.

**Approved Steps:**

1. Place the cursor at the correct location.
2. Open **Insert**.
3. Choose the required item.
4. For images, use an approved file or source.
5. For links, confirm that the destination is safe and accessible.
6. For tables, choose the required number of rows and columns.
7. For a table of contents, apply heading styles first.
8. Review the document layout after insertion.

**Escalation:**

Contact the document owner if inserted items cannot be edited or moved.

**Bot Instruction:** Do not insert copyrighted, confidential, or unapproved school content.

## Topic: Print or Download a Google Document

**Intent Keywords:** print google doc, download docx, save google doc as pdf, email document attachment

**Direct Answer:**

A Google Doc can be printed or downloaded in an approved file format.

**Approved Steps:**

1. Open the document.
2. Select **File**.
3. Choose **Print** or **Download**.
4. Select the required format, such as PDF or Microsoft Word.
5. Review the downloaded file for formatting changes.
6. For printing, review printer, page range, orientation, colour, and two-sided options.
7. Confirm the correct school printer before printing.

**Escalation:**

Contact the IT Helpdesk if the print dialog does not open or the school printer is unavailable.

**Bot Instruction:** Do not download confidential school documents to personal or unmanaged devices.

## Topic: Create or Open a Google Sheet

**Intent Keywords:** create google sheet, new spreadsheet, open spreadsheet, sheet template, saved sheet

**Direct Answer:**

A spreadsheet can be created from Google Drive or opened from Drive, Sheets, Recent, Starred, or Shared with me.

**Approved Steps:**

1. Open Google Drive.
2. Select **New → Google Sheets**.
3. Choose a blank spreadsheet or approved template.
4. Enter a clear file name.
5. Confirm that changes show as saved to Drive.
6. To open an existing file, locate it in Drive and double-click it.
7. Confirm that the correct school account is active.

**Escalation:**

Contact the file owner if the spreadsheet cannot be opened or edited.

**Bot Instruction:** Do not create or store school records in a personal Google account.

## Topic: Format Rows, Columns, Numbers, and Dates in Google Sheets

**Intent Keywords:** format cells google sheets, resize column, wrap text, merge cells, date format, currency format, row height

**Direct Answer:**

Rows, columns, text, numbers, dates, and cell appearance can be formatted from the toolbar and Format menu.

**Approved Steps:**

1. Select the affected cell, row, column, or range.
2. Choose the required number, date, percentage, or currency format.
3. Use text wrapping when content is hidden.
4. Adjust row height or column width.
5. Use alignment and borders when needed.
6. Merge cells only for headings and only when it will not interfere with sorting or filtering.
7. Review the result before applying the format to a large range.

**Escalation:**

Contact the spreadsheet owner before reformatting a gradebook, roster, finance sheet, or official report.

**Bot Instruction:** Do not alter official data formats without authorization.

## Topic: Freeze or Unfreeze Rows and Columns in Google Sheets

**Intent Keywords:** freeze top row, freeze column sheets, headers disappear scrolling, unfreeze sheet

**Direct Answer:**

Freezing keeps selected header rows or columns visible while scrolling.

**Approved Steps:**

1. Open the spreadsheet.
2. Select **View → Freeze**.
3. Choose the number of rows or columns to keep visible.
4. Scroll to confirm that the correct headers remain visible.
5. To remove it, return to **View → Freeze** and choose no rows or columns.

**Escalation:**

Contact the file owner if the sheet is protected and the view cannot be changed.

**Bot Instruction:** Freezing rows or columns changes only the view; it does not protect the data.

## Topic: Use Basic Formulas and Autofill in Google Sheets

**Intent Keywords:** sum google sheets, average formula, min max count, autofill formula, copy formula down

**Direct Answer:**

Google Sheets supports formulas such as SUM, AVERAGE, MIN, MAX, and COUNT.

**Approved Steps:**

1. Select the result cell.
2. Type `=` followed by the function.
3. Select the intended cell range.
4. Close the parentheses.
5. Press Enter.
6. Confirm that the result is reasonable.
7. Use the fill handle to copy the formula when appropriate.
8. Review copied formulas to ensure cell references changed correctly.

**Examples:**

* `=SUM(B2:B10)`
* `=AVERAGE(B2:B10)`
* `=MIN(B2:B10)`
* `=MAX(B2:B10)`
* `=COUNT(B2:B10)`

**Escalation:**

Ask the teacher or spreadsheet owner to confirm the intended calculation.

**Bot Instruction:** Do not create or modify grade, payroll, finance, or reporting calculations without authorization.

## Topic: Create a Dropdown or Data Validation Rule in Google Sheets

**Intent Keywords:** sheets dropdown, data validation, restrict cell entries, list in cell, validation error

**Direct Answer:**

Data validation can limit entries to approved values and help keep school data consistent.

**Approved Steps:**

1. Select the intended cells.
2. Open **Data → Data validation** or the current dropdown control.
3. Choose the validation type.
4. Enter the approved values or range.
5. Choose whether invalid data should be rejected or only warned about.
6. Add clear help text when needed.
7. Test one valid and one invalid entry.

**Escalation:**

Contact the spreadsheet owner before changing validation in an official form, roster, gradebook, or reporting sheet.

**Bot Instruction:** Do not remove validation rules merely to bypass a restriction.

## Topic: Create or Edit a Chart in Google Sheets

**Intent Keywords:** create chart sheets, graph spreadsheet, chart wrong data, change chart type, chart title

**Direct Answer:**

A chart can summarize selected spreadsheet data visually.

**Approved Steps:**

1. Select the complete data range, including headings.
2. Select **Insert → Chart**.
3. Review the suggested chart.
4. Choose a chart type appropriate for the data.
5. Confirm the correct rows and columns are being used.
6. Add a clear chart title and labels.
7. Move or resize the chart when needed.
8. Verify that no confidential information is exposed.

**Escalation:**

Ask the teacher or spreadsheet owner which chart type and data should be presented.

**Bot Instruction:** Do not create misleading charts or publish confidential student data.

## Topic: Print a Google Sheet Correctly

**Intent Keywords:** print google sheet, spreadsheet cut off, fit sheet one page, print selected cells, repeat frozen rows

**Direct Answer:**

Use the Sheets print preview to control the printed area, scale, orientation, margins, headers, and page breaks.

**Approved Steps:**

1. Open the spreadsheet.
2. Select **File → Print**.
3. Choose whether to print the current sheet, selected cells, or workbook.
4. Review page orientation.
5. Adjust scale so columns are not cut off.
6. Review margins and headers.
7. Confirm the page range.
8. Select **Next** and choose the correct school printer.

**Escalation:**

Contact the IT Helpdesk if the preview is correct but the printer output is not.

**Bot Instruction:** Avoid printing confidential school information to an unattended or public printer.

## Topic: Create or Open a Google Slides Presentation

**Intent Keywords:** create google slides, new presentation, slides template, open presentation, make slideshow

**Direct Answer:**

A Google Slides presentation can be created from Drive or opened from Drive, Recent, Starred, or Shared with me.

**Approved Steps:**

1. Open Google Drive.
2. Select **New → Google Slides**.
3. Choose a blank presentation or approved template.
4. Enter a clear presentation name.
5. Confirm that changes show as saved to Drive.
6. To open an existing presentation, find it in Drive and double-click it.
7. Confirm that the correct school account is active.

**Escalation:**

Contact the file owner if the presentation cannot be opened or edited.

**Bot Instruction:** Do not store school presentations in a personal account.

## Topic: Add, Duplicate, Move, Skip, or Delete Slides

**Intent Keywords:** add slide, duplicate slide, move slide, skip slide, hide slide, delete slide, reorder slides

**Direct Answer:**

Slides can be organized from the slide filmstrip or grid view.

**Approved Steps:**

1. Open the presentation.
2. Add a new slide and choose the required layout.
3. Duplicate a slide when reusing its design.
4. Drag a slide to reorder it.
5. Use **Skip slide** when it should remain in the file but not appear during presentation.
6. Unskip it when it should be presented again.
7. Delete a slide only after confirming that it is no longer needed.
8. Use Undo immediately if the wrong slide was removed.

**Escalation:**

Contact the presentation owner before deleting or reorganizing an official shared presentation.

**Bot Instruction:** Do not delete slides containing student or school records without authorization.

## Topic: Add and Use Speaker Notes in Google Slides

**Intent Keywords:** speaker notes, presentation notes, notes not showing, presenter notes google slides

**Direct Answer:**

Speaker notes provide private prompts for the presenter and do not normally appear on the projected slide.

**Approved Steps:**

1. Open the presentation.
2. Select a slide.
3. Open the speaker-notes area below the slide.
4. Enter the presenter's notes.
5. Repeat for other slides.
6. Start Presenter view.
7. Confirm that the notes appear only on the presenter's display.
8. Test with the classroom display before the presentation.

**Escalation:**

Contact the IT Helpdesk if the projector mirrors both displays and exposes speaker notes.

**Bot Instruction:** Do not place passwords, confidential student details, or private staff information in speaker notes.

## Topic: Apply a Theme, Transition, or Animation in Google Slides

**Intent Keywords:** slides theme, slide transition, animate object, change slide design, presentation animation

**Direct Answer:**

Themes control presentation design, transitions control movement between slides, and animations control objects on a slide.

**Approved Steps:**

1. Open the presentation.
2. Select an approved theme.
3. Confirm that fonts and colours remain readable.
4. Select a slide and add a transition if needed.
5. Select an object and add an animation when appropriate.
6. Review animation order and timing.
7. Preview the slideshow.
8. Use effects consistently and sparingly.

**Escalation:**

Contact the presentation owner before modifying the theme or master layout of a shared school template.

**Bot Instruction:** Avoid excessive animation that makes school content difficult to read or inaccessible.

## Topic: Use Presenter View in Google Slides

**Intent Keywords:** presenter view, see notes while presenting, slides timer, audience questions, presentation controls

**Direct Answer:**

Presenter view can show speaker notes, slide controls, and timing tools on the presenter's display.

**Approved Steps:**

1. Connect the classroom display or projector.
2. Confirm the display arrangement.
3. Open the presentation.
4. Start the slideshow.
5. Open Presenter view.
6. Confirm that the audience sees only the slides.
7. Use the slide controls, timer, and notes as needed.
8. Test the setup before the audience arrives.

**Escalation:**

Contact the IT Helpdesk if the audience can see the presenter notes or the wrong screen is displayed.

**Bot Instruction:** Do not change administrator-level display settings.

## Topic: Print Google Slides as Slides, Notes, or Handouts

**Intent Keywords:** print google slides, print handouts, slides with notes, multiple slides per page, save slides pdf

**Direct Answer:**

Slides can be printed as full-page slides, notes pages, or handouts with multiple slides per page.

**Approved Steps:**

1. Open the presentation.
2. Select **File → Print settings and preview**.
3. Choose the required layout.
4. Decide whether speaker notes should be included.
5. Review orientation and background settings.
6. Confirm whether skipped slides should be printed.
7. Select **Print** or download an approved PDF.
8. Choose the correct school printer.

**Escalation:**

Contact the IT Helpdesk if preview and printed output do not match.

**Bot Instruction:** Avoid printing private speaker notes or confidential presentation content unintentionally.

## Topic: Echo or Feedback in Google Meet

**Intent Keywords:** meet echo, feedback sound, hearing myself, repeated audio, loud noise meeting

**Direct Answer:**

Echo usually occurs when a microphone picks up sound from nearby speakers.

**Troubleshooting Steps:**

1. Mute microphones on unused nearby devices.
2. Use headphones or an approved headset.
3. Reduce speaker volume.
4. Move away from other devices joined to the same meeting.
5. Confirm that only one nearby device has audio enabled.
6. In Meet settings, select the correct microphone and speaker.
7. Leave and rejoin the meeting if the echo continues.

**Escalation:**

Contact the IT Helpdesk if the echo occurs with headphones and only one device connected.

**Bot Instruction:** Do not unmute another participant without a legitimate host or moderator need.

## Topic: Turn Google Meet Captions On or Off

**Intent Keywords:** meet captions, closed captions, subtitles meet, live captions not showing

**Direct Answer:**

Google Meet can display automatically generated captions during a meeting.

**Approved Steps:**

1. Join the meeting.
2. Locate the captions control or open **More options**.
3. Turn captions on.
4. Select the available spoken language when offered.
5. Confirm that captions appear.
6. Turn them off using the same control when no longer needed.

**Important Information:**

Automatic captions may contain mistakes and should not be treated as a perfect or official transcript.

**Escalation:**

Contact the IT Helpdesk if captions are required as an accommodation but are unavailable.

**Bot Instruction:** Do not promise that captions are completely accurate.

## Topic: Change Google Meet Layout or Full-Screen View

**Intent Keywords:** meet layout, tiled view, speaker view, full screen meet, participants too small, change meeting view

**Direct Answer:**

Meet layouts can change how the active speaker, presentation, and participants appear.

**Approved Steps:**

1. Join the meeting.
2. Open **More options**.
3. Choose **Change layout**.
4. Select an available layout such as tiled, spotlight, or sidebar.
5. Use full-screen mode when needed.
6. Press Escape to leave full-screen mode.
7. Pin an important speaker or presentation when appropriate.

**Escalation:**

Contact the IT Helpdesk if the layout controls are missing across multiple supported browsers.

**Bot Instruction:** Layout changes normally affect only the current user's view.

## Topic: Google Meet Video Is Choppy or the Connection Is Poor

**Intent Keywords:** meet lagging, choppy video, poor connection, meet freezing, video delayed, low bandwidth

**Direct Answer:**

Poor Meet quality can be caused by weak Wi-Fi, limited bandwidth, high video resolution, or other active applications.

**Troubleshooting Steps:**

1. Close unnecessary browser tabs and applications.
2. Move closer to the wireless access point.
3. Use a wired Ethernet connection when available.
4. Turn off the camera temporarily.
5. Open Meet settings.
6. Reduce send or receive video resolution when available.
7. Disconnect unused VPN or streaming services when permitted.
8. Rejoin the meeting.

**Escalation:**

Contact the IT Helpdesk if several users in the same area experience poor Meet quality.

**Bot Instruction:** Do not advise bypassing the school network or security controls.

## Topic: Copy Google Meet Joining Information or Invite Participants

**Intent Keywords:** copy meet link, invite people to meet, meeting code, share joining information, send meet invitation

**Direct Answer:**

A host or organizer can copy the meeting information and send it to approved participants.

**Approved Steps:**

1. Join or create the meeting.
2. Open the meeting-details panel.
3. Copy the joining information.
4. Share it only with the intended participants.
5. To invite someone during the meeting, open the People panel.
6. Select the option to add people.
7. Enter the approved school email address.
8. Confirm the invitation.

**Escalation:**

Contact the organizer if the meeting link should not be distributed.

**Bot Instruction:** Do not post restricted school meeting links publicly.

## Topic: Admit, Pin, Mute, or Remove a Participant in Google Meet

**Intent Keywords:** admit person meet, pin participant, mute student meet, remove person meeting, host controls

**Direct Answer:**

Available participant controls depend on the user's host, co-host, moderator, and organization permissions.

**Approved Steps:**

1. Confirm that you are authorized to manage participants.
2. Use **Admit** for approved users waiting to join.
3. Use **Pin** to keep a participant visible on your own screen.
4. Use **Mute** only when background noise disrupts the meeting.
5. Remember that another participant normally must unmute themselves.
6. Use **Remove** only for a legitimate safety, behaviour, or access reason.
7. Inform the meeting organizer when a participant is removed.

**Escalation:**

Contact the teacher, meeting organizer, or IT Helpdesk for repeated unauthorized joining or serious behaviour concerns.

**Bot Instruction:** Do not recommend removing, muting, or denying participants without authorization.

## Topic: Access Google Chat

**Intent Keywords:** open google chat, access google chat, where is google chat, chat website, google chat app, use chat on phone, chat in gmail

**Direct Answer:**

Google Chat can be accessed from its website, inside Gmail, or through the Google Chat mobile application.

**Approved Steps:**

1. Confirm that the correct school Google account is active.
2. On a computer, open Google Chat directly or open Gmail and select **Chat**.
3. On a phone or tablet, open the Google Chat app or the Gmail app.
4. Select the school account when more than one Google account is listed.
5. Confirm that existing conversations appear.
6. If Chat is unavailable, try a private browser window.
7. Do not use a personal Google account for private school communication.

**Escalation:**

Contact the IT Helpdesk if Google Chat is disabled, missing, or unavailable for the school account.

**Bot Instruction:** Do not advise using an unapproved personal messaging service to bypass school restrictions.

## Topic: Turn Google Chat On in Gmail

**Intent Keywords:** enable chat in gmail, chat missing from gmail, show google chat sidebar, gmail chat button missing, turn on chat

**Direct Answer:**

Google Chat can normally be displayed inside Gmail, but the setting may be restricted by the school administrator.

**Approved Steps:**

1. Open Gmail using the school account.
2. Select **Settings**.
3. Select **See all settings**.
4. Open **Chat and Meet**.
5. Select Google Chat when the option is available.
6. Save the change.
7. Reload Gmail.
8. Look for **Chat** in the Gmail navigation area.

**Escalation:**

Contact the IT Helpdesk if the Chat setting is missing, locked, or does not remain enabled.

**Bot Instruction:** Do not claim that Chat can be enabled when the school administrator has disabled the service.

## Topic: Start a Direct Message in Google Chat

**Intent Keywords:** start google chat, message someone in chat, direct message teacher, new chat, find person google chat, send chat message

**Direct Answer:**

Start a direct message by searching for the person's approved school name or email address.

**Approved Steps:**

1. Open Google Chat or Chat inside Gmail.
2. Select **New chat**.
3. Enter the person's name or complete school email address.
4. Confirm that the correct person is selected.
5. Select **Start chat**.
6. Enter the message.
7. Review the recipient before sending.
8. Select **Send**.

**Escalation:**

Contact the IT Helpdesk if an internal school user cannot be found or messaged.

**Bot Instruction:** Do not guess email addresses or claim that a message was delivered without confirmation from Google Chat.

## Topic: Start a Group Direct Message in Google Chat

**Intent Keywords:** google chat group message, message multiple people, group dm, add people to chat, staff group chat

**Direct Answer:**

A group direct message can include multiple approved participants.

**Approved Steps:**

1. Open Google Chat.
2. Select **New chat**.
3. Enter the names or school email addresses of the participants.
4. Confirm every participant before creating the conversation.
5. Start the group message.
6. Enter a clear opening message explaining the purpose.
7. Avoid adding unnecessary participants.
8. Do not share confidential student or staff information unless the conversation is approved for it.

**Escalation:**

Contact the IT Helpdesk if school policy prevents adding the required participants.

**Bot Instruction:** Do not add external or unauthorized users to school conversations.

## Topic: Cannot Find Someone in Google Chat

**Intent Keywords:** person not showing in google chat, cannot find teacher chat, contact missing google chat, user not found chat, cannot message colleague

**Direct Answer:**

The person may be listed under a different account, may not have Chat enabled, or may be restricted by school policy.

**Troubleshooting Steps:**

1. Confirm that the school Google account is active.
2. Search using the person's complete school email address.
3. Check the spelling carefully.
4. Confirm that the person still has an active school account.
5. Try Google Chat in a private browser window.
6. Ask the intended recipient whether they use Google Chat.
7. Do not create or use a personal account to work around the restriction.

**Escalation:**

Contact the IT Helpdesk if an active internal user cannot be located.

**Bot Instruction:** Do not reveal private account, employment, enrolment, or directory information.

## Topic: Send a File or Image in Google Chat

**Intent Keywords:** attach file google chat, send document chat, send image in chat, share drive file chat, chat attachment not working

**Direct Answer:**

Google Chat can send approved files, images, or Google Drive links.

**Approved Steps:**

1. Open the correct conversation.
2. Confirm the recipients.
3. Select the attachment, upload, image, or Drive option.
4. Choose the intended file.
5. Confirm that the file does not contain information the recipients should not see.
6. If sharing a Drive file, review its permission level.
7. Add a short explanation.
8. Send the message.
9. Confirm that the attachment or link appears in the conversation.

**Escalation:**

Contact the IT Helpdesk if approved file types are blocked or uploads repeatedly fail.

**Bot Instruction:** Do not recommend sharing passwords, verification codes, grades, medical records, financial records, or confidential student information through Chat.

## Topic: Google Chat Messages Disappear or History Is Off

**Intent Keywords:** chat messages disappeared, google chat history off, missing chat messages, conversation not saved, chat history setting

**Direct Answer:**

Chat history and message retention may be controlled by the conversation settings and school policy.

**Troubleshooting Steps:**

1. Open the affected conversation.
2. Open the conversation details.
3. Check whether history is on or off.
4. Confirm whether the school controls the history setting.
5. Search Chat for a keyword from the conversation.
6. Confirm that the correct Google account is active.
7. Do not assume that missing messages can be recovered.

**Escalation:**

Contact the IT Helpdesk if school-required messages disappear unexpectedly or retention settings appear incorrect.

**Bot Instruction:** Do not promise recovery of deleted or expired Chat messages.

## Topic: Google Chat Recipient Has Not Responded

**Intent Keywords:** teacher not answering chat, no reply google chat, message ignored, recipient not responding, chat response delayed

**Direct Answer:**

A sent Chat message does not guarantee an immediate response.

**Approved Steps:**

1. Confirm that the message was sent to the correct person.
2. Check whether the message appears in the conversation.
3. Allow a reasonable response time.
4. Follow the school's approved communication hours and expectations.
5. For a time-sensitive school matter, use another approved contact method.
6. For an emergency, follow the school's emergency-contact procedure rather than relying on Chat.

**Escalation:**

Contact the school office, teacher, supervisor, or appropriate department when the matter requires a response outside normal Chat use.

**Bot Instruction:** Do not claim that the recipient has read, ignored, or intentionally avoided the message.

## Topic: Access and Navigate Google Drive

**Intent Keywords:** open google drive, access drive, where are my drive files, drive navigation, my drive shared with me, google drive interface

**Direct Answer:**

Google Drive stores school files online and can be accessed through a supported browser or approved application.

**Approved Steps:**

1. Confirm that the school Google account is active.
2. Open Google Drive.
3. Use **My Drive** for files associated with the user's account.
4. Use **Shared with me** for items shared directly by other users.
5. Use **Shared drives** for department, team, or school-owned content.
6. Use **Recent** to find recently opened files.
7. Use **Starred** for important items.
8. Use **Trash** to review deleted items.
9. Switch between list and grid view when helpful.

**Escalation:**

Contact the IT Helpdesk if Drive or an expected Shared drive is unavailable.

**Bot Instruction:** Do not advise storing school data in a personal Drive account.

## Topic: Upload a File or Folder to Google Drive

**Intent Keywords:** upload to google drive, add file to drive, upload folder, drag file into drive, copy file to drive

**Direct Answer:**

Files and folders can be uploaded through the **New** menu or by dragging them into Google Drive.

**Approved Steps:**

1. Open the correct Drive folder.
2. Select **New**.
3. Choose **File upload** or **Folder upload**.
4. Select the intended item from the computer.
5. Keep the Drive tab open while the upload is running.
6. Review the upload-status message.
7. Confirm that the uploaded item appears in the correct folder.
8. Remember that uploading normally creates a Drive copy and does not remove the original file from the computer.

**Escalation:**

Contact the IT Helpdesk if approved files are blocked or repeatedly fail to upload.

**Bot Instruction:** Do not upload confidential school information to a personal account or unauthorized folder.

## Topic: Download a File or Folder from Google Drive

**Intent Keywords:** download google drive file, save drive file to computer, download folder, drive download not working, zip file from drive

**Direct Answer:**

Files can be downloaded from preview or from the Drive actions menu. Downloaded folders are normally packaged as compressed files.

**Approved Steps:**

1. Confirm that the correct school account is active.
2. Select the file or folder.
3. Open the actions menu or right-click the item.
4. Select **Download**.
5. For a folder, wait while Drive prepares the compressed download.
6. Open the computer's Downloads folder.
7. Extract the compressed folder when required.
8. Store downloaded school information only on an approved device and location.

**Escalation:**

Contact the IT Helpdesk if downloads are blocked by policy or repeatedly fail.

**Bot Instruction:** Do not advise downloading confidential school files to a personal or unmanaged device.

## Topic: Search for Files in Google Drive

**Intent Keywords:** search google drive, find drive file, advanced drive search, search by owner, search by file type, cannot remember file location

**Direct Answer:**

Drive can search by file name, content, owner, type, location, and modification date.

**Approved Steps:**

1. Open Google Drive.
2. Enter a file name, keyword, or owner in the search field.
3. Open the search-options control when needed.
4. Filter by:

   * File type
   * Owner
   * Location
   * Date modified
   * Shared user
5. Review **My Drive**, **Shared with me**, and **Shared drives**.
6. Check **Trash** if the file may have been deleted.
7. Confirm the active Google account.

**Escalation:**

Contact the file owner or IT Helpdesk if a school-critical file remains missing.

**Bot Instruction:** Do not state that a file was permanently deleted solely because it does not appear in search.

## Topic: Organize or Move Google Drive Files

**Intent Keywords:** move drive file, organize google drive, create drive folder, star file, add shortcut, file in wrong folder

**Direct Answer:**

Use folders, stars, and shortcuts to organize files without creating unnecessary duplicate copies.

**Approved Steps:**

1. Create a clearly named folder when needed.
2. Select the file or folder to organize.
3. Use **Move** to place an owned item in the correct location.
4. Use **Add shortcut to Drive** for a shared item when appropriate.
5. Use **Star** for frequently used items.
6. Confirm the destination before moving the item.
7. Reopen the destination folder and verify the item.
8. Inform collaborators before moving a widely used school file.

**Escalation:**

Contact the file owner before moving shared departmental or school records.

**Bot Instruction:** Do not move or reorganize official school records without authorization.

## Topic: Remove or Change Someone's Google Drive Access

**Intent Keywords:** unshare drive file, remove access, change editor to viewer, revoke drive permission, sharing expiration, stop someone editing

**Direct Answer:**

The owner or an authorized manager can modify or remove a person's access.

**Approved Steps:**

1. Select the file or folder.
2. Select **Share**.
3. Locate the person or group.
4. Confirm that the correct user is selected.
5. Change their role to the minimum required permission, or remove access when authorized.
6. Set an expiration date when the option is available and appropriate.
7. Save the change.
8. Confirm that other required collaborators still have access.

**Escalation:**

Contact the file owner or IT Helpdesk if access cannot be changed.

**Bot Instruction:** Do not remove access from school leadership, record owners, teachers, or departments without authorization.

## Topic: Understand My Drive and Shared Drives

**Intent Keywords:** my drive vs shared drive, team drive, who owns shared drive files, department drive, shared drive difference

**Direct Answer:**

Files in **My Drive** are associated with an individual account. Files in a **Shared drive** belong to the shared team or organization and remain available independently of one person's account.

**Approved Guidance:**

* Use **My Drive** for individual working files.
* Use an approved **Shared drive** for department, team, or long-term shared material.
* Store files that must remain available after staff changes in an approved Shared drive.
* Do not move records between My Drive and a Shared drive without checking permissions and ownership requirements.
* Shared drive access is based on assigned membership and roles.

**Escalation:**

Contact the IT Helpdesk when a new Shared drive, ownership transfer, or department-level access change is required.

**Bot Instruction:** Do not claim to create a Shared drive or transfer organizational records without administrator confirmation.

## Topic: Shared Drive Is Missing or Cannot Be Opened

**Intent Keywords:** shared drive missing, team drive disappeared, cannot access department drive, shared drive permission, drive not listed

**Direct Answer:**

The Shared drive may be hidden, the user may not be a member, or their role may have changed.

**Troubleshooting Steps:**

1. Confirm that the school account is active.
2. Open **Shared drives**.
3. Search for the Shared drive name.
4. Refresh Google Drive.
5. Try Drive in a private browser window.
6. Ask the Shared drive manager to confirm membership.
7. Record the exact access error.
8. Do not request access through a personal account.

**Escalation:**

Contact the Shared drive manager or IT Helpdesk.

**Bot Instruction:** Do not reveal Shared drive membership or contents to unauthorized users.

## Topic: Manage Members of a Shared Drive

**Intent Keywords:** add member shared drive, shared drive permission, manage team drive, remove member, contributor content manager

**Direct Answer:**

Only an authorized Shared drive manager or administrator should change membership and roles.

**Approved Steps:**

1. Open the correct Shared drive.
2. Open **Manage members**.
3. Confirm that the person requires access.
4. Enter the approved school email address.
5. Select the minimum required role.
6. Review whether the person can add, edit, move, or delete content.
7. Save the membership change.
8. Confirm that access works as intended.

**Escalation:**

Contact the IT Helpdesk for department-wide, external, sensitive, or administrator-level access.

**Bot Instruction:** Do not grant broad Shared drive access merely to solve a single-file permission problem.

## Topic: Manage Versions of a Non-Google File in Drive

**Intent Keywords:** drive manage versions, replace uploaded file, old version of pdf, upload new version, file version history drive

**Direct Answer:**

Google Drive can retain versions of uploaded files such as PDFs, images, Word documents, and other non-Google files.

**Approved Steps:**

1. Select the uploaded file in Drive.
2. Open the actions menu.
3. Select **File information** or **Manage versions** when available.
4. Review the existing versions.
5. Upload the new version only after confirming the correct file.
6. Download an older version when needed.
7. Keep an important older version when the option is available.
8. Confirm that the file link and sharing remain correct.

**Escalation:**

Contact the file owner before deleting versions of official school material.

**Bot Instruction:** Do not promise indefinite version retention or delete earlier versions without authorization.

## Topic: Make Drive for Desktop Files Available Offline

**Intent Keywords:** drive offline file, available offline google drive, use drive without internet, blue cloud icon, green check drive, offline shared drive

**Direct Answer:**

Drive for desktop can stream files from the cloud or keep selected content available offline.

**Approved Steps:**

1. Confirm that Drive for desktop is running.
2. Open Google Drive through Finder on macOS or File Explorer on Windows.
3. Locate the required file or folder.
4. Right-click the item.
5. Open the Drive for desktop options.
6. Select **Available offline** when permitted.
7. Wait for syncing to complete.
8. Confirm the available-offline status before disconnecting from the internet.
9. Confirm that the computer has sufficient local storage.

**Escalation:**

Contact the IT Helpdesk if offline controls are unavailable or restricted on a managed device.

**Bot Instruction:** Do not make large or confidential folders available offline on personal or shared computers.

## Topic: Stream or Mirror Files with Drive for Desktop

**Intent Keywords:** stream files drive, mirror files drive, google drive desktop storage, files only online, files stored on computer

**Direct Answer:**

Drive for desktop can either stream files as they are needed or mirror approved files to local storage.

**Explanation:**

* **Stream files:** Files primarily remain in the cloud and download as needed. Selected items can be made available offline.
* **Mirror files:** A synchronized copy is stored on the computer and uses local disk space.

**Approved Steps:**

1. Open Drive for desktop settings.
2. Review the current streaming or mirroring configuration.
3. Check available local storage.
4. Do not change the managed configuration without approval.
5. Allow syncing to finish before shutting down the computer.
6. Confirm that required files appear in Drive online.

**Escalation:**

Contact the IT Helpdesk before changing stream or mirror settings on a school-managed device.

**Bot Instruction:** Do not recommend changing managed sync configuration as a first troubleshooting step.

## Topic: Create and Customize a Google Classroom Class

**Intent Keywords:** create google classroom class, make new class, classroom name section subject room, teacher create course

**Direct Answer:**

Authorized teachers can create a class and enter its basic details.

**Approved Steps:**

1. Confirm that the teacher's school account is active.
2. Open Google Classroom.
3. Select the create-class option.
4. Enter a clear class name.
5. Add the section, subject, or room when appropriate.
6. Create the class.
7. Open the class settings.
8. Review the class code, Stream settings, and other class details.
9. Do not add students until the class information is correct.

**Escalation:**

Contact the IT Helpdesk if the create-class option is missing or the account has the wrong Classroom role.

**Bot Instruction:** Do not create a class or change a user's teacher role without authorization.

## Topic: Understand Google Classroom Teacher Navigation

**Intent Keywords:** classroom stream classwork people grades, where are assignments classroom, teacher classroom menu, classroom navigation

**Direct Answer:**

Teacher controls are organized into separate Classroom areas.

**Main Areas:**

* **Stream:** Announcements and class communication.
* **Classwork:** Assignments, quiz assignments, questions, materials, and topics.
* **People:** Students and co-teachers.
* **Grades:** Student submissions and marks when grading is enabled.
* **Class settings:** Class details, class code, Stream permissions, and grading settings.

**Troubleshooting Steps:**

1. Confirm that the correct class is open.
2. Check the appropriate Classroom area.
3. Refresh the page if a recent post is missing.
4. Confirm that the teacher account has the expected role.

**Escalation:**

Contact the IT Helpdesk if entire teacher sections or controls are missing.

**Bot Instruction:** Do not confuse teacher controls with student controls.

## Topic: Configure Google Classroom Stream Posting Permissions

**Intent Keywords:** students cannot post classroom, disable classroom comments, stream permissions, only teachers can post, classroom commenting settings

**Direct Answer:**

Teachers can control whether students may post and comment on the class Stream.

**Approved Steps:**

1. Open the class.
2. Open **Class settings**.
3. Locate the Stream or student-posting permissions.
4. Choose the approved option, such as:

   * Students can post and comment
   * Students can only comment
   * Only teachers can post or comment
5. Save the setting.
6. Confirm that the setting matches the class expectations.
7. Explain the communication rules to students.

**Escalation:**

Contact the IT Helpdesk if settings cannot be saved or student controls do not match the selected option.

**Bot Instruction:** Do not change class communication permissions without the teacher's authorization.

## Topic: Set Up Google Classroom Grading

**Intent Keywords:** classroom grading setup, total points, weighted categories, overall grade, classroom grade calculation

**Direct Answer:**

Teachers may use no overall grade, total-points grading, or weighted-category grading when available.

**Approved Steps:**

1. Open the class.
2. Open **Class settings**.
3. Locate the grading section.
4. Select the approved grade-calculation method.
5. Decide whether students should see their overall grade.
6. Add grade categories when required.
7. For weighted grading, confirm that category percentages total 100%.
8. Save the settings.
9. Test the calculation with non-sensitive sample data before relying on it.

**Escalation:**

Contact the teacher responsible for assessment policy or the IT Helpdesk if grading controls malfunction.

**Bot Instruction:** Do not choose a grading system, calculate official marks, or change grade policy on behalf of a teacher.

## Topic: Create Google Classroom Grade Categories

**Intent Keywords:** classroom grade category, homework category, test category, weighted grade classroom, category points

**Direct Answer:**

Grade categories can organize work into areas such as assignments, tests, projects, or participation.

**Approved Steps:**

1. Open **Class settings**.
2. Locate the grading section.
3. Select **Add grade category**.
4. Enter a clear category name.
5. Enter the points or weighting required by the approved grading system.
6. Add additional categories as needed.
7. Confirm that weighted percentages total 100%.
8. Save the class settings.
9. Assign the correct category when creating classwork.

**Escalation:**

Contact the appropriate academic leader if category definitions or weights are unclear.

**Bot Instruction:** Do not invent grade categories, percentages, or academic policy.

## Topic: Invite Students to Google Classroom with a Class Code

**Intent Keywords:** classroom class code teacher, display class code, copy class code, reset class code, invite students code

**Direct Answer:**

Teachers can give students the class code generated for the class.

**Approved Steps:**

1. Open the correct class.
2. Open **Class settings**.
3. Locate the class code.
4. Display or copy the code.
5. Share it only with the intended students.
6. Ask students to join using their school accounts.
7. Reset or disable the code if it was shared improperly.
8. Confirm student enrolment on the **People** page.

**Escalation:**

Contact the IT Helpdesk if the class code is missing or students receive a technical error.

**Bot Instruction:** Do not publish a restricted class code publicly or invent a replacement code.

## Topic: Invite Students or Co-Teachers by Email

**Intent Keywords:** invite student classroom email, add students classroom, invite co teacher, people tab classroom

**Direct Answer:**

Teachers can invite approved students or co-teachers from the Classroom **People** page.

**Approved Steps:**

1. Open the correct class.
2. Select **People**.
3. Choose the add-student or add-teacher option.
4. Enter the approved school email address.
5. Confirm the person's name and role.
6. Send the invitation.
7. Ask the person to accept the invitation.
8. Confirm that they appear in the correct section of the People page.

**Escalation:**

Contact the IT Helpdesk if the user cannot be invited or appears under the wrong role.

**Bot Instruction:** Do not add unauthorized users or change a person's role without approval.

## Topic: Post or Schedule a Google Classroom Announcement

**Intent Keywords:** classroom announcement, post on stream, schedule announcement, save announcement draft, attach file announcement

**Direct Answer:**

Teachers can post announcements immediately, schedule them, or save them as drafts.

**Approved Steps:**

1. Open the class **Stream**.
2. Select the announcement area.
3. Choose the intended class or classes.
4. Choose all students or approved individual students when available.
5. Enter the announcement.
6. Attach approved files or links when needed.
7. Select **Post**, **Schedule**, or **Save draft**.
8. Confirm that the announcement appears at the intended time.

**Escalation:**

Contact the IT Helpdesk if scheduled posts fail or attachments are unavailable.

**Bot Instruction:** Do not post announcements or contact students on behalf of a teacher without authorization.

## Topic: Create a Google Classroom Assignment

**Intent Keywords:** create classroom assignment, add homework classroom, post assignment, schedule assignment, assignment due date

**Direct Answer:**

Teachers create assignments from the Classroom **Classwork** page.

**Approved Steps:**

1. Open the class.
2. Select **Classwork**.
3. Select **Create → Assignment**.
4. Enter a clear title and instructions.
5. Choose the intended class and students.
6. Set points or leave the assignment ungraded when appropriate.
7. Add the due date and time.
8. Select the grade category, grading period, topic, rubric, or originality-report option when approved.
9. Attach or create the required materials.
10. Select **Assign**, **Schedule**, or **Save draft**.
11. Confirm that the assignment appears correctly.

**Escalation:**

Contact the IT Helpdesk if assignment controls are missing or posting repeatedly fails.

**Bot Instruction:** Do not create, publish, grade, or change an assignment without teacher authorization.

## Topic: Choose Classroom Attachment Permissions

**Intent Keywords:** students can view file, students can edit file, make copy for each student, classroom attachment permission

**Direct Answer:**

When attaching a Drive file to an assignment, select how students should use it.

**Attachment Options:**

* **Students can view file:** Students can read the same file but cannot edit it.
* **Students can edit file:** All assigned students may edit the same shared file.
* **Make a copy for each student:** Classroom creates an individual copy for each student.

**Approved Steps:**

1. Attach the intended Drive file.
2. Open the permission menu beside the attachment.
3. Choose the correct student-access option.
4. Confirm the selected students.
5. Preview the assignment before publishing.
6. Do not give shared editing access when individual student work is required.

**Escalation:**

Contact the file owner or IT Helpdesk if the permission option is missing or copies are not created.

**Bot Instruction:** Do not change access to the teacher's original file unless authorized.

## Topic: Create a Quiz Assignment in Google Classroom

**Intent Keywords:** classroom quiz assignment, attach google form quiz, create blank quiz, grade importing, classroom locked mode

**Direct Answer:**

A quiz assignment creates or attaches a Google Forms quiz through Classroom.

**Approved Steps:**

1. Open the class.
2. Select **Classwork**.
3. Select **Create → Quiz assignment**.
4. Enter the title and instructions.
5. Open the attached blank quiz.
6. Add and review the quiz questions and answer key.
7. Configure points, due date, topic, and student selection.
8. Review grade-importing options when permitted.
9. Use managed-Chromebook locked mode only when approved and available.
10. Test the quiz using an approved test account or preview.
11. Assign, schedule, or save it as a draft.

**Escalation:**

Contact the teacher for grading decisions and IT for technical or locked-mode issues.

**Bot Instruction:** Do not generate answer keys, release marks, or change assessment security without teacher approval.

## Topic: Create a Question in Google Classroom

**Intent Keywords:** classroom question, ask students question, short answer classroom, multiple choice question classroom

**Direct Answer:**

Teachers can post short-answer or multiple-choice questions from the Classwork page.

**Approved Steps:**

1. Open the class.
2. Select **Classwork**.
3. Select **Create → Question**.
4. Enter the question and instructions.
5. Choose short answer or multiple choice.
6. Configure whether students may reply to classmates or edit their responses when available.
7. Select the intended students.
8. Set points, due date, and topic when needed.
9. Select **Ask**, **Schedule**, or **Save draft**.
10. Confirm that the question appears correctly.

**Escalation:**

Contact the IT Helpdesk if the question cannot be created or posted.

**Bot Instruction:** Do not post questions or change student-discussion permissions without teacher authorization.

## Topic: Add Class Materials to Google Classroom

**Intent Keywords:** add classroom material, post syllabus classroom, upload class resource, classroom reading material, add link to classwork

**Direct Answer:**

Teachers can post reference material such as a syllabus, reading, video, link, or resource file.

**Approved Steps:**

1. Open the class.
2. Select **Classwork**.
3. Select **Create → Material**.
4. Enter a clear title and description.
5. Attach or create the approved files, links, videos, or Drive resources.
6. Select the intended class and students when available.
7. Add the appropriate topic.
8. Select **Post**, **Schedule**, or **Save draft**.
9. Confirm that students can open the material.

**Escalation:**

Contact the file owner or IT Helpdesk if students receive access errors.

**Bot Instruction:** Do not publish copyrighted, confidential, or unapproved material.

## Topic: Organize Google Classroom Classwork with Topics

**Intent Keywords:** classroom topics, organize classwork, move assignment topic, create classroom section, reorder classroom work

**Direct Answer:**

Topics group related assignments, quizzes, questions, and materials on the Classwork page.

**Approved Steps:**

1. Open the class **Classwork** page.
2. Select **Create → Topic**.
3. Enter a clear topic name.
4. Add the topic.
5. Assign the topic while creating or editing classwork.
6. Reorder topics and posts when needed.
7. Use consistent topic names across the course.
8. Confirm that students can locate the content.

**Escalation:**

Contact the IT Helpdesk if topics cannot be created, saved, or reordered.

**Bot Instruction:** Do not reorganize an active course without the teacher's approval.

## Topic: Reuse a Google Classroom Post

**Intent Keywords:** reuse classroom assignment, copy post from another class, reuse announcement, duplicate classroom material

**Direct Answer:**

Teachers can reuse an announcement, assignment, question, quiz assignment, or material from another class.

**Approved Steps:**

1. Open the appropriate Classroom area.
2. Select **Reuse post**.
3. Choose the source class.
4. Select the post.
5. Review whether new copies of attachments are required.
6. Update the title, instructions, students, due date, topic, and points.
7. Check every attachment and permission.
8. Assign, schedule, or save the reused post as a draft.

**Escalation:**

Contact the IT Helpdesk if the source class or attachments cannot be accessed.

**Bot Instruction:** Never reuse a post without reviewing old dates, class names, attachments, answer keys, and student information.

## Topic: Chrome on Mac Does Not Work Correctly with VoiceOver

**Intent Keywords:** chrome voiceover problem, screen reader chrome mac, voiceover not reading chrome, chrome accessibility problem, cannot navigate chrome voiceover

**Direct Answer:**

First determine whether the issue affects Chrome itself, one website, or the macOS VoiceOver configuration.

**Troubleshooting Steps:**

1. Confirm that VoiceOver works in another application.
2. Close and reopen Chrome.
3. Reload the affected page.
4. Test another page in Chrome.
5. Test the same page in another approved browser.
6. Confirm that Chrome is up to date.
7. Restart VoiceOver.
8. Restart the Mac if the problem continues.
9. Record the exact page, control, and action that cannot be accessed.

**Escalation:**

Contact the IT Helpdesk or the school's accessibility-support contact if the issue prevents access to required school content.

**Bot Instruction:** Do not disable VoiceOver, remove an accommodation, or state that the user must use a mouse.

## Topic: Navigate Chrome on Mac Using the Keyboard

**Intent Keywords:** chrome keyboard navigation mac, use chrome without mouse, tab through chrome, keyboard focus missing, chrome shortcut mac

**Direct Answer:**

Chrome supports keyboard navigation, although some pages or controls may behave differently with assistive technology.

**Troubleshooting Steps:**

1. Press **Tab** to move forward through available controls.
2. Press **Shift + Tab** to move backward.
3. Press **Return** or **Space** to activate the focused control.
4. Use **Command + L** to focus the address bar.
5. Use **Command + F** to search the current page.
6. Confirm that keyboard navigation works on another webpage.
7. Test the same action in another approved browser.
8. Record any control that cannot receive visible keyboard focus.

**Escalation:**

Contact the IT Helpdesk or accessibility-support contact if required content cannot be operated using the keyboard.

**Bot Instruction:** Do not claim that every third-party webpage is fully keyboard accessible.

## Topic: Make Chrome Text or Web Content Larger on Mac

**Intent Keywords:** chrome text too small, zoom chrome mac, enlarge webpage, increase browser text, chrome magnification

**Direct Answer:**

Use browser zoom or macOS accessibility magnification to make web content easier to read.

**Approved Steps:**

1. Press **Command + Plus** to zoom in.
2. Press **Command + Minus** to zoom out.
3. Press **Command + 0** to return to the default zoom.
4. Confirm that content remains visible without unnecessary horizontal scrolling.
5. Try Chrome's page-zoom setting when a consistent zoom level is needed.
6. Use approved macOS Accessibility display or zoom settings when browser zoom is insufficient.

**Escalation:**

Contact the IT Helpdesk or accessibility-support contact if required controls disappear or become unusable when enlarged.

**Bot Instruction:** Do not reduce an approved accessibility setting merely to make a webpage fit.

## Topic: Chrome Contrast or Dark Appearance Problem on Mac

**Intent Keywords:** chrome dark mode problem, low contrast chrome, text hard to see, chrome colours wrong, mac increase contrast

**Direct Answer:**

Chrome may follow macOS appearance and accessibility preferences, while individual websites may use their own colours.

**Troubleshooting Steps:**

1. Determine whether the issue affects Chrome controls, one website, or all websites.
2. Review the macOS light or dark appearance.
3. Review approved macOS Accessibility display settings.
4. Increase contrast when appropriate.
5. Test the same page in another approved browser.
6. Reset only the webpage zoom before changing other settings.
7. Record any text, button, or control that cannot be read.

**Escalation:**

Contact the IT Helpdesk or accessibility-support contact when required school content does not provide sufficient visibility.

**Bot Instruction:** Do not tell a user to disable a required accessibility preference.

## Topic: Determine Whether an Accessibility Issue Is Chrome or the Website

**Intent Keywords:** website not accessible chrome, page screen reader problem, accessibility issue one website, chrome or website problem

**Direct Answer:**

An accessibility issue may come from Chrome, the website, a browser extension, macOS, or assistive technology.

**Troubleshooting Steps:**

1. Test another page in Chrome.
2. Test the affected page in a private browser window.
3. Test the same page in another approved browser.
4. Confirm whether the issue occurs with the same keyboard or assistive-technology action.
5. Temporarily disable only nonessential extensions for testing.
6. Record:

   * The page or service
   * The affected control
   * The expected action
   * What occurred instead
   * Chrome version
   * macOS version
   * Assistive technology being used
7. Capture a screenshot only when it does not expose private information.

**Escalation:**

Contact the IT Helpdesk or accessibility-support contact with the recorded details.

**Bot Instruction:** Do not blame the user, the assistive technology, Chrome, or the website without testing.

## Topic: Request Accessibility Assistance for Chrome or Google Workspace

**Intent Keywords:** accessibility help, disability support google, accommodation browser, accessible school technology, screen reader support

**Direct Answer:**

Accessibility problems affecting required school work should be escalated promptly and should not require the user to abandon an approved accommodation.

**Approved Steps:**

1. Record the affected Google service or webpage.
2. Record the device, browser, and assistive technology.
3. Describe the inaccessible task or control.
4. Note whether another approved browser works.
5. Protect student and staff privacy when providing screenshots.
6. Contact the IT Helpdesk or the school's accessibility-support contact.
7. Follow the school's accommodation and accessibility procedures.

**Escalation:**

Escalate immediately when the issue prevents access to required learning, assessment, communication, or school services.

**Bot Instruction:** Never advise removing an accommodation or sharing private medical information in chat.

# Source Basis

This school support document is based on official Google Workspace Known Issues documentation and official Google help resources for Google Workspace Admin, Gmail, Drive, Docs Editors, Sheets, Slides, Calendar, Classroom, Meet, Forms, and related education services. School-specific password, identity-verification, privacy, role, and escalation rules take priority over generic Google self-service guidance.
