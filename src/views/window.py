# window.py
#
# Copyright 2023
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import time

from gi.repository import Gtk, Gio, Adw, GLib

from bavarder.constants import app_id, build_type, rootdir
from bavarder.widgets.thread_item import ThreadItem
from bavarder.widgets.item import Item
from bavarder.threading import KillableThread

class CustomEntry(Gtk.TextView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

@Gtk.Template(resource_path=f'{rootdir}/ui/window.ui')
class BavarderWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'BavarderWindow'

    split_view = Gtk.Template.Child()
    threads_list = Gtk.Template.Child()
    title = Gtk.Template.Child()

    main_list = Gtk.Template.Child()
    status_no_chat = Gtk.Template.Child()
    status_no_internet = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    local_mode_toggle = Gtk.Template.Child()
    provider_selector_button = Gtk.Template.Child()
    model_selector_button = Gtk.Template.Child()
    clear_all_button = Gtk.Template.Child()
    banner = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    main = Gtk.Template.Child()

    threads = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.app = Gtk.Application.get_default()
        self.settings = Gio.Settings(schema_id=app_id)

        CustomEntry.set_css_name("entry")
        self.message_entry = CustomEntry()
        self.message_entry.set_hexpand(True)
        self.message_entry.set_accepts_tab(False)
        self.message_entry.set_margin_start(5)
        self.message_entry.set_margin_end(5)
        self.message_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        self.message_entry.add_css_class("chat-entry")

        self.scrolled_window.set_child(self.message_entry)
        self.load_threads()

        self.local_mode_toggle.set_active(self.app.local_mode)

        self.on_local_mode_toggled(self.local_mode_toggle)

        self.create_action("cancel", self.cancel, ["<primary>Escape"])

        self.settings.bind(
            "width", self, "default-width", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "height", self, "default-height", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "is-maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "is-fullscreen", self, "fullscreened", Gio.SettingsBindFlags.DEFAULT
        )


    @property
    def chat(self):
        try:
            return self.threads_list.get_selected_row().get_child().chat
        except AttributeError: # create a new chat
            self.on_new_chat_action()
        finally:
            return self.threads_list.get_selected_row().get_child().chat

    @property
    def content(self):
        try:
            return self.chat["content"]
        except KeyError: # no content
            self.chat["content"] = []
        finally:
            return self.chat["content"]

    def load_threads(self):
        self.threads_list.remove_all()
        if self.app.data["chats"]:
            for chat in self.app.data["chats"]:
                thread = ThreadItem(self, chat)
                self.threads_list.append(thread)
                self.threads.append(thread)
                self.stack.set_visible_child(self.main)
        else:
            self.stack.set_visible_child(self.status_no_chat)

    @Gtk.Template.Callback()
    def threads_row_activated_cb(self, *args):
        self.split_view.set_collapsed(True)
        self.split_view.set_show_content(True)

        self.title.set_title(self.chat["title"])

        if self.content:
            self.stack.set_visible_child(self.main)
            self.main_list.remove_all()
            for item in self.content:
                i = Item(self, self.chat, item)
                self.main_list.append(i)
        else:
            self.stack.set_visible_child(self.status_no_chat)

    @Gtk.Template.Callback()
    def on_new_chat_action(self, *args):
        self.app.on_new_chat_action(_, _)

    # @Gtk.Template.Callback()
    # def scroll_down(self, *args):
    #     self.scrolled_window.emit("scroll-child", Gtk.ScrollType.END, False)

    @Gtk.Template.Callback()
    def on_clear_all(self, *args):
        if self.content:
            self.stack.set_visible_child(self.main)
            self.main_list.remove_all()
            del self.chat["content"]
        else:
            self.stack.set_visible_child(self.status_no_chat)

    # PROVIDER - ONLINE
    def load_provider_selector(self):
        provider_menu = Gio.Menu()

        for provider in self.app.providers.values():
            if provider.enabled:
                item_provider = Gio.MenuItem()
                item_provider.set_label(provider.name)
                item_provider.set_action_and_target_value(
                    "app.set_provider",
                    GLib.Variant("s", provider.slug))
                provider_menu.append_item(item_provider)
        else:
            item_provider = Gio.MenuItem()
            item_provider.set_label(_("Preferences"))
            item_provider.set_action_and_target_value("app.preferences", None)
            provider_menu.append_item(item_provider)

        self.provider_selector_button.set_menu_model(provider_menu)

    # MODEL - OFFLINE
    def load_model_selector(self):
        provider_menu = Gio.Menu()

        if not self.app.models:
            self.app.list_models()

        for provider in self.app.models:
            item_provider = Gio.MenuItem()
            item_provider.set_label(provider)
            item_provider.set_action_and_target_value(
                "app.set_model",
                GLib.Variant("s", provider))
            provider_menu.append_item(item_provider)
        else:
            item_provider = Gio.MenuItem()
            item_provider.set_label(_("Preferences"))
            item_provider.set_action_and_target_value("app.preferences", None)
            provider_menu.append_item(item_provider)

        self.model_selector_button.set_menu_model(provider_menu)

    @Gtk.Template.Callback()
    def on_local_mode_toggled(self, widget):
        self.app.local_mode = widget.get_active()

        if self.app.local_mode:
            self.local_mode_toggle.set_icon_name("cloud-disabled-symbolic")
            self.model_selector_button.set_visible(True)
            self.provider_selector_button.set_visible(False)
            self.clear_all_button.set_visible(False)
        else:
            self.local_mode_toggle.set_icon_name("cloud-filled-symbolic")
            self.provider_selector_button.set_visible(True)
            self.model_selector_button.set_visible(False)
            self.clear_all_button.set_visible(False)

    def check_network(self):
        if self.app.check_network(): # Internet
            if not self.content:
                self.status_no_chat.set_visible(True)
                self.status_no_internet.set_visible(False)
            else:
                self.status_no_chat.set_visible(False)
                self.status_no_internet.set_visible(False)
        else:
            self.status_no_chat.set_visible(False)
            self.status_no_internet.set_visible(True)



    @Gtk.Template.Callback()
    def on_ask(self, *args):
        if not self.threads: # no chat
            self.on_new_chat_action()
            self.threads_list.select_row(self.threads_list.get_row_at_index(0))

        prompt = self.message_entry.get_buffer().props.text.strip()
        if prompt:
            self.message_entry.get_buffer().set_text("")

            self.add_user_item(prompt)

            def thread_run():
                self.toast = Adw.Toast()
                self.toast.set_title(_("Generating response"))
                self.toast.set_button_label(_("Cancel"))
                self.toast.set_action_name("win.cancel")
                self.toast.set_timeout(0)
                self.toast_overlay.add_toast(self.toast)
                response = self.app.ask(prompt, self.chat)
                GLib.idle_add(cleanup, response, self.toast)

            def cleanup(response, toast):
                self.t.join()
                self.toast.dismiss()

                self.add_assistant_item(response)

            self.t = KillableThread(target=thread_run)
            self.t.start()

    def cancel(self, *args):
        try:
            self.t.kill()
            self.t.join()
            self.toast.dismiss()
        except AttributeError: # nothing to stop
            pass

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

        if shortcuts:
            self.app.set_accels_for_action(f"win.{name}", shortcuts)
        


    def add_user_item(self, content):
        self.content.append(
            {
                "role": "user",
                "content": content,
                "time": time.strftime("%X")
            }
        )

        self.threads_row_activated_cb()

    def add_assistant_item(self, content):
        c = {
                "role": "assistant",
                "content": content,
                "time": time.strftime("%X"),
            }

        if self.app.local_mode and self.app.model_name:
            c["model"] = self.app.model_name
        elif self.app.current_provider:
            c["model"] = self.app.current_provider
    
        
        self.content.append(c)

        self.threads_row_activated_cb()

