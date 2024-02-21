#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains functions and classes related with Houdini shelves
"""

import os
import json
from collections import OrderedDict

from tp.core import dcc
from tp.core.abstract import shelf

from tp.houdini.core import gui


class HoudiniShelf(shelf.AbstractShelf, object):

    def __init__(
            self, name='HoudiniShelf', label_background=(0, 0, 0, 0), label_color=(0.9, 0.9, 0.9), category_icon=None):
        super(HoudiniShelf, self).__init__(
            name=name, label_background=label_background, label_color=label_color, category_icon=category_icon)

        self.name = name
        self.label_background = label_background
        self.label_color = label_color

        self.category_btn = None
        self.category_menu = None

    def create(self, delete_if_exists=True):
        """
        Creates a new shelf
        """

        if delete_if_exists:
            if gui.shelf_set_exists(shelf_set_name=self.name):
                gui.remove_shelf_set(name=self.name)
        else:
            assert not gui.shelf_set_exists(
                shelf_set_name=self.name), 'Shelf Set with name {} already exists!'.format(self.name)

        gui.create_shelf_set(name=self.name, dock=True)

    def set_as_active(self, delete_if_exists=True):
        """
        Sets this shelf as active shelf in current DCC session
        """

        return

    def add_button(
            self, label, tooltip=None, icon='customIcon.png', command=None, double_command=None, command_type='python'):
        """
        Adds a shelf button width the given parameters
        :param label:
        :param tooltip:
        :param icon:
        :param command:
        :param double_command:
        :param command_type:
        :return:
        """

        return gui.create_shelf_tool(
            tool_name='{}_{}'.format(self.name, label),
            tool_label=label,
            tool_type=command_type,
            tool_script=command,
            icon=icon
        )

    def add_separator(self):
        """
        Adds a separator to shelf
        :param parent:
        :return:
        """

        return dcc.add_shelf_separator(shelf_name=self.name)

    def build_categories(self, shelf_file, categories):
        """
        Builds all categories given
        :param categories: list<str>, list of categories to build
        """

        all_shelves = list()
        for cat in categories:
            shelf_name = '{}_{}'.format(self.name, cat)
            if gui.shelf_exists(shelf_name=shelf_name):
                gui.remove_shelf(name=shelf_name)
            if not gui.shelf_exists(shelf_name=shelf_name):
                new_shelve = gui.create_shelf(shelf_name=shelf_name, shelf_label=cat.title())
                all_shelves.append(new_shelve)
        shelf_set = gui.get_shelf_set(shelf_set_name=self.name)
        if shelf_set and all_shelves:
            all_shelves.reverse()
            shelf_set.setShelves(all_shelves)

    def load_category(self, shelf_file, category_name, clear=True):
        """
        Loads into a shelf all the items of given category name, if exists
        :param category_name: str, name of the category
        """

        if clear:
            self.clear_list()

        with open(shelf_file) as f:
            shelf_data = json.load(f, object_pairs_hook=OrderedDict)

            for item, item_data in shelf_data.items():
                if item != category_name:
                    continue

                all_tools = list()
                for i in item_data:
                    annotation = i.get('annotation')
                    if annotation == 'separator':
                        continue
                    dcc = i.get('dcc')
                    if dcc.name() not in dcc:
                        continue
                    icon = os.path.join(self.ICONS_PATHS, i.get('icon'))
                    command = i.get('command')
                    label = i.get('label')
                    new_tool = self.add_button(label=label, command=command, icon=icon, tooltip=annotation)
                    if new_tool:
                        all_tools.append(new_tool)
                current_shelf = gui.get_shelf(shelf_name='{}_{}'.format(self.name, item))
                if current_shelf and all_tools:
                    current_shelf.setTools(all_tools)

    def build(self, shelf_file):
        """
        Builds shelf from JSON file
        :param shelf_file: str
        """

        with open(shelf_file) as f:
            shelf_data = json.load(f, object_pairs_hook=OrderedDict)

            self.build_categories(shelf_file=shelf_file, categories=shelf_data.keys())
            for i, item in enumerate(shelf_data.keys()):
                self.load_category(shelf_file, item, clear=False)
