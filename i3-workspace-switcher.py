#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import fcntl
import signal
import argparse
try:
    import tkinter
except ImportError:
    import Tkinter as tkinter
import i3ipc


KEY_MAPPING = {
    # i3-to-Tk key mapping
    'Mod1': 'Alt_L',
    'Mod4': 'Super_L',
    'Control': 'Control_L',
    'Shift': 'Shift_L',
}


class Workspace(object):

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

    @classmethod
    def from_container(cls, container):
        return cls(id=container.id, name=container.name)


class HistoryJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        return obj.name


class EventListener(object):

    def __init__(self, i3, history_file_path, size=None):
        i3.on('workspace', self.dispatch_event)
        self.i3 = i3
        self.history_file_path = history_file_path
        self.size = size if isinstance(size, int) and size > 1 else None
        self.history = []

    def run(self):
        try:
            os.unlink(self.history_file_path)
        except OSError:
            pass
        self.i3.main()

    def run_forever(self):
        while True:
            try:
                self.run()
            except Exception:
                time.sleep(1)
            self.history = []

    def write_history(self):
        with open(self.history_file_path, 'w') as history_file_obj:
            json.dump(self.history, history_file_obj, cls=HistoryJSONEncoder)

    def remove_workspace(self, workspace):
        try:
            self.history.remove(workspace)
        except ValueError:
            return False
        return True

    def dispatch_event(self, connection, event):
        event_handler = getattr(self, 'on_' + event.change, None)
        if not event_handler:
            return
        current = Workspace.from_container(event.current)
        old = Workspace.from_container(event.old) if event.old else None
        is_changed = event_handler(current, old)
        if is_changed:
            self.write_history()

    def on_focus(self, current, old):
        if not self.history and old:
            self.history.append(old)
        self.remove_workspace(current)
        self.history.insert(0, current)
        if self.size and len(self.history) > self.size:
            self.history = self.history[:self.size]
        return True

    def on_rename(self, current, old):
        try:
            index = self.history.index(current)
        except ValueError:
            return False
        self.history[index] = current
        return True

    def on_empty(self, current, old):
        return self.remove_workspace(current)


class GUI(object):

    def __init__(self, i3, history, mod='Super_L', reverse=False,
                 gui_options=None):
        self.i3 = i3
        self.history = history
        self.position = (len(history) - 1) if reverse else 1
        signal.signal(signal.SIGUSR1, self.sigusr1_handler)
        signal.signal(signal.SIGUSR2, self.sigusr2_handler)
        root = tkinter.Tk(className='i3-workspace-switcher')
        root.bind_all('<KeyRelease-{}>'.format(mod), self.mod_released)
        width = max(map(len, history))
        height = len(history)
        listbox = tkinter.Listbox(root, width=width, height=height)
        if gui_options:
            listbox.config(**gui_options)
        listbox.pack()
        listbox.focus()
        for workspace_name in history:
            listbox.insert('end', workspace_name)
        self.root = root
        self.listbox = listbox
        self.draw()

    def exit(self):
        self.root.destroy()
        self.i3.command('workspace ' + self.history[self.position])

    def run(self):
        self.root.mainloop()

    def draw(self):
        self.listbox.activate(self.position)

    def mod_released(self, event):
        self.exit()

    def sigusr1_handler(self, signal, frame):
        position = self.position + 1
        if position >= len(self.history):
            position = 0
        self.position = position
        self.draw()

    def sigusr2_handler(self, signal, frame):
        position = self.position - 1
        if position < 0:
            position = len(self.history) - 1
        self.position = position
        self.draw()


if __name__ == '__main__':
    run_dir = os.getenv('XDG_RUNTIME_DIR')
    if run_dir is None:
        sys.exit("env variable XDG_RUNTIME_DIR doesn't exist")

    parser = argparse.ArgumentParser(description='i3-workspace-switcher')
    parser.add_argument('-d', '--daemon',
                        action='store_true',
                        help='run daemon')
    parser.add_argument('-s', '--size',
                        type=int,
                        default=None,
                        help='limit history size')
    parser.add_argument('-m', '--mod',
                        default='Mod4',
                        choices=KEY_MAPPING.keys(),
                        help='i3 modifier key; default: Mod4 (Super)')
    parser.add_argument('-r', '--reverse',
                        action='store_true',
                        help='reverse order')
    args, extra_args = parser.parse_known_args()

    history_file_path = os.path.join(run_dir, 'i3-workspace-switcher.history')
    i3 = i3ipc.Connection()

    if args.daemon:
        EventListener(i3=i3, history_file_path=history_file_path,
                      size=args.size).run_forever()

    elif not os.path.exists(history_file_path):
        sys.exit("history file doesn't exist")

    else:
        with open(history_file_path, 'r') as history_file_obj:
            try:
                history = json.load(history_file_obj)
                if not isinstance(history, list) or len(history) < 2:
                    raise ValueError
            except ValueError:
                sys.exit()

        pid_file_path = os.path.join(run_dir, 'i3-workspace-switcher.gui.pid')
        mode = 'r+' if os.path.exists(pid_file_path) else 'w'
        pid_file_obj = open(pid_file_path, mode)
        try:
            fcntl.lockf(pid_file_obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            pid = int(pid_file_obj.read())
            pid_file_obj.close()
            os.kill(pid, signal.SIGUSR2 if args.reverse else signal.SIGUSR1)
            sys.exit()
        pid = str(os.getpid())
        pid_file_obj.seek(0)
        pid_file_obj.truncate()
        pid_file_obj.write(pid)
        pid_file_obj.flush()

        gui_options_list = []
        for item in extra_args:
            item = item.lstrip('-')
            if '=' in item:
                gui_options_list.extend(item.split('=', 1))
            else:
                gui_options_list.append(item)
        gui_options = dict(zip(gui_options_list[::2], gui_options_list[1::2]))

        GUI(i3=i3, history=history, mod=KEY_MAPPING[args.mod],
            reverse=args.reverse, gui_options=gui_options).run()

        pid_file_obj.close()
        os.unlink(pid_file_path)
