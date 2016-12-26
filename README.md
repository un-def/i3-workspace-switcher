i3-workspace-switcher
=====================

A workspace switcher for [i3 window manager][i3] that acts like Windows Alt-Tab application switcher

[![screenshot][screenshot-preview]][screenshot]

**NOTICE**: This is just-for-fun one-night project. There is at least one notable bug: if you release the binding keys too fast, the popup window stays on screen. In this case, you should press and release the modifier button (usually Alt or Super) one more time.



### Requirements

* Python (2 or 3)
* Tcl/Tk/Tkinter — `apt-get install python-tk` on Ubuntu
* [i3ipc-python][i3ipc-python] — `pip install i3ipc-python`



### Configuration

Add these strings to your i3 config:

```shell
# set super key as modifier
# use Mod1 for Alt key
# usually this string is already present in the config
set $mod Mod4

# set the path to the script
set $ws $HOME/bin/i3-workspace-switcher.py

# set gui options
# see http://effbot.org/tkinterbook/listbox.htm#Tkinter.Listbox.config-method for options description
set $ws_options --borderwidth 10 --selectborderwidth=3 --activestyle=dotbox --relief=flat --font='Ubuntu 16 bold' --background='#551a8b' --foreground '#ffffff'

# bindings: Super+Tab and Super+Shift+Tab
bindsym $mod+Tab exec --no-startup-id $ws --mod $mod $ws_options
bindsym $mod+Shift+Tab exec --no-startup-id $ws --mod $mod --reverse $ws_options

# run the daemon on i3 startup
# it's necessary to keep the history of workspaces
# store 5 last active workspaces in the history
exec --no-startup-id $ws --daemon --size 5

# enable floating mode and hide both border and title for switcher window
for_window [class="^I3-workspace-switcher$"] floating enable border none
```



[i3]: https://i3wm.org/
[screenshot-preview]: https://i.imgur.com/kIkZhQk.png
[screenshot]: https://i.imgur.com/NtiY6wS.png
[i3ipc-python]: https://github.com/acrisci/i3ipc-python
