"""
Snipe

todo 各種機能の隠匿(_)
todo きちんと型ヒント・docstringをつける
todo 記号もキー認識するようにしたい(キーにならない場合はエラーにする？？)
todo readmeをきちんと書きたい
todo listenerをthreadingしなきゃいけないかもしれない(notifyがでないから)
"""

import time
import Quartz
import platform
from typing import Callable, NamedTuple, Dict, List
import sys
import os
import json
import subprocess

__author__ = 'Nomutin'
__version__ = '2.1'

JSON = 'snippets.json'

assert platform.system() == 'Darwin', 'This app is NOT available on any OS other than MacOSX.'


class SnippetContainer(NamedTuple):
    with open(JSON, 'r') as _j:
        snippets: Dict[str, List[str]] = json.load(_j)

    def _auto_rebuild(self, _rb: bool = True) -> None:
        if _rb:
            with open(JSON, 'w') as _j:
                json.dump(self.snippets, _j, indent=4)

    def add_snippet_from_txt(self, fp, _rb=True):
        key = os.path.splitext(os.path.basename(fp))[0]
        with open(fp, 'r') as file:
            values = file.readlines()

        self.snippets[key] = values
        self._auto_rebuild(_rb)


class SnipeStr:
    """ 文字数制限を行うstr """
    content: str = ''
    max_length: int = 10
    auto_free: bool = True

    def __iadd__(self, char_: str):
        assert len(char_) == 1, f"Added srtring('{char_}') must be a character."

        if len(self.content) >= self.max_length and self.auto_free:
            self.content = self.content[1:] + char_
        else:
            self.content += char_

        return self

    def clear(self) -> None:
        self.content = ''

    def __repr__(self) -> str:
        return self.content


class PyAutoGUI:
    km = {'v': 0x09, 'backspace': 0x33, 'command': 0x36, 'option': 0x3a,}  # Needed minimum keymap

    def keyUpDown(self, updown: str, key: str, _pause: bool = True) -> None:
        try:
            _key_code = self.km[key]
            _event = Quartz.CGEventCreateKeyboardEvent(None, _key_code, updown == 'down')
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, _event)
            time.sleep(0.1)

        except KeyError:
            return

    def delete(self) -> None:
        """
        FIXME: できない
        """
        event1 = Quartz.CGEventCreateKeyboardEvent(None, 58, True)
        event2 = Quartz.CGEventCreateKeyboardEvent(None, 58, False)
        event3 = Quartz.CGEventCreateKeyboardEvent(None, 51, True)
        event4 = Quartz.CGEventCreateKeyboardEvent(None, 51, False)

        Quartz.CGEventSetFlags(event3, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventSetFlags(event4, Quartz.kCGEventFlagMaskCommand)

        Quartz.CGEventPost(0, event1)
        Quartz.CGEventPost(0, event2)
        Quartz.CGEventPost(0, event3)
        Quartz.CGEventPost(0, event4)

    def paste(self) -> None:
        event1 = Quartz.CGEventCreateKeyboardEvent(None, 55, True)
        event2 = Quartz.CGEventCreateKeyboardEvent(None, 55, False)
        event3 = Quartz.CGEventCreateKeyboardEvent(None, 9, True)
        event4 = Quartz.CGEventCreateKeyboardEvent(None, 9, False)

        Quartz.CGEventSetFlags(event3, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventSetFlags(event4, Quartz.kCGEventFlagMaskCommand)

        Quartz.CGEventPost(0, event1)
        Quartz.CGEventPost(0, event2)
        Quartz.CGEventPost(0, event3)
        Quartz.CGEventPost(0, event4)


class Listener:
    """
    引数_on_pressはcharacterを引数とする関数
    """

    def __init__(self, _on_press: Callable = lambda _: None):
        _e = [0, 11, 8, 2, 14, 3, 5, 4, 34, 38, 40, 37, 46, 45, 31, 35, 12, 15, 1, 17, 32, 9, 13, 7, 16, 6]
        self.keymap = {code: chr(i + 97) for i, code in enumerate(_e)}
        self.on_press = _on_press

    def _event_call_back(self, roxy, etype, event, refcon):
        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)

        try:
            self.on_press(self.keymap[keycode])
        except KeyError:
            pass

        return event

    def on(self):
        mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
        tap = Quartz.CGEventTapCreate(Quartz.kCGSessionEventTap,
                                      Quartz.kCGHeadInsertEventTap, 0, mask, self._event_call_back, None)

        assert tap, "failed to create event tap"

        run_loop_source = Quartz.CFMachPortCreateRunLoopSource(Quartz.kCFAllocatorDefault, tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), run_loop_source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(tap, True)
        Quartz.CFRunLoopRun()

    @staticmethod
    def off():
        Quartz.CFRunLoopStop()


class Sniper:
    def __init__(self):
        self.snippetContainer = SnippetContainer()
        self.record = SnipeStr()
        self.listener = Listener(self._on_press)

    def hold(self):
        notify('keyboardTracking: ON')
        self.listener.on()

    def down(self):
        self.listener.off()
        notify('keyboardTracking: OFF')

    def _on_press(self, char_):
        self.record += char_
        for snippet in self.snippetContainer.snippets:
            if snippet in self.record.content:
                self.entered_snippet(snippet)
                notify(f'Entered {snippet}')

    @staticmethod
    def _copy(text):
        p = subprocess.Popen(['pbcopy', 'w'], stdin=subprocess.PIPE, close_fds=True)
        p.communicate(input=str(text).encode('utf-8'))

    def entered_snippet(self, _key: str):
        """
        スニペット入力時のプロセス
        文字消去->クリップボードにスニペット(listを結合したもの)を貼り付け->ペースト->SnipeStr.recordを消去
        """
        pgui = PyAutoGUI()
        pgui.delete()
        _value = self.snippetContainer.snippets[_key]
        self._copy(''.join(_value))
        pgui.paste()
        self.record.clear()


class Main:
    welcome = f"Sniper {__version__}\nkeyboardTracking: on\n"

    help = f"\nq ... Exit App\nn ... Turn on Keyboard Tracking\nf ... Turn off Keyboard Tracking\n"

    s = Sniper()

    def run(self):
        notify('Welcome to Sniper!')
        print(self.welcome)

        self.s.hold()

        while True:
            a = input('>>')
            if hasattr(self, a):
                getattr(self, a)()
            else:
                print(f'Oops! "{a}" is not command! Type "h" for more information.')

    def q(self):
        sys.exit()

    def h(self):
        print(self.help)

    def f(self):
        self.s.down()

    def n(self):
        self.s.hold()


def notify(st) -> None:
    # todo もっとかっこいい通知にしたい
    os.system(f"osascript -e 'display notification \"{st}\"'")


if __name__ == '__main__':
    Main().run()
