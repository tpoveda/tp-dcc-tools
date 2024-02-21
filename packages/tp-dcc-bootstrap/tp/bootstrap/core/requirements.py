import re

REQ_PIP_TYPE = 0
PIP_REQ_REGEX = re.compile("(.*)==(.*)")


def parse_requirements_file(file_path):
	"""
	Parses given requirement file and returns a RequirementList instance.

	:param str file_path: aboslute file path pointing to a valid requirements file.
	:return: parsed requirements file.
	:rtype: RequirementsList
	"""

	requirements = RequirementsList()
	with open(file_path, 'r') as f:
		for line in f.readlines():
			line = line.strip()
			if not line:
				continue
			requirements.append(Requirement.from_line(line))

	return requirements


class Requirement:
	def __init__(self, line):
		super().__init__()

		self._line = line
		self._version = ''
		self._type = REQ_PIP_TYPE
		self._name = ''
		self._valid = False

	def __repr__(self):
		return f'<Requirement: {self._line}>'

	def __str__(self):
		return self._line

	def __eq__(self, other):
		return self._line == other.line

	def __hash__(self):
		return hash(f'{self._name}=={self._version}')

	@property
	def line(self):
		return self._line

	@property
	def version(self):
		return self._version

	@version.setter
	def version(self, value):
		self._version = value

	@property
	def type(self):
		return self._type

	@property
	def name(self):
		return self._name

	@name.setter
	def name(self, value):
		self._name = value

	@property
	def valid(self):
		return self._valid

	@valid.setter
	def valid(self, flag):
		self._valid = flag

	@classmethod
	def from_line(cls, line):
		"""
		Creates a new requirement instance based on given line.

		:param str line: requirement line.
		:return: requirement instance.
		:rtype: Requirement
		"""

		req = cls(line)
		pip_requires = PIP_REQ_REGEX.match(line)
		if pip_requires is not None:
			req.name, req.version = list(pip_requires.groups())
		else:
			req.name = line
		req.valid = True

		return req


class RequirementsList:
	def __init__(self, requirements=None):
		super().__init__()

		self._requirements = requirements or list()
		self._requirements_dict = dict()

	def __bool__(self):
		return len(self._requirements) > 0

	def __iter__(self):
		return iter(self._requirements)

	def append(self, requirement):
		if requirement in self._requirements:
			return
		self._requirements.append(requirement)

	def extend(self, requirements):
		to_extend = [i for i in requirements if i not in self._requirements]
		self._requirements.extend(to_extend)
		self._requirements_dict.update({i: i for i in to_extend})
