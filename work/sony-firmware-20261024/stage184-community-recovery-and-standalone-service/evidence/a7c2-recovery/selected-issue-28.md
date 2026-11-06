https://github.com/QAQLeonard/a7c2-fl23-research/issues/28
[A7C II FW 2.01 / Tools 3.0.3] Patch location conflict at appFw.so 0x3528804 — safe factory restore and reinstall?
Hello,

I am using a Sony A7C II (ILCE-7CM2) with firmware version 2.01 and A7C II Tools for Windows v3.0.3.

I attempted to install the following features using the one-click installation option:

Six Creative Looks: NC, CC, NN, Astia, GR Positive, GR Negative
FL2 / FL3
Sony electronic shutter sound
Portrait-orientation shooting information display
Lightroom automatic recognition plugin

The installation failed with the following error:

ValueError: Patch location conflict: appFw.so 0x3528804

The application reported that the expected patch location did not match the current data and stopped the operation.

Important observations:

USB driver installation and the 120-second USB stability test were successful.
The installation logs appear to indicate that the portrait-display-related modification was written and read back before the later patch conflict occurred.
The FL2 / FL3 installation stage stopped with the patch conflict.
The overall setup_all task status is FAILED.
After the error, I safely powered off and disconnected the camera.
The camera restarted successfully.
Camera menus, photography, image playback, and the original Creative Look options are functioning normally.
The six new Creative Looks are not visibly available by their names.
I have not attempted another installation or factory restoration.

I previously used Sony’s official Imaging Edge Desktop / Creators’ App, but I have never used this third-party tool to modify the camera before this attempt.

My questions:

1. Is it safe to use the Restore Factory 2.01 Features function in v3.0.3 after this partially completed installation?
2. Can the restoration function correctly handle the portrait-display-related modification that appears to have been written?
3. What could cause the appFw.so 0x3528804 patch location conflict on firmware 2.01?
4. After a successful restoration, can I reinstall all five selected features using v3.0.3, or is a corrected version required?
5. Is there a recommended procedure to verify that the camera has been fully restored before attempting installation again?

I have preserved the diagnostic ZIP file and the original task logs and can provide them for analysis.

I would appreciate your guidance on the safest recovery and reinstallation procedure.

Thank you very much!