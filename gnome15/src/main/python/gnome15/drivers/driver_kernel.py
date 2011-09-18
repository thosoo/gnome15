############################################################################
##
## Copyright (C), all rights reserved:
##      2010 Brett Smith <tanktarta@blueyonder.co.uk>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Gnome15 - Suite of GNOME applications that work with the logitech G15
##           keyboard
##
############################################################################

 
from cStringIO import StringIO
from pyinputevent.uinput import UInputDevice
from pyinputevent.pyinputevent import InputEvent, SimpleDevice
from pyinputevent.keytrans import *
from threading import Thread

import select 
import pyinputevent.scancodes as S
import gnome15.g15driver as g15driver
import gnome15.g15util as g15util
import gnome15.g15globals as g15globals
import gnome15.g15uinput as g15uinput
import uinput
import gconf
import fcntl
import os
import gtk
import cairo
import re
import usb
import fb
import Image
import ImageMath
import array
import time
import dbus
import gobject

# Logging
import logging
logger = logging.getLogger("driver")

# Driver information (used by driver selection UI)
id = "kernel"
name = "Kernel Drivers"
description = "Requires ali123's Logitech Kernel drivers. This method requires no other " + \
            "daemons to be running, and works with the G13, G15, G19 and G110 keyboards. " 
has_preferences = True


"""
This dictionaries map the default codes emitted by the input system to the
Gnome15 codes.
"""  
g19_key_map = {
               S.KEY_PROG1 : g15driver.G_KEY_M1,
               S.KEY_PROG2 : g15driver.G_KEY_M2,
               S.KEY_PROG3 : g15driver.G_KEY_M3,
               S.KEY_RECORD : g15driver.G_KEY_MR,
               S.KEY_MENU : g15driver.G_KEY_MENU,
               S.KEY_UP : g15driver.G_KEY_UP,
               S.KEY_DOWN : g15driver.G_KEY_DOWN,
               S.KEY_LEFT : g15driver.G_KEY_LEFT,
               S.KEY_RIGHT : g15driver.G_KEY_RIGHT,
               S.KEY_OK : g15driver.G_KEY_OK,
               S.KEY_BACK : g15driver.G_KEY_BACK,
               S.KEY_FORWARD : g15driver.G_KEY_SETTINGS,
               228 : g15driver.G_KEY_LIGHT,
               S.KEY_F1 : g15driver.G_KEY_G1,
               S.KEY_F2 : g15driver.G_KEY_G2,
               S.KEY_F3 : g15driver.G_KEY_G3,
               S.KEY_F4 : g15driver.G_KEY_G4,
               S.KEY_F5 : g15driver.G_KEY_G5,
               S.KEY_F6 : g15driver.G_KEY_G6,
               S.KEY_F7 : g15driver.G_KEY_G7,
               S.KEY_F8 : g15driver.G_KEY_G8,
               S.KEY_F9 : g15driver.G_KEY_G9,
               S.KEY_F10 : g15driver.G_KEY_G10,
               S.KEY_F11 : g15driver.G_KEY_G11,
               S.KEY_F12 : g15driver.G_KEY_G12
               }
g15_key_map = {
               S.KEY_PROG1 : g15driver.G_KEY_M1,
               S.KEY_PROG2 : g15driver.G_KEY_M2,
               S.KEY_PROG3 : g15driver.G_KEY_M3,
               S.KEY_RECORD : g15driver.G_KEY_MR,
               S.KEY_OK : g15driver.G_KEY_L1,
               S.KEY_LEFT : g15driver.G_KEY_L2,
               S.KEY_UP : g15driver.G_KEY_L3,
               S.KEY_DOWN : g15driver.G_KEY_L4,
               S.KEY_RIGHT : g15driver.G_KEY_L5,
               228 : g15driver.G_KEY_LIGHT,
               S.KEY_F1 : g15driver.G_KEY_G1,
               S.KEY_F2 : g15driver.G_KEY_G2,
               S.KEY_F3 : g15driver.G_KEY_G3,
               S.KEY_F4 : g15driver.G_KEY_G4,
               S.KEY_F5 : g15driver.G_KEY_G5,
               S.KEY_F6 : g15driver.G_KEY_G6,
               S.KEY_F7 : g15driver.G_KEY_G7,
               S.KEY_F8 : g15driver.G_KEY_G8,
               S.KEY_F9 : g15driver.G_KEY_G9,
               S.KEY_F10 : g15driver.G_KEY_G10,
               S.KEY_F11 : g15driver.G_KEY_G11,
               S.KEY_F12 : g15driver.G_KEY_G12,
               S.KEY_F13 : g15driver.G_KEY_G13,
               S.KEY_F14 : g15driver.G_KEY_G14,
               S.KEY_F15 : g15driver.G_KEY_G15,
               S.KEY_F16 : g15driver.G_KEY_G16,
               S.KEY_F17 : g15driver.G_KEY_G17,
               S.KEY_F18 : g15driver.G_KEY_G18
               }
g13_key_map = {
               S.KEY_PROG1 : g15driver.G_KEY_M1,
               S.KEY_PROG2 : g15driver.G_KEY_M2,
               S.KEY_PROG3 : g15driver.G_KEY_M3,
               S.KEY_RECORD : g15driver.G_KEY_MR,
               S.KEY_OK : g15driver.G_KEY_L1,
               S.KEY_LEFT : g15driver.G_KEY_L2,
               S.KEY_UP : g15driver.G_KEY_L3,
               S.KEY_DOWN : g15driver.G_KEY_L4,
               S.KEY_RIGHT : g15driver.G_KEY_L5,
               228 : g15driver.G_KEY_LIGHT,
               S.KEY_F1 : g15driver.G_KEY_G1,
               S.KEY_F2 : g15driver.G_KEY_G2,
               S.KEY_F3 : g15driver.G_KEY_G3,
               S.KEY_F4 : g15driver.G_KEY_G4,
               S.KEY_F5 : g15driver.G_KEY_G5,
               S.KEY_F6 : g15driver.G_KEY_G6,
               S.KEY_F7 : g15driver.G_KEY_G7,
               S.KEY_F8 : g15driver.G_KEY_G8,
               S.KEY_F9 : g15driver.G_KEY_G9,
               S.KEY_F10 : g15driver.G_KEY_G10,
               S.KEY_F11 : g15driver.G_KEY_G11,
               S.KEY_F12 : g15driver.G_KEY_G12,
               S.KEY_F13 : g15driver.G_KEY_G13,
               S.KEY_F14 : g15driver.G_KEY_G14,
               S.KEY_F15 : g15driver.G_KEY_G15,
               S.KEY_F16 : g15driver.G_KEY_G16,
               S.KEY_F17 : g15driver.G_KEY_G17,
               S.KEY_F18 : g15driver.G_KEY_G18,
               S.KEY_F19 : g15driver.G_KEY_G19,
               S.KEY_F20 : g15driver.G_KEY_G20,
               S.KEY_F21 : g15driver.G_KEY_G21,
               S.KEY_F22 : g15driver.G_KEY_G22,
               S.BTN_LEFT: g15driver.G_KEY_JOY_LEFT,                     
               S.BTN_MIDDLE: g15driver.G_KEY_JOY_CENTER,                  
               S.BTN_RIGHT: g15driver.G_KEY_JOY_DOWN,
               }
g110_key_map = {
               S.KEY_PROG1 : g15driver.G_KEY_M1,
               S.KEY_PROG2 : g15driver.G_KEY_M2,
               S.KEY_PROG3 : g15driver.G_KEY_M3,
               S.KEY_RECORD : g15driver.G_KEY_MR,
               228 : g15driver.G_KEY_LIGHT,
               S.KEY_F1 : g15driver.G_KEY_G1,
               S.KEY_F2 : g15driver.G_KEY_G2,
               S.KEY_F3 : g15driver.G_KEY_G3,
               S.KEY_F4 : g15driver.G_KEY_G4,
               S.KEY_F5 : g15driver.G_KEY_G5,
               S.KEY_F6 : g15driver.G_KEY_G6,
               S.KEY_F7 : g15driver.G_KEY_G7,
               S.KEY_F8 : g15driver.G_KEY_G8,
               S.KEY_F9 : g15driver.G_KEY_G9,
               S.KEY_F10 : g15driver.G_KEY_G10,
               S.KEY_F11 : g15driver.G_KEY_G11,
               S.KEY_F12 : g15driver.G_KEY_G12
               }

g19_mkeys_control = g15driver.Control("mkeys", "Memory Bank Keys", 0, 0, 15, hint=g15driver.HINT_MKEYS)
g19_keyboard_backlight_control = g15driver.Control("backlight_colour", "Keyboard Backlight Colour", (0, 255, 0), hint=g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE)

g19_foreground_control = g15driver.Control("foreground", "Default LCD Foreground", (255, 255, 255), hint=g15driver.HINT_FOREGROUND | g15driver.HINT_VIRTUAL)
g19_background_control = g15driver.Control("background", "Default LCD Background", (0, 0, 0), hint=g15driver.HINT_BACKGROUND | g15driver.HINT_VIRTUAL)
g19_highlight_control = g15driver.Control("highlight", "Default Highlight Color", (255, 0, 0), hint=g15driver.HINT_HIGHLIGHT | g15driver.HINT_VIRTUAL)
g19_controls = [ g19_keyboard_backlight_control, g19_foreground_control, g19_background_control, g19_highlight_control, g19_mkeys_control ]

g110_keyboard_backlight_control = g15driver.Control("backlight_colour", "Keyboard Backlight Colour", (255, 0, 0), hint=g15driver.HINT_DIMMABLE | g15driver.HINT_SHADEABLE | g15driver.HINT_RED_BLUE_LED)
g110_controls = [ g110_keyboard_backlight_control ]

# TODO doesn't work yet
#g19_lcd_brightness_control = g15driver.Control("lcd_brightness", "LCD Brightness", 100, 0, 100, hint=g15driver.HINT_SHADEABLE)


g15_mkeys_control = g15driver.Control("mkeys", "Memory Bank Keys", 1, 0, 15, hint=g15driver.HINT_MKEYS)
g15_backlight_control = g15driver.Control("keyboard_backlight", "Keyboard Backlight Level", 2, 0, 2, hint=g15driver.HINT_DIMMABLE)
g15_lcd_backlight_control = g15driver.Control("lcd_backlight", "LCD Backlight", 2, 0, 2, g15driver.HINT_SHADEABLE)
g15_lcd_contrast_control = g15driver.Control("lcd_contrast", "LCD Contrast", 22, 0, 48, 0)
g15_invert_control = g15driver.Control("invert_lcd", "Invert LCD", 0, 0, 1, hint=g15driver.HINT_SWITCH)
g15_controls = [ g15_mkeys_control, g15_backlight_control, g15_invert_control, g15_lcd_backlight_control, g15_lcd_contrast_control ]  
g11_controls = [ g15_mkeys_control, g15_backlight_control ]
g13_controls = [ g19_keyboard_backlight_control, g15_mkeys_control, g15_invert_control, g15_mkeys_control ]

"""
Keymaps that are sent to the kernel driver. These are the codes the driver
will emit.
 
"""
K_KEYMAPS = {
             g15driver.MODEL_G19: {
                                   0x0000 : S.KEY_F1,
                                   0x0001 : S.KEY_F2,
                                   0x0002 : S.KEY_F3,
                                   0x0003 : S.KEY_F4,
                                   0x0004 : S.KEY_F5,
                                   0x0005 : S.KEY_F6,
                                   0x0006 : S.KEY_F7,
                                   0x0007 : S.KEY_F8,
                                   0x0008 : S.KEY_F9,
                                   0x0009 : S.KEY_F10,
                                   0x000A : S.KEY_F11,
                                   0x000B : S.KEY_F12,
                                   0x000C : S.KEY_PROG1,
                                   0x000D : S.KEY_PROG2,
                                   0x000E : S.KEY_PROG3,
                                   0x000F : S.KEY_RECORD,
                                   0x0013 : 229,
                                   0x0018 : S.KEY_FORWARD,
                                   0x0019 : S.KEY_BACK,
                                   0x0020 : S.KEY_MENU,
                                   0x0021 : S.KEY_OK,
                                   0x0022 : S.KEY_RIGHT,
                                   0x0023 : S.KEY_LEFT,
                                   0x0024 : S.KEY_DOWN,
                                   0x0025 : S.KEY_UP                                   
                                   },
             g15driver.MODEL_G15_V1: {
                                   0x00 : S.KEY_F1,
                                   0x02 : S.KEY_F13,
                                   0x07 : 228,
                                   0x08 : S.KEY_F7,
                                   0x09 : S.KEY_F2,
                                   0x0b : S.KEY_F14,
                                   0x0f : S.KEY_LEFT,
                                   0x11 : S.KEY_F8,
                                   0x12 : S.KEY_F3,
                                   0x14 : S.KEY_F15,
                                   0x17 : S.KEY_UP,
                                   0x1a : S.KEY_F9,
                                   0x1b : S.KEY_F4,
                                   0x1d : S.KEY_F16,
                                   0x1f : S.KEY_DOWN,
                                   0x23 : S.KEY_F10,
                                   0x24 : S.KEY_F5,
                                   0x26 : S.KEY_F17,
                                   0x27 : S.KEY_RIGHT,
                                   0x28 : S.KEY_PROG1,
                                   0x2c : S.KEY_F11,
                                   0x2d : S.KEY_F6,
                                   0x31 : S.KEY_PROG2,
                                   0x35 : S.KEY_F12,
                                   0x36 : S.KEY_RECORD,
                                   0x3a : S.KEY_PROG3,
                                   0x3e : S.KEY_F18,
                                   0x3f : S.KEY_OK
                                   },
             g15driver.MODEL_G15_V2: {
                                   0 : S.KEY_F1,
                                   2 : S.KEY_F2,
                                   8 : S.KEY_F3,
                                   9 : S.KEY_F4,
                                   11 : S.KEY_F5,
                                   17 : S.KEY_F6,
                                   18 : S.KEY_F7,
                                   20 : S.KEY_F8,
                                   26 : S.KEY_F9,
                                   27 : S.KEY_F10,
                                   29 : S.KEY_F11,
                                   35 : S.KEY_F12,
                                   36 : S.KEY_F13,
                                   38 : S.KEY_F14,
                                   44 : S.KEY_F15,
                                   45 : S.KEY_F16,
                                   53 : S.KEY_F17,
                                   62 : S.KEY_F18
                                   },
             g15driver.MODEL_G13: {
                                   0x0000 : S.KEY_F1,
                                   0x0001 : S.KEY_F2,
                                   0x0002 : S.KEY_F3,
                                   0x0003 : S.KEY_F4,
                                   0x0004 : S.KEY_F5,
                                   0x0005 : S.KEY_F6,
                                   0x0006 : S.KEY_F7,
                                   0x0007 : S.KEY_F8,
                                   0x0008 : S.KEY_F9,
                                   0x0009 : S.KEY_F10,
                                   0x000A : S.KEY_F11,
                                   0x000B : S.KEY_F12,
                                   0x000C : S.KEY_F13,
                                   0x000D : S.KEY_F14,
                                   0x000E : S.KEY_F15,
                                   0x000F : S.KEY_F16,
                                   0x0010 : S.KEY_F17,
                                   0x0011 : S.KEY_F18,
                                   0x0012 : S.KEY_F19,
                                   0x0013 : S.KEY_F20,
                                   0x0014 : S.KEY_F21,
                                   0x0015 : S.KEY_F22,
                                   0x0016 : S.KEY_OK,
                                   0x0017 : S.KEY_LEFT,
                                   0x0018 : S.KEY_UP,
                                   0x0019 : S.KEY_DOWN,
                                   0x0020 : S.KEY_RIGHT,
                                   0x0021 : S.KEY_PROG1,
                                   0x0022 : S.KEY_PROG2,
                                   0x0023 : S.KEY_PROG3,
                                   0x0024 : S.KEY_RECORD,
                                   0x0025 : S.BTN_LEFT,
                                   0x0026 : S.BTN_RIGHT,
                                   0x0027 : S.BTN_MIDDLE,
                                   0x0028 : 228,
                                   },
             g15driver.MODEL_G110: {
                                   0x0000 : S.KEY_F1,
                                   0x0001 : S.KEY_F2,
                                   0x0002 : S.KEY_F3,
                                   0x0003 : S.KEY_F4,
                                   0x0004 : S.KEY_F5,
                                   0x0005 : S.KEY_F6,
                                   0x0006 : S.KEY_F7,
                                   0x0007 : S.KEY_F8,
                                   0x0008 : S.KEY_F9,
                                   0x0009 : S.KEY_F10,
                                   0x000A : S.KEY_F11,
                                   0x000B : S.KEY_F12,
                                   0x000C : S.KEY_PROG1,
                                   0x000D : S.KEY_PROG2,
                                   0x000E : S.KEY_PROG3,
                                   0x000F : S.KEY_RECORD,
                                   0x0013 : 229,
                                   },
             }

class DeviceInfo:
    def __init__(self, leds, controls, key_map, led_prefix, keydev_pattern, sink_pattern = None):
        self.leds = leds
        self.controls = controls
        self.key_map = key_map
        self.led_prefix = led_prefix 
        self.sink_pattern = sink_pattern
        self.keydev_pattern = keydev_pattern
        
device_info = {
               g15driver.MODEL_G19: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "red:mr" ], g19_controls, g19_key_map, "g19", r"usb-Logitech_G19_Gaming_Keyboard-event-if.*", r"usb-Logitech_G19_Gaming_Keyboard-event-kbd.*",), 
               g15driver.MODEL_G11: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "blue:mr" ], g11_controls, g15_key_map, "g15", r"G15_Keyboard_G15.*if"), 
               g15driver.MODEL_G15_V1: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "blue:mr" ], g15_controls, g15_key_map, "g15", r"G15_Keyboard_G15.*if"), 
               g15driver.MODEL_G15_V2: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "blue:mr" ], g15_controls, g15_key_map, "g15", r"G15_Keyboard_G15.*if"),
               g15driver.MODEL_G13: DeviceInfo(["red:m1", "red:m2", "red:m3", "red:mr" ], g13_controls, g13_key_map, "g13", r"_G13-event-mouse"),
               g15driver.MODEL_G110: DeviceInfo(["orange:m1", "orange:m2", "orange:m3", "red:mr" ], g110_controls, g110_key_map, "g110", r"usb-LOGITECH_G110_G-keys-event-if.*")
               }
        

# Other constants
EVIOCGRAB = 0x40044590

def show_preferences(device, parent, gconf_client):
    widget_tree = gtk.Builder()
    widget_tree.add_from_file(os.path.join(g15globals.glade_dir, "driver_kernel.glade"))  
    device_model = widget_tree.get_object("DeviceModel")
    device_model.clear()
    device_model.append(["auto"])
    for dir in os.listdir("/dev"):
        if dir.startswith("fb"):
            device_model.append(["/dev/" + dir])    
    g15util.configure_combo_from_gconf(gconf_client, "/apps/gnome15/%s/fb_device" % device.uid, "DeviceCombo", "auto", widget_tree)  
    g15util.configure_combo_from_gconf(gconf_client, "/apps/gnome15/%s/joymode" % device.uid, "JoyModeCombo", "macro", widget_tree)
    return widget_tree.get_object("DriverComponent")
    
class KeyboardReceiveThread(Thread):
    def __init__(self, device):
        Thread.__init__(self)
        self._run = True
        self.name = "KeyboardReceiveThread-%s" % device.uid
        self.setDaemon(True)
        self.devices = []
        
    def deactivate(self):
        self._run = False
        for dev in self.devices:
            logger.info("Ungrabbing %d" % dev.fileno())
            try :
                fcntl.ioctl(dev.fileno(), EVIOCGRAB, 0)
            except Exception as e:
                logger.info("Failed ungrab. %s" % str(e))
            logger.info("Closing %d" % dev.fileno())
            try :
                self.fds[dev.fileno()].close()
            except Exception as e:
                logger.info("Failed close. %s" % str(e))
            logger.info("Stopped %d" % dev.fileno())
        logger.info("Stopped all input devices")
        
    def run(self):        
        self.poll = select.poll()
        self.fds = {}
        for dev in self.devices:
            self.poll.register(dev, select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLNVAL | select.POLLERR)
            fcntl.ioctl(dev.fileno(), EVIOCGRAB, 1)
            self.fds[dev.fileno()] = dev
        while self._run:
            for x, e in self.poll.poll(1000):
                dev = self.fds[x]
                try :
                    dev.read()
                except OSError as e:
                    # Ignore this error if deactivated
                    if self._run:
                        raise e
        logger.info("Thread left")
        
'''
SimpleDevice implementation that does nothng with events. This is used to
work-around a problem where X ends up getting the G19 F-key events
'''
class SinkDevice(SimpleDevice):
    def __init__(self, *args, **kwargs):
        SimpleDevice.__init__(self, *args, **kwargs)
        
    def receive(self, event):
        pass

'''
SimpleDevice implementation that translates kernel input events
into Gnome15 key events and forwards them to the registered 
Gnome15 keyboard callback.
'''
class ForwardDevice(SimpleDevice):
    def __init__(self, driver, callback, key_map, *args, **kwargs):
        SimpleDevice.__init__(self, *args, **kwargs)
        self.callback = callback
        self.driver = driver
        self.key_map = key_map
        self.ctrl = False
        self.held_keys = []
        self.alt = False
        self.shift = False
        self.current_x = 0
        self.current_y = 0
        self.last_x = 0
        self.last_y = 0
        self.move_timer = None
        self.state = None
        self.doq = False # queue keystrokes for processing?
        self.mouseev = []
        self.keyev = []

    def send_all(self, events):
        for event in events:
            logger.debug(" --> %r" % event)
            self.udev.send_event(event)

    @property
    def modcode(self):
        code = 0
        if self.shift:
            code += 1
        if self.ctrl:
            code += 2
        if self.alt:
            code += 4
        return code
    
    def receive(self, event):
        
        # For now, emulate a digital joystick
        if event.etype == S.EV_ABS:
            if self.driver.joy_mode == "joystick":
                self._abs_joystick(event)
            elif self.driver.joy_mode == "mouse":
                low_val = 128 - self.driver.calibration
                high_val = 128 + self.driver.calibration
                
                if event.ecode == S.REL_X:
                    self.current_x = event.evalue
                if event.ecode == S.REL_Y:
                    self.current_y = event.evalue
                
                # Get the amount between the current value and the centre to move
                move_x = 0    
                move_y = 0
                if self.current_x >= high_val:
                    move_x = self.current_x - high_val
                elif self.current_x <= low_val:
                    move_x = self.current_x - low_val
                if self.current_y >= high_val:
                    move_y = self.current_y - high_val
                elif self.current_y <= low_val:
                    move_y = self.current_y - low_val
                    
                if self.current_x != self.last_x or self.current_y != self.last_y:
                    self.last_x = self.current_x
                    self.last_y = self.current_y
                    self.move_x = move_x / 8
                    
                    
                    self.move_y = self._clamp(-3, move_y / 8, 3) 
                    self.move_x = self._clamp(-3, move_x / 8, 3) 
                    self._mouse_move()
                else:
                    if self.move_timer is not None:                    
                        self.move_timer.cancel()
            else:
                self._emit_macro(event)                        
        elif event.etype == S.EV_KEY:
            state = g15driver.KEY_STATE_DOWN if event.evalue == 1 else g15driver.KEY_STATE_UP
            if event.evalue == 2:
                # Drop auto repeat for now
                return
            else:
                if event.ecode in [ S.BTN_LEFT, S.BTN_RIGHT, S.BTN_MIDDLE ]:
                    """
                    Handle joystick buttons separately
                    """
                    if self.driver.joy_mode == "mouse":                    
                        g15uinput.emit(g15uinput.MOUSE, event.ecode, event.evalue, syn=True)                
                    elif self.driver.joy_mode == "joystick":
                        g15uinput.emit(g15uinput.JOYSTICK, self._translate_joystick_buttons(event.ecode), event.evalue, syn=True)                
                    else:
                        self._event(self._translate_joystick_buttons(event.ecode), state)
                else:
                    self._event(event.ecode, state)
        elif event.etype == 0:
            return
        else:
            logger.warning("Unhandled event: %s" % str(event))
            
    def _emit_macro(self, event):
        low_val = 128 - ( self.driver.calibration * 2 )
        high_val = 128 + ( self.driver.calibration * 2 )
        if event.ecode == S.REL_X:
            if event.evalue < low_val:
                self._release_keys([g15driver.G_KEY_RIGHT])
                if not g15driver.G_KEY_LEFT in self.held_keys:
                    self.callback([g15driver.G_KEY_LEFT], g15driver.KEY_STATE_DOWN)
                    self.held_keys.append(g15driver.G_KEY_LEFT)
            elif event.evalue > high_val:
                self._release_keys([g15driver.G_KEY_LEFT])
                if not g15driver.G_KEY_RIGHT in self.held_keys:
                    self.callback([g15driver.G_KEY_RIGHT], g15driver.KEY_STATE_DOWN)
                    self.held_keys.append(g15driver.G_KEY_RIGHT)
            else:                                         
                self._release_keys([g15driver.G_KEY_LEFT,g15driver.G_KEY_RIGHT])    
        if event.ecode == S.REL_Y:
            if event.evalue < low_val:
                self._release_keys([g15driver.G_KEY_DOWN])
                if not g15driver.G_KEY_UP in self.held_keys:
                    self.callback([g15driver.G_KEY_UP], g15driver.KEY_STATE_DOWN)
                    self.held_keys.append(g15driver.G_KEY_UP)                        
            if event.evalue > high_val:
                self._release_keys([g15driver.G_KEY_UP])
                if  not g15driver.G_KEY_DOWN in self.held_keys:
                    self.callback([g15driver.G_KEY_DOWN], g15driver.KEY_STATE_DOWN)
                    self.held_keys.append(g15driver.G_KEY_DOWN)
            else:                                         
                self._release_keys([g15driver.G_KEY_UP,g15driver.G_KEY_DOWN])
                
    def _release_keys(self, keys):
        for k in keys:
            if k in self.held_keys:
                self.callback([k], g15driver.KEY_STATE_UP)
                self.held_keys.remove(k)
                
    
    def _clamp(self, minimum, x, maximum):
        return max(minimum, min(x, maximum))

    def _mouse_move(self):
        if self.move_x != 0 or self.move_y != 0:
            if self.move_x != 0:
                g15uinput.emit(g15uinput.MOUSE, uinput.REL_X, self.move_x)        
            if self.move_y != 0:
                g15uinput.emit(g15uinput.MOUSE, uinput.REL_Y, self.move_y)
            self.move_timer = g15util.schedule("MouseMove", 0.1, self._mouse_move)
            
    def _translate_joystick_buttons(self, ecode):
        if ecode == S.BTN_LEFT:
            return uinput.BTN_0
        elif ecode == S.BTN_RIGHT:
            return uinput.BTN_1
        elif ecode == S.BTN_MIDDLE:
            return uinput.BTN_2
        
    def _abs_joystick(self, event):
#        self._check_js_buttons(this_keys) 
        g15uinput.emit(g15uinput.JOYSTICK, uinput.ABS_X if event.ecode == S.REL_X else uinput.ABS_Y, event.evalue, syn=True)

    def _event(self, event_code, state):
        if event_code in self.key_map:
            key = self.key_map[event_code]
            self.callback([key], state)
        else:
            logger.warning("Unmapped key for event: %s" % event_code)

class Driver(g15driver.AbstractDriver):

    def __init__(self, device, on_close=None):
        g15driver.AbstractDriver.__init__(self, "kernel")
        self.fb = None
        self.var_info = None
        self.on_close = on_close
        self.key_thread = None
        self.device = device
        self.device_info = None
        self.system_service = None
        self.conf_client = gconf.client_get_default()
        
        try:
            self._init_device()
        except Exception as e:
            # Reset the framebuffer choice back to auto if the requested device does not exist
            if self.device_name != None and self.device_name != "" or self.device_name != "auto":
                self.conf_client.set_string("/apps/gnome15/%s/fb_device" % self.device.uid, "auto")
                self._init_device()
            else:            
                logger.warning("Could not open %s. %s" %(self.device_name, str(e)))
    
    def get_antialias(self):         
        if self.device.bpp != 1:
            return cairo.ANTIALIAS_DEFAULT
        else:
            return cairo.ANTIALIAS_NONE
        
    def on_disconnect(self):
        if not self.is_connected():
            raise Exception("Not connected")
        
        g15uinput.deregister_codes("g15_kernel/%s" % self.device.uid)
        for h in self.notify_handles:
            self.conf_client.notify_remove(h)
        self._stop_receiving_keys()
        self.fb.__del__()
        self.fb = None
        if self.on_close != None:
            g15util.schedule("Close", 0, self.on_close, self)
        self.system_service = None
        
    def is_connected(self):
        return self.system_service != None
    
    def get_model_names(self):
        return device_info.keys()
            
    def get_name(self):
        return "Linux Logitech Kernel Driver"
    
    def get_model_name(self):
        return self.device.model_id if self.device != None else None
    
    def simulate_key(self, widget, key, state):
        if self.callback != None:
            keys = []
            keys.append(key)
            self.callback(keys, state)
    
    def get_action_keys(self):
        return self.device.action_keys
        
    def get_key_layout(self):
        if self.get_model_name() == g15driver.MODEL_G13 and "macro" == self.conf_client.get_string("/apps/gnome15/%s/joymode" % self.device.uid):
            """
            This driver with the G13 supports some additional keys
            """
            l = list(self.device.key_layout)
            l.append([ g15driver.G_KEY_UP ])
            l.append([ g15driver.G_KEY_JOY_LEFT, g15driver.G_KEY_LEFT, g15driver.G_KEY_JOY_CENTER, g15driver.G_KEY_RIGHT ])
            l.append([ g15driver.G_KEY_JOY_DOWN, g15driver.G_KEY_DOWN ])
            return l
        else:
            return self.device.key_layout
        
    def connect(self):
        if self.is_connected():
            raise Exception("Already connected")
        
        self.notify_handles = []
        # Check hardware again
        self._init_driver()

        # Sanity check        
        if not self.device:
            raise usb.USBError("No supported logitech keyboards found on USB bus")
        if self.device == None:
            raise usb.USBError("WARNING: Found no " + self.model + " Logitech keyboard, Giving up")
        
        # If there is no LCD for this device, don't open the framebuffer
        if self.device.bpp != 0:
            if self.fb_mode == None or self.device_name == None:
                raise usb.USBError("No matching framebuffer device found")
            if self.fb_mode != self.framebuffer_mode:
                raise usb.USBError("Unexpected framebuffer mode %s, expected %s for device %s" % (self.fb_mode, self.framebuffer_mode, self.device_name))
            
            # Open framebuffer
            logger.info("Using framebuffer %s"  % self.device_name)
            self.fb = fb.fb_device(self.device_name)
            if logger.isEnabledFor(logging.DEBUG):
                self.fb.dump()
            self.var_info = self.fb.get_var_info()
                    
            # Create an empty string buffer for use with monochrome LCD
            self.empty_buf = ""
            for i in range(0, self.fb.get_fixed_info().smem_len):
                self.empty_buf += chr(0)
            
        # Connect to DBUS        
        system_bus = dbus.SystemBus()
        system_service_object = system_bus.get_object('org.gnome15.SystemService', '/org/gnome15/SystemService')     
        self.system_service = dbus.Interface(system_service_object, 'org.gnome15.SystemService')    
        # Setup joystick configuration on G13
        self.calibration = 18   
        self._load_configuration()
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/%s/joymode" % self.device.uid, self._config_changed, None))
        self.notify_handles.append(self.conf_client.notify_add("/apps/gnome15/%s/fb_device" % self.device.uid, self._framebuffer_device_changed, None))
             
                   
    def _load_configuration(self):
        self.joy_mode = self.conf_client.get_string("/apps/gnome15/%s/joymode" % self.device.uid)
        g15uinput.deregister_codes("g15_kernel/%s" % self.device.uid)
        if self.joy_mode == "mouse":
            logger.info("Enabling mouse emulation")            
            g15uinput.register_codes("g15_kernel/%s" % self.device.uid, g15uinput.MOUSE, [uinput.BTN_MOUSE, uinput.BTN_RIGHT, uinput.BTN_MIDDLE ])
        elif self.joy_mode == "joystick":
            logger.info("Enabling joystick emulation")            
            g15uinput.register_codes("g15_kernel/%s" % self.device.uid, g15uinput.JOYSTICK, [uinput.BTN_0, uinput.BTN_1, uinput.BTN_2 ], {
                                        uinput.ABS_X: (0, 255, 0, 0),
                                        uinput.ABS_Y: (0, 255, 0, 0),
                                                 })
        else:
            logger.info("Enabling macro keys for joystick")
            
    def _config_changed(self, client, connection_id, entry, args):
        self._load_configuration()
        
    def _framebuffer_device_changed(self, client, connection_id, entry, args):
        if self.is_connected():
            self.disconnect()
        
    def get_size(self):
        return self.device.lcd_size
        
    def get_bpp(self):
        return self.device.bpp
    
    def get_controls(self):
        return self.device_info.controls if self.device_info != None else None
    
    def paint(self, img):  
        if not self.fb:
            return 
        width = img.get_width()
        height = img.get_height()
        character_width = width / 8
        fixed = self.fb.get_fixed_info()
        padding = fixed.line_length - character_width
        file_str = StringIO()
        
        if self.get_model_name() == g15driver.MODEL_G19:
            try:
                back_surface = cairo.ImageSurface (4, width, height)
            except:
                # Earlier version of Cairo
                back_surface = cairo.ImageSurface (cairo.FORMAT_ARGB32, width, height)
            back_context = cairo.Context (back_surface)
            back_context.set_source_surface(img, 0, 0)
            back_context.set_operator (cairo.OPERATOR_SOURCE);
            back_context.paint()
                
            if back_surface.get_format() == cairo.FORMAT_ARGB32:
                """
                If the creation of the type 4 image failed (i.e. earlier version of Cairo)
                then we have to convert it ourselves. This is slow. 
                
                TODO Replace with C routine 
                """
                file_str = StringIO()
                data = back_surface.get_data()
                for i in range(0, len(data), 4):
                    r = ord(data[i + 2])
                    g = ord(data[i + 1])
                    b = ord(data[i + 0])
                    file_str.write(self.rgb_to_uint16(r, g, b))             
                buf = file_str.getvalue()
            else:   
                buf = str(back_surface.get_data())
        else:
            width, height = self.get_size()
            arrbuf = array.array('B', self.empty_buf)
            
            argb_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            argb_context = cairo.Context(argb_surface)
            argb_context.set_source_surface(img)
            argb_context.paint()
            
            '''
            Now convert the ARGB to a PIL image so it can be converted to a 1 bit monochrome image, with all
            colours dithered. It would be nice if Cairo could do this :( Any suggestions?
            ''' 
            pil_img = Image.frombuffer("RGBA", (width, height), argb_surface.get_data(), "raw", "RGBA", 0, 1)
            pil_img = ImageMath.eval("convert(pil_img,'1')",pil_img=pil_img)
            pil_img = ImageMath.eval("convert(pil_img,'P')",pil_img=pil_img)
            pil_img = pil_img.point(lambda i: i >= 250,'1')
            
            # Invert the screen if required
            if g15_invert_control.value == 0:            
                pil_img = pil_img.point(lambda i: 1^i)
            
            # Data is 160x43, 1 byte per pixel. Will have value of 0 or 1.
            width, height = self.get_size()
            data = list(pil_img.getdata())
            fixed = self.fb.get_fixed_info()
            v = 0
            b = 1
            
            # TODO Replace with C routine
            for row in range(0, height):
                for col in range(0, width):
                    if data[( row * width ) + col]:
                        v += b
                    b = b << 1
                    if b == 256:
                        # Full byte
                        b = 1          
                        i = row * fixed.line_length + col / 8
                        
                        if row > 7 and col < 96:
                            '''
                            ????? This was discovered more by trial and error rather than any 
                            understanding of what is going on
                            '''
                            i -= 12 + ( 7 * fixed.line_length )
                            
                        arrbuf[i] = v   
                        v = 0 
            buf = arrbuf.tostring()
                
        if self.fb and self.fb.buffer:
            self.fb.buffer[0:len(buf)] = buf
            
    def process_svg(self, document):  
        if self.get_bpp() == 1:
            for element in document.getroot().iter():
                style = element.get("style")
                if style != None:
                    element.set("style", style.replace("font-family:Sans", "font-family:%s" % g15globals.fixed_size_font_name))
                    
    def on_update_control(self, control):
        if control == g19_keyboard_backlight_control or control == g110_keyboard_backlight_control:
            self._write_to_led("red:bl", control.value[0])
            if control.hint & g15driver.HINT_RED_BLUE_LED == 0:
                self._write_to_led("green:bl", control.value[1])
            self._write_to_led("blue:bl", control.value[2])            
        elif control == g15_backlight_control:
            self._write_to_led("blue:keys", control.value)          
        elif control == g15_lcd_backlight_control:
            self._write_to_led("white:screen", control.value)          
        elif control == g15_lcd_contrast_control:
            self._write_to_led("contrast:screen", control.value)          
        elif control == g15_mkeys_control or control == g19_mkeys_control:
            self._set_mkey_lights(control.value)
        else:
            logger.warning("Setting the control " + control.id + " is not yet supported on this model. " + \
                           "Please report this as a bug, providing the contents of your /sys/class/led" + \
                           "directory and the keyboard model you use.")
    
    def grab_keyboard(self, callback):
        if self.key_thread != None:
            raise Exception("Keyboard already grabbed")
        
        # Configure the keymap
        logger.info("Grabbing current keymap settings")
        self.keymap_index = self.system_service.GetKeymapIndex(self.device.uid)
        self.keymap_switching = self.system_service.GetKeymapSwitching(self.device.uid)
        self.current_keymap = self.system_service.GetKeymap(self.device.uid)
        new_keymap = self.current_keymap.copy()
        logger.info("Disabling keymap switching")
        self.system_service.SetKeymapSwitching(self.device.uid, False)
        logger.info("Resetting keymap index")        
        self.system_service.SetKeymapIndex(self.device.uid, 0)
        kernel_keymap_replacement = K_KEYMAPS[self.device.model_id]
        self.system_service.SetKeymap(self.device.uid, kernel_keymap_replacement)
              
        self.key_thread = KeyboardReceiveThread(self.device)
        for devpath in self.keyboard_devices:
            logger.info("Adding input device %s" % devpath)
            self.key_thread.devices.append(ForwardDevice(self, callback, self.device_info.key_map, devpath, devpath))
        for devpath in self.sink_devices:
            logger.info("Adding input sink device %s" % devpath)
            self.key_thread.devices.append(SinkDevice(devpath, devpath))
        self.key_thread.start()
        
    '''
    Private
    '''
    def _set_mkey_lights(self, lights):
        if self.device_info.leds:
            leds = self.device_info.leds
            self._write_to_led(leds[0], lights & g15driver.MKEY_LIGHT_1 != 0)        
            self._write_to_led(leds[1], lights & g15driver.MKEY_LIGHT_2 != 0)        
            self._write_to_led(leds[2], lights & g15driver.MKEY_LIGHT_3 != 0)        
            self._write_to_led(leds[3], lights & g15driver.MKEY_LIGHT_MR != 0)
        else:
            logger.warning(" Setting MKey lights on " + self.device.model_id + " not yet supported. " + \
            "Please report this as a bug, providing the contents of your /sys/class/led" + \
            "directory and the keyboard model you use.")
    
    def _stop_receiving_keys(self):
        if self.key_thread != None:
            self.key_thread.deactivate()
            self.key_thread = None
            
            # Configure the keymap
            logger.info("Resetting keymap settings back to the way they were")
            self.system_service.SetKeymapSwitching(self.device.uid, self.keymap_switching)
            self.system_service.SetKeymapIndex(self.device.uid, self.keymap_index)        
            self.system_service.SetKeymap(self.device.uid, self.current_keymap)
            
    def _do_write_to_led(self, name, value):
        if not self.system_service:
            logger.warning("Attempt to write to LED when not connected")
        else:
            logger.debug("Writing %d to LED %s" % (value, name ))
            self.system_service.SetLight(self.device.uid, name, value)
    
    def _write_to_led(self, name, value):
        gobject.idle_add(self._do_write_to_led, name, value)

    
    def _handle_bound_key(self, key):
        logger.info("G key - %d", key)
        return True
        
    def _mode_changed(self, client, connection_id, entry, args):
        if self.is_connected():
            self.disconnect()
        else:
            logger.warning("WARNING: Mode change would cause disconnect when already connected.", entry)
            
    def _init_device(self):
        if not self.device.model_id in device_info:
            return
            
        self.device_info = device_info[self.device.model_id]
        
        if self.device.bpp == 1:
            self.framebuffer_mode = "GFB_MONO"
        else:
            self.framebuffer_mode = "GFB_QVGA"
        logger.info("Using %s frame buffer mode" % self.framebuffer_mode)
            
                
        # Determine the framebuffer device to use
        self.device_name = self.conf_client.get_string("/apps/gnome15/%s/fb_device" % self.device.uid)
        self.fb_mode = None
        if self.device_name == None or self.device_name == "" or self.device_name == "auto":
            
            # Find the first framebuffer device that matches the mode
            for fb in os.listdir("/sys/class/graphics"):
                if fb != "fbcon":
                    try:
                        logger.info("Trying %s" %fb)
                        f = open("/sys/class/graphics/" + fb + "/name", "r")
                        try :
                            fb_mode = f.readline().replace("\n", "")
                            logger.info("%s is a %s" % ( fb, fb_mode ) )
                            if fb_mode == self.framebuffer_mode:
                                self.fb_mode = fb_mode
                                self.device_name = "/dev/" + fb
                                break
                        finally :
                            f.close() 
                    except Exception as e:
                        logger.warning("Could not open %s. %s" %(self.device_name, str(e)))
        else:
            f = open("/sys/class/graphics/" + os.path.basename(self.device_name) + "/name", "r")
            try :
                self.fb_mode = f.readline().replace("\n", "")
            finally :
                f.close() 
        
    def _init_driver(self):
        self._init_device()
            
        # Try and find the paths for the keyboard devices
        self.keyboard_devices = []
        self.sink_devices = []
        dir = "/dev/input/by-id"
        for p in os.listdir(dir):
            if re.search(self.device_info.keydev_pattern, p):
                logger.info("Input device %s matches %s" % (p, self.device_info.keydev_pattern))
                self.keyboard_devices.append(dir + "/" + p)
            if self.device_info.sink_pattern is not None and re.search(self.device_info.sink_pattern, p):
                logger.info("Input sink device %s matches %s" % (p, self.device_info.sink_pattern))
                self.sink_devices.append(dir + "/" + p)