# -*- coding: utf-8 -*-
#
# Auto Tab for gedit, automatically detect tab preferences for source files.
# Can be used together with the Modelines plugin without ill effect, modelines
# will take precedence.
#
# Copyright (C) 2007-2010 Kristoffer Lundén (kristoffer.lunden@gmail.com)
# Copyright (C) 2007 Lars Uebernickel (larsuebernickel@gmx.de)
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject, Gio, Gedit
import operator

# Main class
class AutoTab(GObject.Object, Gedit.WindowActivatable):
  __gtype_name__ = "AutoTab"

  window = GObject.property(type=Gedit.Window)
  
  def do_activate(self):
    self.spaces_instead_of_tabs = False
    self.tabs_width = 2

    settings = Gio.Settings("org.gnome.gedit.preferences.editor")
    
    self.new_tabs_size(settings)
    self.new_insert_spaces(settings)
    
    settings.connect("changed::tabs-size", self.new_tabs_size)
    settings.connect("changed::insert-spaces", self.new_insert_spaces)

    for view in self.window.get_views(): 
      self.connect_handlers(view)
      self.auto_tab(view.get_buffer(), view)

    tab_added_id = self.window.connect("tab_added", lambda w, t: self.connect_handlers(t.get_view()))
    self.window.AutoTabPluginHandlerId = tab_added_id

  def do_deactivate(self):
    self.window.disconnect(self.window.AutoTabPluginHandlerId)
    self.window.AutoTabPluginHandlerId = None

    for view in self.window.get_views():
      self.disconnect_handlers(view)


  def connect_handlers(self, view):
    doc = view.get_buffer()
    # Using connect_after() because we want other plugins to do their
    # thing first.
    loaded_id = doc.connect_after("loaded", self.auto_tab, view)
    saved_id  = doc.connect_after("saved", self.auto_tab, view)
    doc.AutoTabPluginHandlerIds = (loaded_id, saved_id)

  def disconnect_handlers(self, view):
    doc = view.get_buffer()
    loaded_id, saved_id = doc.AutoTabPluginHandlerIds
    doc.disconnect(loaded_id)
    doc.disconnect(saved_id)
    doc.AutoTabPluginHandlerIds = None

  # If default tab size changes
  def new_tabs_size(self, settings, key=None):
    self.tabs_width = settings.get_value("tabs-size").get_uint32()

  # If default space/tabs changes
  def new_insert_spaces(self, settings, key=None):
    self.spaces_instead_of_tabs = settings.get_boolean("insert-spaces")

  # Update the values and set a new statusbar message  
  def update_tabs(self, view, size, space):
    view.set_tab_width(size)
    view.set_insert_spaces_instead_of_tabs(space)

  # Main workhorse, identify what tabs we should use and use them.
  def auto_tab(self, doc, view):
    # Other plugins compatibility, other plugins can do
    # view.AutoTabSkip = True
    # and Auto Tab will skip that document as long as this value is true.
    if hasattr(view, 'AutoTabSkip') and view.AutoTabSkip:
      return

    # Special case for makefiles, so the plugin uses tabs even for the empty file:    
    if doc.get_mime_type() == "text/x-makefile" or doc.get_short_name_for_display() == "Makefile":
      self.update_tabs(view, self.tabs_width, False)
      return

    start, end = doc.get_bounds()

    if not end:
      return
    text = doc.get_text(start, end, True)

    # Special marker so all keys are ints
    TABS = 666

    # Needs to be ordered from largest to smallest
    indent_levels = (TABS, 8, 4, 3, 2)

    indent_count = {}
    for spaces in indent_levels:
      indent_count[spaces] = 0

    seen_tabs = 0
    seen_spaces = 0
    prev_indent = 0

    for line in text.splitlines():
      if len(line) == 0 or not line[0].isspace():
        prev_indent = 0
        continue

      if line[0] == '\t':
        indent_count[TABS] += 1
        prev_indent = 0
        seen_tabs += 1
        continue
      elif line[0] == ' ':
        seen_spaces += 1

      indent = 0
      for indent in range(0, len(line)):
        if line[indent] != ' ':
          break

      # First pass: indented exactly one step from the previous line?
      #             larger steps are favoured over smaller ones as
      #             they might be multiples of a smaller one
      for spaces in indent_levels:
        if spaces == TABS:
          continue

        if (indent % spaces) != 0:
          continue

        if abs(indent - prev_indent) != spaces:
          continue

        indent_count[spaces] += 1
        break
      else:
        # Second pass: indentation ambigious; add to all candidates
        for spaces in indent_levels:
          if spaces == TABS:
            continue

          if (indent % spaces) != 0:
            continue

          indent_count[spaces] += 1

      prev_indent = indent

    # no indentations detected
    if sum(indent_count.values()) == 0:
      # if we've seen tabs or spaces, default to those
      # can't guess at size, so using default
      if seen_tabs or seen_spaces:
        if seen_tabs > seen_spaces:
          self.update_tabs(view, self.tabs_width, False)
        else:
          self.update_tabs(view, self.tabs_width, True)
      return    

    # Since some indentation steps may be multiples of others, we
    # need to prioritise larger indentations when there is a tie.
    winner = None
    for key in indent_levels:
      if (winner is None) or (indent_count[key] > indent_count[winner]):
        winner = key

    if winner == TABS:
      self.update_tabs(view, self.tabs_width, False)
    else:
      self.update_tabs(view, winner, True)
