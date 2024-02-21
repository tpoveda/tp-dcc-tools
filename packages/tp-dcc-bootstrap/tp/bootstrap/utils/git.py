#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains custom GitPython wrappers and helper functions
"""

import os
import git

from tp.bootstrap import log

from tp.bootstrap.utils import process
from tp.bootstrap.core import exceptions

logger = log.bootstrapLogger


def has_git():
    """
    Returns whether current user has git installed in their machine.

    :return: True if git executable is installed; False otherwise.
    :rtype: bool
    """

    process.check_output(('git', '--version'))


class RepoChecker(object):
    def __init__(self, repo_path=None):
        self._repo = git.Repo(repo_path) if repo_path is not None else None
        self._repo_path = repo_path
        self._new_tag = None

    @property
    def repo_path(self):
        return self._repo_path

    @classmethod
    def clone(cls, repo_path, destination, **kwargs):
        repo = git.Repo.clone_from(repo_path, destination, **kwargs)
        wrapper = cls(os.path.dirname(repo.git_dir))

        return wrapper

    def assert_repo(self):
        assert not self._repo.bare
        if self._repo.is_dirty():
            raise exceptions.DirtyGitRepoError('Current repo has uncommited changes')
        if self._repo.active_branch.name not in ('master', 'main'):
            raise exceptions.IncorrectCurrentBranchError(
                f'Cannot release on branch: {self._repo.active_branch.name} only (master, main) are allowed!')

        return True

    def checkout(self, name):
        self._repo.git.checkout(name)

    def tags(self):
        return sorted(self._repo.tags, key=lambda t: t.commit.committed_datetime)

    def latest_tag(self):
        tags = sorted(self._repo.tags, key=lambda t: t.commit.committed_datetime)
        if not tags:
            logger.warning('no tags', tags)
        return tags[-1].name

    def pull_tags(self):
        self._repo.git.fetch('--tags')

    def create_tag(self, tag, message):
        logger.info(f'Creating tag {tag} with message: {message}')
        self._new_tag = self._repo.create_tag(tag, message=message)

    def push_tag(self):
        logger.info(f'Pushing next tag {self._new_tag}')
        if not self._new_tag:
            raise ValueError('No new tag has been created')
        self._repo.remotes.origin.push(self._new_tag)
        logger.info(f'Finished pushing tag {self._new_tag} to remote')

    def commit(self, message):
        logger.info(f'Commit to current branch with message: {message}')
        self._repo.git.add('--all')
        self._repo.git.commit('-m', message)

    def push_changes(self):
        logger.info('Pusing local changes')
        self._repo.git.push()

    def latest_commit_message(self):
        return self._repo.head.commit.message


class Commit(dict):

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return super(Commit, self).__getattribute__(item)
