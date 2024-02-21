import os
import cProfile
from functools import wraps

from tp.bootstrap import log

logger = log.bootstrapLogger


def profile(fn):
	"""
	Decorator function that allows to profile a function and write that information into disk.

	:param callable fn: decorated function.
	"""

	profile_flag = int(os.environ.get('TPDCC_PROFILE', '0'))
	profile_export_path = os.path.expandvars(os.path.expanduser(os.environ.get('TPDCC_PROFILE_PATH', '')))
	should_profile = True if profile_flag and profile_export_path else False

	@wraps(fn)
	def inner(*args, **kwargs):
		if not should_profile:
			return fn(*args, **kwargs)
		logger.debug(f'Running profile output to: {profile_export_path}')
		prof = cProfile.Profile()
		result = prof.runcall(fn)
		prof.dump_stats(profile_export_path)
		return result

	return inner
